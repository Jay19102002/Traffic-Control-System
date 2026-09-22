# demo_generator.py
import cv2
import numpy as np
import random
from dataclasses import dataclass
from typing import Tuple, List

@dataclass
class VehicleTypeMeta:
    name: str
    dim: Tuple[int, int]
    color: Tuple[int, int, int]
    pce: float

VEHICLE_META = {
    2: VehicleTypeMeta(name="car", dim=(34, 60), color=(220, 150, 50), pce=1.0),
    3: VehicleTypeMeta(name="motorcycle", dim=(18, 35), color=(50, 220, 220), pce=0.5),
    5: VehicleTypeMeta(name="bus", dim=(42, 110), color=(40, 180, 50), pce=2.5),
    7: VehicleTypeMeta(name="truck", dim=(46, 120), color=(50, 60, 200), pce=2.5),
}

class SyntheticTrafficGenerator:
    """
    Generates synthetic realistic intersection video frames with moving vehicles
    (cars, buses, trucks, bikes) for testing and demonstrating the traffic AI system
    without requiring a physical video camera or file.
    """
    def __init__(self, width: int = 1280, height: int = 720):
        self.w = width
        self.h = height
        self.vehicles: List[dict] = []
        self.next_id = 1
        self.frame_count = 0

    def _spawn_vehicle(self, approach: str):
        cls_id = random.choices([2, 3, 5, 7], weights=[0.65, 0.15, 0.10, 0.10])[0]
        meta = VEHICLE_META[cls_id]

        if approach == "NORTH":
            x = float(random.choice([550, 610]))
            y = -100.0
            vx, vy = 0.0, random.uniform(3.0, 5.0)
            vw, vh = meta.dim[0], meta.dim[1]
        elif approach == "SOUTH":
            x = float(random.choice([690, 750]))
            y = float(self.h + 100)
            vx, vy = 0.0, -random.uniform(3.0, 5.0)
            vw, vh = meta.dim[0], meta.dim[1]
        elif approach == "EAST":
            x = float(self.w + 100)
            y = float(random.choice([350, 410]))
            vx, vy = -random.uniform(3.0, 5.0), 0.0
            vw, vh = meta.dim[1], meta.dim[0]
        else: # WEST
            x = -100.0
            y = float(random.choice([470, 530]))
            vx, vy = random.uniform(3.0, 5.0), 0.0
            vw, vh = meta.dim[1], meta.dim[0]

        self.vehicles.append({
            "id": self.next_id,
            "cls_id": cls_id,
            "name": meta.name,
            "color": meta.color,
            "x": x,
            "y": y,
            "w": vw,
            "h": vh,
            "vx": vx,
            "vy": vy,
            "approach": approach
        })
        self.next_id += 1

    def generate_frame(self) -> np.ndarray:
        self.frame_count += 1

        # Background: Asphalt gray
        frame = np.full((self.h, self.w, 3), 45, dtype=np.uint8)

        # North-South Road
        cv2.rectangle(frame, (500, 0), (780, self.h), (60, 60, 60), -1)
        # East-West Road
        cv2.rectangle(frame, (0, 310), (self.w, 590), (60, 60, 60), -1)

        # Center intersection box
        cv2.rectangle(frame, (500, 310), (780, 590), (70, 70, 70), -1)

        # Lane dividers
        for y in range(0, self.h, 40):
            if not (310 <= y <= 590):
                cv2.line(frame, (640, y), (640, y + 20), (255, 255, 255), 2)
        for x in range(0, self.w, 40):
            if not (500 <= x <= 780):
                cv2.line(frame, (x, 450), (x + 20, 450), (255, 255, 255), 2)

        # Stop lines
        cv2.line(frame, (500, 310), (640, 310), (255, 255, 255), 4) # North stop line
        cv2.line(frame, (640, 590), (780, 590), (255, 255, 255), 4) # South stop line
        cv2.line(frame, (780, 310), (780, 450), (255, 255, 255), 4) # East stop line
        cv2.line(frame, (500, 450), (500, 590), (255, 255, 255), 4) # West stop line

        # Spawn new vehicles with probability
        if random.random() < 0.08:
            self._spawn_vehicle("NORTH")
        if random.random() < 0.06:
            self._spawn_vehicle("SOUTH")
        if random.random() < 0.04:
            self._spawn_vehicle("EAST")
        if random.random() < 0.03:
            self._spawn_vehicle("WEST")

        # Update and draw vehicles
        remaining_vehicles = []
        for v in self.vehicles:
            v["x"] += v["vx"]
            v["y"] += v["vy"]

            # Keep vehicles within reasonable margin
            if -150 <= v["x"] <= self.w + 150 and -150 <= v["y"] <= self.h + 150:
                remaining_vehicles.append(v)

                # Draw vehicle body
                vx1, vy1 = int(v["x"] - v["w"] / 2.0), int(v["y"] - v["h"] / 2.0)
                vx2, vy2 = int(v["x"] + v["w"] / 2.0), int(v["y"] + v["h"] / 2.0)
                cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), v["color"], -1)
                cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), (255, 255, 255), 1)

                # Headlights
                if v["vy"] > 0: # Moving down
                    cv2.circle(frame, (vx1 + 5, vy2 - 3), 3, (180, 255, 255), -1)
                    cv2.circle(frame, (vx2 - 5, vy2 - 3), 3, (180, 255, 255), -1)
                elif v["vy"] < 0: # Moving up
                    cv2.circle(frame, (vx1 + 5, vy1 + 3), 3, (180, 255, 255), -1)
                    cv2.circle(frame, (vx2 - 5, vy1 + 3), 3, (180, 255, 255), -1)
                elif v["vx"] > 0: # Moving right
                    cv2.circle(frame, (vx2 - 3, vy1 + 5), 3, (180, 255, 255), -1)
                    cv2.circle(frame, (vx2 - 3, vy2 - 5), 3, (180, 255, 255), -1)
                elif v["vx"] < 0: # Moving left
                    cv2.circle(frame, (vx1 + 3, vy1 + 5), 3, (180, 255, 255), -1)
                    cv2.circle(frame, (vx1 + 3, vy2 - 5), 3, (180, 255, 255), -1)

        self.vehicles = remaining_vehicles
        return frame

    def get_active_detections(self):
        """Returns current simulated vehicle bounding boxes and metadata."""
        dets = []
        for v in self.vehicles:
            vx1 = int(v["x"] - v["w"] / 2.0)
            vy1 = int(v["y"] - v["h"] / 2.0)
            vx2 = int(v["x"] + v["w"] / 2.0)
            vy2 = int(v["y"] + v["h"] / 2.0)
            dets.append({
                "box": (vx1, vy1, vx2, vy2),
                "track_id": v["id"],
                "cls_id": v["cls_id"]
            })
        return dets
