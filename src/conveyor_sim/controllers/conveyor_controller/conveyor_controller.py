#!/usr/bin/env python3

from controller import Supervisor
import json
import os
print("======================================")
print("CONTROLLER NUEVO CARGADO DESDE conveyor_sim")
print("MOVIMIENTO FORZADO DE PRUEBA")
print("======================================")

STATE_FILE = "/home/darhf/conveyor_sim_state.json"

robot = Supervisor()
timestep = int(robot.getBasicTimeStep())

box = robot.getFromDef("CAJA")

marks = [
    robot.getFromDef("MARCA_1"),
    robot.getFromDef("MARCA_2"),
    robot.getFromDef("MARCA_3"),
    robot.getFromDef("MARCA_4"),
]

x_min = -0.65
x_max = 0.65
mps_per_hz = 0.00625

freq_out_hz = 0.0
direction = 0
state = 4
error = 0


print("[conveyor_controller] Webots controller iniciado")
print(f"[conveyor_controller] Leyendo estado desde {STATE_FILE}")

if box is None:
    print("[ERROR] No se encontró DEF CAJA")

for i, mark in enumerate(marks, start=1):
    if mark is None:
        print(f"[ERROR] No se encontró DEF MARCA_{i}")


def read_state():
    global freq_out_hz, direction, state, error

    if not os.path.exists(STATE_FILE):
        return

    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)

        freq_out_hz = float(data.get("freq_out_hz") or 0.0)
        direction = int(data.get("direction") or 0)
        state = int(data.get("state") or 4)
        error = int(data.get("error") or 0)

    except Exception as e:
        print(f"[ERROR] Leyendo JSON: {e}")


def speed_mps():
    if error != 0:
        return 0.0

    if direction == 0:
        return 0.0

    if abs(freq_out_hz) <= 0.05:
        return 0.0

    return direction * freq_out_hz * mps_per_hz


def move_node_x(node, speed, dt):
    if node is None:
        return

    field = node.getField("translation")

    if field is None:
        print("[ERROR] Nodo sin campo translation")
        return

    pos = field.getSFVec3f()
    pos[0] += speed * dt

    if pos[0] > x_max:
        pos[0] = x_min

    elif pos[0] < x_min:
        pos[0] = x_max

    field.setSFVec3f(pos)


while robot.step(timestep) != -1:
    dt = timestep / 1000.0

    read_state()
    speed = speed_mps()

    for mark in marks:
        move_node_x(mark, speed, dt)

    move_node_x(box, speed, dt)
    if int(robot.getTime()) % 2 == 0:
        print(f"[SIM] freq={freq_out_hz}, dir={direction}, state={state}, error={error}, speed={speed}")
