#!/usr/bin/env python3

import json
import os
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ConveyorSimNode(Node):
    def __init__(self):
        super().__init__("conveyor_sim_node")

        self.declare_parameter("telemetry_topic", "/conveyor/telemetry")
        self.declare_parameter("cmd_topic", "/conveyor/cmd")
        self.declare_parameter("output_file", "/home/darhf/conveyor_sim_state.json")

        self.telemetry_topic = self.get_parameter("telemetry_topic").value
        self.cmd_topic = self.get_parameter("cmd_topic").value
        self.output_file = self.get_parameter("output_file").value

        self.freq_out_hz = 0.0
        self.direction = 0
        self.state = 4
        self.error = 0
        self.last_update = time.time()

        self.create_subscription(
            String,
            self.telemetry_topic,
            self.telemetry_callback,
            10,
        )

        self.create_subscription(
            String,
            self.cmd_topic,
            self.cmd_callback,
            10,
        )

        self.timer = self.create_timer(0.05, self.write_state)

        self.get_logger().info(f"SIM escuchando telemetría: {self.telemetry_topic}")
        self.get_logger().info(f"SIM escuchando comandos: {self.cmd_topic}")
        self.get_logger().info(f"SIM escribiendo estado: {self.output_file}")

    def telemetry_callback(self, msg):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            return

        self.freq_out_hz = float(data.get("freq_out_hz") or 0.0)
        self.state = int(data.get("state") or 4)
        self.error = int(data.get("error") or 0)

        if self.state == 5:
            self.direction = 1
        elif self.state == 7:
            self.direction = -1
        elif self.state == 4:
            self.direction = 0

        self.last_update = time.time()

    def cmd_callback(self, msg):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            return

        action = data.get("action")

        if action == "forward":
            self.direction = 1
        elif action == "reverse":
            self.direction = -1
        elif action in ("stop", "emergency_stop"):
            self.direction = 0

        self.last_update = time.time()

    def write_state(self):
        state = {
            "freq_out_hz": self.freq_out_hz,
            "direction": self.direction,
            "state": self.state,
            "error": self.error,
            "timestamp": time.time(),
            "last_update": self.last_update,
        }

        tmp_file = self.output_file + ".tmp"

        try:
            with open(tmp_file, "w") as f:
                json.dump(state, f)

            os.replace(tmp_file, self.output_file)

        except Exception as e:
            self.get_logger().warn(f"No se pudo escribir estado sim: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = ConveyorSimNode()

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