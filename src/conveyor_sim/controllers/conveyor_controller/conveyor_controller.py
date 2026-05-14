#!/usr/bin/env python3

import json
import math

from controller import Supervisor

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ConveyorDigitalTwin(Node):
    def __init__(self):
        super().__init__("conveyor_digital_twin")

        self.freq_out_hz = 0.0
        self.direction = 0

        self.mps_per_hz = 0.00625

        self.create_subscription(
            String,
            "/conveyor/telemetry",
            self.telemetry_callback,
            10,
        )

        self.create_subscription(
            String,
            "/conveyor/cmd",
            self.cmd_callback,
            10,
        )

        self.get_logger().info("Digital twin conectado a /conveyor/telemetry y /conveyor/cmd")

    def telemetry_callback(self, msg):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            return

        self.freq_out_hz = float(data.get("freq_out_hz") or 0.0)

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

    def speed_mps(self):
        return self.direction * self.freq_out_hz * self.mps_per_hz


robot = Supervisor()
timestep = int(robot.getBasicTimeStep())

rclpy.init()
ros_node = ConveyorDigitalTwin()

roller_start = robot.getFromDef("RODILLO_INICIO")
roller_end = robot.getFromDef("RODILLO_FINAL")
box = robot.getFromDef("CAJA")

marks = [
    robot.getFromDef("MARCA_1"),
    robot.getFromDef("MARCA_2"),
    robot.getFromDef("MARCA_3"),
    robot.getFromDef("MARCA_4"),
]

roller_angle = 0.0
roller_radius = 0.05

x_min = -0.65
x_max = 0.65

while robot.step(timestep) != -1:
    dt = timestep / 1000.0

    rclpy.spin_once(ros_node, timeout_sec=0.0)

    speed = ros_node.speed_mps()

    omega = speed / roller_radius
    roller_angle = (roller_angle + omega * dt) % (2.0 * math.pi)

    if roller_start is not None:
        roller_start.getField("rotation").setSFRotation([0, 1, 0, roller_angle])

    if roller_end is not None:
        roller_end.getField("rotation").setSFRotation([0, 1, 0, roller_angle])

    for mark in marks:
        if mark is None:
            continue

        field = mark.getField("translation")
        pos = field.getSFVec3f()

        pos[0] += speed * dt

        if pos[0] > x_max:
            pos[0] = x_min
        elif pos[0] < x_min:
            pos[0] = x_max

        field.setSFVec3f(pos)

    if box is not None:
        box_field = box.getField("translation")
        box_pos = box_field.getSFVec3f()

        box_pos[0] += speed * dt

        if box_pos[0] > x_max:
            box_pos[0] = x_min
        elif box_pos[0] < x_min:
            box_pos[0] = x_max

        box_field.setSFVec3f(box_pos)

ros_node.destroy_node()
rclpy.shutdown()
