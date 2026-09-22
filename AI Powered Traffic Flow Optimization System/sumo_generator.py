# sumo_generator.py
import os
import shutil
import subprocess

def is_netconvert_available():
    """Checks if netconvert binary is available in PATH or SUMO_HOME."""
    if shutil.which("netconvert") is not None or shutil.which("netconvert.exe") is not None:
        return True
    sumo_home = os.environ.get("SUMO_HOME")
    if sumo_home and os.path.exists(os.path.join(sumo_home, "bin", "netconvert.exe")):
        return True
    return False

def get_netconvert_cmd():
    if shutil.which("netconvert"):
        return "netconvert"
    sumo_home = os.environ.get("SUMO_HOME")
    if sumo_home:
        binary = os.path.join(sumo_home, "bin", "netconvert.exe")
        if os.path.exists(binary):
            return binary
    return "netconvert"

def create_sumo_network(output_dir="sumo_env"):
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Node definitions
    nodes_xml = """<nodes>
    <node id="center" x="0.0" y="0.0" type="traffic_light"/>
    <node id="north" x="0.0" y="300.0" type="priority"/>
    <node id="south" x="0.0" y="-300.0" type="priority"/>
    <node id="east" x="300.0" y="0.0" type="priority"/>
    <node id="west" x="-300.0" y="0.0" type="priority"/>
</nodes>"""
    with open(f"{output_dir}/cross.nod.xml", "w") as f:
        f.write(nodes_xml)

    # 2. Edge definitions
    edges_xml = """<edges>
    <edge id="N2C" from="north" to="center" numLanes="2" speed="13.89"/>
    <edge id="C2N" from="center" to="north" numLanes="2" speed="13.89"/>
    <edge id="S2C" from="south" to="center" numLanes="2" speed="13.89"/>
    <edge id="C2S" from="center" to="south" numLanes="2" speed="13.89"/>
    <edge id="E2C" from="east" to="center" numLanes="2" speed="13.89"/>
    <edge id="C2E" from="center" to="east" numLanes="2" speed="13.89"/>
    <edge id="W2C" from="west" to="center" numLanes="2" speed="13.89"/>
    <edge id="C2W" from="center" to="west" numLanes="2" speed="13.89"/>
</edges>"""
    with open(f"{output_dir}/cross.edg.xml", "w") as f:
        f.write(edges_xml)

    # 3. Traffic Flow & Demand definitions
    routes_xml = """<routes>
    <vType id="car" accel="2.6" decel="4.5" length="4.5" maxSpeed="14.0"/>
    <vType id="truck" accel="1.2" decel="3.5" length="10.0" maxSpeed="10.0"/>

    <route id="r_NS" edges="N2C C2S"/>
    <route id="r_SN" edges="S2C C2N"/>
    <route id="r_EW" edges="E2C C2W"/>
    <route id="r_WE" edges="W2C C2E"/>

    <!-- Asymmetric demand to demonstrate adaptive balancing -->
    <flow id="flow_NS" type="car" route="r_NS" begin="0" end="1000" period="3"/>
    <flow id="flow_SN" type="car" route="r_SN" begin="0" end="1000" period="4"/>
    <flow id="flow_EW" type="car" route="r_EW" begin="0" end="1000" period="10"/>
    <flow id="flow_WE" type="truck" route="r_WE" begin="0" end="1000" period="12"/>
</routes>"""
    with open(f"{output_dir}/cross.rou.xml", "w") as f:
        f.write(routes_xml)

    # 4. SUMO Configuration file
    config_xml = f"""<configuration>
    <input>
        <net-file value="cross.net.xml"/>
        <route-files value="cross.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="1000"/>
    </time>
</configuration>"""
    with open(f"{output_dir}/cross.sumocfg", "w") as f:
        f.write(config_xml)

    # 5. Compile network using netconvert if installed
    if is_netconvert_available():
        cmd = get_netconvert_cmd()
        try:
            subprocess.run([
                cmd,
                f"--node-files={output_dir}/cross.nod.xml",
                f"--edge-files={output_dir}/cross.edg.xml",
                f"--output-file={output_dir}/cross.net.xml"
            ], check=True, stdout=subprocess.DEVNULL)
            print("✓ SUMO Network successfully compiled into cross.net.xml")
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            print("! Warning: netconvert encountered an error during compilation.")
            return False
    else:
        return False

if __name__ == "__main__":
    create_sumo_network()