#!/usr/bin/env python3

import json
import os
import time
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge


class FaceRecognitionNode(Node):
    def __init__(self):
        super().__init__("face_recognition_node")

        self.declare_parameter("image_topic", "/camera/face_recognition/image_raw")
        self.declare_parameter("database_dir", "/home/darhf/jazzy_ws/src/face_recognition_pkg/face_database")
        self.declare_parameter("show_window", True)
        self.declare_parameter("threshold", 0.42)
        self.declare_parameter("reload_period", 5.0)

        self.image_topic = self.get_parameter("image_topic").value
        self.database_dir = self.get_parameter("database_dir").value
        self.show_window = bool(self.get_parameter("show_window").value)
        self.threshold = float(self.get_parameter("threshold").value)
        self.reload_period = float(self.get_parameter("reload_period").value)

        self.bridge = CvBridge()
        self.database = []
        self.last_reload = 0.0

        cascade_path = self.find_haar_cascade()
        if cascade_path is None:
            raise RuntimeError("No se encontró haarcascade_frontalface_default.xml")

        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        self.load_database()

        self.sub = self.create_subscription(
            Image,
            self.image_topic,
            self.image_callback,
            10,
        )

        self.pub = self.create_publisher(
            String,
            "/face_recognition/detections",
            10,
        )

        if self.show_window:
            cv2.namedWindow("Face Recognition", cv2.WINDOW_NORMAL)

        self.get_logger().info("Face recognition iniciado")
        self.get_logger().info(f"Suscrito a: {self.image_topic}")
        self.get_logger().info(f"Base de datos: {self.database_dir}")
        self.get_logger().info(f"Threshold: {self.threshold}")

    def find_haar_cascade(self):
        paths = [
            "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
            "/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml",
            "/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
            "/usr/local/share/opencv/haarcascades/haarcascade_frontalface_default.xml",
        ]

        try:
            import cv2.data
            paths.insert(0, os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
        except Exception:
            pass

        for path in paths:
            if os.path.exists(path):
                return path

        return None

    def load_database(self):
        self.database = []

        if not os.path.exists(self.database_dir):
            os.makedirs(self.database_dir, exist_ok=True)

        labels = [
            d for d in os.listdir(self.database_dir)
            if os.path.isdir(os.path.join(self.database_dir, d))
        ]

        for label in labels:
            label_dir = os.path.join(self.database_dir, label)

            for filename in os.listdir(label_dir):
                if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    continue

                path = os.path.join(label_dir, filename)
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)

                if img is None:
                    continue

                img = cv2.resize(img, (160, 160))
                img = cv2.equalizeHist(img)
                embedding = self.get_embedding(img)

                self.database.append({
                    "label": label,
                    "path": path,
                    "embedding": embedding,
                })

        self.last_reload = time.time()
        self.get_logger().info(f"Base cargada con {len(self.database)} rostro(s)")

    def get_embedding(self, gray_face):
        img = gray_face.astype(np.float32) / 255.0
        img = cv2.resize(img, (64, 64))
        vec = img.flatten()

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec

    def detect_faces(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(70, 70),
        )

        return faces

    def preprocess_face(self, frame, box):
        x, y, w, h = box

        margin = int(0.20 * w)
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(frame.shape[1], x + w + margin)
        y2 = min(frame.shape[0], y + h + margin)

        crop = frame[y1:y2, x1:x2]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (160, 160))
        gray = cv2.equalizeHist(gray)

        return gray

    def recognize_face(self, gray_face):
        if len(self.database) == 0:
            return "desconocido", None

        emb = self.get_embedding(gray_face)

        best_label = "desconocido"
        best_dist = 999.0

        for item in self.database:
            dist = float(np.linalg.norm(emb - item["embedding"]))

            if dist < best_dist:
                best_dist = dist
                best_label = item["label"]

        if best_dist <= self.threshold:
            return best_label, best_dist

        return "desconocido", best_dist

    def image_callback(self, msg):
        now = time.time()

        if now - self.last_reload >= self.reload_period:
            self.load_database()

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as e:
            self.get_logger().warn(f"Error cv_bridge: {e}")
            return

        faces = self.detect_faces(frame)
        detections = []

        for i, box in enumerate(faces):
            x, y, w, h = box
            gray_face = self.preprocess_face(frame, box)
            label, dist = self.recognize_face(gray_face)

            detections.append({
                "id": i,
                "label": label,
                "distance": dist,
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
            })

            color = (0, 255, 0) if label != "desconocido" else (0, 0, 255)

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

            text = label
            if dist is not None:
                text += f" {dist:.2f}"

            cv2.putText(
                frame,
                text,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
            )

        out = String()
        out.data = json.dumps({
            "count": len(detections),
            "faces": detections,
            "database_size": len(self.database),
        })
        self.pub.publish(out)

        if self.show_window:
            cv2.imshow("Face Recognition", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("r"):
                self.load_database()

            elif key == ord("q"):
                rclpy.shutdown()

    def destroy_node(self):
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = FaceRecognitionNode()

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
