#!/usr/bin/env python3

import asyncio
import json
import threading
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn


app = FastAPI()

ros_node = None
latest_telemetry = {}
latest_frame = None

command_queue = []
command_seq = 0


class DashboardRemoteNode(Node):
    def __init__(self):
        super().__init__("dashboard_remote_node")

        self.cmd_pub = self.create_publisher(String, "/conveyor/cmd", 10)
        self.telemetry_pub = self.create_publisher(String, "/conveyor/telemetry", 10)

        self.get_logger().info("Dashboard remoto Jazzy iniciado")
        self.get_logger().info("Publicando comandos locales en /conveyor/cmd")
        self.get_logger().info("Publicando telemetría real en /conveyor/telemetry")

    def publish_cmd(self, data):
        msg = String()
        msg.data = json.dumps(data)
        self.cmd_pub.publish(msg)

    def publish_telemetry(self, data):
        msg = String()
        msg.data = json.dumps(data)
        self.telemetry_pub.publish(msg)


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Remoto Conveyor</title>
    <style>
        body {
            background: #111827;
            color: white;
            font-family: Arial, sans-serif;
            padding: 20px;
        }

        .grid {
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 20px;
        }

        .card {
            background: #1f2937;
            padding: 20px;
            border-radius: 16px;
            margin-bottom: 20px;
        }

        button {
            font-size: 20px;
            padding: 16px 22px;
            margin: 6px;
            border-radius: 12px;
            border: none;
            cursor: pointer;
        }

        .run { background: #22c55e; }
        .rev { background: #f59e0b; }
        .stop { background: #ef4444; color: white; }
        .emg { background: #991b1b; color: white; font-weight: bold; }

        input[type=range] {
            width: 100%;
            height: 45px;
        }

        img {
            width: 100%;
            border-radius: 12px;
            background: black;
        }

        .metric {
            background: #111827;
            padding: 14px;
            border-radius: 12px;
            margin: 8px 0;
            border: 1px solid #374151;
        }

        .value {
            font-size: 24px;
            font-weight: bold;
            color: #38bdf8;
        }
    </style>
</head>

<body>
    <h1>Dashboard Remoto - Conveyor L510</h1>

    <div class="grid">
        <div class="card">
            <h2>Cámara real desde Humble</h2>
            <img src="/video">
        </div>

        <div class="card">
            <h2>Control de banda</h2>

            <button class="run" onclick="cmd('forward')">Avanzar</button>
            <button class="rev" onclick="cmd('reverse')">Reversa</button>
            <button class="stop" onclick="cmd('stop')">Detener</button>
            <button class="emg" onclick="cmd('emergency_stop')">Paro emergencia</button>

            <h3>Velocidad: <span id="speedLabel">10</span> Hz</h3>
            <input type="range" min="0" max="60" value="10" step="1" oninput="setSpeed(this.value)">
        </div>
    </div>

    <div class="card">
        <h2>Telemetría real</h2>

        <div class="metric">Estado: <span class="value" id="state">---</span></div>
        <div class="metric">Error: <span class="value" id="error">---</span></div>
        <div class="metric">Frecuencia solicitada: <span class="value" id="freqCmd">---</span></div>
        <div class="metric">Frecuencia salida: <span class="value" id="freqOut">---</span></div>
        <div class="metric">Corriente: <span class="value" id="current">---</span></div>
    </div>

<script>
const ws = new WebSocket(`ws://${location.host}/ws`);

ws.onmessage = (event) => {
    const d = JSON.parse(event.data || "{}");

    document.getElementById("state").innerText = d.state ?? "---";
    document.getElementById("error").innerText = d.error ?? "---";

    document.getElementById("freqCmd").innerText =
        d.freq_cmd_hz !== undefined && d.freq_cmd_hz !== null
            ? Number(d.freq_cmd_hz).toFixed(2) + " Hz"
            : "---";

    document.getElementById("freqOut").innerText =
        d.freq_out_hz !== undefined && d.freq_out_hz !== null
            ? Number(d.freq_out_hz).toFixed(2) + " Hz"
            : "---";

    document.getElementById("current").innerText =
        d.current_raw !== undefined && d.current_raw !== null
            ? d.current_raw
            : "---";
};

function cmd(action) {
    fetch("/cmd", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({action: action})
    });
}

function setSpeed(hz) {
    document.getElementById("speedLabel").innerText = hz;

    fetch("/cmd", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            action: "set_speed",
            hz: parseFloat(hz)
        })
    });
}
</script>

</body>
</html>
"""


@app.get("/")
def index():
    return HTMLResponse(HTML)


@app.post("/cmd")
async def receive_dashboard_command(data: dict):
    global command_seq, command_queue

    command_seq += 1

    item = {
        "seq": command_seq,
        "timestamp": time.time(),
        "cmd": data,
    }

    command_queue.append(item)
    command_queue = command_queue[-200:]

    if ros_node is not None:
        ros_node.publish_cmd(data)

    return {
        "ok": True,
        "queued": item,
    }


@app.get("/api/commands")
async def get_commands(after: int = 0):
    pending = [
        item for item in command_queue
        if int(item["seq"]) > int(after)
    ]

    return {
        "ok": True,
        "latest_seq": command_seq,
        "commands": pending,
    }


@app.post("/api/telemetry")
async def receive_telemetry(data: dict):
    global latest_telemetry

    latest_telemetry = data

    if ros_node is not None:
        ros_node.publish_telemetry(data)

    return {
        "ok": True,
        "received": data,
    }


@app.post("/api/frame")
async def receive_frame(request: Request):
    global latest_frame

    latest_frame = await request.body()

    return {
        "ok": True,
        "bytes": len(latest_frame),
    }


@app.get("/api/status")
async def status():
    return {
        "ok": True,
        "latest_telemetry": latest_telemetry,
        "has_frame": latest_frame is not None,
        "latest_command_seq": command_seq,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        await websocket.send_text(json.dumps(latest_telemetry))
        await asyncio.sleep(0.25)


def mjpeg_generator():
    global latest_frame

    while True:
        if latest_frame is not None:
            yield (
                b"--frame\\r\\n"
                b"Content-Type: image/jpeg\\r\\n\\r\\n" +
                latest_frame +
                b"\\r\\n"
            )

        time.sleep(0.05)


@app.get("/video")
def video():
    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


def ros_spin():
    global ros_node

    rclpy.init()
    ros_node = DashboardRemoteNode()
    rclpy.spin(ros_node)


def main():
    thread = threading.Thread(target=ros_spin, daemon=True)
    thread.start()
    time.sleep(1.0)

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
