import os 
import subprocess
import argparse
import shutil

print(" FLOW 0: VTR Flow ") 

parser = argparse.ArgumentParser(description='Run VTR Flow')
parser.add_argument('--verilog_file', required=True, help='Path to the verilog file')
parser.add_argument('--arch_file', required=True, help='Path to the architecture file')
parser.add_argument('--route_chan_width', type=int, default=8, help='Route channel width')
parser.add_argument('--run_bitstream_generator', action='store_true', help='Run the bitstream generator (flow 4)')
args = parser.parse_args()

vtr_root = os.environ.get("VTR_ROOT")
if vtr_root is None:
    print("Error: VTR_ROOT environment variable is not set.")
    exit(1)

command = [
    os.path.join(vtr_root, "vtr_flow/scripts/run_vtr_flow.py"),
    args.verilog_file,
    args.arch_file,
    "--route_chan_width",
    str(args.route_chan_width)
]

print("Running command: " + " ".join(command))
subprocess.run(command)

# --- New intermediate step ---
print("\n FLOW 1: Intermediate step")
hdl_filename = os.path.basename(args.verilog_file)
hdl_name_without_ext = os.path.splitext(hdl_filename)[0]

source_blif_path = os.path.join("temp", f"{hdl_name_without_ext}.pre-vpr.blif")
dest_blif_path = os.path.join("temp", f"{hdl_name_without_ext}.blif")

print(f"Copying {source_blif_path} to {dest_blif_path}")
try:
    shutil.copyfile(source_blif_path, dest_blif_path)
    print("Copy successful.")
except FileNotFoundError:
    print(f"Error: {source_blif_path} not found. Make sure VTR flow ran successfully and the temp directory is in the current working directory.")
    exit(1)

# --- VPR execution step ---
print("\n FLOW 2: VPR execution")

# Get project root before changing directory
project_root = os.getcwd()
temp_dir = os.path.join(project_root, "temp")

# VPR command arguments adjustment
arch_file_abs = os.path.abspath(args.arch_file)
circuit_file_in_temp = os.path.basename(dest_blif_path)


vpr_command = [
    os.path.join(vtr_root, "vpr", "vpr"),
    arch_file_abs,
    hdl_name_without_ext,
    "--circuit_file",
    circuit_file_in_temp,
    "--route_chan_width",
    str(args.route_chan_width),
    "--analysis",
    "--disp",
    "on"
]

print(f"Changing directory to {temp_dir}")
try:
    os.chdir(temp_dir)
    print("Running command: " + " ".join(vpr_command))
    print("Command will be executed in a new terminal window...")            
    subprocess.run(['gnome-terminal', '--'] + vpr_command) 
    # subprocess.run(vpr_command)

    # --- FASM Generation step ---
    print("\n FLOW 3: FASM Generation")

    genfasm_command = [
        os.path.join(vtr_root, "build", "utils", "fasm", "genfasm"),
        arch_file_abs,
        circuit_file_in_temp,
        "--route_chan_width",
        str(args.route_chan_width)
    ]

    print("Running command: " + " ".join(genfasm_command))
    subprocess.run(genfasm_command)

    # --- Bitstream Generation step ---
    if args.run_bitstream_generator:
        print("\n FLOW 4: Bitstream Generation")

        fasm_file = f"{hdl_name_without_ext}.fasm"
        place_file = f"{hdl_name_without_ext}.place"
        route_file = f"{hdl_name_without_ext}.route"

        bitstream_command = [
            "python3",
            os.path.join(project_root, "scripts", "gen_pseudo_bitstream.py"),
            "--fasm_file",
            fasm_file,
            "--place_file",
            place_file,
            "--route_file",
            route_file
        ]

        print("Running command: " + " ".join(bitstream_command))
        
        # Create bitstreams directory if it doesn't exist
        bitstreams_dir = os.path.join(project_root, "bitstreams")
        os.makedirs(bitstreams_dir, exist_ok=True)
        
        bitstream_file_path = os.path.join(bitstreams_dir, f"{hdl_name_without_ext}.bitstream")

        with open(bitstream_file_path, "w") as f:
            subprocess.run(bitstream_command, stdout=f)
        
        print(f"Bitstream saved to {bitstream_file_path}")

finally:
    # Change back to the original directory
    os.chdir(project_root)
    print(f"Changed directory back to {project_root}")

print("\nAll flows completed.")