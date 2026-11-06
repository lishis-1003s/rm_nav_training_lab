import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from rm_nav_training_lab.launch_utils import check_ports
from launch.actions import OpaqueFunction, DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, SetEnvironmentVariable, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory('rm_nav_training_lab')
    nav2_share = get_package_share_directory('nav2_bringup')
    slam_share = get_package_share_directory('slam_toolbox')
    from nav2_common.launch import RewrittenYaml
    params_path = RewrittenYaml(source_file=LaunchConfiguration('params_file'), param_rewrites={'robot_radius': LaunchConfiguration('robot_radius')}, convert_types=True)
    slam_params_path = LaunchConfiguration('slam_params_file')
    web_port = LaunchConfiguration('web_port')
    rosbridge_port = LaunchConfiguration('rosbridge_port')
    rviz = LaunchConfiguration('rviz')
    ros_domain_id = LaunchConfiguration('ros_domain_id')
    default_params = os.path.join(share, 'config', 'nav2_params.yaml')
    default_slam_params = os.path.join(share, 'config', 'slam_toolbox.yaml')
    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(slam_share, 'launch', 'online_async_launch.py')),
        launch_arguments={'slam_params_file': slam_params_path, 'use_sim_time': 'False'}.items(),
    )
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2_share, 'launch', 'navigation_launch.py')),
        launch_arguments={
            'params_file': params_path,
            'use_sim_time': 'False',
            'autostart': 'True',
            'use_composition': 'False',
        }.items(),
    )
    return LaunchDescription([
        DeclareLaunchArgument('ros_domain_id', default_value=os.environ.get('ROS_DOMAIN_ID', '0')),
        DeclareLaunchArgument('params_file', default_value=default_params),
        DeclareLaunchArgument('slam_params_file', default_value=default_slam_params),
        DeclareLaunchArgument('web_port', default_value='8080'),
        DeclareLaunchArgument('serve_web', default_value='True'),
        DeclareLaunchArgument('robot_radius', default_value='0.3'),
        DeclareLaunchArgument('map', default_value=os.path.join(share, 'maps', 'rmul2026_3v3.yaml')),
        DeclareLaunchArgument('rosbridge_port', default_value='9090'),
        DeclareLaunchArgument('rviz', default_value='True'),
        SetEnvironmentVariable('ROS_DOMAIN_ID', ros_domain_id),
        OpaqueFunction(function=check_ports),
        Node(package='rm_nav_training_lab', executable='training_simulator', output='screen',
             parameters=[{'map': LaunchConfiguration('map'), 'robot_radius': ParameterValue(LaunchConfiguration('robot_radius'), value_type=float), 'publish_map': False, 'publish_map_to_odom': False}]),
        slam,
        TimerAction(period=2.0, actions=[navigation]),
        Node(package='rm_nav_training_lab', executable='training_bridge', output='screen', parameters=[{'runtime_mode': 'slam'}]),
        Node(package='rviz2', executable='rviz2', arguments=['-d', os.path.join(share, 'config', 'training.rviz')],
             condition=IfCondition(rviz), output='screen'),
        Node(package='rosbridge_server', executable='rosbridge_websocket', output='screen',
             parameters=[{'address': '127.0.0.1', 'port': ParameterValue(rosbridge_port, value_type=int)}]),
        ExecuteProcess(condition=IfCondition(LaunchConfiguration('serve_web')), cmd=['python3', '-m', 'http.server', LaunchConfiguration('web_port'),
                            '--bind', '127.0.0.1', '--directory', os.path.join(share, 'web')],
                       output='screen'),
    ])
