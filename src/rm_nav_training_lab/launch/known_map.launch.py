import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from rm_nav_training_lab.launch_utils import check_ports
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, SetEnvironmentVariable, OpaqueFunction, SetLaunchConfiguration
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory('rm_nav_training_lab')
    nav2_share = get_package_share_directory('nav2_bringup')
    map_path = LaunchConfiguration('map')
    from nav2_common.launch import RewrittenYaml
    params_path = RewrittenYaml(source_file=LaunchConfiguration('params_file'), param_rewrites={'robot_radius': LaunchConfiguration('robot_radius'), 'amcl.ros__parameters.initial_pose.x': LaunchConfiguration('spawn_x'), 'amcl.ros__parameters.initial_pose.y': LaunchConfiguration('spawn_y')}, convert_types=True)
    web_port = LaunchConfiguration('web_port')
    rosbridge_port = LaunchConfiguration('rosbridge_port')
    rviz = LaunchConfiguration('rviz')
    ros_domain_id = LaunchConfiguration('ros_domain_id')
    default_map = os.path.join(share, 'maps', 'rmul2026_3v3.yaml')
    default_params = os.path.join(share, 'config', 'nav2_params.yaml')
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2_share, 'launch', 'bringup_launch.py')),
        launch_arguments={
            'map': map_path,
            'params_file': params_path,
            'use_sim_time': 'False',
            'autostart': 'True',
            'use_composition': 'False',
            'slam': 'False',
        }.items(),
    )
    def configure_spawn(context):
        from pathlib import Path
        from rm_nav_training_lab.simulator import TrainingSimulator, find_spawn
        data = TrainingSimulator._load_pgm(Path(LaunchConfiguration('map').perform(context)))
        x, y = find_spawn(*data, float(LaunchConfiguration('robot_radius').perform(context)))
        return [SetLaunchConfiguration('spawn_x', str(x)), SetLaunchConfiguration('spawn_y', str(y))]

    return LaunchDescription([
        DeclareLaunchArgument('ros_domain_id', default_value=os.environ.get('ROS_DOMAIN_ID', '0')),
        DeclareLaunchArgument('map', default_value=default_map),
        DeclareLaunchArgument('params_file', default_value=default_params),
        DeclareLaunchArgument('web_port', default_value='8080'),
        DeclareLaunchArgument('serve_web', default_value='True'),
        DeclareLaunchArgument('robot_radius', default_value='0.3'),
        DeclareLaunchArgument('rosbridge_port', default_value='9090'),
        DeclareLaunchArgument('rviz', default_value='True'),
        SetEnvironmentVariable('ROS_DOMAIN_ID', ros_domain_id),
        OpaqueFunction(function=check_ports),
        Node(package='rm_nav_training_lab', executable='training_simulator', output='screen',
             parameters=[{'map': LaunchConfiguration('map'), 'robot_radius': ParameterValue(LaunchConfiguration('robot_radius'), value_type=float), 'publish_map': False, 'publish_map_to_odom': False}]),
        OpaqueFunction(function=configure_spawn),
        nav2,
        Node(package='rm_nav_training_lab', executable='training_bridge', output='screen', parameters=[{'runtime_mode': 'navigation'}]),
        Node(package='rviz2', executable='rviz2', arguments=['-d', os.path.join(share, 'config', 'training.rviz')],
             condition=IfCondition(rviz), output='screen'),
        Node(package='rosbridge_server', executable='rosbridge_websocket', output='screen',
             parameters=[{'address': '127.0.0.1', 'port': ParameterValue(rosbridge_port, value_type=int)}]),
        ExecuteProcess(condition=IfCondition(LaunchConfiguration('serve_web')), cmd=['python3', '-m', 'http.server', LaunchConfiguration('web_port'),
                            '--bind', '127.0.0.1', '--directory', os.path.join(share, 'web')],
                       output='screen'),
    ])
