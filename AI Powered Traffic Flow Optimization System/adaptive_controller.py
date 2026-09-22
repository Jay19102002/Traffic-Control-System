# adaptive_controller.py
from config import TIMING_CONFIG

class AdaptiveSignalController:
    def __init__(self, timing_cfg=None):
        self.cfg = timing_cfg if timing_cfg is not None else TIMING_CONFIG
        self.phases = ["NS_PHASE", "EW_PHASE"]
        self.starvation_counter = {"NS_PHASE": 0, "EW_PHASE": 0}
        
        # Exponential Moving Average (EMA) to prevent single-instant post-discharge bias
        self.ema_load = {"NS_PHASE": 5.0, "EW_PHASE": 2.0}
        self.alpha = 0.35

    def compute_green_times(self, lane_data):
        """
        Aggregates antagonistic approaches:
        - Phase 1: North-South (NS_PHASE)
        - Phase 2: East-West (EW_PHASE)
        Allocates green times dynamically based on PCE saturation and demand history.
        """
        ns_load = float(lane_data.get("NORTH", {}).get("pce_load", 0.0) + lane_data.get("SOUTH", {}).get("pce_load", 0.0))
        ew_load = float(lane_data.get("EAST", {}).get("pce_load", 0.0) + lane_data.get("WEST", {}).get("pce_load", 0.0))

        # Update EMA demand estimates
        self.ema_load["NS_PHASE"] = self.alpha * ns_load + (1.0 - self.alpha) * self.ema_load["NS_PHASE"]
        self.ema_load["EW_PHASE"] = self.alpha * ew_load + (1.0 - self.alpha) * self.ema_load["EW_PHASE"]

        # Blend instant queue pressure with historical demand rate
        blended_ns = 0.6 * ns_load + 0.4 * self.ema_load["NS_PHASE"]
        blended_ew = 0.6 * ew_load + 0.4 * self.ema_load["EW_PHASE"]

        # Apply starvation compensation (+20% load bias per starved cycle)
        effective_ns_load = blended_ns * (1.0 + 0.20 * self.starvation_counter["NS_PHASE"])
        effective_ew_load = blended_ew * (1.0 + 0.20 * self.starvation_counter["EW_PHASE"])

        total_effective_load = effective_ns_load + effective_ew_load

        total_clearance_time = 2 * (self.cfg["YELLOW_TIME"] + self.cfg["ALL_RED_TIME"])
        available_green_pool = self.cfg["DEFAULT_CYCLE"] - total_clearance_time

        if total_effective_load <= 0.001:
            # No vehicles detected: divide equally
            g_ns = available_green_pool / 2.0
            g_ew = available_green_pool / 2.0
        else:
            # Proportional split according to demand saturation
            ratio_ns = effective_ns_load / total_effective_load
            g_ns = ratio_ns * available_green_pool
            g_ew = (1.0 - ratio_ns) * available_green_pool

        # Enforce hard safety bounds
        min_g = int(self.cfg["MIN_GREEN"])
        max_g = int(self.cfg["MAX_GREEN"])
        g_ns_clamped = max(min_g, min(max_g, int(round(g_ns))))
        g_ew_clamped = max(min_g, min(max_g, int(round(g_ew))))

        return {
            "NS_PHASE": {
                "green": g_ns_clamped,
                "yellow": self.cfg["YELLOW_TIME"],
                "all_red": self.cfg["ALL_RED_TIME"],
                "pce_load": ns_load
            },
            "EW_PHASE": {
                "green": g_ew_clamped,
                "yellow": self.cfg["YELLOW_TIME"],
                "all_red": self.cfg["ALL_RED_TIME"],
                "pce_load": ew_load
            }
        }

    def should_terminate_early(self, active_phase, elapsed_green, lane_data):
        """
        Actuated gap-out logic: if minimum green is reached, current queue has
        cleared, and opposing phase has waiting traffic, terminate phase early.
        """
        min_g = int(self.cfg["MIN_GREEN"])
        max_g = int(self.cfg["MAX_GREEN"])

        if elapsed_green < min_g:
            return False
        if elapsed_green >= max_g:
            return True

        if active_phase == "NS_PHASE":
            active_q = float(lane_data.get("NORTH", {}).get("pce_load", 0.0) + lane_data.get("SOUTH", {}).get("pce_load", 0.0))
            opposing_q = float(lane_data.get("EAST", {}).get("pce_load", 0.0) + lane_data.get("WEST", {}).get("pce_load", 0.0))
        else:
            active_q = float(lane_data.get("EAST", {}).get("pce_load", 0.0) + lane_data.get("WEST", {}).get("pce_load", 0.0))
            opposing_q = float(lane_data.get("NORTH", {}).get("pce_load", 0.0) + lane_data.get("SOUTH", {}).get("pce_load", 0.0))

        # If active approach has discharged its queue and opposing approach is waiting, gap-out early
        if active_q < 0.5 and opposing_q > 0.0:
            return True

        return False

    def update_starvation(self, active_phase):
        for p in self.phases:
            if p == active_phase:
                self.starvation_counter[p] = 0
            else:
                self.starvation_counter[p] += 1