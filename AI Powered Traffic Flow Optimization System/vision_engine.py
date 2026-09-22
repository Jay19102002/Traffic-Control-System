# vision_engine.py
import cv2
import numpy as np
from ultralytics import YOLO
from config import VEHICLE_CLASSES, DEFAULT_ROIS
from ui_overlay import render_advanced_hud, render_vehicle_reticles

class TrafficVisionEngine:
    def __init__(self, model_weight="yolov8n.pt", rois=None):
        """
        Initializes YOLOv8 detector with ByteTrack tracker.
        """
        self.model = YOLO(model_weight)
        self.base_rois = rois if rois is not None else DEFAULT_ROIS
        self.target_classes = list(VEHICLE_CLASSES.keys())
        self._cached_resolution = None
        self.rois = self.base_rois

    def _get_scaled_rois(self, frame_w, frame_h):
        """Scale ROIs proportionally if frame resolution is different from 1280x720."""
        if (frame_w, frame_h) == self._cached_resolution:
            return self.rois

        base_w, base_h = 1280.0, 720.0
        scale_x = frame_w / base_w
        scale_y = frame_h / base_h

        scaled = {}
        for lane, poly in self.base_rois.items():
            scaled_poly = np.copy(poly).astype(np.float32)
            scaled_poly[:, 0] *= scale_x
            scaled_poly[:, 1] *= scale_y
            scaled[lane] = scaled_poly.astype(np.int32)

        self._cached_resolution = (frame_w, frame_h)
        self.rois = scaled
        return self.rois

    def point_inside_polygon(self, point, polygon):
        """Checks if vehicle bottom-center point falls inside a lane ROI."""
        return cv2.pointPolygonTest(polygon, (float(point[0]), float(point[1])), False) >= 0

    def process_frame(self, frame, decisions=None, fps=0.0, current_phase="NS_PHASE", is_yellow=False, show_hud=True, show_rois=True, fallback_detections=None):
        """
        Processes a single frame: runs tracking, assigns vehicles to lane ROIs,
        and renders state-of-the-art telemetry and tactical vehicle reticles.
        """
        frame_h, frame_w = frame.shape[:2]
        current_rois = self._get_scaled_rois(frame_w, frame_h)

        results = self.model.track(
            source=frame,
            persist=True,
            classes=self.target_classes,
            tracker="bytetrack.yaml",
            verbose=False
        )

        lane_data = {lane: {"vehicles": [], "pce_load": 0.0, "count": 0} for lane in current_rois}
        annotated_frame = frame.copy()
        detections = []

        # Parse Detections
        if results and len(results) > 0 and results[0].boxes is not None and len(results[0].boxes) > 0:
            boxes_obj = results[0].boxes

            raw_xyxy = boxes_obj.xyxy
            if hasattr(raw_xyxy, "cpu"):
                raw_xyxy = raw_xyxy.cpu()
            if hasattr(raw_xyxy, "numpy"):
                raw_xyxy = raw_xyxy.numpy()
            boxes = np.asarray(raw_xyxy)

            raw_cls = boxes_obj.cls
            if hasattr(raw_cls, "cpu"):
                raw_cls = raw_cls.cpu()
            if hasattr(raw_cls, "numpy"):
                raw_cls = raw_cls.numpy()
            class_ids = np.asarray(raw_cls).astype(int)

            track_ids = None
            raw_id = getattr(boxes_obj, "id", None)
            if raw_id is not None:
                if hasattr(raw_id, "cpu"):
                    raw_id = raw_id.cpu()
                if hasattr(raw_id, "numpy"):
                    raw_id = raw_id.numpy()
                track_ids = np.asarray(raw_id).astype(int)

            for i in range(len(boxes)):
                x1, y1, x2, y2 = boxes[i]
                cls_id = int(class_ids[i])
                track_id = int(track_ids[i]) if track_ids is not None and i < len(track_ids) else (i + 1)
                
                bottom_center = (int((x1 + x2) / 2.0), int(y2))
                label, pce_weight = VEHICLE_CLASSES.get(cls_id, ("unknown", 1.0))

                assigned_lane = None
                for lane_name, poly in current_rois.items():
                    if self.point_inside_polygon(bottom_center, poly):
                        assigned_lane = lane_name
                        lane_data[lane_name]["vehicles"].append({
                            "id": track_id, "type": label, "pce": pce_weight
                        })
                        lane_data[lane_name]["pce_load"] += pce_weight
                        lane_data[lane_name]["count"] += 1
                        break

                detections.append({
                    "box": (x1, y1, x2, y2),
                    "track_id": track_id,
                    "label": label,
                    "pce": pce_weight,
                    "assigned_lane": assigned_lane
                })

        # Process fallback detections if model yielded no detections (e.g., synthetic demo canvas)
        if len(detections) == 0 and fallback_detections:
            for det in fallback_detections:
                x1, y1, x2, y2 = det["box"]
                cls_id = int(det.get("cls_id", 2))
                track_id = int(det.get("track_id", 1))
                label, pce_weight = VEHICLE_CLASSES.get(cls_id, ("unknown", 1.0))
                bottom_center = (int((x1 + x2) / 2.0), int(y2))

                assigned_lane = None
                for lane_name, poly in current_rois.items():
                    if self.point_inside_polygon(bottom_center, poly):
                        assigned_lane = lane_name
                        lane_data[lane_name]["vehicles"].append({
                            "id": track_id, "type": label, "pce": pce_weight
                        })
                        lane_data[lane_name]["pce_load"] += pce_weight
                        lane_data[lane_name]["count"] += 1
                        break

                detections.append({
                    "box": (x1, y1, x2, y2),
                    "track_id": track_id,
                    "label": label,
                    "pce": pce_weight,
                    "assigned_lane": assigned_lane
                })

        # 1. Render Tactical Vehicle Reticles
        render_vehicle_reticles(annotated_frame, detections)

        # 2. Render Advanced Operations Center HUD
        if show_hud:
            render_advanced_hud(
                annotated_frame,
                lane_data=lane_data,
                rois=current_rois,
                decisions=decisions,
                fps=fps,
                current_phase=current_phase,
                is_yellow=is_yellow,
                show_rois=show_rois
            )

        return annotated_frame, lane_data