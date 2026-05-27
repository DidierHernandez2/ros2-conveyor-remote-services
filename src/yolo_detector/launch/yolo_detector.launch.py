from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="yolo_detector",
            executable="yolo_detector_node",
            name="yolo_detector_node",
            output="screen",
            parameters=[
                {"image_topic": "/camera/image/compressed"},
                {"model_path": "/home/darhf/jazzy_ws/src/yolo_detector/models/yolo11n-seg.pt"},
                {"confidence": 0.45},
                {"show_window": True},
                {"post_to_api": True},
                {"server_url": "http://localhost:8000"},
                {"api_period": 0.2},
                {"post_debug_frame": True},
            ],
        ),
    ])
