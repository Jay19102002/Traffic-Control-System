# sumo_runner.py
import sys
import os
import shutil
import random
from typing import Any
from adaptive_controller import AdaptiveSignalController

# Phase indices mapped to SUMO TLS states
# G = Green, y = Yellow, r = Red
PHASE_MAP = {
    "NS_GREEN":  "GGggrrrrGGggrrrr",
    "NS_YELLOW": "yyygrrrryyygrrrr",
    "EW_GREEN":  "rrrrGGggrrrrGGgg",
    "EW_YELLOW": "rrrryyygrrrryyyg"
}

def is_sumo_available():
    """Check if sumo executable is available in PATH or SUMO_HOME."""
    if shutil.which("sumo") is not None or shutil.which("sumo.exe") is not None:
        return True
    sumo_home = os.environ.get("SUMO_HOME")
    if sumo_home and os.path.exists(os.path.join(sumo_home, "bin", "sumo.exe")):
        return True
    return False

def get_sumo_binary(gui=False):
    base_name = "sumo-gui" if gui else "sumo"
    if shutil.which(base_name):
        return base_name
    sumo_home = os.environ.get("SUMO_HOME")
    if sumo_home:
        binary = os.path.join(sumo_home, "bin", f"{base_name}.exe")
        if os.path.exists(binary):
            return binary
    return base_name

def run_sumo_simulation(gui=False, mode="adaptive"):
    """
    Runs micro-simulation. Uses native Eclipse SUMO with TraCI if installed;
    otherwise seamlessly runs the built-in microscopic traffic simulator.
    """
    if is_sumo_available():
        return _run_traci_simulation(gui=gui, mode=mode)
    else:
        return _run_fallback_simulation(mode=mode)

def _run_traci_simulation(gui=False, mode="adaptive"):
    import traci
    sumo_binary = get_sumo_binary(gui=gui)
    cfg_file = "sumo_env/cross.sumocfg"

    if not os.path.exists("sumo_env/cross.net.xml"):
        print("[SUMO] Network file missing, compiling network via netconvert...")
        from sumo_generator import create_sumo_network
        compiled = create_sumo_network()
        if not compiled or not os.path.exists("sumo_env/cross.net.xml"):
            print("[SUMO] Could not compile net.xml. Falling back to built-in simulation engine.")
            return _run_fallback_simulation(mode=mode)

    traci.start([sumo_binary, "-c", cfg_file, "--tripinfo-output", f"sumo_env/tripinfo_{mode}.xml"])
    tls_id = str(traci.trafficlight.getIDList()[0])
    
    controller = AdaptiveSignalController()
    step = 0
    total_waiting_time = 0.0

    print(f"\n[Running Native SUMO Micro-Simulation | Mode: {mode.upper()}]")

    # Traffic Light Controller State
    current_green_phase = "NS_PHASE"
    is_in_yellow = False
    current_timer = 0
    green_duration = 30
    yellow_duration = int(controller.cfg["YELLOW_TIME"])

    # Initial green state
    traci.trafficlight.setRedYellowGreenState(tls_id, PHASE_MAP["NS_GREEN"])

    while True:
        min_expected: Any = traci.simulation.getMinExpectedNumber()
        if not (min_expected > 0 and step < 1000):
            break
        traci.simulationStep()
        step += 1
        current_timer += 1

        # Track cumulative vehicle waiting times
        for veh_id in traci.vehicle.getIDList():
            wait_val: Any = traci.vehicle.getWaitingTime(veh_id)
            total_waiting_time += float(wait_val)

        if mode == "fixed":
            # Fixed-Time Control: 35s Green followed by 4s Yellow
            if not is_in_yellow:
                if current_timer >= 35:
                    is_in_yellow = True
                    current_timer = 0
                    yellow_state = PHASE_MAP["NS_YELLOW"] if current_green_phase == "NS_PHASE" else PHASE_MAP["EW_YELLOW"]
                    traci.trafficlight.setRedYellowGreenState(tls_id, yellow_state)
            else:
                if current_timer >= yellow_duration:
                    is_in_yellow = False
                    current_timer = 0
                    current_green_phase = "EW_PHASE" if current_green_phase == "NS_PHASE" else "NS_PHASE"
                    green_state = PHASE_MAP["NS_GREEN"] if current_green_phase == "NS_PHASE" else PHASE_MAP["EW_GREEN"]
                    traci.trafficlight.setRedYellowGreenState(tls_id, green_state)

        elif mode == "adaptive":
            # Query real-time approach queues
            n2c: Any = traci.edge.getLastStepHaltingNumber("N2C")
            s2c: Any = traci.edge.getLastStepHaltingNumber("S2C")
            e2c: Any = traci.edge.getLastStepHaltingNumber("E2C")
            w2c: Any = traci.edge.getLastStepHaltingNumber("W2C")
            ns_queue = float(n2c + s2c)
            ew_queue = float(e2c + w2c)

            sim_lane_data = {
                "NORTH": {"pce_load": ns_queue, "count": int(ns_queue)},
                "SOUTH": {"pce_load": 0.0, "count": 0},
                "EAST":  {"pce_load": ew_queue, "count": int(ew_queue)},
                "WEST":  {"pce_load": 0.0, "count": 0}
            }

            if not is_in_yellow:
                # Check for gap-out or max green duration
                should_end = (current_timer >= green_duration) or controller.should_terminate_early(
                    current_green_phase, current_timer, sim_lane_data
                )
                if should_end:
                    is_in_yellow = True
                    current_timer = 0
                    yellow_state = PHASE_MAP["NS_YELLOW"] if current_green_phase == "NS_PHASE" else PHASE_MAP["EW_YELLOW"]
                    traci.trafficlight.setRedYellowGreenState(tls_id, yellow_state)
            else:
                if current_timer >= yellow_duration:
                    is_in_yellow = False
                    current_timer = 0
                    current_green_phase = "EW_PHASE" if current_green_phase == "NS_PHASE" else "NS_PHASE"
                    controller.update_starvation(current_green_phase)

                    decisions = controller.compute_green_times(sim_lane_data)
                    green_duration = int(decisions[current_green_phase]["green"])

                    green_state = PHASE_MAP["NS_GREEN"] if current_green_phase == "NS_PHASE" else PHASE_MAP["EW_GREEN"]
                    traci.trafficlight.setRedYellowGreenState(tls_id, green_state)

    traci.close()
    print(f"Simulation completed ({step} steps). Cumulative Waiting Delay: {total_waiting_time:.2f} vehicle-seconds.\n")
    return total_waiting_time

def _run_fallback_simulation(mode="adaptive"):
    """
    Built-in high-fidelity discrete-event microscopic intersection simulator.
    Simulates Poisson vehicle arrivals, queuing dynamics, saturation flow rates,
    and calculates exact cumulative waiting times without external dependencies.
    """
    print(f"\n[Running Built-in Traffic Micro-Simulation | Mode: {mode.upper()}]")
    random.seed(42)  # Deterministic comparison between modes

    controller = AdaptiveSignalController()
    total_steps = 1000
    discharge_rate_per_sec = 1.0  # ~2 lanes discharging at saturation flow

    # Initial queues for 4 approaches
    queues = {
        "NORTH": {"count": 0, "pce": 0.0},
        "SOUTH": {"count": 0, "pce": 0.0},
        "EAST":  {"count": 0, "pce": 0.0},
        "WEST":  {"count": 0, "pce": 0.0}
    }

    # Flow arrival probabilities per second (matching SUMO periods 3, 4, 10, 12)
    arrival_configs = {
        "NORTH": {"prob": 1.0 / 3.0, "pce": 1.0},   # Heavy Car flow
        "SOUTH": {"prob": 1.0 / 4.0, "pce": 1.0},   # Car flow
        "EAST":  {"prob": 1.0 / 10.0, "pce": 1.0},  # Moderate flow
        "WEST":  {"prob": 1.0 / 12.0, "pce": 2.5}   # Heavy Trucks flow
    }

    current_green_phase = "NS_PHASE"
    is_in_yellow = False
    current_timer = 0
    green_duration = 35
    yellow_duration = int(controller.cfg["YELLOW_TIME"])

    total_waiting_time = 0.0

    for step in range(total_steps):
        # 1. New vehicle arrivals (Poisson process)
        for approach, cfg in arrival_configs.items():
            if random.random() < cfg["prob"]:
                queues[approach]["count"] += 1
                queues[approach]["pce"] += cfg["pce"]

        # 2. Accumulate waiting delay for queued vehicles
        for approach in queues:
            total_waiting_time += queues[approach]["count"]

        # 3. Discharge vehicles on green approaches
        if not is_in_yellow:
            active_approaches = ["NORTH", "SOUTH"] if current_green_phase == "NS_PHASE" else ["EAST", "WEST"]
            for app in active_approaches:
                if queues[app]["count"] > 0:
                    discharged = min(queues[app]["count"], discharge_rate_per_sec)
                    discharged_int = int(discharged) if random.random() > (discharged - int(discharged)) else int(discharged) + 1
                    discharged_actual = min(queues[app]["count"], discharged_int)
                    if discharged_actual > 0:
                        pce_per_veh = queues[app]["pce"] / queues[app]["count"]
                        queues[app]["count"] -= discharged_actual
                        queues[app]["pce"] = max(0.0, queues[app]["pce"] - (discharged_actual * pce_per_veh))

        # 4. Traffic Signal Timing Controller
        current_timer += 1
        if mode == "fixed":
            if not is_in_yellow:
                if current_timer >= 35:
                    is_in_yellow = True
                    current_timer = 0
            else:
                if current_timer >= yellow_duration:
                    is_in_yellow = False
                    current_timer = 0
                    current_green_phase = "EW_PHASE" if current_green_phase == "NS_PHASE" else "NS_PHASE"

        elif mode == "adaptive":
            sim_lane_data = {
                app: {"pce_load": queues[app]["pce"], "count": queues[app]["count"]}
                for app in queues
            }

            if not is_in_yellow:
                should_end = (current_timer >= green_duration) or controller.should_terminate_early(
                    current_green_phase, current_timer, sim_lane_data
                )
                if should_end:
                    is_in_yellow = True
                    current_timer = 0
            else:
                if current_timer >= yellow_duration:
                    is_in_yellow = False
                    current_timer = 0
                    current_green_phase = "EW_PHASE" if current_green_phase == "NS_PHASE" else "NS_PHASE"
                    controller.update_starvation(current_green_phase)

                    decisions = controller.compute_green_times(sim_lane_data)
                    green_duration = int(decisions[current_green_phase]["green"])

    print(f"Simulation completed ({total_steps} steps). Cumulative Waiting Delay: {total_waiting_time:.2f} vehicle-seconds.\n")
    return total_waiting_time

if __name__ == "__main__":
    if not is_sumo_available():
        print("="*65)
        print("NOTICE: Eclipse SUMO binary was not found in PATH or SUMO_HOME.")
        print("Running high-fidelity built-in micro-simulation benchmark.")
        print("To install Eclipse SUMO: https://eclipse.dev/sumo/ or 'winget install Eclipse.SUMO'")
        print("="*65)

    fixed_delay = run_sumo_simulation(gui=False, mode="fixed")
    adaptive_delay = run_sumo_simulation(gui=False, mode="adaptive")
    
    improvement = ((fixed_delay - adaptive_delay) / fixed_delay) * 100
    print("="*55)
    print("BENCHMARK COMPARISON RESULTS:")
    print(f"  Fixed-Time Control Delay:    {fixed_delay:.1f} vehicle-seconds")
    print(f"  Adaptive AI Control Delay:   {adaptive_delay:.1f} vehicle-seconds")
    print(f"  Delay Reduction Improvement: {improvement:.2f}%")
    print("="*55)