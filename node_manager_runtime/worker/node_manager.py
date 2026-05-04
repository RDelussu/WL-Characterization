import threading
import time
import psutil
import os
import platform
from kubernetes import client, config, watch

from predictor2 import predict_best_governor, load_model
from actuator import apply_profile, get_governors_and_freqs
import monitor
from monitor import monitor_pod_crictl

WORKER_NODE_NAME = platform.node().lower()
os.makedirs("results_test", exist_ok=True)

processing_pods = set()
processing_lock = threading.Lock()

def get_linux_distro():
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=")[1].strip().strip('"')
    except Exception:
        return "Unknown Linux"

device_os = get_linux_distro()

def monitor_idle_node(userspace_available, min_freq):
    zero_seconds = 0
    idle_applied = False
    while True:
        current = monitor.current_running_pods
        if current == 0:
            if not idle_applied:
                zero_seconds += 1
                if zero_seconds >= 5:
                    if userspace_available:
                        print("[IdleMonitor] Node idle for 5 seconds -> setting 333.33 MHz")
                        apply_profile("userspace", min_freq)
                    else:
                        print("[IdleMonitor] Node idle for 5 seconds -> setting powersave governor")
                        apply_profile("powersave")
                    idle_applied = True
        else:
            zero_seconds = 0
            idle_applied = False
        time.sleep(1)
        
def wait_pod_end(pod_name, namespace):
    api = client.CoreV1Api()
    while True:
        pod = api.read_namespaced_pod(pod_name, namespace)
        phase = pod.status.phase.lower()

        if phase in ("succeeded", "failed", "unknown"):
            break
        time.sleep(1)
    
def get_pod_env_vars(pod):
    envs = {}
    for container in pod.spec.containers:
        if container.env:
            for e in container.env:
                envs[e.name] = e.value
    return envs    
        
def handle_pod(v1, pod, model, candidate_freqs, candidate_governors):
    pod_name = pod.metadata.name
    namespace = pod.metadata.namespace
    image = pod.spec.containers[0].image
    env_vars = get_pod_env_vars(pod)    
    env = ";".join(f"{k}={v}" for k, v in env_vars.items())
    print(f"[Handle] Handling pod {pod_name}")
    try:
        n_pod_running = monitor.current_running_pods
        cpu_usage_start = psutil.cpu_percent(interval=None)
        if model is not None:
            governor, frequency = predict_best_governor(model, pod_name, n_pod_running, cpu_usage_start, WORKER_NODE_NAME, device_os, env, candidate_freqs, candidate_governors)
        else:
            governor = "powersave"
            frequency = 0
        if governor == "user1" or governor == "user2":
            governor = "userspace"
        apply_profile(governor, frequency)
        start_time = time.time()
        monitor_thread = threading.Thread(target=monitor_pod_crictl, args=(v1, WORKER_NODE_NAME, device_os, governor, pod_name, image, start_time, n_pod_running, cpu_usage_start, env), daemon=True)
        monitor_thread.start()
        pass
        wait_pod_end(pod_name, namespace)
    finally:
        monitor_thread.join()
        print(f"[Handle] Monitor ended for pod {pod_name}")

def main():
    use_model_input = input("Model required? (y/n): ").strip().lower()
    use_model = use_model_input == "y"
    model = None
    if use_model:
        print("[Main] Loading model...")
        model = load_model("pc")
        #model = load_model()
    else:
        print("[Main] A static profile will be used")
    print("[Main] Starting system...")
    pid = psutil.Process(os.getpid())
    result = get_governors_and_freqs()
    userspace_available = result["userspace_available"]
    min_freq = 0
    config.load_kube_config()
    v1 = client.CoreV1Api()
    w = watch.Watch()    
    if result["userspace_frequencies"]:
        min_freq = min(result["userspace_frequencies"])
    threading.Thread(target=monitor_idle_node, args=(userspace_available,min_freq), daemon=True).start()
    threading.Thread(target=monitor.start_monitoring, args=(v1,pid,WORKER_NODE_NAME,device_os), daemon=True).start()
    print("[Main] Watching for pods...")
    for event in w.stream(v1.list_pod_for_all_namespaces, field_selector=f"spec.nodeName={WORKER_NODE_NAME}"):
        pod = event["object"]
        pod_ok = (event["type"] == "MODIFIED" and pod.spec.node_name == WORKER_NODE_NAME and pod.status.phase == "Pending")
        if not pod_ok:
            continue
        pod_name = pod.metadata.name
        namespace = pod.metadata.namespace
        with processing_lock:
            if pod_name in processing_pods:
                continue
            processing_pods.add(pod_name)
        handle_thread = threading.Thread(
            target=handle_pod,
            args=(v1,pod,model,result["userspace_frequencies"],result["governors"]),
            daemon=True
        )
        handle_thread.start()        

if __name__ == "__main__":
    main()
