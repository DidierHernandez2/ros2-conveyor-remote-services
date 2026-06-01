from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node

from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():

    package_dir = get_package_share_directory("conveyor_sim")

    world_path = os.path.join(
        package_dir,
        "worlds",
        "conveyor_world.wbt"
    )

    webots = ExecuteProcess(
        cmd=[
            "webots",
            world_path,
        ],
        output="screen"
    )

    conveyor_sim = Node(
        package="conveyor_sim",
        executable="conveyor_sim_node",
        name="conveyor_sim_node",
        output="screen",
        parameters=[
            {
                "telemetry_topic": "/conveyor/telemetry"
            }
        ]
    )

    return LaunchDescription([
        webots,
        conveyor_sim,
    ])