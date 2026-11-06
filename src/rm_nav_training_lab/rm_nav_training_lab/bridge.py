"""Small ROS action gateway for browser clients using rosbridge services/topics."""

import json

import rclpy
from action_msgs.msg import GoalStatus, GoalStatusArray
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import OccupancyGrid
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_action_status_default
from rclpy.task import Future
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener, TransformException
from tf2_msgs.msg import TFMessage
from std_msgs.msg import Empty, String
from lifecycle_msgs.srv import GetState


class TrainingBridge(Node):
    def __init__(self):
        super().__init__('training_bridge')
        self.declare_parameter('runtime_mode', 'unknown')
        self.runtime_pub = self.create_publisher(String, '/training/runtime_status', 10)
        self.lifecycle_states = {}
        self.lifecycle_pending = set()
        self.lifecycle_clients = {name: self.create_client(GetState, '/'+name+'/get_state') for name in ('bt_navigator','planner_server','controller_server')}
        self.goal_pending = False
        self.cancel_requested = False
        self.status_cache = None
        self.action_statuses = []
        self.create_subscription(GoalStatusArray, '/navigate_to_pose/_action/status', self._on_action_statuses, qos_profile_action_status_default)
        self.navigation_status_pub = self.create_publisher(String, '/training/navigation_status', 10)
        self.events_pub = self.create_publisher(String, '/training/events', 10)
        self.nodes_pub = self.create_publisher(String, '/training/node_status', 10)
        self.map_relay_pub = self.create_publisher(OccupancyGrid, '/training/map', 10)
        self.create_subscription(PoseStamped, '/training/navigate_to_pose', self._on_goal, 10)
        self.create_subscription(Empty, '/training/cancel_navigation', self._on_cancel, 10)
        map_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(OccupancyGrid, '/map', self._on_map, map_qos)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.tf_pub = self.create_publisher(TFMessage, '/training/tf', 10)
        self.create_timer(.1, self._relay_tf)
        self.map_cache = None
        self.create_timer(1.0, self._republish_map)
        self.create_timer(2.0, self._publish_node_graph)
        self.nav_client = ActionClient(self, NavigateToPose, '/navigate_to_pose')
        self.active_goal = None
        self.create_timer(1.0, self._publish_runtime)
        self._status('READY', 'Action gateway started; waiting for a NavigateToPose request.')
        self.get_logger().info('ROS action gateway ready; browser goals are forwarded to /navigate_to_pose.')

    def _on_action_statuses(self, msg):
        self.action_statuses = [item.status for item in msg.status_list]

    def _navigation_ready(self):
        if not self.nav_client.server_is_ready():
            return False
        if not all(self.lifecycle_states.get(name) == 3 for name in self.lifecycle_clients):
            return False
        try:
            tf = self.tf_buffer.lookup_transform('map', 'base_link', Time())
            now = self.get_clock().now()
            age = (now-Time.from_msg(tf.header.stamp, clock_type=now.clock_type)).nanoseconds/1e9
            return age < 2.5 and self.map_cache is not None
        except TransformException:
            return False

    def _publish_runtime(self):
        for name, client in self.lifecycle_clients.items():
            if not client.service_is_ready():
                self.lifecycle_states.pop(name, None)
                continue
            if name not in self.lifecycle_pending:
                self.lifecycle_pending.add(name)
                def done(future, name=name):
                    self.lifecycle_pending.discard(name)
                    try:
                        self.lifecycle_states[name] = future.result().current_state.id
                    except Exception:
                        self.lifecycle_states.pop(name, None)
                client.call_async(GetState.Request()).add_done_callback(done)
        mode = self.get_parameter('runtime_mode').value
        ready = self._navigation_ready()
        detail = ('导航已就绪：点击空白区域选择目标，再点击开始导航' if ready else
                  '定位体验：用 W/A/S/D 移动，Q/E 旋转；定位偏差时拖动初始位姿箭头，观察激光与墙体是否重合' if mode == 'localization' else
                  '仅仿真模式没有 Nav2，不能自主导航。请停止当前 Launch，启动 known_map.launch.py' if mode == 'sim' else
                  '正在等待 Nav2 激活、地图和有效 TF；请查看诊断面板')
        msg = String()
        msg.data = json.dumps({'mode': mode, 'ros_domain_id': self.context.get_domain_id(), 'navigation_ready': ready,
            'active_goal_count': sum(status in (1,2,3) for status in self.action_statuses),
            'action_available': self.nav_client.server_is_ready(), 'lifecycle_states': self.lifecycle_states, 'detail': detail})
        self.runtime_pub.publish(msg)
        if self.status_cache:
            self.navigation_status_pub.publish(self.status_cache)

    def _relay_tf(self):
        transforms = []
        for parent, child in [('map','odom'),('odom','base_link'),('base_link','laser_frame')]:
            try:
                transforms.append(self.tf_buffer.lookup_transform(parent, child, Time()))
            except TransformException:
                pass
        if transforms:
            self.tf_pub.publish(TFMessage(transforms=transforms))

    def _status(self, state, detail):
        msg = String()
        msg.data = json.dumps({'state': state, 'detail': detail})
        self.status_cache = msg
        self.navigation_status_pub.publish(msg)
        self._event(f'Navigation {state}: {detail}')

    def _event(self, text):
        msg = String()
        msg.data = json.dumps({'source': 'training_bridge', 'message': text})
        self.events_pub.publish(msg)
        self.get_logger().info(text)

    def _on_map(self, msg):
        self.map_cache = msg

    def _republish_map(self):
        if self.map_cache is not None:
            self.map_relay_pub.publish(self.map_cache)

    def _publish_node_graph(self):
        nodes = sorted(f'{namespace.rstrip("/")}/{name}'.replace('//', '/')
                       for name, namespace in self.get_node_names_and_namespaces())
        msg = String()
        msg.data = json.dumps({'nodes': nodes, 'topics': [{'name': name, 'types': types, 'publishers': self.count_publishers(name), 'subscribers': self.count_subscribers(name)} for name, types in self.get_topic_names_and_types()]})
        self.nodes_pub.publish(msg)

    def _on_goal(self, goal):
        if not goal.header.frame_id:
            goal.header.frame_id = 'map'
        if self.goal_pending or self.active_goal is not None:
            self._event('已有导航任务，请先取消或等待完成，再发送新目标。')
            return
        if not self._navigation_ready():
            self._status('UNAVAILABLE', 'Nav2 /navigate_to_pose action server is not available.')
            self.get_logger().warning('Rejected browser request: Nav2 action server is unavailable.')
            return
        request = NavigateToPose.Goal()
        request.pose = goal
        self._status('SENDING', f"Sending goal ({goal.pose.position.x:.2f}, {goal.pose.position.y:.2f}) in {goal.header.frame_id}.")
        self.goal_pending = True
        self.cancel_requested = False
        goal.header.stamp = self.get_clock().now().to_msg()
        future = self.nav_client.send_goal_async(request, feedback_callback=self._on_feedback)
        future.add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future: Future):
        self.goal_pending = False
        try:
            handle = future.result()
        except Exception as exc:  # surfaced to the UI instead of reporting success
            self._status('ERROR', f'Nav2 rejected the action request: {exc}')
            return
        if not handle.accepted:
            self.active_goal = None
            self._status('REJECTED', 'Nav2 rejected the goal.')
            return
        self.active_goal = handle
        self._status('ACCEPTED', 'Nav2 accepted the goal and is executing it.')
        handle.get_result_async().add_done_callback(self._on_result)
        if self.cancel_requested:
            self._on_cancel(None)

    def _on_feedback(self, feedback_message):
        distance = getattr(feedback_message.feedback, 'distance_remaining', None)
        if distance is not None:
            msg = String()
            feedback = feedback_message.feedback
            eta = feedback.estimated_time_remaining
            elapsed = feedback.navigation_time
            msg.data = json.dumps({'state': 'ACTIVE', 'distance_remaining': float(distance),
                'estimated_time_remaining': eta.sec + eta.nanosec/1e9,
                'navigation_time': elapsed.sec + elapsed.nanosec/1e9,
                'number_of_recoveries': int(feedback.number_of_recoveries)})
            self.status_cache = msg
            self.navigation_status_pub.publish(msg)

    def _on_result(self, future: Future):
        try:
            wrapped = future.result()
        except Exception as exc:
            self._status('ERROR', f'Navigation result could not be read: {exc}')
            self.active_goal = None
            return
        if wrapped.status == GoalStatus.STATUS_SUCCEEDED:
            state = 'SUCCEEDED'
        elif wrapped.status == GoalStatus.STATUS_CANCELED:
            state = 'CANCELED'
        else:
            state = 'FAILED'
        self._status(state, f'Nav2 action finished with goal status {wrapped.status}.')
        self.active_goal = None

    def _on_cancel(self, _msg):
        if self.goal_pending:
            self.cancel_requested = True
            return
        if self.active_goal is None:
            self._status('IDLE', 'Cancel requested; no active goal is recorded by the bridge.')
            return
        future = self.active_goal.cancel_goal_async()
        future.add_done_callback(self._on_cancel_result)

    def _on_cancel_result(self, future: Future):
        try:
            response = future.result()
            count = len(response.goals_canceling)
            self._status('CANCEL_REQUESTED', f'Nav2 accepted cancellation for {count} goal(s).')
        except Exception as exc:
            self._status('ERROR', f'Nav2 cancellation call failed: {exc}')


def main(args=None):
    rclpy.init(args=args)
    node = TrainingBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
