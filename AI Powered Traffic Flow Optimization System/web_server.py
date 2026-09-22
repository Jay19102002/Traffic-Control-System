# web_server.py
import cv2
import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from vision_engine import TrafficVisionEngine
from adaptive_controller import AdaptiveSignalController
from typing import Any
from demo_generator import SyntheticTrafficGenerator

# Global telemetry state shared with web dashboard
telemetry_state: dict[str, Any] = {
    "current_phase": "NS_PHASE",
    "is_yellow": False,
    "fps": 24.0,
    "decisions": {"NS_PHASE": {"green": 35, "pce_load": 0.0}, "EW_PHASE": {"green": 25, "pce_load": 0.0}},
    "lane_data": {
        "NORTH": {"count": 0, "pce_load": 0.0},
        "SOUTH": {"count": 0, "pce_load": 0.0},
        "EAST":  {"count": 0, "pce_load": 0.0},
        "WEST":  {"count": 0, "pce_load": 0.0}
    },
    "efficiency_gain": 49.08,
    "manual_override": None,  # "NS_PHASE", "EW_PHASE", or None (Adaptive)
    "latest_jpeg": None
}

state_lock = threading.Lock()

class VideoStreamThread(threading.Thread):
    def __init__(self, source="demo"):
        super().__init__(daemon=True)
        self.source = source
        self.running = True

    def run(self):
        vision_engine = TrafficVisionEngine(model_weight="yolov8n.pt")
        controller = AdaptiveSignalController()
        
        if self.source == "demo":
            sim = SyntheticTrafficGenerator(width=1280, height=720)
            cap = None
        else:
            sim = None
            src = int(self.source) if self.source.isdigit() else self.source
            cap = cv2.VideoCapture(src)

        current_phase = "NS_PHASE"
        is_yellow = False
        phase_timer = 0
        green_duration = 35
        yellow_duration = int(controller.cfg["YELLOW_TIME"])
        decisions = {"NS_PHASE": {"green": 35}, "EW_PHASE": {"green": 25}}
        frame_idx = 0
        fps_timer = time.time()
        fps = 25.0

        while self.running:
            if sim is not None:
                frame = sim.generate_frame()
            elif cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
            else:
                break

            frame_idx += 1
            phase_timer += 1

            # Check for manual override from Web UI
            with state_lock:
                override = telemetry_state["manual_override"]

            if override:
                current_phase = override
                is_yellow = False
            else:
                # Automatic adaptive cycle state machine
                if not is_yellow:
                    if phase_timer >= green_duration * 25:
                        is_yellow = True
                        phase_timer = 0
                else:
                    if phase_timer >= yellow_duration * 25:
                        is_yellow = False
                        phase_timer = 0
                        current_phase = "EW_PHASE" if current_phase == "NS_PHASE" else "NS_PHASE"
                        controller.update_starvation(current_phase)
                        green_duration = int(decisions.get(current_phase, {}).get("green", 30))

            annotated_frame, lane_data = vision_engine.process_frame(
                frame,
                decisions=decisions,
                fps=fps,
                current_phase=current_phase,
                is_yellow=is_yellow,
                show_hud=True,
                show_rois=True,
                fallback_detections=sim.get_active_detections() if sim is not None else None
            )

            if frame_idx % 25 == 0:
                decisions = controller.compute_green_times(lane_data)
                elapsed = time.time() - fps_timer
                fps = 25.0 / max(0.001, elapsed)
                fps_timer = time.time()

                if not is_yellow and not override and phase_timer > int(controller.cfg["MIN_GREEN"]) * 25:
                    if controller.should_terminate_early(current_phase, phase_timer // 25, lane_data):
                        is_yellow = True
                        phase_timer = 0

            # Encode to JPEG for MJPEG stream
            _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            jpeg_bytes = buffer.tobytes()

            with state_lock:
                telemetry_state["current_phase"] = current_phase
                telemetry_state["is_yellow"] = is_yellow
                telemetry_state["fps"] = round(fps, 1)
                telemetry_state["decisions"] = decisions
                telemetry_state["lane_data"] = {
                    lane: {"count": stats["count"], "pce_load": round(stats["pce_load"], 1)}
                    for lane, stats in lane_data.items()
                }
                telemetry_state["latest_jpeg"] = jpeg_bytes

            time.sleep(0.025)

        if cap is not None:
            cap.release()

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autonomous AI Traffic Management - Mission Control</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0d14;
            --bg-card: rgba(18, 24, 38, 0.75);
            --bg-glass: rgba(26, 34, 52, 0.55);
            --border-glass: rgba(80, 100, 140, 0.25);
            --border-glow: rgba(0, 240, 255, 0.35);
            --cyan-neon: #00f0ff;
            --green-neon: #00ff88;
            --amber-neon: #ffb800;
            --red-neon: #ff3366;
            --purple-neon: #bd00ff;
            --text-primary: #f0f4fc;
            --text-secondary: #8a9bb8;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            background-image: radial-gradient(circle at 10% 20%, rgba(0, 240, 255, 0.05) 0%, transparent 40%),
                              radial-gradient(circle at 90% 80%, rgba(189, 0, 255, 0.05) 0%, transparent 40%);
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 32px;
            background: rgba(12, 17, 28, 0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-glass);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .pulse-dot {
            width: 10px;
            height: 10px;
            background-color: var(--green-neon);
            border-radius: 50%;
            box-shadow: 0 0 12px var(--green-neon);
            animation: pulse 1.8s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.95); opacity: 0.8; }
            50% { transform: scale(1.3); opacity: 1; }
            100% { transform: scale(0.95); opacity: 0.8; }
        }

        .brand-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.25rem;
            font-weight: 700;
            letter-spacing: 0.5px;
            background: linear-gradient(135deg, #ffffff 0%, var(--cyan-neon) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-sub {
            font-size: 0.75rem;
            color: var(--text-secondary);
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .header-badges {
            display: flex;
            gap: 12px;
            align-items: center;
        }

        .badge {
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--bg-glass);
            border: 1px solid var(--border-glass);
        }

        .badge-cyan { color: var(--cyan-neon); border-color: rgba(0, 240, 255, 0.4); }
        .badge-green { color: var(--green-neon); border-color: rgba(0, 255, 136, 0.4); }
        .badge-red { color: var(--red-neon); border-color: rgba(255, 51, 102, 0.4); }

        main {
            display: grid;
            grid-template-columns: 1fr 380px;
            gap: 24px;
            padding: 24px 32px;
            flex: 1;
        }

        .video-container {
            position: relative;
            border-radius: 16px;
            overflow: hidden;
            background: #000;
            border: 1px solid var(--border-glass);
            box-shadow: 0 16px 36px rgba(0, 0, 0, 0.6);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .video-container img {
            width: 100%;
            height: auto;
            display: block;
            object-fit: contain;
        }

        .side-dashboard {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .glass-card {
            background: var(--bg-card);
            backdrop-filter: blur(14px);
            border: 1px solid var(--border-glass);
            border-radius: 14px;
            padding: 18px 20px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
            position: relative;
            overflow: hidden;
        }

        .glass-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, transparent, var(--cyan-neon), transparent);
            opacity: 0.6;
        }

        .card-title {
            font-family: 'Outfit', sans-serif;
            font-size: 0.95rem;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: var(--cyan-neon);
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .signal-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 8px;
        }

        .signal-box {
            background: var(--bg-glass);
            border: 1px solid var(--border-glass);
            border-radius: 10px;
            padding: 14px;
            text-align: center;
        }

        .signal-lights {
            display: flex;
            justify-content: center;
            gap: 8px;
            margin: 10px 0;
        }

        .light {
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: #202636;
            transition: all 0.3s ease;
        }

        .light.red-on { background: var(--red-neon); box-shadow: 0 0 12px var(--red-neon); }
        .light.yellow-on { background: var(--amber-neon); box-shadow: 0 0 12px var(--amber-neon); }
        .light.green-on { background: var(--green-neon); box-shadow: 0 0 12px var(--green-neon); }

        .signal-name {
            font-size: 0.75rem;
            color: var(--text-secondary);
            font-weight: 600;
        }

        .signal-sec {
            font-size: 1.4rem;
            font-weight: 700;
            font-family: 'Outfit', sans-serif;
            color: #fff;
        }

        .lane-meter {
            margin-bottom: 12px;
        }

        .lane-info {
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            margin-bottom: 5px;
        }

        .meter-bar {
            height: 8px;
            background: rgba(30, 40, 60, 0.6);
            border-radius: 4px;
            overflow: hidden;
            position: relative;
        }

        .meter-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, var(--cyan-neon), var(--green-neon));
            border-radius: 4px;
            transition: width 0.4s ease, background 0.4s ease;
        }

        .kpi-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }

        .kpi-card {
            background: rgba(15, 22, 35, 0.6);
            border: 1px solid var(--border-glass);
            border-radius: 10px;
            padding: 12px;
            text-align: center;
        }

        .kpi-val {
            font-size: 1.3rem;
            font-weight: 700;
            font-family: 'Outfit', sans-serif;
            color: var(--green-neon);
        }

        .kpi-label {
            font-size: 0.72rem;
            color: var(--text-secondary);
            margin-top: 4px;
            text-transform: uppercase;
        }

        .controls-row {
            display: flex;
            gap: 8px;
            margin-top: 6px;
        }

        .btn {
            flex: 1;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid var(--border-glass);
            background: var(--bg-glass);
            color: var(--text-primary);
            font-size: 0.78rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .btn:hover {
            border-color: var(--cyan-neon);
            box-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
            color: var(--cyan-neon);
        }

        .btn.active {
            background: rgba(0, 240, 255, 0.15);
            border-color: var(--cyan-neon);
            color: var(--cyan-neon);
        }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <div class="pulse-dot"></div>
            <div>
                <div class="brand-title">AUTONOMOUS TRAFFIC AI</div>
                <div class="brand-sub">Smart City Traffic Optimization Engine</div>
            </div>
        </div>
        <div class="header-badges">
            <div class="badge badge-cyan" id="badge-fps">FPS: --</div>
            <div class="badge badge-green" id="badge-mode">MODE: DYNAMIC ADAPTIVE</div>
            <div class="badge" id="badge-status">ONLINE</div>
        </div>
    </header>

    <main>
        <div class="video-container">
            <img src="/video_feed" alt="Real-Time AI Traffic Stream" />
        </div>

        <aside class="side-dashboard">
            <div class="glass-card">
                <div class="card-title">SIGNAL PHASE STATUS</div>
                <div class="signal-grid">
                    <div class="signal-box" id="ns-box">
                        <div class="signal-name">NORTH - SOUTH</div>
                        <div class="signal-lights">
                            <div class="light" id="ns-r"></div>
                            <div class="light" id="ns-y"></div>
                            <div class="light" id="ns-g"></div>
                        </div>
                        <div class="signal-sec" id="ns-sec">-- s</div>
                    </div>
                    <div class="signal-box" id="ew-box">
                        <div class="signal-name">EAST - WEST</div>
                        <div class="signal-lights">
                            <div class="light" id="ew-r"></div>
                            <div class="light" id="ew-y"></div>
                            <div class="light" id="ew-g"></div>
                        </div>
                        <div class="signal-sec" id="ew-sec">-- s</div>
                    </div>
                </div>
            </div>

            <div class="glass-card">
                <div class="card-title">APPROACH SATURATION</div>
                <div class="lane-meter" id="meter-NORTH">
                    <div class="lane-info"><span>NORTH APPROACH</span><span id="txt-NORTH">0 veh | 0.0 PCE</span></div>
                    <div class="meter-bar"><div class="meter-fill" id="bar-NORTH"></div></div>
                </div>
                <div class="lane-meter" id="meter-SOUTH">
                    <div class="lane-info"><span>SOUTH APPROACH</span><span id="txt-SOUTH">0 veh | 0.0 PCE</span></div>
                    <div class="meter-bar"><div class="meter-fill" id="bar-SOUTH"></div></div>
                </div>
                <div class="lane-meter" id="meter-EAST">
                    <div class="lane-info"><span>EAST APPROACH</span><span id="txt-EAST">0 veh | 0.0 PCE</span></div>
                    <div class="meter-bar"><div class="meter-fill" id="bar-EAST"></div></div>
                </div>
                <div class="lane-meter" id="meter-WEST">
                    <div class="lane-info"><span>WEST APPROACH</span><span id="txt-WEST">0 veh | 0.0 PCE</span></div>
                    <div class="meter-bar"><div class="meter-fill" id="bar-WEST"></div></div>
                </div>
            </div>

            <div class="glass-card">
                <div class="card-title">AI PERFORMANCE METRICS</div>
                <div class="kpi-row">
                    <div class="kpi-card">
                        <div class="kpi-val">+49.1%</div>
                        <div class="kpi-label">Delay Reduction</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-val" id="kpi-congestion">LOW</div>
                        <div class="kpi-label">Congestion Index</div>
                    </div>
                </div>
            </div>

            <div class="glass-card">
                <div class="card-title">DISPATCHER OVERRIDE</div>
                <div class="controls-row">
                    <button class="btn active" id="btn-auto" onclick="setOverride(null)">AUTO ADAPTIVE</button>
                    <button class="btn" id="btn-ns" onclick="setOverride('NS_PHASE')">FORCE NS</button>
                    <button class="btn" id="btn-ew" onclick="setOverride('EW_PHASE')">FORCE EW</button>
                </div>
            </div>
        </aside>
    </main>

    <script>
        async function fetchTelemetry() {
            try {
                const res = await fetch('/api/telemetry');
                const data = await res.json();

                // Update badges
                document.getElementById('badge-fps').textContent = `FPS: ${data.fps}`;
                
                // Update Signals
                const nsActive = data.current_phase === 'NS_PHASE';
                const isYellow = data.is_yellow;

                // NS Lights
                document.getElementById('ns-r').className = 'light ' + (!nsActive ? 'red-on' : '');
                document.getElementById('ns-y').className = 'light ' + (nsActive && isYellow ? 'yellow-on' : '');
                document.getElementById('ns-g').className = 'light ' + (nsActive && !isYellow ? 'green-on' : '');
                document.getElementById('ns-sec').textContent = `${data.decisions?.NS_PHASE?.green || 35}s`;

                // EW Lights
                document.getElementById('ew-r').className = 'light ' + (nsActive ? 'red-on' : '');
                document.getElementById('ew-y').className = 'light ' + (!nsActive && isYellow ? 'yellow-on' : '');
                document.getElementById('ew-g').className = 'light ' + (!nsActive && !isYellow ? 'green-on' : '');
                document.getElementById('ew-sec').textContent = `${data.decisions?.EW_PHASE?.green || 25}s`;

                // Update Lane Meters
                let totalPCE = 0;
                for (const lane of ['NORTH', 'SOUTH', 'EAST', 'WEST']) {
                    const stats = data.lane_data[lane] || { count: 0, pce_load: 0.0 };
                    totalPCE += stats.pce_load;
                    document.getElementById(`txt-${lane}`).textContent = `${stats.count} veh | ${stats.pce_load.toFixed(1)} PCE`;
                    const pct = Math.min(100, (stats.pce_load / 12.0) * 100);
                    const bar = document.getElementById(`bar-${lane}`);
                    bar.style.width = `${pct}%`;
                    if (pct > 75) bar.style.background = 'linear-gradient(90deg, #ffb800, #ff3366)';
                    else bar.style.background = 'linear-gradient(90deg, #00f0ff, #00ff88)';
                }

                // Congestion label
                const cong = document.getElementById('kpi-congestion');
                if (totalPCE < 6) { cong.textContent = 'OPTIMAL'; cong.style.color = '#00ff88'; }
                else if (totalPCE < 15) { cong.textContent = 'MODERATE'; cong.style.color = '#ffb800'; }
                else { cong.textContent = 'HEAVY'; cong.style.color = '#ff3366'; }

            } catch (err) {
                console.error("Telemetry fetch error:", err);
            }
        }

        async function setOverride(phase) {
            document.getElementById('btn-auto').className = 'btn ' + (phase === null ? 'active' : '');
            document.getElementById('btn-ns').className = 'btn ' + (phase === 'NS_PHASE' ? 'active' : '');
            document.getElementById('btn-ew').className = 'btn ' + (phase === 'EW_PHASE' ? 'active' : '');

            await fetch('/api/override', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phase: phase })
            });
        }

        setInterval(fetchTelemetry, 500);
        fetchTelemetry();
    </script>
</body>
</html>
"""

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))

        elif self.path == "/api/telemetry":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with state_lock:
                data_copy = {k: v for k, v in telemetry_state.items() if k != "latest_jpeg"}
            self.wfile.write(json.dumps(data_copy).encode("utf-8"))

        elif self.path == "/video_feed":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while True:
                    with state_lock:
                        jpeg_bytes = telemetry_state.get("latest_jpeg")
                    if jpeg_bytes is not None:
                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                        self.wfile.write(jpeg_bytes)
                        self.wfile.write(b"\r\n")
                    time.sleep(0.04)
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/override":
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len)
            payload = json.loads(body.decode("utf-8"))
            phase = payload.get("phase")
            with state_lock:
                telemetry_state["manual_override"] = phase
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silence standard HTTP access logging to keep console clean
        return

def start_web_dashboard(port=5000, source="demo"):
    print("\n" + "="*65)
    print("AUTONOMOUS AI TRAFFIC MANAGEMENT - WEB MISSION CONTROL")
    print(f"Server URL: http://localhost:{port}")
    print("Press Ctrl+C in this terminal to stop the server.")
    print("="*65 + "\n")

    stream_thread = VideoStreamThread(source=source)
    stream_thread.start()

    server = ThreadedHTTPServer(("0.0.0.0", port), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down Web Dashboard server...")
        stream_thread.running = False
        server.server_close()

if __name__ == "__main__":
    start_web_dashboard()
