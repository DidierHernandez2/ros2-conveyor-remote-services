#!/usr/bin/env python3

import json
import time

import cv2
import numpy as np
import requests
import torch
import rclpy

from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage
from std_msgs.msg import String
from cv_bridge import CvBridge
from ultralytics import YOLO


class YoloDetectorNode(Node):
    def __init__(self):
        super().__init__("yolo_detector_node")

        self.declare_parameter(
            "model_path",
            "/home/darhf/jazzy_ws/src/yolo_detector/models/yolo11n-seg.pt",
        )
        self.declare_parameter("image_topic", "/camera/image/compressed")
        self.declare_parameter("confidence", 0.45)
        self.declare_parameter("show_window", True)
        self.declare_parameter("post_to_api", True)
        self.declare_parameter("server_url", "http://localhost:8000")
        self.declare_parameter("api_period", 0.2)
        self.declare_parameter("post_debug_frame", True)

        self.model_path = self.get_parameter("model_path").value
        self.image_topic = self.get_parameter("image_topic").value
        self.confidence = float(self.get_parameter("confidence").value)
        self.show_window = bool(self.get_parameter("show_window").value)
        self.post_to_api = bool(self.get_parameter("post_to_api").value)
        self.server_url = self.get_parameter("server_url").value.rstrip("/")
        self.api_period = float(self.get_parameter("api_period").value)
        self.post_debug_frame = bool(self.get_parameter("post_debug_frame").value)
        self.last_api_time = 0.0

        self.allowed_classes = [2, 39, 42, 47, 51]
        self.allowed_names = ["car", "bottle", "fork", "apple", "carrot"]

        self.bridge = CvBridge()

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.get_logger().info(f"Usando dispositivo: {self.device}")

        if self.device == "cuda":
            self.get_logger().info(f"GPU: {torch.cuda.get_device_name(0)}")

        self.get_logger().info(f"Cargando modelo: {self.model_path}")
        self.model = YOLO(self.model_path)
        self.model.to(self.device)
        self.class_names = self.model.names

        self.image_sub = self.create_subscription(
            CompressedImage,
            self.image_topic,
            self.image_callback,
            10,
        )

        self.debug_pub = self.create_publisher(
            Image,
            "/yolo/debug/image",
            10,
        )

        self.debug_compressed_pub = self.create_publisher(
            CompressedImage,
            "/yolo/debug/image/compressed",
            10,
        )

        self.detection_pub = self.create_publisher(
            String,
            "/yolo/detections",
            10,
        )

        if self.show_window:
            cv2.namedWindow("YOLO Detection", cv2.WINDOW_NORMAL)

        self.get_logger().info("YOLO detector iniciado")
        self.get_logger().info(f"Suscrito a: {self.image_topic}")
        self.get_logger().info("Publicando JSON en: /yolo/detections")
        self.get_logger().info("Publicando debug en: /yolo/debug/image")
        self.get_logger().info(f"Enviando inferencia a: {self.server_url}/api/yolo")

    def image_callback(self, msg: CompressedImage):
        frame = self.decode_compressed_image(msg)

        if frame is None:
            self.get_logger().warn("No se pudo decodificar imagen comprimida")
            return

        results = self.model(
            frame,
            conf=self.confidence,
            device=self.device,
            imgsz=640,
            classes=self.allowed_classes,
            verbose=False,
        )

        result = results[0]
        detections = []

        if result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy()

            for box, conf, cls in zip(boxes, confs, classes):
                x1, y1, x2, y2 = map(int, box)
                class_id = int(cls)
                class_name = self.class_names[class_id]
                confidence = float(conf)

                detections.append({
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": confidence,
                    "bbox": {
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "center_x": int((x1 + x2) / 2),
                        "center_y": int((y1 + y2) / 2),
                        "width": int(x2 - x1),
                        "height": int(y2 - y1),
                    },
                })

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2,
                )

                label = f"{class_name} {confidence:.2f}"

                cv2.putText(
                    frame,
                    label,
                    (x1, max(25, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )

        payload = {
            "timestamp": time.time(),
            "frame_id": msg.header.frame_id,
            "source_topic": self.image_topic,
            "device": self.device,
            "allowed_classes": self.allowed_names,
            "count": len(detections),
            "objects": detections,
        }

        self.publish_detections(payload)
        self.publish_debug_image(frame, msg)
        self.post_yolo(payload, frame)

        if detections:
            names = [d["class_name"] for d in detections]
            self.get_logger().info(f"Detectado: {names}")

        if self.show_window:
            cv2.imshow("YOLO Detection", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                self.get_logger().info("Cerrando YOLO")
                rclpy.shutdown()

    def decode_compressed_image(self, msg: CompressedImage):
        try:
            np_arr = np.frombuffer(msg.data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            self.get_logger().warn(f"Error decodificando JPEG: {e}")
            return None

    def publish_detections(self, payload: dict):
        out = String()
        out.data = json.dumps(payload)
        self.detection_pub.publish(out)

    def publish_debug_image(self, frame, original_msg: CompressedImage):
        debug_msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        debug_msg.header.stamp = original_msg.header.stamp
        debug_msg.header.frame_id = original_msg.header.frame_id
        self.debug_pub.publish(debug_msg)

        ok, encoded = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), 70],
        )

        if ok:
            comp = CompressedImage()
            comp.header.stamp = original_msg.header.stamp
            comp.header.frame_id = original_msg.header.frame_id
            comp.format = "jpeg"
            comp.data = encoded.tobytes()
            self.debug_compressed_pub.publish(comp)

    def post_yolo(self, payload: dict, frame):
        if not self.post_to_api:
            return

        now = time.time()

        if now - self.last_api_time < self.api_period:
            return

        self.last_api_time = now

        try:
            response = requests.post(
                f"{self.server_url}/api/yolo",
                json=payload,
                timeout=0.5,
            )
            response.raise_for_status()
        except Exception as e:
            self.get_logger().warn(f"No se pudo enviar YOLO al API: {e}")

        if self.post_debug_frame:
            try:
                ok, encoded = cv2.imencode(
                    ".jpg",
                    frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 70],
                )

                if ok:
                    response = requests.post(
                        f"{self.server_url}/api/yolo_frame",
                        data=encoded.tobytes(),
                        headers={"Content-Type": "image/jpeg"},
                        timeout=0.5,
                    )
                    response.raise_for_status()
            except Exception as e:
                self.get_logger().warn(f"No se pudo enviar frame YOLO al API: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = YoloDetectorNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
