import os

from launch import LaunchDescription
from launch.actions import SetEnvironmentVariable
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution

from webots_ros2_driver.webots_launcher import WebotsLauncher


def generate_launch_description():
    world = PathJoinSubstitution([
        FindPackageShare("conveyor_sim"),
        "worlds",
        "conveyor_world.wbt",
    ])

    webots = WebotsLauncher(
        world=world,
    )

    return LaunchDescription([
        SetEnvironmentVariable(
            name="WEBOTS_CONTROLLER_URL_PREFIX",
            value="",
        ),
        webots,
    ])
