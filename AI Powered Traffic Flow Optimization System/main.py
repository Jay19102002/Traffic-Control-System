# main.py
import cv2
import argparse
import time
import os
from datetime import datetime
from vision_engine import TrafficVisionEngine
from adaptive_controller import AdaptiveSignalController

def run_video_pipeline(video_path, display=True, max_frames=None):
    print(f"\n[Starting Traffic Vision Engine on: {video_path}]")
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"\n[ERROR] Could not open video source: '{video_path}'")
        print("Possible solutions:")
        print("  1. Connect a USB webcam (default index 0)")
        print("  2. Specify a valid video file: python main.py --source traffic_sample.mp4")
        print("  3. Run the interactive visual demonstration: python main.py --demo")
        print("  4. Run the micro-simulation benchmark: python main.py --sumo\n")
        return

    vision_engine = TrafficVisionEngine(model_weight="yolov8n.pt")
    controller = AdaptiveSignalController()

    frame_idx = 0
    fps_timer = time.time()
    fps = 25.0

    # Real-time traffic signal state machine
    current_phase = "NS_PHASE"
    is_yellow = False
    phase_timer = 0
    green_duration = 35
    yellow_duration = int(controller.cfg["YELLOW_TIME"])
    decisions = {
        "NS_PHASE": {"green": 35, "pce_load": 0.0},
        "EW_PHASE": {"green": 25, "pce_load": 0.0}
    }

    # UI display flags
    show_hud = True
    show_rois = True
    paused = False
    annotated_frame = None

    try:
        while cap.isOpened():
            if max_frames is not None and frame_idx >= max_frames:
                break

            if not paused:
                ret, frame = cap.read()
                if not ret:
                    print("[INFO] Video feed reached end of stream.")
                    break

                frame_idx += 1
                phase_timer += 1

                # Signal state machine progression (~30 frames per second)
                if not is_yellow:
                    if phase_timer >= green_duration * 30:
                        is_yellow = True
                        phase_timer = 0
                else:
                    if phase_timer >= yellow_duration * 30:
                        is_yellow = False
                        phase_timer = 0
                        current_phase = "EW_PHASE" if current_phase == "NS_PHASE" else "NS_PHASE"
                        controller.update_starvation(current_phase)
                        green_duration = int(decisions.get(current_phase, {}).get("green", 30))

                # Process detection, tracking, and render advanced HUD
                annotated_frame, lane_data = vision_engine.process_frame(
                    frame,
                    decisions=decisions,
                    fps=fps,
                    current_phase=current_phase,
                    is_yellow=is_yellow,
                    show_hud=show_hud,
                    show_rois=show_rois
                )

                # Periodic dynamic decision update (~every 1 second / 30 frames)
                if frame_idx % 30 == 0:
                    decisions = controller.compute_green_times(lane_data)
                    elapsed = time.time() - fps_timer
                    fps = 30.0 / max(0.001, elapsed)
                    fps_timer = time.time()

                    # Actuated gap-out check during green phase
                    if not is_yellow and phase_timer > int(controller.cfg["MIN_GREEN"]) * 30:
                        if controller.should_terminate_early(current_phase, phase_timer // 30, lane_data):
                            is_yellow = True
                            phase_timer = 0

            if display and annotated_frame is not None:
                cv2.imshow("Autonomous AI Traffic System - Mission Control", annotated_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # 'q' or ESC
                    print("\n[INFO] Stopped by user.")
                    break
                elif key == ord('h') or key == ord('H'):
                    show_hud = not show_hud
                elif key == ord('r') or key == ord('R'):
                    show_rois = not show_rois
                elif key == ord(' '):
                    paused = not paused
                    print(f"[INFO] Feed {'PAUSED' if paused else 'RESUMED'}")
                elif key == ord('s') or key == ord('S'):
                    os.makedirs("snapshots", exist_ok=True)
                    fname = f"snapshots/traffic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    cv2.imwrite(fname, annotated_frame)
                    print(f"[SNAPSHOT] Saved to {fname}")
    finally:
        cap.release()
        cv2.destroyAllWindows()

def run_demo_pipeline(display=True, max_frames=None):
    """Runs live vision and adaptive control on synthetic 4-way intersection feed."""
    from demo_generator import SyntheticTrafficGenerator
    print("\n" + "="*65)
    print("AUTONOMOUS AI TRAFFIC FLOW CONTROL - MISSION CONTROL HUD")
    print("Hotkeys:")
    print("  [Q / ESC]  Quit Application")
    print("  [H]        Toggle Futuristic Telemetry HUD")
    print("  [R]        Toggle Lane Detection ROIs")
    print("  [SPACE]    Pause / Resume Feed")
    print("  [S]        Save High-Resolution Screenshot Snapshot")
    print("="*65 + "\n")

    sim = SyntheticTrafficGenerator(width=1280, height=720)
    vision_engine = TrafficVisionEngine(model_weight="yolov8n.pt")
    controller = AdaptiveSignalController()

    frame_idx = 0
    fps_timer = time.time()
    fps = 25.0

    # Signal state machine
    current_phase = "NS_PHASE"
    is_yellow = False
    phase_timer = 0
    green_duration = 35
    yellow_duration = int(controller.cfg["YELLOW_TIME"])
    decisions = {
        "NS_PHASE": {"green": 35, "pce_load": 0.0},
        "EW_PHASE": {"green": 25, "pce_load": 0.0}
    }

    show_hud = True
    show_rois = True
    paused = False
    annotated_frame = None

    try:
        while True:
            if max_frames is not None and frame_idx >= max_frames:
                break

            if not paused:
                frame = sim.generate_frame()
                frame_idx += 1
                phase_timer += 1

                # Signal phase progression (~25-30 frames per second)
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

                # Process detections and render futuristic HUD
                annotated_frame, lane_data = vision_engine.process_frame(
                    frame,
                    decisions=decisions,
                    fps=fps,
                    current_phase=current_phase,
                    is_yellow=is_yellow,
                    show_hud=show_hud,
                    show_rois=show_rois,
                    fallback_detections=sim.get_active_detections()
                )

                # Periodic dynamic decision update (~every 1 second)
                if frame_idx % 25 == 0:
                    decisions = controller.compute_green_times(lane_data)
                    elapsed = time.time() - fps_timer
                    fps = 25.0 / max(0.001, elapsed)
                    fps_timer = time.time()

                    # Actuated gap-out check
                    if not is_yellow and phase_timer > int(controller.cfg["MIN_GREEN"]) * 25:
                        if controller.should_terminate_early(current_phase, phase_timer // 25, lane_data):
                            is_yellow = True
                            phase_timer = 0

            if display and annotated_frame is not None:
                cv2.imshow("Autonomous AI Traffic System - Mission Control", annotated_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    print("\n[INFO] Demonstration stopped by user.")
                    break
                elif key == ord('h') or key == ord('H'):
                    show_hud = not show_hud
                elif key == ord('r') or key == ord('R'):
                    show_rois = not show_rois
                elif key == ord(' '):
                    paused = not paused
                    print(f"[INFO] Feed {'PAUSED' if paused else 'RESUMED'}")
                elif key == ord('s') or key == ord('S'):
                    os.makedirs("snapshots", exist_ok=True)
                    fname = f"snapshots/traffic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    cv2.imwrite(fname, annotated_frame)
                    print(f"[SNAPSHOT] Saved to {fname}")
    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Traffic Flow Optimization System")
    parser.add_argument("--source", type=str, default="0", help="Path to video file or webcam index (default: 0)")
    parser.add_argument("--sumo", action="store_true", help="Run SUMO micro-simulation benchmark")
    parser.add_argument("--gui", action="store_true", help="Launch SUMO with GUI (requires Eclipse SUMO)")
    parser.add_argument("--demo", action="store_true", help="Run interactive visual demonstration without camera")
    parser.add_argument("--web", action="store_true", help="Launch browser-based real-time telemetry dashboard")
    args = parser.parse_args()

    if args.sumo:
        from sumo_runner import run_sumo_simulation
        print("Executing comparative benchmark...")
        fixed_time = run_sumo_simulation(gui=args.gui, mode="fixed")
        adaptive_time = run_sumo_simulation(gui=args.gui, mode="adaptive")
        diff = ((fixed_time - adaptive_time) / fixed_time) * 100
        print(f"\n[SUMMARY] Fixed Delay: {fixed_time:.1f}s | Adaptive Delay: {adaptive_time:.1f}s | Efficiency Gain: {diff:.2f}%")
    elif args.web:
        from web_server import start_web_dashboard
        start_web_dashboard(source=args.source if not args.demo else "demo")
    elif args.demo:
        run_demo_pipeline(display=True)
    else:
        source = int(args.source) if args.source.isdigit() else args.source
        run_video_pipeline(source)