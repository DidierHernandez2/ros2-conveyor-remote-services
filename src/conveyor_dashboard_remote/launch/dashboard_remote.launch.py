from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

import os


def generate_launch_description():
    face_camera_id = LaunchConfiguration("face_camera_id")
    face_database_path = LaunchConfiguration("face_database_path")

    yolo_launch = os.path.join(
        get_package_share_directory("yolo_detector"),
        "launch",
        "yolo_detector.launch.py",
    )

    conveyor_sim_launch = os.path.join(
        get_package_share_directory("conveyor_sim"),
        "launch",
        "conveyor_sim.launch.py",
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "face_camera_id",
            default_value="2",
            description="Índice de la segunda cámara usada para reconocimiento facial",
        ),

        DeclareLaunchArgument(
            "face_database_path",
            default_value="/home/darhf/jazzy_ws/src/face_recognition_pkg/face_database",
            description="Ruta de la base de datos de rostros",
        ),

        Node(
            package="conveyor_dashboard_remote",
            executable="dashboard_remote_node",
            name="dashboard_remote_node",
            output="screen",
        ),

        Node(
            package="face_camera_reader",
            executable="face_camera_node",
            name="face_camera_node",
            output="screen",
            parameters=[
                {"camera_id": face_camera_id},
                {"image_topic": "/camera/face_recognition/image_raw"},
                {"width": 640},
                {"height": 480},
                {"fps": 15.0},
            ],
        ),

        Node(
            package="face_recognition_pkg",
            executable="face_auth_node",
            name="face_auth_node",
            output="screen",
            parameters=[
                {"image_topic": "/camera/face_recognition/image_raw"},
                {"database_path": face_database_path},
                {"auth_topic": "/auth/face_role"},
                {"show_window": True},
                {"recognition_threshold": 65.0},
            ],
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(yolo_launch),
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(conveyor_sim_launch),
        ),
    ])