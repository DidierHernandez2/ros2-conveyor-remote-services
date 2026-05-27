#!/usr/bin/env python3

import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class FaceCameraNode(Node):
    def __init__(self):
        super().__init__("face_camera_node")

        self.declare_parameter("camera_id", 2)
        self.declare_parameter("width", 640)
        self.declare_parameter("height", 480)
        self.declare_parameter("fps", 15.0)
        self.declare_parameter("topic", "/camera/face_recognition/image_raw")

        camera_id = int(self.get_parameter("camera_id").value)
        width = int(self.get_parameter("width").value)
        height = int(self.get_parameter("height").value)
        fps = float(self.get_parameter("fps").value)
        topic = self.get_parameter("topic").value

        self.bridge = CvBridge()

        self.cap = cv2.VideoCapture(camera_id, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

        if not self.cap.isOpened():
            raise RuntimeError(f"No se pudo abrir la cámara con ID {camera_id}")

        self.pub = self.create_publisher(Image, topic, 10)

        self.timer = self.create_timer(1.0 / fps, self.publish_frame)

        self.get_logger().info(f"Cámara de rostros abierta en ID {camera_id}")
        self.get_logger().info(f"Publicando en {topic}")

    def publish_frame(self):
        ret, frame = self.cap.read()

        if not ret:
            self.get_logger().warn("No se pudo leer frame")
            return

        msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "face_camera"

        self.pub.publish(msg)

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = FaceCameraNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
