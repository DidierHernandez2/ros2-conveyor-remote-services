from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="conveyor_dashboard_remote",
            executable="dashboard_remote_node",
            name="dashboard_remote_node",
            output="screen",
        ),
    ])
