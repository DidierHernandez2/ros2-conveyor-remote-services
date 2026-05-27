import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2


class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        self.declare_parameter('camera_id', 0)
        self.camera_id = self.get_parameter('camera_id').value

        self.bridge = CvBridge()
        self.cap = cv2.VideoCapture(self.camera_id)

        self.publisher = self.create_publisher(
            Image,
            '/camera/image_raw',
            10
        )

        self.timer = self.create_timer(1.0 / 30.0, self.publish_frame)

        self.get_logger().info(f'Publicando cámara en /camera/image_raw desde cámara {self.camera_id}')

    def publish_frame(self):
        ret, frame = self.cap.read()

        if not ret:
            self.get_logger().warn('No se pudo leer frame de la cámara')
            return

        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera_frame'

        self.publisher.publish(msg)

    def destroy_node(self):
        if self.cap.isOpened():
            self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
