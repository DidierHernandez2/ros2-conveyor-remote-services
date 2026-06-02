#!/usr/bin/env python3

import asyncio
import json
import threading
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import CompressedImage

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from starlette.websockets import WebSocketDisconnect
import uvicorn


app = FastAPI()

ros_node = None
latest_telemetry = {}
latest_lidar = {}
latest_yolo = {}
latest_face_role = {
    "role": "none",
    "name": "none",
    "confidence": 0.0,
    "face_detected": False,
    "timestamp": 0.0,
}
latest_frame = None
latest_yolo_frame = None

command_queue = []
command_seq = 0


class DashboardRemoteNode(Node):
    def __init__(self):
        super().__init__("dashboard_remote_node")

        self.cmd_pub = self.create_publisher(String, "/conveyor/cmd", 10)
        self.telemetry_pub = self.create_publisher(String, "/conveyor/telemetry", 10)

        self.camera_pub = self.create_publisher(
            CompressedImage,
            "/camera/image/compressed",
            10,
        )

        self.telemetry_sub = self.create_subscription(
            String,
            "/conveyor/telemetry",
            self.telemetry_callback,
            10,
        )

        self.lidar_sub = self.create_subscription(
            String,
            "/lidar/distance",
            self.lidar_callback,
            10,
        )
        self.face_role_sub = self.create_subscription(
            String,
            "/auth/face_role",
            self.face_role_callback,
            10,
        )

        self.get_logger().info("Suscrito a /auth/face_role")
        self.get_logger().info("Dashboard remoto Jazzy iniciado")
        self.get_logger().info("Publicando comandos locales en /conveyor/cmd")
        self.get_logger().info("Publicando imagen remota en /camera/image/compressed")
        self.get_logger().info("Suscrito a /conveyor/telemetry")
        self.get_logger().info("Suscrito a /lidar/distance")

    def publish_cmd(self, data: dict):
        msg = String()
        msg.data = json.dumps(data)
        self.cmd_pub.publish(msg)

    def publish_telemetry(self, data: dict):
        msg = String()
        msg.data = json.dumps(data)
        self.telemetry_pub.publish(msg)

    def publish_camera_frame(self, frame_bytes: bytes):
        msg = CompressedImage()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "remote_camera"
        msg.format = "jpeg"
        msg.data = frame_bytes
        self.camera_pub.publish(msg)

    def telemetry_callback(self, msg: String):
        global latest_telemetry

        try:
            latest_telemetry = json.loads(msg.data)
        except Exception as e:
            self.get_logger().warn(f"Telemetría inválida en /conveyor/telemetry: {e}")

    def lidar_callback(self, msg: String):
        global latest_lidar

        try:
            latest_lidar = json.loads(msg.data)
        except Exception as e:
            self.get_logger().warn(f"LiDAR inválido en /lidar/distance: {e}")
    def face_role_callback(self, msg: String):
        global latest_face_role

        try:
            latest_face_role = json.loads(msg.data)
        except Exception as e:
            self.get_logger().warn(f"Face role inválido en /auth/face_role: {e}")


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Remoto Conveyor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #111827;
            color: white;
            margin: 0;
            padding: 20px;
        }

        h1 { margin-bottom: 20px; }

        .grid {
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 20px;
        }

        .card {
            background: #1f2937;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.25);
        }

        button {
            font-size: 18px;
            padding: 12px 18px;
            margin: 6px;
            border-radius: 10px;
            border: none;
            cursor: pointer;
        }

        .run { background: #22c55e; color: black; }
        .rev { background: #f59e0b; color: black; }
        .stop { background: #ef4444; color: white; }
        .emg { background: #991b1b; color: white; font-weight: bold; }

        input { width: 100%; }
        input[type=range] { height: 45px; }

        img {
            width: 100%;
            border-radius: 12px;
            background: black;
        }

        .telemetry-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 14px;
        }

        .metric {
            background: #111827;
            padding: 16px;
            border-radius: 12px;
            border: 1px solid #374151;
        }

        .label {
            color: #9ca3af;
            font-size: 14px;
            margin-bottom: 6px;
        }

        .value {
            font-size: 24px;
            font-weight: bold;
        }

        .description {
            margin-top: 6px;
            color: #d1d5db;
            font-size: 14px;
        }

        .ok { color: #22c55e; }
        .warn { color: #facc15; }
        .bad { color: #ef4444; }
        .info { color: #38bdf8; }

        .status-banner {
            padding: 16px;
            border-radius: 12px;
            margin-bottom: 18px;
            font-size: 22px;
            font-weight: bold;
            text-align: center;
        }

        .banner-stop { background: #374151; color: white; }
        .banner-run { background: #064e3b; color: #86efac; }
        .banner-error { background: #7f1d1d; color: #fecaca; }

        .small {
            font-size: 13px;
            color: #9ca3af;
            margin-top: 10px;
        }
    </style>
</head>

<body>
    <h1>Dashboard Remoto - Conveyor Digital Twin</h1>

    <div id="mainStatus" class="status-banner banner-stop">
        Esperando datos del sistema...
    </div>

    <div class="grid">
        <div class="card">
            <h2>Video remoto original</h2>
            <img src="/video">
            <div class="small">Imagen recibida desde Jetson por /api/frame.</div>
        </div>

        <div class="card">
            <h2>Video YOLO</h2>
            <img src="/video_yolo">
            <div class="small">Imagen procesada por YOLO con cuadros verdes.</div>
        </div>
    </div>

    <div class="card" style="margin-top:20px;">
        <h2>Control de banda</h2>

        <button class="run" onclick="cmd('forward')">Avanzar</button>
        <button class="rev" onclick="cmd('reverse')">Reversa</button>
        <button class="stop" onclick="cmd('stop')">Detener</button>
        <button class="emg" onclick="cmd('emergency_stop')">Paro de emergencia</button>

        <h3>Velocidad solicitada: <span id="speedLabel">10</span> Hz</h3>
        <input type="range" min="0" max="60" value="10" step="1"
               oninput="setSpeed(this.value)">
    </div>

    <div class="card" style="margin-top:20px;">
        <h2>Telemetría interpretada</h2>

        <div class="telemetry-grid">
            <div class="metric">
                <div class="label">Estado general</div>
                <div class="value" id="stateText">---</div>
                <div class="description" id="stateDesc">Sin datos todavía.</div>
            </div>

            <div class="metric">
                <div class="label">Condición del variador</div>
                <div class="value" id="errorText">---</div>
                <div class="description" id="errorDesc">Sin datos todavía.</div>
            </div>

            <div class="metric">
                <div class="label">Velocidad solicitada</div>
                <div class="value info" id="freqCmd">---</div>
                <div class="description">Referencia enviada al sistema remoto.</div>
            </div>

            <div class="metric">
                <div class="label">Velocidad real de salida</div>
                <div class="value info" id="freqOut">---</div>
                <div class="description">Velocidad real reportada por la banda.</div>
            </div>

            <div class="metric">
                <div class="label">Carga aproximada del motor</div>
                <div class="value" id="currentText">---</div>
                <div class="description" id="currentDesc">Corriente de salida interpretada.</div>
            </div>

            <div class="metric">
                <div class="label">Resumen para operador</div>
                <div class="value" id="operatorText">---</div>
                <div class="description" id="operatorDesc">Mensaje simple de operación.</div>
            </div>
        </div>
    </div>

    <div class="card" style="margin-top:20px;">
        <h2>LiDAR - Distancia frontal</h2>

        <div class="telemetry-grid">
            <div class="metric">
                <div class="label">Detección frontal</div>
                <div class="value" id="lidarDetected">---</div>
                <div class="description" id="lidarDetectedDesc">Sin datos todavía.</div>
            </div>

            <div class="metric">
                <div class="label">Distancia mínima frontal</div>
                <div class="value info" id="lidarFrontMin">---</div>
                <div class="description">Objeto más cercano detectado al frente.</div>
            </div>

            <div class="metric">
                <div class="label">Promedio reciente</div>
                <div class="value info" id="lidarAvgRecent">---</div>
                <div class="description">Promedio usado para decidir si queda libre.</div>
            </div>

            <div class="metric">
                <div class="label">Hits en rango</div>
                <div class="value" id="lidarHits">---</div>
                <div class="description">Lecturas recientes menores al umbral.</div>
            </div>
        </div>
    </div>

    <div class="card" style="margin-top:20px;">
        <h2>YOLO - Inferencia</h2>

        <div class="telemetry-grid">
            <div class="metric">
                <div class="label">Objetos detectados</div>
                <div class="value" id="yoloCount">---</div>
                <div class="description" id="yoloObjects">Sin detecciones todavía.</div>
            </div>

            <div class="metric">
                <div class="label">Dispositivo</div>
                <div class="value info" id="yoloDevice">---</div>
                <div class="description">CPU/GPU usada por YOLO.</div>
            </div>
        </div>
    </div>

<script>
    let ws = null;

    function connectWS() {
        ws = new WebSocket(`ws://${location.host}/ws`);

        ws.onmessage = (event) => {
            const packet = JSON.parse(event.data || "{}");
            updateTelemetry(packet.telemetry || {});
            updateLidar(packet.lidar || {});
            updateYolo(packet.yolo || {});
        };

        ws.onclose = () => {
            setTimeout(connectWS, 1000);
        };

        ws.onerror = () => {
            try { ws.close(); } catch(e) {}
        };
    }

    connectWS();

    function setClass(element, cls) {
        element.className = "value " + cls;
    }

    function interpretState(state) {
        if (state === null || state === undefined) {
            return {
                text: "Sin datos",
                desc: "No se está recibiendo información.",
                cls: "warn",
                banner: "Esperando datos del sistema...",
                bannerClass: "banner-stop"
            };
        }

        if (state === 4) {
            return {
                text: "Detenida",
                desc: "La banda está lista, pero no está corriendo.",
                cls: "warn",
                banner: "Banda detenida",
                bannerClass: "banner-stop"
            };
        }

        if (state === 5) {
            return {
                text: "Avanzando",
                desc: "La banda está corriendo en dirección normal.",
                cls: "ok",
                banner: "Banda avanzando",
                bannerClass: "banner-run"
            };
        }

        if (state === 7) {
            return {
                text: "Corriendo",
                desc: "La banda está en movimiento.",
                cls: "ok",
                banner: "Banda en movimiento",
                bannerClass: "banner-run"
            };
        }

        return {
            text: `Estado ${state}`,
            desc: "Estado recibido. Requiere interpretación específica.",
            cls: "info",
            banner: `Estado del sistema: ${state}`,
            bannerClass: "banner-stop"
        };
    }

    function interpretError(error) {
        if (error === null || error === undefined) {
            return { text: "Sin datos", desc: "No se pudo leer el estado de error.", cls: "warn" };
        }

        if (error === 0) {
            return { text: "Normal", desc: "No hay errores activos.", cls: "ok" };
        }

        return { text: `Código ${error}`, desc: "El sistema reporta un código de error/estado.", cls: "bad" };
    }

    function interpretCurrent(currentRaw) {
        if (currentRaw === null || currentRaw === undefined) {
            return { text: "Sin lectura", desc: "No se pudo leer la corriente del motor.", cls: "warn" };
        }

        const ampsApprox = currentRaw / 10.0;

        if (currentRaw === 0) {
            return { text: "Sin carga", desc: "El motor no está consumiendo corriente significativa.", cls: "warn" };
        }

        if (currentRaw <= 8) {
            return { text: `${ampsApprox.toFixed(1)} A aprox.`, desc: "Carga baja. Operación normal.", cls: "ok" };
        }

        if (currentRaw <= 15) {
            return { text: `${ampsApprox.toFixed(1)} A aprox.`, desc: "Carga media.", cls: "warn" };
        }

        return { text: `${ampsApprox.toFixed(1)} A aprox.`, desc: "Carga alta. Revisar atoros o fricción.", cls: "bad" };
    }

    function operatorSummary(data) {
        const state = data.state;
        const error = data.error;
        const fout = data.freq_out_hz ?? 0;
        const current = data.current_raw ?? 0;

        if (error !== null && error !== undefined && error !== 0 && error !== 26) {
            return { text: "Revisar sistema", desc: "Hay un código de error activo.", cls: "bad" };
        }

        if (state === 4 || fout === 0) {
            return { text: "Lista para operar", desc: "La banda está detenida.", cls: "warn" };
        }

        if ((state === 5 || state === 7) && current <= 8) {
            return { text: "Operación normal", desc: "La banda se mueve correctamente.", cls: "ok" };
        }

        return { text: "Operando", desc: "La banda está en movimiento.", cls: "info" };
    }

    function updateTelemetry(data) {
        const stateInfo = interpretState(data.state);
        const errorInfo = interpretError(data.error);
        const currentInfo = interpretCurrent(data.current_raw);
        const opInfo = operatorSummary(data);

        const banner = document.getElementById("mainStatus");
        banner.innerText = stateInfo.banner;
        banner.className = "status-banner " + stateInfo.bannerClass;

        const stateText = document.getElementById("stateText");
        stateText.innerText = stateInfo.text;
        setClass(stateText, stateInfo.cls);
        document.getElementById("stateDesc").innerText = stateInfo.desc;

        const errorText = document.getElementById("errorText");
        errorText.innerText = errorInfo.text;
        setClass(errorText, errorInfo.cls);
        document.getElementById("errorDesc").innerText = errorInfo.desc;

        document.getElementById("freqCmd").innerText =
            data.freq_cmd_hz !== null && data.freq_cmd_hz !== undefined
                ? `${Number(data.freq_cmd_hz).toFixed(2)} Hz`
                : "---";

        document.getElementById("freqOut").innerText =
            data.freq_out_hz !== null && data.freq_out_hz !== undefined
                ? `${Number(data.freq_out_hz).toFixed(2)} Hz`
                : "---";

        const currentText = document.getElementById("currentText");
        currentText.innerText = currentInfo.text;
        setClass(currentText, currentInfo.cls);
        document.getElementById("currentDesc").innerText = currentInfo.desc;

        const operatorText = document.getElementById("operatorText");
        operatorText.innerText = opInfo.text;
        setClass(operatorText, opInfo.cls);
        document.getElementById("operatorDesc").innerText = opInfo.desc;
    }

    function updateLidar(data) {
        const detectedEl = document.getElementById("lidarDetected");
        const detectedDesc = document.getElementById("lidarDetectedDesc");

        if (data.detected === true) {
            detectedEl.innerText = "Objeto detectado";
            setClass(detectedEl, "bad");
            detectedDesc.innerText = "La lógica del LiDAR considera que hay un objeto presente.";
        } else if (data.detected === false) {
            detectedEl.innerText = "Libre";
            setClass(detectedEl, "ok");
            detectedDesc.innerText = "La zona frontal está libre.";
        } else {
            detectedEl.innerText = "---";
            setClass(detectedEl, "warn");
            detectedDesc.innerText = "Sin datos todavía.";
        }

        document.getElementById("lidarFrontMin").innerText =
            data.front_min_m !== null && data.front_min_m !== undefined
                ? `${Number(data.front_min_m).toFixed(3)} m`
                : "---";

        document.getElementById("lidarAvgRecent").innerText =
            data.avg_recent_m !== null && data.avg_recent_m !== undefined
                ? `${Number(data.avg_recent_m).toFixed(3)} m`
                : "---";

        document.getElementById("lidarHits").innerText =
            data.hits_in_range !== null && data.hits_in_range !== undefined
                ? `${data.hits_in_range}/${data.history_size ?? "?"}`
                : "---";
    }

    function updateYolo(data) {
        const count = data.count ?? 0;
        const objects = data.objects || [];

        const yoloCount = document.getElementById("yoloCount");
        yoloCount.innerText = `${count}`;
        setClass(yoloCount, count > 0 ? "ok" : "warn");

        if (objects.length > 0) {
            const text = objects.map(o =>
                `${o.class_name} (${Number(o.confidence).toFixed(2)})`
            ).join(", ");

            document.getElementById("yoloObjects").innerText = text;
        } else {
            document.getElementById("yoloObjects").innerText = "Sin objetos detectados.";
        }

        document.getElementById("yoloDevice").innerText = data.device || "---";
    }

    function cmd(action) {
        fetch("/cmd", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({action})
        });
    }

    function setSpeed(hz) {
        document.getElementById("speedLabel").innerText = hz;

        fetch("/cmd", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                action: "set_speed",
                hz: parseFloat(hz),
                speed_hz: parseFloat(hz)
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

    return {"ok": True, "queued": item}


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

    return {"ok": True, "received": data}


@app.get("/api/telemetry")
async def get_telemetry():
    return {
        "ok": True,
        "latest_telemetry": latest_telemetry,
    }


@app.get("/api/lidar")
async def get_lidar():
    return {
        "ok": True,
        "latest_lidar": latest_lidar,
    }


@app.post("/api/yolo")
async def receive_yolo(data: dict):
    global latest_yolo

    latest_yolo = data

    return {
        "ok": True,
        "received": data,
    }


@app.get("/api/yolo")
async def get_yolo():
    return {
        "ok": True,
        "latest_yolo": latest_yolo,
    }


@app.post("/api/yolo_frame")
async def receive_yolo_frame(request: Request):
    global latest_yolo_frame

    latest_yolo_frame = await request.body()

    return {
        "ok": True,
        "bytes": len(latest_yolo_frame),
    }


@app.post("/api/frame")
async def receive_frame(request: Request):
    global latest_frame

    latest_frame = await request.body()

    if ros_node is not None:
        ros_node.publish_camera_frame(latest_frame)

    return {
        "ok": True,
        "bytes": len(latest_frame),
    }


@app.get("/api/status")
async def status():
    return {
        "ok": True,
        "latest_telemetry": latest_telemetry,
        "latest_lidar": latest_lidar,
        "latest_yolo": latest_yolo,
        "latest_face_role": latest_face_role,
        "has_frame": latest_frame is not None,
        "has_yolo_frame": latest_yolo_frame is not None,
        "latest_command_seq": command_seq,
    }

@app.post("/api/face_role")
async def receive_face_role(data: dict):
    global latest_face_role

    latest_face_role = data

    return {
        "ok": True,
        "received": latest_face_role,
    }


@app.get("/api/face_role")
async def get_face_role():
    return {
        "ok": True,
        "latest_face_role": latest_face_role,
    }
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            await websocket.send_text(json.dumps({
                "telemetry": latest_telemetry,
                "lidar": latest_lidar,
                "yolo": latest_yolo,
                "face_role": latest_face_role,
                "has_frame": latest_frame is not None,
                "has_yolo_frame": latest_yolo_frame is not None,
                "latest_command_seq": command_seq,
            }))
            await asyncio.sleep(0.25)

    except WebSocketDisconnect:
        return

    except Exception:
        return


def mjpeg_generator():
    global latest_frame

    while True:
        if latest_frame is not None:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                latest_frame +
                b"\r\n"
            )

        time.sleep(0.05)


def yolo_mjpeg_generator():
    global latest_yolo_frame

    while True:
        if latest_yolo_frame is not None:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                latest_yolo_frame +
                b"\r\n"
            )

        time.sleep(0.05)


@app.get("/video")
def video():
    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/video_yolo")
def video_yolo():
    return StreamingResponse(
        yolo_mjpeg_generator(),
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
