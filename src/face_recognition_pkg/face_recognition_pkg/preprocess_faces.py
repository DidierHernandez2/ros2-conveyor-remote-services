#!/usr/bin/env python3

import os
import time
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class PreprocessFacesNode(Node):
    def __init__(self):
        super().__init__("preprocess_faces")

        self.declare_parameter("image_topic", "/camera/face_recognition/image_raw")
        self.declare_parameter("output_dir", "/home/darhf/jazzy_ws/src/face_recognition_pkg/face_database")
        self.declare_parameter("show_window", True)

        self.image_topic = self.get_parameter("image_topic").value
        self.output_dir = self.get_parameter("output_dir").value
        self.show_window = bool(self.get_parameter("show_window").value)

        self.bridge = CvBridge()
        self.paused = False
        self.latest_frame = None

        self.labels = {
            ord("j"): "jefe",
            ord("t"): "trabajador",
            ord("n"): "otros",
        }

        for label in self.labels.values():
            os.makedirs(os.path.join(self.output_dir, label), exist_ok=True)

        cascade_path = self.find_haar_cascade()
        if cascade_path is None:
            raise RuntimeError("No se encontró haarcascade_frontalface_default.xml")

        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        self.sub = self.create_subscription(
            Image,
            self.image_topic,
            self.image_callback,
            10,
        )

        if self.show_window:
            cv2.namedWindow("Preprocess Faces", cv2.WINDOW_NORMAL)

        self.get_logger().info("Preprocess faces iniciado")
        self.get_logger().info(f"Suscrito a: {self.image_topic}")
        self.get_logger().info(f"Guardando en: {self.output_dir}")
        self.get_logger().info("Teclas: J=jefe, T=trabajador, N=otros, P=pausar, Q=salir")

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

    def image_callback(self, msg):
        if self.paused:
            return

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as e:
            self.get_logger().warn(f"Error cv_bridge: {e}")
            return

        self.latest_frame = frame.copy()

        display = frame.copy()
        faces = self.detect_faces(frame)

        for (x, y, w, h) in faces:
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cv2.putText(
            display,
            "J=jefe | T=trabajador | N=otros | P=pausa | Q=salir",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        if self.show_window:
            cv2.imshow("Preprocess Faces", display)

            key = cv2.waitKey(1) & 0xFF

            if key in self.labels:
                self.save_faces(frame, self.labels[key])

            elif key == ord("p"):
                self.paused = not self.paused
                self.get_logger().info(f"Pausa: {self.paused}")

            elif key == ord("q"):
                rclpy.shutdown()

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

    def save_faces(self, frame, label):
        faces = self.detect_faces(frame)

        if len(faces) == 0:
            self.get_logger().warn("No se detectó ningún rostro para guardar")
            return

        saved = 0

        for box in faces:
            face_img = self.preprocess_face(frame, box)

            filename = f"{label}_{int(time.time() * 1000)}_{saved}.png"
            path = os.path.join(self.output_dir, label, filename)

            cv2.imwrite(path, face_img)
            saved += 1

            self.get_logger().info(f"Rostro guardado: {path}")

        self.get_logger().info(f"Guardados {saved} rostro(s) como clase: {label}")

    def destroy_node(self):
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = PreprocessFacesNode()

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
