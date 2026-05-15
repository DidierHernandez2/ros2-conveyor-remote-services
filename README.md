# ROS2 Conveyor Remote Services

Sistema de servicios remotos para una banda transportadora usando **ROS2 Jazzy**, **FastAPI**, **WebSockets** y **Webots**.

Este repositorio contiene únicamente la parte que corre en la **laptop con Ubuntu 24.04 + ROS2 Jazzy**:

- Dashboard remoto
- Servidor HTTP/API
- WebSocket para telemetría en tiempo real
- Simulación Webots tipo Digital Twin
- Publicación local de tópicos ROS2 para la simulación
- Recepción de datos enviados desde otra computadora/servicio remoto

> Este repositorio **no contiene el control físico del hardware real**.  
> El control físico de la banda se ejecuta en otra computadora, por ejemplo una Jetson con ROS2 Humble.

---

# Arquitectura general

```text
Laptop Ubuntu 24.04 + ROS2 Jazzy
Repositorio: ros2-conveyor-remote-services

├── Dashboard Web
├── API FastAPI
├── WebSocket
├── Webots Digital Twin
│
├── Publica:
│   ├── /conveyor/cmd
│   └── /conveyor/telemetry
│
└── Expone endpoints:
    ├── GET  /
    ├── POST /cmd
    ├── GET  /api/commands
    ├── POST /api/telemetry
    ├── POST /api/frame
    ├── GET  /api/status
    ├── GET  /video
    └── WS   /ws
```

La computadora remota que controla la banda real puede comunicarse con este repositorio usando HTTP:

```text
Servicio remoto / ROS2 Humble

GET  /api/commands      -> lee comandos pendientes
POST /api/telemetry     -> manda telemetría al dashboard y a Webots
POST /api/frame         -> manda imagen JPEG para el dashboard
```

---

# Requisitos

## Sistema recomendado

- Ubuntu 24.04
- ROS2 Jazzy Jalisco
- Python 3.12
- Git
- Webots

## Paquetes principales

- `conveyor_dashboard_remote`
- `conveyor_sim`

---

# Instalación desde cero

## 1. Instalar dependencias base

```bash
sudo apt update

sudo apt install -y \
  git \
  python3-pip \
  python3-venv \
  python3-full \
  python3-colcon-common-extensions \
  python3-rosdep \
  ros-jazzy-webots-ros2 \
  ros-jazzy-webots-ros2-driver
```

---

## 2. Inicializar rosdep

Si es la primera vez que usas `rosdep` en esta computadora:

```bash
sudo rosdep init
```

Después ejecuta:

```bash
rosdep update
```

Si `sudo rosdep init` indica que ya fue inicializado, no hay problema. Continúa con `rosdep update`.

---

# Clonar el repositorio

Ubícate en la carpeta donde quieras guardar el proyecto:

```bash
git clone https://github.com/DidierHernandez2/ros2-conveyor-remote-services.git
```

Entra al repositorio:

```bash
cd ros2-conveyor-remote-services
```

Este repositorio funciona directamente como workspace ROS2 porque contiene la carpeta:

```text
src/
```

La estructura esperada es:

```text
ros2-conveyor-remote-services/
├── src/
│   ├── conveyor_dashboard_remote/
│   └── conveyor_sim/
│
├── python_requirements.txt
├── jazzy_requirements.txt
├── README.md
└── .gitignore
```

---

# Crear entorno virtual de Python

Ubuntu 24 no permite instalar paquetes globales con `pip` sin romper el entorno del sistema.  
Por eso se usa un entorno virtual.

Desde la raíz del repositorio:

```bash
python3 -m venv venv
```

Activar el entorno virtual:

```bash
source venv/bin/activate
```

Cuando esté activo, en la terminal debe aparecer algo parecido a:

```text
(venv)
```

Actualizar `pip`:

```bash
pip install --upgrade pip
```

---

# Instalar dependencias Python

Con el entorno virtual activado:

```bash
pip install -r python_requirements.txt
```

Ejemplo de dependencias que puede contener `python_requirements.txt`:

```text
fastapi
uvicorn
requests
pillow
```

---

# Instalar dependencias ROS2 Jazzy

Primero activa ROS2 Jazzy:

```bash
source /opt/ros/jazzy/setup.bash
```

Luego instala dependencias ROS2 usando `rosdep`:

```bash
rosdep install --from-paths src --ignore-src -r -y
```

Si además quieres instalar dependencias listadas en `jazzy_requirements.txt` mediante `apt`, puedes usar:

```bash
sudo apt update
sudo apt install -y $(cat jazzy_requirements.txt)
```

---

# Compilar el proyecto

Desde la raíz del repositorio:

```bash
source venv/bin/activate
source /opt/ros/jazzy/setup.bash

colcon build --symlink-install
```

Después de compilar:

```bash
source install/setup.bash
```

---

# Comandos necesarios en cada terminal nueva

Cada vez que abras una terminal nueva para trabajar con este proyecto:

```bash
cd ros2-conveyor-remote-services

source venv/bin/activate
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

Si el repositorio está en otra ruta, reemplaza `ros2-conveyor-remote-services` por la ruta correcta.

---

# Ejecutar el dashboard remoto

En una terminal:

```bash
cd ros2-conveyor-remote-services

source venv/bin/activate
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch conveyor_dashboard_remote dashboard_remote.launch.py
```

Abrir en navegador:

```text
http://localhost:8000
```

---

# Ejecutar la simulación Webots

En otra terminal:

```bash
cd ros2-conveyor-remote-services

source venv/bin/activate
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch conveyor_sim conveyor_sim.launch.py
```

---

# Ejecutar dashboard y simulación al mismo tiempo

## Terminal 1 — Dashboard

```bash
cd ros2-conveyor-remote-services

source venv/bin/activate
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch conveyor_dashboard_remote dashboard_remote.launch.py
```

## Terminal 2 — Webots

```bash
cd ros2-conveyor-remote-services

source venv/bin/activate
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch conveyor_sim conveyor_sim.launch.py
```

---

# Tópicos ROS2 usados

## Comandos de banda

```text
/conveyor/cmd
```

Este tópico recibe comandos generados desde el dashboard.  
También lo usa la simulación para saber si debe avanzar, detenerse o cambiar de dirección.

---

## Telemetría

```text
/conveyor/telemetry
```

Este tópico recibe datos de telemetría enviados desde el endpoint `/api/telemetry`.  
La simulación usa esta información para comportarse como Digital Twin.

---

# Endpoints disponibles

El dashboard remoto expone los siguientes endpoints:

## Dashboard web

```text
GET /
```

Abre la interfaz web principal.

---

## Enviar comando

```text
POST /cmd
```

Ejemplo:

```bash
curl -X POST http://localhost:8000/cmd \
  -H "Content-Type: application/json" \
  -d '{"action":"forward"}'
```

Este endpoint:

1. Guarda el comando en una cola para que un servicio remoto pueda consultarlo.
2. Publica localmente el comando en `/conveyor/cmd`.

---

## Consultar comandos pendientes

```text
GET /api/commands?after=0
```

Ejemplo:

```bash
curl "http://localhost:8000/api/commands?after=0"
```

Este endpoint lo puede usar una computadora remota para leer comandos generados desde el dashboard.

---

## Recibir telemetría

```text
POST /api/telemetry
```

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "state": 7,
    "error": 0,
    "freq_cmd_hz": 30.0,
    "freq_out_hz": 28.5,
    "current_raw": 6,
    "timestamp": 123456
  }'
```

Este endpoint:

1. Actualiza la información mostrada en el dashboard.
2. Publica la telemetría en `/conveyor/telemetry`.

---

## Recibir imagen JPEG

```text
POST /api/frame
```

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/frame \
  -H "Content-Type: image/jpeg" \
  --data-binary "@/tmp/test_camera.jpg"
```

---

## Ver stream de video

```text
GET /video
```

Abrir en navegador:

```text
http://localhost:8000/video
```

---

## Estado del servidor

```text
GET /api/status
```

Ejemplo:

```bash
curl http://localhost:8000/api/status
```

---

## WebSocket

```text
WS /ws
```

Usado por el dashboard para mostrar telemetría en tiempo real.

---

# Pruebas locales sin computadora remota

Estas pruebas permiten validar el dashboard y la simulación sin tener conectada la computadora que controla la banda real.

---

## 1. Probar telemetría falsa

Con el dashboard corriendo:

```bash
curl -X POST http://localhost:8000/api/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "state": 7,
    "error": 0,
    "freq_cmd_hz": 30.0,
    "freq_out_hz": 28.5,
    "current_raw": 6,
    "timestamp": 123456
  }'
```

Verificar que se publique en ROS2:

```bash
ros2 topic echo /conveyor/telemetry
```

---

## 2. Probar comando falso

```bash
curl -X POST http://localhost:8000/cmd \
  -H "Content-Type: application/json" \
  -d '{"action":"forward"}'
```

Verificar que se publique en ROS2:

```bash
ros2 topic echo /conveyor/cmd
```

Verificar que quede disponible para un servicio remoto:

```bash
curl "http://localhost:8000/api/commands?after=0"
```

---

## 3. Probar imagen falsa

Instalar Pillow si no está instalado:

```bash
pip install pillow
```

Crear imagen de prueba:

```bash
python3 - << 'EOF'
from PIL import Image, ImageDraw

img = Image.new("RGB", (640, 360), color=(20, 20, 20))
draw = ImageDraw.Draw(img)
draw.text((220, 160), "PRUEBA CAMARA", fill=(255, 255, 255))
img.save("/tmp/test_camera.jpg")
EOF
```

Enviar imagen:

```bash
curl -X POST http://localhost:8000/api/frame \
  -H "Content-Type: image/jpeg" \
  --data-binary "@/tmp/test_camera.jpg"
```

Abrir en navegador:

```text
http://localhost:8000/video
```

---

# Conexión desde otra computadora

Para que una computadora remota pueda comunicarse con el dashboard, primero obtén la IP de la laptop:

```bash
hostname -I
```

Ejemplo:

```text
192.168.1.70
```

La computadora remota debe conectarse a:

```text
http://192.168.1.70:8000
```

---

# Acceso remoto con Cloudflare

Para exponer el dashboard públicamente:

```bash
cloudflared tunnel --url http://localhost:8000
```

Esto genera una URL pública para acceder al dashboard desde otra red.

---

# Solución de problemas

## Error: externally-managed-environment

Este error aparece cuando se intenta usar `pip` global en Ubuntu 24.

Solución:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r python_requirements.txt
```

---

## ROS2 no encuentra el paquete

Ejecutar:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

Verificar:

```bash
ros2 pkg list | grep conveyor
```

---

## Webots no abre

Verificar instalación:

```bash
webots --version
```

Verificar paquetes ROS2 Webots:

```bash
ros2 pkg list | grep webots
```

---

## El dashboard no abre

Verificar que el proceso esté corriendo:

```bash
curl http://localhost:8000/api/status
```

Verificar que no haya otro proceso usando el puerto 8000:

```bash
sudo lsof -i :8000
```

---

# Resumen rápido

```bash
git clone https://github.com/DidierHernandez2/ros2-conveyor-remote-services.git
cd ros2-conveyor-remote-services

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r python_requirements.txt

source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y

colcon build --symlink-install
source install/setup.bash
```

Ejecutar dashboard:

```bash
ros2 launch conveyor_dashboard_remote dashboard_remote.launch.py
```

Ejecutar simulación:

```bash
ros2 launch conveyor_sim conveyor_sim.launch.py
```
