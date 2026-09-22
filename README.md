# 🚦 Autonomous AI Traffic Flow Optimization & Control System

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8n-00FFFF.svg)](https://docs.ultralytics.com/)
[![SUMO](https://img.shields.io/badge/Simulator-Eclipse%20SUMO-orange.svg)](https://eclipse.dev/sumo/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.8%2B-red.svg)](https://opencv.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An intelligent, real-time traffic signal optimization platform powered by **Computer Vision (YOLOv8 + ByteTrack)** and **Adaptive Saturation Control (Webster's Delay Formulation & Actuated Gap-Out Logic)**. 

The system analyzes continuous CCTV, drone, or IP camera video streams, classifies multi-modal traffic into Passenger Car Equivalents (PCE), tracks lane queues in customizable Regions of Interest (ROIs), and dynamically allocates green times to eliminate congestion, cut vehicle idling, and minimize carbon emissions.

---

## 📑 Table of Contents
1. [Key Features](#-key-features)
2. [System Architecture](#-system-architecture)
3. [Step-by-Step Guidance](#-step-by-step-guidance)
   - [Prerequisites](#prerequisites)
   - [1. Environment Setup](#1-environment-setup)
   - [2. Installing Dependencies](#2-installing-dependencies)
   - [3. Running the System](#3-running-the-system)
     - [Mode A: Zero-Hardware Synthetic Demonstration](#mode-a-zero-hardware-synthetic-demonstration)
     - [Mode B: Live Web Telemetry Dashboard](#mode-b-live-web-telemetry-dashboard)
     - [Mode C: Live Video Feed / USB Webcam / RTSP](#mode-c-live-video-feed--usb-webcam--rtsp)
     - [Mode D: Micro-Simulation Comparative Benchmark](#mode-d-micro-simulation-comparative-benchmark)
4. [Dataset & Simulation Details](#-dataset--simulation-details)
   - [Detection & Classification Classes](#detection--classification-classes)
   - [Passenger Car Equivalent (PCE) Weights](#passenger-car-equivalent-pce-weights)
   - [SUMO Simulation Demand & Network Topology](#sumo-simulation-demand--network-topology)
   - [Recommended Benchmark Datasets](#recommended-benchmark-datasets)
5. [Configuration & Lane Calibration](#-configuration--lane-calibration)
6. [Deployment Guide](#-deployment-guide)
   - [Edge AI Deployment (NVIDIA Jetson / TensorRT)](#edge-ai-deployment-nvidia-jetson--tensorrt)
   - [Docker Containerization](#docker-containerization)
   - [Physical Traffic Controller Interfacing](#physical-traffic-controller-interfacing)
7. [Reference Links & Research Citations](#-reference-links--research-citations)

---

## 🌟 Key Features

- **Real-Time Multi-Object Tracking**: Uses YOLOv8 paired with ByteTrack (`bytetrack.yaml`) to persist vehicle IDs across occlusions and dynamic camera views.
- **PCE-Weighted Saturation Metrics**: Accommodates diverse vehicle dynamics by weighting cars (1.0), motorcycles (0.5), buses (2.5), and heavy trucks (2.5) to reflect true road occupancy.
- **Anti-Starvation & EMA Smoothing**: Utilizes Exponential Moving Average ($\alpha=0.35$) with anti-starvation boost (+20% load weight per skipped cycle) to protect minor lanes from endless red lights.
- **Actuated Gap-Out Logic**: Automatically triggers yellow transition early if an active phase's queue discharges before max green duration expires, saving green time for waiting cross-traffic.
- **Dual Simulation Engine**:
  - **Eclipse SUMO & TraCI**: Native micro-simulation evaluating waiting delays and queue metrics.
  - **Self-Contained Micro-Engine**: Built-in fallback simulator allowing full comparative benchmarking even without SUMO installed.
- **Glassmorphism Web Mission Control**: Integrated HTTP/MJPEG streaming server with real-time HUD telemetry, phase charts, and manual override capabilities.
- **Zero-Dependency Synthetic Canvas**: Built-in procedural traffic generator for live demonstrations and testing without physical cameras or video files.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Ingestion["1. Video Ingestion & Sensing"]
        CAM["CCTV / Webcam / RTSP / Drone"] --> PRE["Frame Preprocessing"]
        SYN["Synthetic Traffic Generator"] --> PRE
    end

    subgraph Perception["2. Deep Learning Perception"]
        PRE --> YOLO["YOLOv8 Object Detector (yolov8n.pt)"]
        YOLO --> TRACK["ByteTrack Multi-Object Tracker"]
        TRACK --> ROI["Lane Polygon ROI Spatial Mapping"]
        ROI --> PCE["PCE Weighted Load Calculation"]
    end

    subgraph Control["3. Adaptive Decision Engine"]
        PCE --> EMA["Exponential Moving Average (EMA) Demand Filter"]
        EMA --> STARV["Starvation Prevention Compensator"]
        STARV --> SPLIT["Dynamic Green Time Allocation (Webster Model)"]
        SPLIT --> GAP["Actuated Gap-Out Early Termination"]
    end

    subgraph Actuation["4. Interface & Actuation"]
        GAP --> HUD["Tactical HUD Canvas Overlay"]
        GAP --> WEB["Web Mission Control Dashboard (Port 5000)"]
        GAP --> TRACI["SUMO TraCI / Physical Signal Controller"]
    end
```

---

## 🚀 Step-by-Step Guidance

### Prerequisites
- **Operating System**: Windows 10/11, Ubuntu 20.04+, or macOS
- **Python**: Version 3.10 to 3.12
- **Hardware**: CPU (Intel/AMD) or NVIDIA GPU with CUDA support for accelerated inference
- **Optional**: [Eclipse SUMO](https://eclipse.dev/sumo/) (v1.19.0+) for native TraCI simulation

---

### 1. Environment Setup

Clone the repository and set up a clean Python virtual environment:

```bash
# Clone the repository
git clone https://github.com/your-org/ai-traffic-system.git
cd "ai-traffic-system"

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Windows (Command Prompt):
.\.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate
```

---

### 2. Installing Dependencies

Install the verified dependencies listed in `requirements.txt`:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> [!NOTE]
> The default configuration downloads and executes `yolov8n.pt` (Nano). For GPU acceleration, ensure PyTorch with CUDA support is installed:
> ```bash
> pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
> ```

---

### 3. Running the System

The main entry point is [`main.py`](file:///d:/AI%20Traffic%20System/main.py), supporting multiple operational modes:

#### Mode A: Zero-Hardware Synthetic Demonstration
Runs an interactive visual simulation with synthetic vehicles, real-time YOLO tracking, and dynamic signal phase changes:

```bash
python main.py --demo
```

**Interactive HUD Controls:**
| Key | Action | Description |
|---|---|---|
| `Q` or `ESC` | **Quit** | Exits the live demo window |
| `H` | **Toggle HUD** | Shows or hides the futuristic operations overlay |
| `R` | **Toggle ROIs** | Toggles lane detection boundary polygons |
| `SPACE` | **Pause / Resume** | Freezes the stream for visual analysis |
| `S` | **Snapshot** | Saves a high-resolution tagged frame to `snapshots/` |

---

#### Mode B: Live Web Telemetry Dashboard
Launches the browser-based mission control console featuring live video streaming, approach load bars, and manual signal overrides:

```bash
python main.py --web
```
Or directly:
```bash
python web_server.py
```
Open your web browser and navigate to:
```
http://localhost:5000
```

**Dashboard Features:**
- **Live Stream**: Real-time MJPEG feed with vehicle reticles and HUD.
- **Phase Status**: Live signal state (NS Green, EW Green, Transition Yellow) with countdown timer.
- **Lane Analytics**: Real-time PCE queue loads for North, South, East, and West approaches.
- **Manual Override Controls**: Buttons to force North-South green, East-West green, or restore autonomous AI control.

---

#### Mode C: Live Video Feed / USB Webcam / RTSP
To process an attached USB webcam:
```bash
python main.py --source 0
```

To process a pre-recorded traffic video file:
```bash
python main.py --source traffic_sample.mp4
```

To ingest an IP Camera RTSP feed:
```bash
python main.py --source "rtsp://username:password@192.168.1.100:554/live/ch0"
```

---

#### Mode D: Micro-Simulation Comparative Benchmark
Runs a rigorous 1,000-second micro-simulation comparing **Traditional Fixed-Time Control** against **Adaptive AI Control**:

```bash
python main.py --sumo
```

To launch Eclipse SUMO with a graphical visualizer (requires Eclipse SUMO installed):
```bash
python main.py --sumo --gui
```

**Sample Benchmark Output:**
```
Executing comparative benchmark...
[Running Native SUMO Micro-Simulation | Mode: FIXED]
Step: 1000 | Active Vehicles: 42 | Cumulative Delay: 29842.0s
[Running Native SUMO Micro-Simulation | Mode: ADAPTIVE]
Step: 1000 | Active Vehicles: 14 | Cumulative Delay: 15195.5s

[SUMMARY] Fixed Delay: 29.8s | Adaptive Delay: 15.2s | Efficiency Gain: 49.08%
```

---

## 📊 Dataset & Simulation Details

### Detection & Classification Classes
The vision engine utilizes weights pre-trained on the **MS COCO (Common Objects in Context)** dataset, filtering detections to relevant vehicular classes:

| Class ID | Class Name | Base Dataset | Description |
|---|---|---|---|
| **`2`** | `car` | MS COCO | Standard passenger cars, sedans, hatchbacks, SUVs |
| **`3`** | `motorcycle` | MS COCO | Motorcycles, scooters, mopeds |
| **`5`** | `bus` | MS COCO | Transit buses, school buses, coaches |
| **`7`** | `truck` | MS COCO | Box trucks, delivery vans, articulated freight trucks |

### Passenger Car Equivalent (PCE) Weights
In urban traffic engineering (Highway Capacity Manual standards), different vehicles consume varying amounts of road space and acceleration capacity. The controller uses the following standard PCE weights:

$$\text{PCE Load} = \sum_{i \in \text{Vehicles}} w_i$$

- **Motorcycle / Bike**: $0.5 \times \text{PCE}$
- **Passenger Car**: $1.0 \times \text{PCE}$
- **Transit Bus**: $2.5 \times \text{PCE}$
- **Freight Truck**: $2.5 \times \text{PCE}$

---

### SUMO Simulation Demand & Network Topology
The microscopic simulation environment is defined in [`sumo_env/`](file:///d:/AI%20Traffic%20System/sumo_env):

- **Network Topology (`cross.nod.xml`, `cross.edg.xml`)**:
  - A symmetrical 4-leg intersection with 300m approach arms (`north`, `south`, `east`, `west`) connecting to a central traffic light node (`center`).
  - 2 inbound lanes and 2 outbound lanes per arm.
  - Speed limit: $13.89\text{ m/s}$ ($50\text{ km/h}$).
- **Traffic Demand (`cross.rou.xml`)**:
  - Configured with intentional **asymmetric demand** to test adaptive balancing:
    - **North-to-South (`flow_NS`)**: High demand (1 car every 3 seconds)
    - **South-to-North (`flow_SN`)**: Moderate-high demand (1 car every 4 seconds)
    - **East-to-West (`flow_EW`)**: Low demand (1 car every 10 seconds)
    - **West-to-East (`flow_WE`)**: Heavy truck freight flow (1 truck every 12 seconds)

---

### Recommended Benchmark Datasets
For fine-tuning YOLO models on domain-specific surveillance angles or training Reinforcement Learning (RL) agents:

1. **[UA-DETRAC](https://detrac-db.rit.albany.edu/)**: High-quality benchmark consisting of 100 video sequences recorded at intersections across varied weather and lighting conditions.
2. **[BDD100K](https://www.vis.xyz/bdd100k/)**: Diverse driving dataset covering urban, highway, daytime, night, and rainy scenes.
3. **[CityFlow](https://cityflow-project.github.io/)**: City-scale multi-intersection traffic dataset with ground-truth vehicle counts and travel times.
4. **[KITTI Vision Benchmark](https://www.cvlibs.net/datasets/kitti/)**: Canonical autonomous driving dataset for 2D/3D object detection.

---

## ⚙️ Configuration & Lane Calibration

All operational parameters are centralized in [`config.py`](file:///d:/AI%20Traffic%20System/config.py):

### 1. Signal Timing Constraints
```python
TIMING_CONFIG = {
    "MIN_GREEN": 10,       # Minimum green duration (pedestrian clearance & driver safety)
    "MAX_GREEN": 60,       # Maximum allowable green to prevent queue starvation
    "YELLOW_TIME": 4,      # Fixed yellow change interval
    "ALL_RED_TIME": 2,     # Inter-green safety clearance
    "DEFAULT_CYCLE": 90,   # Nominal cycle time budget (seconds)
}
```

### 2. Calibrating Lane ROIs
To adjust detection zones for your specific camera installation, modify the quadrilateral polygons in `DEFAULT_ROIS` in `config.py` (coordinates based on 1280x720 resolution; coordinates scale automatically to other resolutions):

```python
DEFAULT_ROIS = {
    "NORTH": np.array([[520, 100], [660, 100], [620, 360], [450, 360]], dtype=np.int32),
    "SOUTH": np.array([[640, 480], [860, 480], [920, 720], [600, 720]], dtype=np.int32),
    "EAST":  np.array([[700, 320], [1150, 300], [1150, 500], [680, 450]], dtype=np.int32),
    "WEST":  np.array([[100, 350], [450, 350], [480, 500], [100, 550]], dtype=np.int32)
}
```

---

## 🚢 Deployment Guide

### Edge AI Deployment (NVIDIA Jetson / TensorRT)

For roadside cabinet deployment on embedded hardware such as NVIDIA Jetson Orin Nano, Xavier, or IGX:

1. **Export YOLOv8 to TensorRT Engine**:
   ```bash
   yolo export model=yolov8n.pt format=engine device=0 half=True
   ```
2. **Update Engine in Code**:
   In `vision_engine.py`, instantiate the model with the compiled engine file:
   ```python
   vision_engine = TrafficVisionEngine(model_weight="yolov8n.engine")
   ```
3. **Connect IP Camera Streams**:
   Pass the RTSP URL via systemd or environment configuration.

---

### Docker Containerization

Deploy the web telemetry dashboard and vision pipeline inside a portable container:

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OpenCV and networking
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    sumo \
    sumo-tools \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "main.py", "--web"]
```

Build and run:
```bash
docker build -t ai-traffic-system .
docker run -d -p 5000:5000 --name traffic-control ai-traffic-system
```

---

### Physical Traffic Controller Interfacing

To interface this system with commercial physical intersection controllers (NEMA TS2, 170/2070, or ATC controllers):
- **GPIO / Relay Interface**: Use industrial relay boards (e.g., Modbus RTU or Advantech ADAM modules) triggered via Python when `current_phase` transitions occur.
- **NTCIP Protocol**: Connect via UDP/IP using NTCIP 1202 (National Transportation Communications for Intelligent Transportation System Protocol for Actuated Traffic Signal Controller Units).
- **MQTT / Webhooks**: Broadcast phase change events over MQTT to roadside edge gateways.

---

## 📚 Reference Links & Research Citations

### Computer Vision & Tracking
- **Ultralytics YOLOv8**: [https://docs.ultralytics.com](https://docs.ultralytics.com)
- **ByteTrack (ECCV 2022)**: *Zhang et al., "ByteTrack: Multi-Object Tracking by Associating Every Detection Box"*, [arXiv:2110.06864](https://arxiv.org/abs/2110.06864)
- **OpenCV Documentation**: [https://docs.opencv.org/](https://docs.opencv.org/)

### Traffic Engineering & Microscopic Simulation
- **Eclipse SUMO (Simulation of Urban MObility)**: [https://eclipse.dev/sumo/](https://eclipse.dev/sumo/)
- **TraCI (Traffic Control Interface)**: [https://sumo.dlr.de/docs/TraCI.html](https://sumo.dlr.de/docs/TraCI.html)
- **Webster's Signal Timing Model**: *Webster, F.V., "Traffic Signal Settings", Road Research Technical Paper No. 39, London, 1958.*
- **Highway Capacity Manual (HCM 6th Edition)**: Transportation Research Board, Washington D.C.

### Reinforcement Learning & Multi-Intersection Extensions
- **CityFlow Simulation Platform**: [https://cityflow-project.github.io/](https://cityflow-project.github.io/)
- **SUMO-RL Environment**: [https://github.com/LucasAlegre/sumo-rl](https://github.com/LucasAlegre/sumo-rl)
- **Stable-Baselines3**: [https://stable-baselines3.readthedocs.io/](https://stable-baselines3.readthedocs.io/)

---

## 📄 License
This project is released under the [MIT License](LICENSE). Contributions, issues, and feature requests are welcome!

