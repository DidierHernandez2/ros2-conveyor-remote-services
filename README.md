# Sistema Conveyor Digital Twin — ROS2 Jazzy + Dashboard Remoto + Webots

## Descripción

Este proyecto implementa un sistema modular para supervisar y simular una banda transportadora real usando:

- ROS2 Jazzy
- FastAPI
- WebSocket
- Webots
- Dashboard remoto
- Simulación tipo Digital Twin
- Comunicación HTTP con una computadora en ROS2 Humble

La laptop con **Ubuntu 24.04 + ROS2 Jazzy** ejecuta el dashboard y la simulación.  
La computadora con **ROS2 Humble** controla la banda real y manda datos hacia este sistema.

---

# Arquitectura general

```text
Laptop Ubuntu 24.04 + ROS2 Jazzy
Repositorio clonado

├── src/
│   ├── conveyor_dashboard_remote/
│   └── conveyor_sim/
│
├── python_requirements.txt
└── jazzy_requirements.txt
```

Flujo de comunicación:

```text
Dashboard Web
     │
     ▼
FastAPI / WebSocket
     │
     ├── Publica /conveyor/cmd
     ├── Publica /conveyor/telemetry
     ├── Expone /api/commands
     ├── Recibe /api/telemetry
     └── Recibe /api/frame

     │
     ▼

Webots Digital Twin
     │
     ├── Escucha /conveyor/cmd
     └── Escucha /conveyor/telemetry


ROS2 Humble / Banda real
     │
     ├── Consulta comandos desde /api/commands
     ├── Manda telemetría a /api/telemetry
     └── Manda cámara a /api/frame
```

---

# Requisitos

- Ubuntu 24.04
- ROS2 Jazzy
- Python 3
- Git
- Webots

---

# Instalación desde cero

## 1. Instalar dependencias base del sistema

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

Si nunca se ha inicializado `rosdep` en la computadora:

```bash
sudo rosdep init
```

Después ejecutar:

```bash
rosdep update
```

Si `sudo rosdep init` dice que ya existe, no pasa nada. Continúa con `rosdep update`.

---

## 3. Clonar repositorio

Desde cualquier carpeta donde se quiera guardar el proyecto:

```bash
git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
```

Entrar al repositorio clonado:

```bash
cd TU_REPOSITORIO
```

A partir de este punto, el repositorio clonado será el workspace ROS2.

La estructura debe verse similar a:

```text
TU_REPOSITORIO/
├── src/
├── python_requirements.txt
└── jazzy_requirements.txt
```

---

# Configuración de Python

Ubuntu 24 no permite instalar paquetes Python globalmente con `pip`.  
Por eso se debe usar un entorno virtual (`venv`) dentro del repositorio.

---

## 4. Crear entorno virtual

Dentro del repositorio clonado:

```bash
python3 -m venv venv
```

---

## 5. Activar entorno virtual

```bash
source venv/bin/activate
```

Si se activó correctamente, aparecerá algo como:

```text
(venv)
```

al inicio de la terminal.

---

## 6. Actualizar pip

```bash
pip install --upgrade pip
```

---

## 7. Instalar dependencias Python

```bash
pip install -r python_requirements.txt
```

---

# Configuración ROS2 Jazzy

## 8. Activar ROS2 Jazzy

```bash
source /opt/ros/jazzy/setup.bash
```

---

## 9. Instalar dependencias ROS2 del proyecto

Desde la raíz del repositorio clonado:

```bash
rosdep install --from-paths src --ignore-src -r -y
```

---

# Compilar proyecto

## 10. Compilar workspace

Desde la raíz del repositorio clonado:

```bash
colcon build --symlink-install
```

---

## 11. Activar workspace compilado

```bash
source install/setup.bash
```

---

# Comandos que se deben ejecutar en cada terminal nueva

Cada vez que se abra una terminal nueva para usar este proyecto:

```bash
cd RUTA/AL/REPOSITORIO_CLONADO

source venv/bin/activate
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

Ejemplo:

```bash
cd ~/Documentos/TU_REPOSITORIO

source venv/bin/activate
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

---

# Ejecutar dashboard remoto

Abrir una terminal y ejecutar:

```bash
cd RUTA/AL/REPOSITORIO_CLONADO

source venv/bin/activate
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch conveyor_dashboard_remote dashboard_remote.launch.py
```

Abrir en el navegador:

```text
http://localhost:8000
```

---

# Ejecutar simulación Webots

Abrir otra terminal y ejecutar:

```bash
cd RUTA/AL/REPOSITORIO_CLONADO

source venv/bin/activate
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch conveyor_sim conveyor_sim.launch.py
```

---

# Ver tópicos ROS2

## Ver todos los tópicos

```bash
ros2 topic list
```

---

## Ver comandos de la banda

```bash
ros2 topic echo /conveyor/cmd
```

---

## Ver telemetría de la banda

```bash
ros2 topic echo /conveyor/telemetry
```

---

# Pruebas locales sin Humble

Estas pruebas permiten verificar que el dashboard y la simulación funcionan aunque todavía no esté conectada la computadora con Humble.

---

## Probar telemetría falsa

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

Después revisar:

```bash
ros2 topic echo /conveyor/telemetry
```

---

## Probar comando falso

```bash
curl -X POST http://localhost:8000/cmd \
  -H "Content-Type: application/json" \
  -d '{"action":"forward"}'
```

Después revisar:

```bash
ros2 topic echo /conveyor/cmd
```

---

## Ver comandos pendientes para Humble

```bash
curl "http://localhost:8000/api/commands?after=0"
```

---

# Conexión con computadora Humble

Para que Humble pueda conectarse al dashboard, primero obtener la IP de la laptop Jazzy:

```bash
hostname -I
```

Ejemplo:

```text
192.168.1.70
```

La computadora con Humble debe usar esta URL:

```text
http://192.168.1.70:8000
```

---

# Endpoints disponibles

El dashboard remoto expone:

```text
GET  /                  Dashboard web
POST /cmd               Recibe comandos desde el dashboard
GET  /api/commands      Humble consulta comandos pendientes
POST /api/telemetry     Humble manda telemetría real
POST /api/frame         Humble manda imagen JPEG
GET  /api/status        Estado del servidor
GET  /video             Streaming MJPEG de cámara
WS   /ws                Telemetría en tiempo real
```

---

# Cloudflare Tunnel

Para exponer el dashboard públicamente:

```bash
cloudflared tunnel --url http://localhost:8000
```

Esto generará una URL pública para acceder al dashboard desde otra red.

---

# Flujo recomendado de ejecución

## Terminal 1 — Dashboard remoto

```bash
cd RUTA/AL/REPOSITORIO_CLONADO

source venv/bin/activate
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch conveyor_dashboard_remote dashboard_remote.launch.py
```

---

## Terminal 2 — Simulación Webots

```bash
cd RUTA/AL/REPOSITORIO_CLONADO

source venv/bin/activate
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch conveyor_sim conveyor_sim.launch.py
```

---

## Terminal 3 — Monitoreo de telemetría

```bash
cd RUTA/AL/REPOSITORIO_CLONADO

source venv/bin/activate
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 topic echo /conveyor/telemetry
```

---

# Notas importantes

- El repositorio clonado funciona como el workspace ROS2.
- No se debe crear otro workspace aparte.
- La carpeta `src/` debe estar directamente dentro del repositorio.
- No usar `pip install` global en Ubuntu 24.
- Usar siempre el entorno virtual `venv`.
- Activar ROS2 Jazzy antes de compilar.
- Activar `install/setup.bash` después de compilar.
- El dashboard corre en el puerto `8000`.
- Humble y Jazzy no se comunican por DDS directo.
- La comunicación Humble/Jazzy se hace por HTTP.
- Webots funciona como Digital Twin de la banda real.
