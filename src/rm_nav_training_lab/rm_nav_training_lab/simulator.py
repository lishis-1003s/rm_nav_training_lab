"""Lightweight holonomic simulator that publishes normal ROS messages."""

import json
import copy
import math
import random
import time
from pathlib import Path

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import TransformStamped, Twist, PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid, Odometry
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from std_srvs.srv import Trigger
from visualization_msgs.msg import Marker
from tf2_ros import StaticTransformBroadcaster, TransformBroadcaster


def quaternion_from_yaw(yaw):
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


def find_spawn(width, height, resolution, origin, cells, radius):
    def clear(x, y):
        for row in range(math.floor((y-radius-origin[1])/resolution), math.floor((y+radius-origin[1])/resolution)+1):
            for col in range(math.floor((x-radius-origin[0])/resolution), math.floor((x+radius-origin[0])/resolution)+1):
                left, bottom = origin[0]+col*resolution, origin[1]+row*resolution
                nx, ny = max(left,min(x,left+resolution)), max(bottom,min(y,bottom+resolution))
                if math.hypot(nx-x,ny-y) <= radius:
                    if not (0 <= col < width and 0 <= row < height) or cells[row*width+col] != 0:
                        return False
        return True
    if clear(-4.5, -4.5):
        return -4.5, -4.5
    for row in range(height):
        for col in range(width):
            x, y = origin[0]+(col+.5)*resolution, origin[1]+(row+.5)*resolution
            if clear(x, y):
                return x, y
    raise ValueError('Map has no free spawn for robot radius')


class TrainingSimulator(Node):
    """A deterministic map and a small ray-cast robot sim for Nav2 exercises."""

    def __init__(self):
        super().__init__('training_simulator')
        self.declare_parameter('robot_radius', 0.3)
        self.declare_parameter('map', '')
        self.declare_parameter('publish_map', True)
        self.declare_parameter('publish_map_to_odom', True)
        self.declare_parameter('rate_hz', 20.0)
        self.declare_parameter('scan_rate_hz', 10.0)
        share = Path(get_package_share_directory('rm_nav_training_lab'))
        self.map_path = Path(self.get_parameter('map').value or share / 'maps' / 'training_map.yaml')
        self.robot_radius = float(self.get_parameter('robot_radius').value)
        if not 0.05 <= self.robot_radius <= 1.0:
            raise ValueError('robot_radius must be between 0.05 and 1.0 m')
        self.obstacles = {}
        self.publish_map_to_odom = bool(self.get_parameter('publish_map_to_odom').value)
        self.map_width, self.map_height, self.map_resolution, self.map_origin, self.map_cells = self._load_pgm(self.map_path)

        transient_map_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.map_pub = self.create_publisher(OccupancyGrid, '/map', transient_map_qos)
        self.body_pub = self.create_publisher(Marker, '/training/robot_body', 10)
        self.scan_pub = self.create_publisher(LaserScan, '/scan', 10)
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.fault_pub = self.create_publisher(String, '/training/fault_state', 10)
        self.event_pub = self.create_publisher(String, '/training/events', 10)
        self.applied_cmd_pub = self.create_publisher(Twist, '/training/sim_cmd_vel', 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.static_tf_broadcaster = StaticTransformBroadcaster(self)

        self.create_subscription(Twist, '/cmd_vel', self._on_nav_cmd, 10)
        self.create_subscription(Twist, '/cmd_vel_explore', self._on_explore_cmd, 10)
        self.create_subscription(String, '/training/fault_command', self._on_fault_command, 10)
        self.create_subscription(String, '/training/obstacle_command', self._on_obstacle, 10)

        # The simulator's world coordinates match the fixed training map. In known-map
        # mode AMCL owns map->odom; in sim-only mode we publish the identity transform.
        self.x, self.y = self._spawn()
        self.yaw = 0.0
        self.odom_x = self.x
        self.odom_y = self.y
        self.odom_yaw = self.yaw
        self.faults = {
            'scan_outage': False,
            'tf_perturbation': False,
            'odometry_noise': False,
            'dynamic_obstacle': False,
            'base_stuck': False,
        }
        self.nav_cmd = (0.0, 0.0, 0.0)
        self.nav_cmd_time = 0.0
        self.explore_cmd = (0.0, 0.0, 0.0)
        self.explore_cmd_time = 0.0
        self.last_tick = time.monotonic()
        self.started = self.last_tick
        self.scan_count = 360
        self.scan_max_range = 8.0
        self.checkpoint = None
        self.initial_pose_pub = self.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
        self.create_service(Trigger, '/training/capture_start', self._capture_start)
        self.create_service(Trigger, '/training/restore_start', self._restore_start)
        self.rng = random.Random(7)
        self.map_message = self._make_map_message()

        self._publish_static_laser_tf()

        update_period = 1.0 / max(float(self.get_parameter('rate_hz').value), 1.0)
        scan_period = 1.0 / max(float(self.get_parameter('scan_rate_hz').value), 1.0)
        self.create_timer(update_period, self._tick)
        self.create_timer(scan_period, self._publish_scan)
        self.create_timer(1.0, self._publish_map_if_enabled)
        self.create_timer(1.0, self._publish_fault_state)
        self.get_logger().info('2D training simulator ready; publishes /odom, /scan and odom->base_link.')

    @staticmethod
    def _load_pgm(path):
        import yaml
        from PIL import Image
        metadata = yaml.safe_load(path.read_text())
        if metadata.get('mode', 'trinary') != 'trinary':
            raise ValueError('Only trinary map mode is supported')
        image_path = Path(metadata['image'])
        if not image_path.is_absolute():
            image_path = path.parent / image_path
        resolution = float(metadata['resolution'])
        origin = metadata['origin']
        if resolution <= 0 or abs(float(origin[2])) > 1e-8:
            raise ValueError('Map resolution must be positive; rotated map origins are unsupported')
        if image_path.read_bytes()[:2] == b'P2':
            tokens = []
            for line in image_path.read_text().splitlines():
                tokens.extend(line.split('#', 1)[0].split())
            width, height, maximum = map(int, tokens[1:4])
            values = [round(int(v)*255/maximum) for v in tokens[4:]]
            if len(values) != width*height:
                raise ValueError('Invalid ASCII PGM dimensions')
            image = Image.new('L', (width, height))
            image.putdata(values)
        else:
            image = Image.open(image_path).convert('L')
        width, height = image.size
        occupied = float(metadata.get('occupied_thresh', .65))
        free = float(metadata.get('free_thresh', .25))
        if not 0 <= free < occupied <= 1:
            raise ValueError('Map thresholds must satisfy 0 <= free < occupied <= 1')
        negate = bool(metadata.get('negate', 0))
        cells = []
        for y in range(height - 1, -1, -1):
            for x in range(width):
                value = image.getpixel((x, y)) / 255.0
                probability = value if negate else 1 - value
                cells.append(100 if probability > occupied else 0 if probability < free else -1)
        return width, height, resolution, tuple(origin[:2]), cells

    def _make_map_message(self):
        msg = OccupancyGrid()
        msg.header.frame_id = 'map'
        msg.info.resolution = self.map_resolution
        msg.info.width = self.map_width
        msg.info.height = self.map_height
        msg.info.origin.position.x = self.map_origin[0]
        msg.info.origin.position.y = self.map_origin[1]
        msg.info.origin.orientation.w = 1.0
        msg.data = self.map_cells
        return msg

    def _publish_map_if_enabled(self):
        if self.get_parameter('publish_map').value:
            self.map_message.header.stamp = self.get_clock().now().to_msg()
            self.map_pub.publish(self.map_message)

    def _publish_map_to_odom(self):
        tf = TransformStamped()
        tf.header.stamp = self.get_clock().now().to_msg()
        tf.header.frame_id = 'map'
        tf.child_frame_id = 'odom'
        tf.transform.rotation.w = 1.0
        self.tf_broadcaster.sendTransform(tf)

    def _publish_static_laser_tf(self):
        tf = TransformStamped()
        tf.header.stamp = self.get_clock().now().to_msg()
        tf.header.frame_id = 'base_link'
        tf.child_frame_id = 'laser_frame'
        tf.transform.translation.x = 0.18
        tf.transform.translation.z = 0.12
        tf.transform.rotation.w = 1.0
        self.static_tf_broadcaster.sendTransform(tf)

    def _on_nav_cmd(self, msg):
        self.nav_cmd = (msg.linear.x, msg.linear.y, msg.angular.z)
        self.nav_cmd_time = time.monotonic()

    def _on_explore_cmd(self, msg):
        self.explore_cmd = (msg.linear.x, msg.linear.y, msg.angular.z)
        self.explore_cmd_time = time.monotonic()

    def _on_fault_command(self, msg):
        try:
            command = json.loads(msg.data)
        except (TypeError, json.JSONDecodeError):
            self._event('Fault command ignored: expected a JSON object.')
            return
        if command.get('reset') is True:
            for name in self.faults:
                self.faults[name] = False
            self._event('All simulation faults reset by command.')
        else:
            name = command.get('fault')
            if name not in self.faults or not isinstance(command.get('enabled'), bool):
                self._event('Fault command ignored: unknown fault or missing boolean enabled value.')
                return
            self.faults[name] = command['enabled']
            self._event(f"Fault '{name}' set to {str(command['enabled']).lower()} in the simulator.")
        self._publish_fault_state()

    def _publish_fault_state(self):
        msg = String()
        msg.data = json.dumps({'faults': self.faults, 'robot_radius': self.robot_radius, 'obstacles': self.obstacles}, sort_keys=True)
        self.fault_pub.publish(msg)

    def _event(self, text):
        msg = String()
        msg.data = json.dumps({'source': 'training_simulator', 'message': text})
        self.event_pub.publish(msg)
        self.get_logger().info(text)

    def _spawn(self):
        return find_spawn(self.map_width, self.map_height, self.map_resolution,
                          self.map_origin, self.map_cells, self.robot_radius)

    def _on_obstacle(self, msg):
        try:
            c = json.loads(msg.data)
            action = c.get('action')
            if action == 'clear':
                self.obstacles.clear()
            elif action == 'remove':
                self.obstacles.pop(str(c['id']), None)
            elif action == 'add':
                x, y, radius = float(c['x']), float(c['y']), float(c.get('radius', .3))
                if not all(math.isfinite(v) for v in (x, y, radius)) or not .05 <= radius <= 2 or not self._inside_map(x, y):
                    raise ValueError('Invalid obstacle position or radius')
                if math.hypot(x-self.x, y-self.y) <= radius+self.robot_radius:
                    raise ValueError('Obstacle overlaps robot')
                self.obstacles[str(c['id'])] = dict(x=x, y=y, radius=radius)
            else:
                raise ValueError('Unknown obstacle operation')
            self._publish_fault_state()
        except (ValueError, KeyError, TypeError) as exc:
            self._event(f'Obstacle rejected: {exc}')

    def _clear_body(self, x, y):
        # Test grid cells intersecting the circular body, not only its center.
        r, res = self.robot_radius, self.map_resolution
        min_col = math.floor((x-r-self.map_origin[0])/res)
        max_col = math.floor((x+r-self.map_origin[0])/res)
        min_row = math.floor((y-r-self.map_origin[1])/res)
        max_row = math.floor((y+r-self.map_origin[1])/res)
        for row in range(min_row, max_row+1):
            for col in range(min_col, max_col+1):
                left, bottom = self.map_origin[0]+col*res, self.map_origin[1]+row*res
                nx, ny = max(left,min(x,left+res)), max(bottom,min(y,bottom+res))
                if math.hypot(nx-x,ny-y) <= r and self._occupied(left+res/2,bottom+res/2):
                    return False
        for o in self.obstacles.values():
            if math.hypot(x-o['x'],y-o['y']) <= r+o['radius']:
                return False
        return True

    def _inside_map(self, x, y):
        col = math.floor((x - self.map_origin[0]) / self.map_resolution)
        row = math.floor((y - self.map_origin[1]) / self.map_resolution)
        return 0 <= col < self.map_width and 0 <= row < self.map_height

    def _occupied(self, x, y):
        col = math.floor((x - self.map_origin[0]) / self.map_resolution)
        row = math.floor((y - self.map_origin[1]) / self.map_resolution)
        if col < 0 or row < 0 or col >= self.map_width or row >= self.map_height:
            return True
        if self.map_cells[row * self.map_width + col] != 0:
            return True
        if any(math.hypot(x-o['x'], y-o['y']) <= o['radius'] for o in self.obstacles.values()):
            return True
        if getattr(self, 'faults', {}).get('dynamic_obstacle', False):
            t = time.monotonic() - self.started
            obstacle_x = 0.6 + 0.7 * math.sin(t * 0.35)
            obstacle_y = 0.2
            if math.hypot(x - obstacle_x, y - obstacle_y) <= 0.28:
                return True
        return False

    def _capture_start(self, request, response):
        self.checkpoint = dict(x=self.x, y=self.y, yaw=self.yaw, obstacles=copy.deepcopy(self.obstacles))
        response.success = True
        response.message = json.dumps(self.checkpoint)
        return response

    def _restore_start(self, request, response):
        if self.checkpoint is None:
            response.success = False
            response.message = '请先保存对比起点与障碍布局'
            return response
        p = self.checkpoint
        self.x = self.odom_x = p['x']
        self.y = self.odom_y = p['y']
        self.yaw = self.odom_yaw = p['yaw']
        self.obstacles = copy.deepcopy(p['obstacles'])
        self.nav_cmd = self.explore_cmd = (0.0, 0.0, 0.0)
        self.nav_cmd_time = self.explore_cmd_time = 0.0
        self._publish_odom_and_tf(0.0, 0.0, 0.0)
        initial = PoseWithCovarianceStamped()
        initial.header.frame_id = 'map'
        initial.header.stamp = self.get_clock().now().to_msg()
        initial.pose.pose.position.x, initial.pose.pose.position.y = self.x, self.y
        q = initial.pose.pose.orientation
        q.x, q.y, q.z, q.w = quaternion_from_yaw(self.yaw)
        initial.pose.covariance[0] = initial.pose.covariance[7] = .0004
        initial.pose.covariance[35] = .0001
        self.initial_pose_pub.publish(initial)
        self._publish_fault_state()
        response.success = True
        response.message = json.dumps(p)
        return response

    def _selected_command(self, now):
        if now - self.explore_cmd_time < 0.5:
            return self.explore_cmd
        if now - self.nav_cmd_time < 0.5:
            return self.nav_cmd
        return (0.0, 0.0, 0.0)

    def _tick(self):
        now = time.monotonic()
        dt = min(max(now - self.last_tick, 0.0), 0.1)
        self.last_tick = now
        vx, vy, wz = self._selected_command(now)
        if self.faults['base_stuck']:
            vx, vy, wz = 0.0, 0.0, 0.0
        next_yaw = self.yaw + wz * dt
        next_x = self.x + (vx * math.cos(next_yaw) - vy * math.sin(next_yaw)) * dt
        next_y = self.y + (vx * math.sin(next_yaw) + vy * math.cos(next_yaw)) * dt
        steps = max(1, math.ceil(math.hypot(next_x-self.x,next_y-self.y)/(self.map_resolution*.5)))
        if all(self._clear_body(self.x+(next_x-self.x)*i/steps, self.y+(next_y-self.y)*i/steps) for i in range(1,steps+1)):
            self.x, self.y = next_x, next_y
        else:
            vx, vy = 0.0, 0.0
        self.yaw = math.atan2(math.sin(next_yaw), math.cos(next_yaw))

        if self.faults['odometry_noise']:
            self.odom_x += (vx * math.cos(self.odom_yaw) - vy * math.sin(self.odom_yaw)) * dt + self.rng.gauss(0.0, 0.025)
            self.odom_y += (vx * math.sin(self.odom_yaw) + vy * math.cos(self.odom_yaw)) * dt + self.rng.gauss(0.0, 0.025)
            self.odom_yaw += wz * dt + self.rng.gauss(0.0, 0.012)
        else:
            self.odom_x, self.odom_y, self.odom_yaw = self.x, self.y, self.yaw

        applied = Twist()
        applied.linear.x = vx
        applied.linear.y = vy
        applied.angular.z = wz
        self.applied_cmd_pub.publish(applied)
        body = Marker()
        body.header.frame_id = 'base_link'
        body.header.stamp = self.get_clock().now().to_msg()
        body.ns = 'circular_chassis'
        body.id = 0
        body.type = Marker.CYLINDER
        body.action = Marker.ADD
        body.pose.orientation.w = 1.0
        body.pose.position.z = .04
        body.scale.x = body.scale.y = self.robot_radius*2
        body.scale.z = .08
        body.color.r, body.color.g, body.color.b, body.color.a = .56, .89, .42, 1.0
        self.body_pub.publish(body)
        self._publish_odom_and_tf(vx, vy, wz)
        if self.publish_map_to_odom:
            self._publish_map_to_odom()

    def _publish_odom_and_tf(self, applied_vx, applied_vy, applied_wz):
        now = self.get_clock().now().to_msg()
        x, y, yaw = self.odom_x, self.odom_y, self.odom_yaw
        if self.faults['tf_perturbation']:
            x += 0.65
            yaw += 0.30
        qx, qy, qz, qw = quaternion_from_yaw(self.odom_yaw)
        odom = Odometry()
        odom.header.stamp = now
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self.odom_x
        odom.pose.pose.position.y = self.odom_y
        odom.pose.pose.orientation.x = qx
        odom.pose.pose.orientation.y = qy
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = applied_vx
        odom.twist.twist.linear.y = applied_vy
        odom.twist.twist.angular.z = applied_wz
        odom.pose.covariance[0] = 0.04 if self.faults['odometry_noise'] else 0.01
        odom.pose.covariance[7] = 0.04 if self.faults['odometry_noise'] else 0.01
        odom.pose.covariance[35] = 0.08 if self.faults['odometry_noise'] else 0.02
        self.odom_pub.publish(odom)

        tf = TransformStamped()
        tf.header.stamp = now
        tf.header.frame_id = 'odom'
        tf.child_frame_id = 'base_link'
        tf.transform.translation.x = x
        tf.transform.translation.y = y
        tf.transform.rotation.x, tf.transform.rotation.y, tf.transform.rotation.z, tf.transform.rotation.w = quaternion_from_yaw(yaw)
        self.tf_broadcaster.sendTransform(tf)

    def _publish_scan(self):
        if self.faults['scan_outage']:
            return
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'laser_frame'
        msg.angle_min = -math.pi
        msg.angle_max = math.pi - (2.0 * math.pi / self.scan_count)
        msg.angle_increment = 2.0 * math.pi / self.scan_count
        msg.time_increment = 0.0
        msg.scan_time = 0.1
        msg.range_min = 0.1
        msg.range_max = self.scan_max_range
        laser_x = self.x + 0.18 * math.cos(self.yaw)
        laser_y = self.y + 0.18 * math.sin(self.yaw)
        ranges = []
        for index in range(self.scan_count):
            angle = self.yaw + msg.angle_min + index * msg.angle_increment
            distance = msg.range_min
            while distance < self.scan_max_range:
                ray_x = laser_x + distance * math.cos(angle)
                ray_y = laser_y + distance * math.sin(angle)
                if self._occupied(ray_x, ray_y):
                    break
                distance += 0.05
            ranges.append(min(distance, self.scan_max_range))
        msg.ranges = ranges
        self.scan_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = TrainingSimulator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
