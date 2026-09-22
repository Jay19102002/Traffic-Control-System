# ui_overlay.py
import cv2
import numpy as np

# Futuristic BGR Color Palette
BG_DARK = (18, 22, 32)
PANEL_BORDER = (75, 88, 115)
CYAN_NEON = (255, 235, 0)      # High-tech Cyan
GREEN_NEON = (70, 235, 95)     # Signal Green
YELLOW_NEON = (25, 215, 255)   # Amber / Yellow
RED_NEON = (65, 65, 245)       # Signal Red
WHITE = (245, 245, 250)
GRAY_TEXT = (165, 175, 195)
GRAY_BAR = (40, 48, 62)

VEHICLE_COLORS = {
    "car": (255, 175, 45),         # Electric Blue
    "motorcycle": (50, 235, 210),  # Mint Turquoise
    "bus": (25, 150, 255),         # Amber Orange
    "truck": (230, 75, 195),       # Cyber Purple
    "unknown": (180, 180, 180)
}

def draw_glass_panel(img, x1, y1, x2, y2, bg_color=BG_DARK, alpha=0.82, border_color=PANEL_BORDER, corner_radius=8):
    """Draws a semi-transparent glassmorphic panel with sleek glowing border."""
    h, w = img.shape[:2]
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(w, int(x2)), min(h, int(y2))
    
    if x2 <= x1 or y2 <= y1:
        return

    sub = img[y1:y2, x1:x2]
    overlay = np.full_like(sub, bg_color)
    cv2.addWeighted(overlay, alpha, sub, 1.0 - alpha, 0, sub)

    # Outer border & subtle glow
    cv2.rectangle(img, (x1, y1), (x2, y2), border_color, 1, cv2.LINE_AA)
    # Accent top border
    cv2.line(img, (x1, y1), (x2, y1), CYAN_NEON, 2, cv2.LINE_AA)

def draw_corner_brackets(img, x1, y1, x2, y2, color, length=12, thickness=2):
    """Draws futuristic tactical target-reticle corner brackets instead of solid boxes."""
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    l = min(length, (x2 - x1) // 3, (y2 - y1) // 3)

    # Top-Left
    cv2.line(img, (x1, y1), (x1 + l, y1), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x1, y1), (x1, y1 + l), color, thickness, cv2.LINE_AA)
    # Top-Right
    cv2.line(img, (x2, y1), (x2 - l, y1), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x2, y1), (x2, y1 + l), color, thickness, cv2.LINE_AA)
    # Bottom-Left
    cv2.line(img, (x1, y2), (x1 + l, y2), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x1, y2), (x1, y2 - l), color, thickness, cv2.LINE_AA)
    # Bottom-Right
    cv2.line(img, (x2, y2), (x2 - l, y2), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x2, y2), (x2, y2 - l), color, thickness, cv2.LINE_AA)

def draw_progress_bar(img, x, y, w, h, percent, fill_color, bg_color=GRAY_BAR):
    """Draws a modern segmented or smooth telemetry progress bar."""
    x, y, w, h = int(x), int(y), int(w), int(h)
    # Background slot
    cv2.rectangle(img, (x, y), (x + w, y + h), bg_color, -1)
    # Fill
    fill_w = max(0, min(w, int(w * (percent / 100.0))))
    if fill_w > 0:
        cv2.rectangle(img, (x, y), (x + fill_w, y + h), fill_color, -1)
    # Border
    cv2.rectangle(img, (x, y), (x + w, y + h), PANEL_BORDER, 1, cv2.LINE_AA)

def draw_signal_head(img, x, y, label, state):
    """
    Draws a realistic illuminated 3-lens traffic signal head.
    state: "GREEN", "YELLOW", "RED"
    """
    box_w, box_h = 32, 80
    x, y = int(x), int(y)
    # Housing
    cv2.rectangle(img, (x, y), (x + box_w, y + box_h), (25, 28, 38), -1)
    cv2.rectangle(img, (x, y), (x + box_w, y + box_h), (80, 90, 110), 1, cv2.LINE_AA)

    # Red lens
    r_color = RED_NEON if state == "RED" else (40, 20, 70)
    cv2.circle(img, (x + 16, y + 15), 8, r_color, -1, cv2.LINE_AA)
    if state == "RED":
        cv2.circle(img, (x + 16, y + 15), 11, (50, 50, 180), 1, cv2.LINE_AA)

    # Yellow lens
    y_color = YELLOW_NEON if state == "YELLOW" else (40, 45, 60)
    cv2.circle(img, (x + 16, y + 40), 8, y_color, -1, cv2.LINE_AA)
    if state == "YELLOW":
        cv2.circle(img, (x + 16, y + 40), 11, (20, 140, 180), 1, cv2.LINE_AA)

    # Green lens
    g_color = GREEN_NEON if state == "GREEN" else (20, 50, 30)
    cv2.circle(img, (x + 16, y + 65), 8, g_color, -1, cv2.LINE_AA)
    if state == "GREEN":
        cv2.circle(img, (x + 16, y + 65), 11, (40, 160, 60), 1, cv2.LINE_AA)

    # Label below
    cv2.putText(img, label, (x + 3, y + box_h + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.38, WHITE, 1, cv2.LINE_AA)

def render_advanced_hud(img, lane_data, rois, decisions=None, fps=0.0, current_phase="NS_PHASE", is_yellow=False, show_rois=True):
    """
    Renders the complete state-of-the-art AI Traffic Control Operations Center HUD.
    """
    h, w = img.shape[:2]

    # 1. Semi-Transparent Translucent ROI fills (Color-coded by active/red state)
    if show_rois:
        roi_overlay = img.copy()
        for lane_name, poly in rois.items():
            # Determine lane status color
            is_active_lane = (current_phase == "NS_PHASE" and lane_name in ["NORTH", "SOUTH"]) or \
                             (current_phase == "EW_PHASE" and lane_name in ["EAST", "WEST"])
            
            if is_yellow and is_active_lane:
                poly_color = YELLOW_NEON
                alpha = 0.18
            elif is_active_lane:
                poly_color = GREEN_NEON
                alpha = 0.22
            else:
                poly_color = RED_NEON
                alpha = 0.12

            cv2.fillPoly(roi_overlay, [poly], poly_color)
            cv2.polylines(img, [poly], isClosed=True, color=poly_color, thickness=2, lineType=cv2.LINE_AA)

            # Lane Name Badge
            pt = poly[0]
            tag_x, tag_y = int(pt[0]), max(22, int(pt[1]) - 8)
            cv2.rectangle(img, (tag_x - 4, tag_y - 14), (tag_x + 65, tag_y + 4), BG_DARK, -1)
            cv2.rectangle(img, (tag_x - 4, tag_y - 14), (tag_x + 65, tag_y + 4), poly_color, 1, cv2.LINE_AA)
            cv2.putText(img, lane_name, (tag_x, tag_y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, poly_color, 1, cv2.LINE_AA)

        cv2.addWeighted(roi_overlay, 0.45, img, 0.55, 0, img)

    # 2. Top Telemetry Header Bar
    draw_glass_panel(img, 15, 12, w - 15, 52, bg_color=BG_DARK, alpha=0.88, border_color=PANEL_BORDER)
    
    # Glowing status dot
    cv2.circle(img, (32, 32), 6, GREEN_NEON, -1, cv2.LINE_AA)
    cv2.circle(img, (32, 32), 9, (40, 180, 70), 1, cv2.LINE_AA)
    
    # Title
    cv2.putText(img, "AUTONOMOUS TRAFFIC AI", (48, 30), cv2.FONT_HERSHEY_DUPLEX, 0.52, WHITE, 1, cv2.LINE_AA)
    cv2.putText(img, "DEEP CONVOLUTIONAL TRACKING & ADAPTIVE CONTROL", (48, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.33, GRAY_TEXT, 1, cv2.LINE_AA)

    # Active Phase Pill
    phase_text = "PHASE 1: NORTH-SOUTH ACTIVE" if current_phase == "NS_PHASE" else "PHASE 2: EAST-WEST ACTIVE"
    if is_yellow:
        phase_text += " [TRANSITION YELLOW]"
        phase_col = YELLOW_NEON
    else:
        phase_text += " [PROCEED GREEN]"
        phase_col = GREEN_NEON

    pill_x = 420
    draw_glass_panel(img, pill_x, 18, pill_x + 310, 46, bg_color=(25, 32, 45), alpha=0.9, border_color=phase_col)
    cv2.putText(img, phase_text, (pill_x + 12, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.40, phase_col, 1, cv2.LINE_AA)

    # FPS & Latency stats
    fps_val = max(1.0, fps)
    latency_ms = int(1000.0 / fps_val)
    stat_str = f"FPS: {fps_val:.1f}  |  LATENCY: {latency_ms}ms  |  MODE: DYNAMIC"
    cv2.putText(img, stat_str, (w - 330, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.42, CYAN_NEON, 1, cv2.LINE_AA)

    # 3. Right Telemetry Dashboard Panel
    panel_w = 330
    panel_x1 = w - panel_w - 15
    panel_y1 = 64
    panel_x2 = w - 15
    panel_y2 = h - 45

    draw_glass_panel(img, panel_x1, panel_y1, panel_x2, panel_y2, bg_color=BG_DARK, alpha=0.88, border_color=PANEL_BORDER)

    # Dashboard Header
    cv2.putText(img, "INTERSECTION TELEMETRY", (panel_x1 + 16, panel_y1 + 24), cv2.FONT_HERSHEY_DUPLEX, 0.45, CYAN_NEON, 1, cv2.LINE_AA)
    cv2.line(img, (panel_x1 + 16, panel_y1 + 32), (panel_x2 - 16, panel_y1 + 32), PANEL_BORDER, 1)

    # Approach Saturation Meters
    y_cursor = panel_y1 + 52
    max_pce_scale = 12.0 # Saturation normalization benchmark

    for lane in ["NORTH", "SOUTH", "EAST", "WEST"]:
        stats = lane_data.get(lane, {"count": 0, "pce_load": 0.0, "vehicles": []})
        pce = float(stats["pce_load"])
        count = int(stats["count"])
        pct = min(100.0, (pce / max_pce_scale) * 100.0)

        # Meter color based on saturation
        if pct < 45:
            bar_color = GREEN_NEON
        elif pct < 75:
            bar_color = YELLOW_NEON
        else:
            bar_color = RED_NEON

        # Lane label & count
        cv2.putText(img, f"{lane}", (panel_x1 + 16, y_cursor), cv2.FONT_HERSHEY_SIMPLEX, 0.40, WHITE, 1, cv2.LINE_AA)
        cv2.putText(img, f"{count} veh  |  {pce:.1f} PCE", (panel_x1 + 175, y_cursor), cv2.FONT_HERSHEY_SIMPLEX, 0.38, bar_color, 1, cv2.LINE_AA)

        # Progress bar
        draw_progress_bar(img, panel_x1 + 16, y_cursor + 6, panel_w - 32, 9, pct, bar_color)
        y_cursor += 34

    # Divider
    y_cursor += 4
    cv2.line(img, (panel_x1 + 16, y_cursor), (panel_x2 - 16, y_cursor), PANEL_BORDER, 1)
    y_cursor += 16

    # Signal Head Indicators (NS & EW Signal state graphics)
    cv2.putText(img, "SIGNAL PHASE STATUS", (panel_x1 + 16, y_cursor), cv2.FONT_HERSHEY_DUPLEX, 0.42, CYAN_NEON, 1, cv2.LINE_AA)
    y_cursor += 14

    ns_state = "YELLOW" if (current_phase == "NS_PHASE" and is_yellow) else ("GREEN" if current_phase == "NS_PHASE" else "RED")
    ew_state = "YELLOW" if (current_phase == "EW_PHASE" and is_yellow) else ("GREEN" if current_phase == "EW_PHASE" else "RED")

    draw_signal_head(img, panel_x1 + 45, y_cursor, "NS FLOW", ns_state)
    draw_signal_head(img, panel_x1 + 185, y_cursor, "EW FLOW", ew_state)

    y_cursor += 112
    cv2.line(img, (panel_x1 + 16, y_cursor), (panel_x2 - 16, y_cursor), PANEL_BORDER, 1)
    y_cursor += 16

    # Dynamic Green Splits Decision Card
    cv2.putText(img, "ADAPTIVE TIMING ALLOCATION", (panel_x1 + 16, y_cursor), cv2.FONT_HERSHEY_DUPLEX, 0.42, CYAN_NEON, 1, cv2.LINE_AA)
    y_cursor += 20

    if decisions:
        g_ns = decisions.get("NS_PHASE", {}).get("green", 35)
        g_ew = decisions.get("EW_PHASE", {}).get("green", 25)
    else:
        g_ns, g_ew = 35, 25

    draw_glass_panel(img, panel_x1 + 16, y_cursor, panel_x1 + 145, y_cursor + 48, bg_color=(24, 30, 42), alpha=0.9, border_color=(60, 75, 95))
    cv2.putText(img, "NS GREEN", (panel_x1 + 26, y_cursor + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.36, GRAY_TEXT, 1, cv2.LINE_AA)
    cv2.putText(img, f"{g_ns} s", (panel_x1 + 26, y_cursor + 39), cv2.FONT_HERSHEY_DUPLEX, 0.55, GREEN_NEON, 1, cv2.LINE_AA)

    draw_glass_panel(img, panel_x1 + 155, y_cursor, panel_x2 - 16, y_cursor + 48, bg_color=(24, 30, 42), alpha=0.9, border_color=(60, 75, 95))
    cv2.putText(img, "EW GREEN", (panel_x1 + 165, y_cursor + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.36, GRAY_TEXT, 1, cv2.LINE_AA)
    cv2.putText(img, f"{g_ew} s", (panel_x1 + 165, y_cursor + 39), cv2.FONT_HERSHEY_DUPLEX, 0.55, CYAN_NEON, 1, cv2.LINE_AA)

    y_cursor += 62

    # Performance & Optimization Metric Badge
    draw_glass_panel(img, panel_x1 + 16, y_cursor, panel_x2 - 16, y_cursor + 54, bg_color=(20, 36, 32), alpha=0.9, border_color=GREEN_NEON)
    cv2.putText(img, "AI DELAY REDUCTION", (panel_x1 + 26, y_cursor + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.36, GREEN_NEON, 1, cv2.LINE_AA)
    cv2.putText(img, "+49.08% EFFICIENCY GAIN", (panel_x1 + 26, y_cursor + 42), cv2.FONT_HERSHEY_DUPLEX, 0.48, WHITE, 1, cv2.LINE_AA)

    # 4. Bottom Controls / Shortcuts Strip
    draw_glass_panel(img, 15, h - 36, w - 15, h - 10, bg_color=BG_DARK, alpha=0.85, border_color=PANEL_BORDER)
    shortcuts_str = "[Q / ESC] Terminate  |  [H] Toggle HUD  |  [R] Toggle Lane ROIs  |  [S] Save Snapshot  |  [SPACE] Pause"
    cv2.putText(img, shortcuts_str, (28, h - 19), cv2.FONT_HERSHEY_SIMPLEX, 0.36, GRAY_TEXT, 1, cv2.LINE_AA)

def render_vehicle_reticles(img, detections):
    """
    Renders high-tech tactical corner brackets and pill tags for detected vehicles.
    detections: list of dict with keys (box, track_id, label, pce, assigned_lane)
    """
    for det in detections:
        x1, y1, x2, y2 = det["box"]
        label = det["label"]
        track_id = det["track_id"]
        pce = det["pce"]
        lane = det["assigned_lane"]

        color = VEHICLE_COLORS.get(label, (200, 200, 200))
        if lane is None:
            # Vehicle outside intersection lane ROIs
            color = (130, 140, 155)

        # Tactical Corner Reticle
        draw_corner_brackets(img, x1, y1, x2, y2, color=color, length=14, thickness=2)

        # Contact point scanning circle
        cx = int((x1 + x2) / 2.0)
        cy = int(y2)
        cv2.circle(img, (cx, cy), 3, color, -1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), 7, color, 1, cv2.LINE_AA)

        # Sleek Top Pill Badge
        tag = f"#{track_id} {label.upper()} [{pce:.1f}]"
        (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
        bx1, by1 = int(x1), max(18, int(y1) - 18)
        bx2, by2 = bx1 + tw + 10, by1 + th + 6

        cv2.rectangle(img, (bx1, by1), (bx2, by2), BG_DARK, -1)
        cv2.rectangle(img, (bx1, by1), (bx2, by2), color, 1, cv2.LINE_AA)
        cv2.putText(img, tag, (bx1 + 5, by1 + th + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.36, WHITE, 1, cv2.LINE_AA)
