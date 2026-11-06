import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from rm_nav_training_lab.launch_utils import check_ports
from launch.actions import OpaqueFunction, DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory('rm_nav_training_lab')
    web_port = LaunchConfiguration('web_port')
    rosbridge_port = LaunchConfiguration('rosbridge_port')
    rviz = LaunchConfiguration('rviz')
    ros_domain_id = LaunchConfiguration('ros_domain_id')
    return LaunchDescription([
        DeclareLaunchArgument('ros_domain_id', default_value=os.environ.get('ROS_DOMAIN_ID', '0')),
        DeclareLaunchArgument('web_port', default_value='8080'),
        DeclareLaunchArgument('serve_web', default_value='True'),
        DeclareLaunchArgument('robot_radius', default_value='0.3'),
        DeclareLaunchArgument('map', default_value=os.path.join(share, 'maps', 'rmul2026_3v3.yaml')),
        DeclareLaunchArgument('rosbridge_port', default_value='9090'),
        DeclareLaunchArgument('rviz', default_value='True'),
        SetEnvironmentVariable('ROS_DOMAIN_ID', ros_domain_id),
        OpaqueFunction(function=check_ports),
        Node(package='rm_nav_training_lab', executable='training_simulator', output='screen',
             parameters=[{'map': LaunchConfiguration('map'), 'robot_radius': ParameterValue(LaunchConfiguration('robot_radius'), value_type=float), 'publish_map': True, 'publish_map_to_odom': True}]),
        Node(package='rm_nav_training_lab', executable='training_bridge', output='screen', parameters=[{'runtime_mode': 'sim'}]),
        Node(package='rviz2', executable='rviz2', arguments=['-d', os.path.join(share, 'config', 'training.rviz')],
             condition=IfCondition(rviz), output='screen'),
        Node(package='rosbridge_server', executable='rosbridge_websocket', output='screen',
             parameters=[{'address': '127.0.0.1', 'port': ParameterValue(rosbridge_port, value_type=int)}]),
        ExecuteProcess(condition=IfCondition(LaunchConfiguration('serve_web')), cmd=['python3', '-m', 'http.server', LaunchConfiguration('web_port'),
                            '--bind', '127.0.0.1', '--directory', os.path.join(share, 'web')],
                       output='screen'),
    ])
