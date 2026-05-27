#!/usr/bin/env python3

import json
import math
import time
from collections import deque

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String, Float32


class LidarDistanceNode(Node):
    def __init__(self):
        super().__init__("lidar_distance_node")

        self.declare_parameter("scan_topic", "/scan")
        self.declare_parameter("distance_topic", "/lidar/distance")
        self.declare_parameter("front_distance_topic", "/lidar/front_distance")

        self.declare_parameter("front_angle_deg", 180.0)
        self.declare_parameter("window_deg", 20.0)

        self.declare_parameter("min_valid_m", 0.05)
        self.declare_parameter("max_valid_m", 40.0)

        self.declare_parameter("history_size", 10)
        self.declare_parameter("presence_threshold_m", 0.50)
        self.declare_parameter("clear_threshold_m", 0.70)
        self.declare_parameter("min_hits_to_detect", 7)

        self.scan_topic = self.get_parameter("scan_topic").value
        self.distance_topic = self.get_parameter("distance_topic").value
        self.front_distance_topic = self.get_parameter("front_distance_topic").value

        self.front_angle_deg = float(self.get_parameter("front_angle_deg").value)
        self.window_deg = float(self.get_parameter("window_deg").value)

        self.min_valid_m = float(self.get_parameter("min_valid_m").value)
        self.max_valid_m = float(self.get_parameter("max_valid_m").value)

        self.history_size = int(self.get_parameter("history_size").value)
        self.presence_threshold_m = float(self.get_parameter("presence_threshold_m").value)
        self.clear_threshold_m = float(self.get_parameter("clear_threshold_m").value)
        self.min_hits_to_detect = int(self.get_parameter("min_hits_to_detect").value)

        self.front_history = deque(maxlen=self.history_size)
        self.object_present = False

        self.distance_pub = self.create_publisher(String, self.distance_topic, 10)
        self.front_float_pub = self.create_publisher(Float32, self.front_distance_topic, 10)

        self.scan_sub = self.create_subscription(
            LaserScan,
            self.scan_topic,
            self.scan_callback,
            10,
        )

        self.get_logger().info("LidarDistanceNode iniciado")
        self.get_logger().info(f"Suscrito a: {self.scan_topic}")
        self.get_logger().info(f"Publicando JSON en: {self.distance_topic}")
        self.get_logger().info(f"Publicando Float32 en: {self.front_distance_topic}")
        self.get_logger().info(f"Frente configurado en: {self.front_angle_deg} grados")
        self.get_logger().info(f"Ventana angular: {self.window_deg} grados")
        self.get_logger().info(
            f"Detección: {self.min_hits_to_detect}/{self.history_size} valores <= "
            f"{self.presence_threshold_m} m"
        )
        self.get_logger().info(
            f"Liberación: promedio últimos {self.history_size} valores >= "
            f"{self.clear_threshold_m} m"
        )

    def angle_in_window(self, angle_rad: float) -> bool:
        center = math.radians(self.front_angle_deg)
        half_window = math.radians(self.window_deg / 2.0)

        diff = math.atan2(
            math.sin(angle_rad - center),
            math.cos(angle_rad - center),
        )

        return abs(diff) <= half_window

    def compute_presence_logic(self, front_min_m):
        if front_min_m is not None:
            self.front_history.append(float(front_min_m))
        else:
            self.front_history.append(float("inf"))

        values = list(self.front_history)

        hits_in_range = sum(
            1 for d in values
            if math.isfinite(d) and d <= self.presence_threshold_m
        )

        finite_values = [
            d for d in values
            if math.isfinite(d)
        ]

        avg_recent_m = (
            sum(finite_values) / len(finite_values)
            if finite_values else float("inf")
        )

        if len(values) >= self.history_size:
            if hits_in_range >= self.min_hits_to_detect:
                self.object_present = True
            elif avg_recent_m >= self.clear_threshold_m:
                self.object_present = False

        return {
            "detected": self.object_present,
            "hits_in_range": hits_in_range,
            "avg_recent_m": avg_recent_m if math.isfinite(avg_recent_m) else None,
            "history_count": len(values),
        }

    def scan_callback(self, msg: LaserScan):
        valid_ranges = []

        for i, distance in enumerate(msg.ranges):
            if not math.isfinite(distance):
                continue

            if distance < self.min_valid_m or distance > self.max_valid_m:
                continue

            angle = msg.angle_min + i * msg.angle_increment

            if self.angle_in_window(angle):
                valid_ranges.append(float(distance))

        if valid_ranges:
            front_min_m = min(valid_ranges)
            front_avg_m = sum(valid_ranges) / len(valid_ranges)
        else:
            front_min_m = None
            front_avg_m = None

        presence = self.compute_presence_logic(front_min_m)

        payload = {
            "detected": presence["detected"],
            "front_min_m": front_min_m,
            "front_avg_m": front_avg_m,
            "samples_used": len(valid_ranges),
            "front_angle_deg": self.front_angle_deg,
            "window_deg": self.window_deg,
            "timestamp": time.time(),

            "history_size": self.history_size,
            "history_count": presence["history_count"],
            "presence_threshold_m": self.presence_threshold_m,
            "clear_threshold_m": self.clear_threshold_m,
            "min_hits_to_detect": self.min_hits_to_detect,
            "hits_in_range": presence["hits_in_range"],
            "avg_recent_m": presence["avg_recent_m"],
        }

        msg_out = String()
        msg_out.data = json.dumps(payload)
        self.distance_pub.publish(msg_out)

        if front_min_m is not None:
            self.front_float_pub.publish(Float32(data=float(front_min_m)))


def main(args=None):
    rclpy.init(args=args)
    node = LidarDistanceNode()

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
