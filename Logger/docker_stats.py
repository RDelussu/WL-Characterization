import subprocess
import time
import datetime
import json
import os

# --------------------
# CONFIGURATIONS
# --------------------
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
basename_file = f"stats_output_{timestamp}"

# Container info
container = "first_test"
name_image = "one/ad-base:v2"
bash_file = "source DemoAD_start.sh" # bash_command
gpu_enabled = False  # True if GPU is used

# Docker stats options
memory = "1g"
memory_reservation = "999m"
cpus = "1"
cpuset_cpus = "2"
gpus = "device=0"

# Sampling info
interval = 0.1  # seconds
num_iterations = 100

# Output files
config_file = f"{basename_file}_config.json"
if not gpu_enabled:
    output_file = f"{basename_file}_cpu_only.csv"
else:
    output_file = f"{basename_file}_with_gpu.csv"

# --------------------
# WRITE JSON CONFIG
# --------------------
config = {
    "timestamp": timestamp,
    "output_basename": basename_file,
    "container": {
        "name": container,
        "image": name_image,
        "gpu_enabled": gpu_enabled,
        "bash_command": bash_file
    },
    "docker_stats": {
        "memory": memory,
        "memory_reservation": memory_reservation,
        "cpus": cpus,
        "cpuset_cpus": cpuset_cpus,
        "gpus": gpus
    },
    "sampling": {
        "interval_seconds": interval,
        "num_iterations": num_iterations
    }
}

with open(config_file, "w") as f:
    json.dump(config, f, indent=2)

# --------------------
# WRITE CSV HEADER
# --------------------
if not os.path.exists(output_file):
    with open(output_file, "w") as f:
        if gpu_enabled:
            f.write("Timestamp,Iteration,Container,Name,CPU %,Mem Usage,Mem %,Net I/O,Block I/O,PIDs,GPU Power,GPU Temp.,Virtual RAM,GPU Utilization,GPU Memory Usage\n")
        else:
            f.write("Timestamp,Iteration,Container,Name,CPU %,Mem Usage,Mem %,Net I/O,Block I/O,PIDs\n")

# --------------------
# MAIN LOOP
# --------------------
for i in range(1, num_iterations + 1):
    print(f"Iteration number {i}")

    docker_run_cmd = [
        "docker", "run", "-ti", "-d",
        "--memory", memory,
        "--memory-reservation", memory_reservation,
        "--cpus", cpus,
        "--cpuset-cpus", cpuset_cpus,
        "--name", container
    ]

    if gpu_enabled:
        docker_run_cmd += ["--runtime=nvidia", "--gpus", gpus]

    docker_run_cmd += [name_image, "bash", "-c", bash_file]

    subprocess.run(docker_run_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    while True:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name=^/{container}$", "--format", "{{{{.Names}}}}"],
            stdout=subprocess.PIPE
        )
        if container not in result.stdout.decode():
            print(f"Container '{container}' is no longer active. Exit.")
            break

        timestamp_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        stats_cmd = ["docker", "stats", "--no-stream", "--format",
                     "{{.Container}},{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}",
                     container]
        stats_result = subprocess.run(stats_cmd, stdout=subprocess.PIPE)
        stats_line = stats_result.stdout.decode().strip()

        with open(output_file, "a") as f:
            if gpu_enabled:
                nvidia_cmd = ["nvidia-smi", "--query-gpu=power.draw,temperature.gpu,utilization.memory,utilization.gpu,memory.used,memory.total",
                              "--format=csv,noheader,nounits", "-i", "0"]
                nvidia_result = subprocess.run(nvidia_cmd, stdout=subprocess.PIPE)
                gpu_stats = nvidia_result.stdout.decode().strip().split(',')
                gpu_stats = [x.strip() for x in gpu_stats]
                gpu_line = ",".join(gpu_stats[:4] + [f"{gpu_stats[4]}/{gpu_stats[5]}"])
                f.write(f"{timestamp_now},{i},{stats_line},{gpu_line}\n")
            else:
                f.write(f"{timestamp_now},{i},{stats_line}\n")

        time.sleep(interval)

    subprocess.run(["docker", "rm", container], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
