# config.py
import numpy as np

# COCO Dataset vehicle class indices
VEHICLE_CLASSES = {
    2: ("car", 1.0),        # Class ID 2: Car (PCE weight: 1.0)
    3: ("motorcycle", 0.5), # Class ID 3: Bike (PCE weight: 0.5)
    5: ("bus", 2.5),        # Class ID 5: Bus (PCE weight: 2.5)
    7: ("truck", 2.5),      # Class ID 7: Truck (PCE weight: 2.5)
}

# Signal Timing Constraints (in seconds)
TIMING_CONFIG = {
    "MIN_GREEN": 10,       # Minimum green time for safety/pedestrian clearance
    "MAX_GREEN": 60,       # Maximum green time to prevent starvation
    "YELLOW_TIME": 4,      # Fixed yellow transition time
    "ALL_RED_TIME": 2,     # Inter-green safety clearance
    "DEFAULT_CYCLE": 90,   # Total nominal cycle budget
}

# Default 4-Approach Lane Polygons (Normalized 0.0 to 1.0 for 1280x720 video)
# In production, adjust these normalized coordinates to your specific intersection angles.
DEFAULT_ROIS = {
    "NORTH": np.array([[520, 100], [660, 100], [620, 360], [450, 360]], dtype=np.int32),
    "SOUTH": np.array([[640, 480], [860, 480], [920, 720], [600, 720]], dtype=np.int32),
    "EAST":  np.array([[700, 320], [1150, 300], [1150, 500], [680, 450]], dtype=np.int32),
    "WEST":  np.array([[100, 350], [450, 350], [480, 500], [100, 550]], dtype=np.int32)
}