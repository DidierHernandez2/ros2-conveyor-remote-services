#!/usr/bin/env python3

import json
import os
import time
from pathlib import Path

import cv2
import numpy as np

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge


VALID_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".bmp")


class FaceAuthNode(Node):
    def __init__(self):
        super().__init__("face_auth_node")

        self.declare_parameter("image_topic", "/camera/face_recognition/image_raw")
        self.declare_parameter(
            "database_path",
            str(Path.home() / "jazzy_ws/src/face_recognition_pkg/face_database"),
        )
        self.declare_parameter("auth_topic", "/auth/face_role")
        self.declare_parameter("show_window", True)
        self.declare_parameter("publish_period", 0.5)
        self.declare_parameter("recognition_threshold", 65.0)

        self.image_topic = self.get_parameter("image_topic").value
        self.database_path = self.get_parameter("database_path").value
        self.auth_topic = self.get_parameter("auth_topic").value
        self.show_window = bool(self.get_parameter("show_window").value)
        self.publish_period = float(self.get_parameter("publish_period").value)
        self.recognition_threshold = float(
            self.get_parameter("recognition_threshold").value
        )

        self.bridge = CvBridge()

        self.auth_pub = self.create_publisher(String, self.auth_topic, 10)

        self.image_sub = self.create_subscription(
            Image,
            self.image_topic,
            self.image_callback,
            10,
        )

        self.face_cascade = self.load_face_cascade()

        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.label_to_role = {}
        self.label_to_name = {}
        self.model_ready = False

        self.last_publish_time = 0.0
        self.last_payload = None

        self.train_database()

        self.get_logger().info(f"Face Auth escuchando: {self.image_topic}")
        self.get_logger().info(f"Publicando auth en: {self.auth_topic}")
        self.get_logger().info(f"Base de datos: {self.database_path}")

    def load_face_cascade(self):
        candidates = []

        if hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
            candidates.append(
                os.path.join(
                    cv2.data.haarcascades,
                    "haarcascade_frontalface_default.xml",
                )
            )

        candidates.extend([
            "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
            "/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml",
        ])

        for path in candidates:
            if os.path.exists(path):
                cascade = cv2.CascadeClassifier(path)
                if not cascade.empty():
                    self.get_logger().info(f"Cascade cargado: {path}")
                    return cascade

        raise RuntimeError("No se encontró haarcascade_frontalface_default.xml")

    def train_database(self):
        faces = []
        labels = []

        role_dirs = {
            "jefe": "jefe",
            "trabajador": "trabajador",
            "otro": "otros",
        }

        label_id = 0

        for role, folder in role_dirs.items():
            folder_path = os.path.join(self.database_path, folder)

            if not os.path.isdir(folder_path):
                self.get_logger().warn(f"No existe carpeta: {folder_path}")
                continue

            for filename in os.listdir(folder_path):
                if not filename.lower().endswith(VALID_IMAGE_EXT):
                    continue

                image_path = os.path.join(folder_path, filename)
                img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

                if img is None:
                    self.get_logger().warn(f"No pude leer: {image_path}")
                    continue

                detected = self.face_cascade.detectMultiScale(
                    img,
                    scaleFactor=1.1,
                    minNeighbors=4,
                    minSize=(60, 60),
                )

                if len(detected) > 0:
                    x, y, w, h = max(detected, key=lambda b: b[2] * b[3])
                    face = img[y:y + h, x:x + w]
                else:
                    face = img

                face = cv2.resize(face, (160, 160))

                faces.append(face)
                labels.append(label_id)

                self.label_to_role[label_id] = role
                self.label_to_name[label_id] = os.path.splitext(filename)[0]

                self.get_logger().info(
                    f"Entrenando label={label_id}, role={role}, file={filename}"
                )

                label_id += 1

        if not faces:
            self.get_logger().error("No hay rostros en base de datos")
            self.model_ready = False
            return

        self.recognizer.train(faces, np.array(labels, dtype=np.int32))
        self.model_ready = True

        self.get_logger().info(f"Modelo entrenado con {len(faces)} imágenes")

    def publish_auth(self, role, name="none", confidence=0.0, face_detected=False):
        now = time.time()

        if now - self.last_publish_time < self.publish_period:
            return

        payload = {
            "role": role,
            "name": name,
            "confidence": float(confidence),
            "face_detected": bool(face_detected),
            "timestamp": now,
        }

        if payload == self.last_payload:
            return

        msg = String()
        msg.data = json.dumps(payload)
        self.auth_pub.publish(msg)

        self.last_payload = payload
        self.last_publish_time = now

        self.get_logger().info(f"[AUTH] {msg.data}")

    def image_callback(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as e:
            self.get_logger().warn(f"No pude convertir imagen: {e}")
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(70, 70),
        )

        role = "none"
        name = "none"
        confidence_value = 0.0
        face_detected = False

        if len(faces) == 0:
            role = "none"
            name = "none"
            confidence_value = 0.0
            face_detected = False

        elif not self.model_ready:
            role = "unknown"
            name = "unknown"
            confidence_value = 0.0
            face_detected = True

        else:
            face_detected = True

            x, y, w, h = max(faces, key=lambda b: b[2] * b[3])
            face_roi = gray[y:y + h, x:x + w]
            face_roi = cv2.resize(face_roi, (160, 160))

            label, distance = self.recognizer.predict(face_roi)

            confidence_value = max(0.0, min(1.0, 1.0 - (distance / 100.0)))

            if distance <= self.recognition_threshold:
                role = self.label_to_role.get(label, "unknown")
                name = self.label_to_name.get(label, "unknown")
            else:
                role = "unknown"
                name = "unknown"

            if self.show_window:
                color = (0, 255, 0) if role in ("jefe", "trabajador") else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(
                    frame,
                    f"{role} | {name} | dist={distance:.1f}",
                    (x, max(30, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    color,
                    2,
                )

        self.publish_auth(
            role=role,
            name=name,
            confidence=confidence_value,
            face_detected=face_detected,
        )

        if self.show_window:
            cv2.imshow("Face Auth Node", frame)
            cv2.waitKey(1)


def main(args=None):
    rclpy.init(args=args)
    node = FaceAuthNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.show_window:
            cv2.destroyAllWindows()

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
