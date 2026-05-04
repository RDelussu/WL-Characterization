import time
import psutil
import csv
import os
import re
import json
import subprocess
import threading
from datetime import datetime
from kubernetes import client, config
from queue import Queue

cores_percent = []
current_running_pods = 0
device_cpu = 0
device_ram = 0
current = 0
voltage = 0
power = 0
current_freq = 0
monitor_cpu = 0
monitor_ram = 0

n_cores = psutil.cpu_count(logical=True)
core_fields = [f"core_{i}" for i in range(n_cores)]
total_ram = psutil.virtual_memory().available

csv_files = {
    "MONITOR_LOG": "results_test/monitor_log.csv",
    "DEVICE_LOG": "results_test/device_log.csv",
    "PODS_LOG": "results_test/pods_log.csv",
}

MONITOR_LOG = csv_files["MONITOR_LOG"]
DEVICE_LOG = csv_files["DEVICE_LOG"]
PODS_LOG = csv_files["PODS_LOG"]

csv_fields = {
    "MONITOR_LOG": ["timestamp", "device", "os", "pods_running", "cpu_usage", "ram_usage"],
    "DEVICE_LOG": ["timestamp", "device", "os", "pods_running", "frequency", "voltage", "current", "power", "cpu_usage", "ram_usage"] + core_fields,
    "PODS_LOG": ["timestamp", "device", "os", "governor", "pods_running", "pod_name", "image", "parameters", "frequency", "voltage", "current", "power", "pod_cpu", "pod_ram", "net_read", "net_write", "block_read", "block_write", "monitor_cpu", "monitor_ram", "device_cpu", "device_ram"] + core_fields,
}

writer_queue = Queue()

def writer_thread():
    buffer = []
    while True:
        row, path = writer_queue.get()
        buffer.append((row, path))
        if len(buffer) >= 20:
            flush(buffer)
            buffer = []

def flush(buffer):
    files = {}
    for row, path in buffer:
        if path not in files:
            files[path] = []
        files[path].append(row)
    for path, rows in files.items():
        with open(path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

threading.Thread(target=writer_thread, daemon=True).start()
container_cache = {}

def get_pod_container_id_crictl(pod_name, namespace="default"):
    try:
        result = subprocess.run(["sudo", "crictl", "ps", "--namespace", namespace], capture_output=True, text=True)
        lines = result.stdout.strip().splitlines()
        if len(lines) < 2:
            return None
        for line in lines[1:]:
            cols = line.split()
            if len(cols) < 2:
                continue
            if any(pod_name in col for col in cols[1:]):
                return cols[0]
        return None
    except Exception as e:
        print(f"[Monitor] Error obtaining container ID: {e}")
        return None

def get_cached_container_id(pod_name, namespace="default"):
    if pod_name in container_cache:
        return container_cache[pod_name]
    cid = get_pod_container_id_crictl(pod_name, namespace)
    if cid:
        container_cache[pod_name] = cid
    return cid

def read_hwmon():
    base_path = "/sys/class/hwmon"
    try:
        for hwmon in os.listdir(base_path):
            hwmon_path = os.path.join(base_path, hwmon)
            name_file = os.path.join(hwmon_path, "name")
            if not os.path.exists(name_file):
                continue
            with open(name_file) as f:
                name = f.read().strip()
            if name == "amdgpu":
                power_file = os.path.join(hwmon_path, "power1_input")
                if os.path.exists(power_file):
                    power = int(open(power_file).read().strip()) / 1_000_000.0
                    return 0.00, 0.00, power
        return None, None, None
    except:
        return None, None, None

def read_hwmon2():
    base = "/sys/class/hwmon/hwmon2"
    try:
        with open(f"{base}/in1_input") as f:
            V = int(f.read().strip()) / 1000.0
        with open(f"{base}/curr1_input") as f:
            I = int(f.read().strip()) / 1000.0
        with open(f"{base}/power1_input") as f:
            P = int(f.read().strip()) / 1000000.0
        return V, I, P
    except:
        return None, None, None

def start_monitoring(v1, pid, device, device_os):
    for key, path in csv_files.items():
        if not os.path.exists(path):
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=csv_fields[key])
                writer.writeheader()
    global device_cpu, device_ram, cores_percent, current_running_pods, current, voltage, power, current_freq, monitor_cpu, monitor_ram
    power_samples = []
    time_samples = []
    interval_start = time.time()
    interval_length = 10
    while True:
        start = time.time()
        current_running_pods = get_running_pods_on_node(v1, device)
        device_ram = psutil.virtual_memory().percent
        cores_percent = psutil.cpu_percent(interval=None, percpu=True)
        device_cpu = sum(cores_percent) / n_cores
        monitor_cpu = pid.cpu_percent(interval=None) / n_cores
        monitor_ram = (pid.memory_info().rss / total_ram) * 100
        freq = psutil.cpu_freq()
        current_freq = freq.current if freq else 0
        if device == "kria":
            voltage, current, power = read_hwmon2()
        else:
            voltage, current, power = read_hwmon()
        now = time.time()
        if power is not None:
            power_samples.append(power)
            time_samples.append(now)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"[Monitoring] CPU:{device_cpu:.2f}% | "
            f"Ram:{device_ram:.2f}% | "
            f"FREQ:{current_freq:.2f} MHz | "
            f"V(V)={voltage if voltage else 'N/A'} | "
            f"I(A)={current if current else 'N/A'} | "
            f"P(W)={power if power else 'N/A'} | "
            f"Pods running={current_running_pods} | "
            f"MON_CPU={monitor_cpu:.2f}% | "
            f"MON_MEM={monitor_ram:.2f}%"
        )
        if now - interval_start >= interval_length and power_samples:
            avg_power = sum(power_samples) / len(power_samples)
            energy = avg_power * interval_length
            print(f"[Energy] Last {interval_length} sec avg power: {avg_power:.2f} W | Last {interval_length} sec energy used: {energy:.2f} J")
            power_samples.clear()
            time_samples.clear()
            interval_start = now        
        writer_queue.put(([timestamp, device, device_os, current_running_pods, f"{monitor_cpu:.2f}", f"{monitor_ram:.2f}"], MONITOR_LOG))
        writer_queue.put(([timestamp, device, device_os, current_running_pods, f"{current_freq:.2f}", f"{voltage:.2f}", f"{current:.2f}", f"{power:.2f}", f"{device_cpu:.2f}", f"{device_ram:.2f}", *[f"{c:.2f}" for c in cores_percent]], DEVICE_LOG))
        elapsed = time.time() - start
        time.sleep(max(0, 1 - elapsed))

def get_running_pods_on_node(v1, node_name):
    count = 0
    try:
        pods = v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}").items
        for pod in pods:
            if pod.status.phase == "Running" and pod.metadata.namespace != "kube-system":
                count += 1
        return count
    except Exception as e:
        print(f"[DEBUG] Error finding pod: {e}")
        return 0

last_crictl = 0
CRICTL_INTERVAL = 1.0

def get_pod_cpu_crictl(container_id):
    global last_crictl
    if time.time() - last_crictl < CRICTL_INTERVAL:
        return None, None
    last_crictl = time.time()
    try:
        result = subprocess.run(["sudo", "crictl", "stats", container_id], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")
        cols = re.split(r'\s{2,}', lines[1].strip())
        cpu = float(cols[2]) / n_cores if cols[2] != "-" else 0.0
        mem = cols[3]
        mem_value = float(mem[:-2]) if mem.endswith("MB") else 0
        return cpu, mem_value
    except:
        return 0.0, 0.0

def get_container_pid(container_id):
    try:
        result = subprocess.run(
            ["sudo", "crictl", "inspect", container_id],
            capture_output=True,
            text=True
        )
        data = json.loads(result.stdout)
        return data["info"]["pid"]
    except:
        return None

def get_network_usage(pid):
    try:
        with open(f"/proc/{pid}/net/dev") as f:
            lines = f.readlines()[2:]
        rx = 0
        tx = 0
        for line in lines:
            parts = line.split()
            rx += int(parts[1])
            tx += int(parts[9])
        rx_mb = rx / (1024 * 1024)
        tx_mb = tx / (1024 * 1024)
        return rx_mb, tx_mb
    except:
        return 0, 0

def get_cgroup_v2(pid):
    try:
        with open(f"/proc/{pid}/cgroup") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) == 3:
                    if parts[0] == "0":
                        return parts[2]
        return None
    except:
        return None

def get_block_io(pid):
    try:
        cg = get_cgroup_v2(pid)
        if not cg:
            return 0, 0
        path = f"/sys/fs/cgroup{cg}/io.stat"
        if not os.path.exists(path):
            print("Path not found")
            return 0, 0
        read_bytes = 0
        write_bytes = 0
        with open(path) as f:
            for line in f:
                for token in line.split():
                    if token.startswith("rbytes="):
                        read_bytes += int(token.split("=")[1])
                    elif token.startswith("wbytes="):
                        write_bytes += int(token.split("=")[1])
            read_mb = read_bytes / (1024 * 1024)
            write_mb = write_bytes / (1024 * 1024)
        return read_mb, write_mb
    except Exception as e:
        print(f"[BLOCK IO] Cgroup v2 error for pid {pid}: {e}")
        return 0, 0    

def monitor_pod_crictl(v1, device, device_os, governor, pod_name, image, start_time, n_pod_running, cpu_usage_start, env, namespace="default", interval=0.5):
    container_id = None
    while not container_id:
        container_id = get_cached_container_id(pod_name, namespace)
        time.sleep(0.5)
    pid = None
    pid_last_update = 0
    PID_REFRESH = 5    
    while True:
        start = time.time()
        now = time.time()        
        if pid is None or now - pid_last_update > PID_REFRESH:
            pid = get_container_pid(container_id)
            pid_last_update = now
        try:
            pod = v1.read_namespaced_pod(pod_name, namespace)
            if pod.status.phase.lower() in ("succeeded", "failed"):
                finish_time = time.time()
                exec_time = round(finish_time - start_time, 2)
                break
        except:
            break
        pod_cpu, pod_ram = get_pod_cpu_crictl(container_id)
        net_read, net_write = (0, 0)
        block_read, block_write = (0, 0)
        if pid:
            net_read, net_write = get_network_usage(pid)
            block_read, block_write = get_block_io(pid)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  
        writer_queue.put(([timestamp, device, device_os, governor, n_pod_running, pod_name, image, env, f"{current_freq:.2f}", f"{voltage:.2f}", f"{current:.2f}", f"{power:.2f}", f"{pod_cpu or 0:.2f}", f"{pod_ram or 0:.2f}", f"{net_read:.2f}", f"{net_write:.2f}", f"{block_read:.2f}", f"{block_write:.2f}", f"{monitor_cpu:.2f}", f"{monitor_ram:.2f}", f"{device_cpu:.2f}", f"{device_ram:.2f}", *[f"{c:.2f}" for c in cores_percent]], PODS_LOG))
        elapsed = time.time() - start
        time.sleep(max(0, interval - elapsed))        
    print(f"[Monitor] Pod {pod_name} finished")
