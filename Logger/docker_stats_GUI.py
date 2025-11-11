import os
import json
import time
import queue
import threading
import datetime
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import platform
import psutil
import sys
import subprocess
import pprint

# Lookup table con (Thermal Design Power) TDP (aggiungine altri modelli se serve)
CPU_TDP_TABLE = {
    "Intel(R) Core(TM) i7-9750H": 45,
    "Intel(R) Core(TM) i5-8250U": 15,
    "Intel(R) Core(TM) i7-10750H": 45,
    "Intel(R) Core(TM) i9-9900K": 95,
    "Intel(R) Core(TM) i7-8700K": 95,
    "Intel(R) Core(TM) i5-9600K": 95,
    "AMD Ryzen 5 3600": 65,
    "AMD Ryzen 7 3700X": 65,
    "AMD Ryzen 9 3900X": 105,
    "AMD Ryzen 9 5950X": 105,
    "AMD Ryzen 7 5800X": 105,
    "AMD Ryzen 5 5600X": 65,
}

def lookup_tdp(cpu_name: str):
    for key, tdp in CPU_TDP_TABLE.items():
        if key in cpu_name:
            return tdp
    return None
# aggiunta queste due funzioni qui sotto: get_core_mapping_linux e get_physical_core_freq #
def get_core_mapping_linux():
    mapping = {}  # {logical_cpu: (physical_id, core_id)}
    try:
        with open("/proc/cpuinfo") as f:
            cpu_info = {}
            for line in f:
                if not line.strip():
                    if "processor" in cpu_info:
                        mapping[int(cpu_info["processor"])] = (
                            int(cpu_info.get("physical id", 0)),
                            int(cpu_info.get("core id", 0)),
                        )
                    cpu_info = {}
                else:
                    key, _, value = line.partition(":")
                    cpu_info[key.strip()] = value.strip()
    except FileNotFoundError:
        return {}

    return mapping

def get_physical_core_freq(core_id):
    mapping = get_core_mapping_linux()
    # trova i thread che appartengono a quel core fisico
    logical_cpus = [lid for lid, (_, cid) in mapping.items() if cid == core_id]
    if not logical_cpus:
        raise ValueError(f"Nessun core fisico con ID {core_id} trovato.")
    
    freqs = psutil.cpu_freq(percpu=True)
    # media delle frequenze dei thread appartenenti al core fisico
    psutil_version = psutil.version_info
    if psutil_version == (5,9,0):
        # print('sono dentro get_physical_... if psutil')
        avg_freq = (sum(freqs[i].current for i in logical_cpus) / len(logical_cpus))*1000
    else: 
        avg_freq = sum(freqs[i].current for i in logical_cpus) / len(logical_cpus)

    return avg_freq

# qui sotto nuova get_cpu_report
def get_cpu_report(physical_core_id=None):
    report = {}
    # check psultil version - bug in 5.9.0 
    # psutil_version = tuple(map(int, psutil.__version__.split('.')))
    if physical_core_id is not None and sys.platform.startswith("linux"):
        try:
            report["cpu_mhz"] = round(get_physical_core_freq(physical_core_id), 2)
        except Exception as e:
            report["cpu_mhz"] = f"Error: {e}"
    else:
        freq = psutil.cpu_freq()
        report["cpu_mhz"] = round(freq.current, 2) if freq else "N/A"

    report["cpu_clock_min_mhz"] = round(psutil.cpu_freq().min, 2) 
    report["cpu_clock_max_mhz"] = round(psutil.cpu_freq().max, 2) 
    report["cpu_cores_physical"] = psutil.cpu_count(logical=False)
    report["cpu_cores_logical"] = psutil.cpu_count(logical=True)
    report["cpu_model_name"] = platform.processor()

    # --- Model name CPU (OS specific) ---
    model_name = None
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        model_name = line.strip().split(":")[1].strip()
                        break
        except FileNotFoundError:
            pass
        # Proviamo a leggere TDP se disponibile
        try:
            tdp_output = subprocess.check_output("lscpu", shell=True).decode()
            for line in tdp_output.splitlines():
                if "TDP" in line:
                    report["cpu_power_watt"] = line.split(":")[1].strip()
                    break
        except Exception:
            report["cpu_power_watt"] = None

    elif sys.platform == "darwin":  # macOS
        try:
            model_name = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"]
            ).strip().decode()
        except Exception:
            pass
        report["cpu_power_watt"] = None  # non disponibile nativamente

    elif sys.platform == "win32":  # Windows
        try:
            model_name = subprocess.check_output(
                ["wmic", "cpu", "get", "Name"]
            ).decode().split("\n")[1].strip()
        except Exception:
            pass
        report["cpu_power_watt"] = None  # non disponibile via WMI standard

    report["cpu_model_name"] = model_name or platform.processor() or "N/A"

    # --- Lookup TDP (se non già trovato dal sistema) ---
    if report.get("cpu_power_watt") in [None, ""]:
        tdp_value = lookup_tdp(report["cpu_model_name"])
        report["cpu_power_watt"] = f"{tdp_value} W" if tdp_value else None


    return report


def NO_get_cpu_report():
    report = {}
    
    # --- Frequenze ---
    freq = psutil.cpu_freq()
    psutil_version = psutil.version_info
    if freq:
        if psutil_version == (5, 9, 0):
            report["cpu_mhz"] = round(freq.current*1000, 2) # frequenza attuale
        else:
            report["cpu_mhz"] = round(freq.current, 2) # frequenza attuale
        
        # print("sono in GET CPU REPORT -- frequenza attuale-corrente", report["cpu_mhz"])
        report["cpu_clock_min_mhz"] = round(freq.min, 2)
        report["cpu_clock_max_mhz"] = round(freq.max, 2)  # "potenza max"
    else:
        report["cpu_mhz"] = report["cpu_clock_min_mhz"] = report["cpu_clock_max_mhz"] = "N/A"

    # --- Cores ---
    report["cpu_cores_physical"] = psutil.cpu_count(logical=False)
    report["cpu_cores_logical"] = psutil.cpu_count(logical=True)

    # --- Model name CPU (OS specific) ---
    model_name = None
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        model_name = line.strip().split(":")[1].strip()
                        break
        except FileNotFoundError:
            pass
        # Proviamo a leggere TDP se disponibile
        try:
            tdp_output = subprocess.check_output("lscpu", shell=True).decode()
            for line in tdp_output.splitlines():
                if "TDP" in line:
                    report["cpu_power_watt"] = line.split(":")[1].strip()
                    break
        except Exception:
            report["cpu_power_watt"] = None

    elif sys.platform == "darwin":  # macOS
        try:
            model_name = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"]
            ).strip().decode()
        except Exception:
            pass
        report["cpu_power_watt"] = None  # non disponibile nativamente

    elif sys.platform == "win32":  # Windows
        try:
            model_name = subprocess.check_output(
                ["wmic", "cpu", "get", "Name"]
            ).decode().split("\n")[1].strip()
        except Exception:
            pass
        report["cpu_power_watt"] = None  # non disponibile via WMI standard

    report["cpu_model_name"] = model_name or platform.processor() or "N/A"

    # --- Lookup TDP (se non già trovato dal sistema) ---
    if report.get("cpu_power_watt") in [None, ""]:
        tdp_value = lookup_tdp(report["cpu_model_name"])
        report["cpu_power_watt"] = f"{tdp_value} W" if tdp_value else None

    return report
    
# ----------------------------
# Utilities
# ----------------------------
def now_stamp(fmt="%Y%m%d_%H%M%S"):
    return datetime.datetime.now().strftime(fmt)

def safe_run(cmd, **popen_kwargs):
    """
    Run a subprocess command and return (retcode, stdout, stderr) with UTF-8 decoding.
    """
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            **popen_kwargs
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except FileNotFoundError as e:
        return 127, "", str(e)
    except Exception as e:
        return 1, "", str(e)

def docker_available():
    code, out, err = safe_run(["docker", "--version"])
    return code == 0

def nvidia_smi_available():
    code, out, err = safe_run(["nvidia-smi", "--help"])
    return code == 0

# ----------------------------
# Worker (background thread)
# ----------------------------
class StatsWorker(threading.Thread):
    def __init__(self, params, log_q, stop_event):
        super().__init__(daemon=True)
        self.params = params
        self.log_q = log_q
        self.stop_event = stop_event
        self.list_cpu_curr = []

    def log(self, msg):
        self.log_q.put(msg)

    def write_config(self, config_path, config_obj):
        with open(config_path, "w") as f:
            json.dump(config_obj, f, indent=2)

    def ensure_csv_header(self, csv_path, gpu_enabled):
        if not os.path.exists(csv_path):
            with open(csv_path, "w") as f:
                if gpu_enabled:
                    f.write("Timestamp,Iteration,Container,Name,CPU %,Mem Usage,Mem %,Net I/O,Block I/O,PIDs,CPU MHz,CPU Min MHz,CPU Max MHz,"
                            "GPU Power (W),GPU Temp. (°C),Virtual RAM (%),GPU Utilization (%),GPU Memory Usage (B)\n")
                else:
                    f.write("Timestamp,Iteration,Container,Name,CPU %,Mem Usage,Mem %,Net I/O,Block I/O,PIDs,CPU MHz,CPU Min MHz,CPU Max MHz\n")

    def container_active(self, name):
        code, out, err = safe_run(
            ["docker", "ps", "--filter", f"name=^/{name}$", "--format", "{{.Names}}"]
        )
        if code != 0:
            return False
        return name in out.splitlines()

    def rm_container(self, name, force=False):
        if not name:
            return
        cmd = ["docker", "rm"]
        if force:
            cmd.append("-f")
        cmd.append(name)
        safe_run(cmd)

    def run_one_iteration(self, i, files, p):
        """
        Start container, monitor with docker stats, append CSV, stop when container exits
        or when stop_event is set.
        """
        # Build docker run
        docker_run_cmd = [
            "docker", "run", "-ti", "-d",
            "--memory", p["memory"],
            "--memory-reservation", p["memory_reservation"],
            "--cpus", p["cpus"],
            "--cpuset-cpus", p["cpuset_cpus"],
            "--name", p["container"]
        ]

        if p["gpu_enabled"]:
            docker_run_cmd += ["--runtime=nvidia", "--gpus", p["gpus"]]

        docker_run_cmd += [p["name_image"], "bash", "-c", p["bash_file"]]

        self.log(f"[{i}] Launching container: {' '.join(docker_run_cmd)}")
        code, out, err = safe_run(docker_run_cmd)

        if code != 0:
            self.log(f"[{i}] ERROR starting container: {err or out}")
            return False  # fail this iteration

        
        # Poll until container exits or stop requested
        interval = float(p["interval"])
        while not self.stop_event.is_set():
            if not self.container_active(p["container"]):
                self.log(f"[{i}] Container '{p['container']}' is no longer active. Exiting iteration.")
                break

            timestamp_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            stats_cmd = [
                "docker", "stats", "--no-stream",
                "--format", "{{.Container}},{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}",
                p["container"]
            ]
            scode, sout, serr = safe_run(stats_cmd)
            if scode != 0:
                self.log(f"[{i}] WARNING: docker stats failed: {serr or sout}")
                time.sleep(interval)
                continue

            line = sout.strip()

            # freq = get_cpu_report(physical_core_id=p["cpuset_cpus"])
            physical_cores = [int(x) for x in p["cpuset_cpus"].split(',') if x.strip().isdigit()]
            # print('physical cores', physical_cores)
            freq = get_cpu_report(physical_core_id=physical_cores[0] if physical_cores else None)
            if freq:
                # cpu_cur = round(freq["cpu_mhz"], 2)
                cpu_cur = round(freq["cpu_mhz"], 2)
                cpu_min = round(freq["cpu_clock_min_mhz"], 2)
                cpu_max = round(freq["cpu_clock_max_mhz"], 2)
            else:
                cpu_cur = cpu_min = cpu_max = "N/A"
            # print("frequenza attuale-corrente", cpu_cur)
            self.list_cpu_curr.append(cpu_cur)
            
            # Costruisci la riga con i campi aggiuntivi
            #line_with_cpu = f"{line.split(',')[0]},{line.split(',')[1]},{cpu_cur},{cpu_min},{cpu_max}," + ",".join(
            #    line.split(',')[2:])
            line_with_cpu = f"{line},{cpu_cur},{cpu_min},{cpu_max}"

            try:
                with open(files["csv"], "a") as f:
                    if p["gpu_enabled"]:
                        # Query GPU stats
                        ncode, nout, nerr = safe_run([
                            "nvidia-smi",
                            "--query-gpu=power.draw,temperature.gpu,utilization.memory,utilization.gpu,memory.used,memory.total",
                            "--format=csv,noheader,nounits", "-i", "0"
                        ])
                        if ncode == 0 and nout:
                            gpu_stats = [x.strip() for x in nout.split(",")]
                            # GPU columns: power, temp, util.mem, util.gpu, mem.used/mem.total
                            gpu_line = ",".join(gpu_stats[:4] + [f"{gpu_stats[4]}/{gpu_stats[5]}"])
                            f.write(f"{timestamp_now},{i},{line_with_cpu},{gpu_line}\n")
                        else:
                            self.log(f"[{i}] WARNING: nvidia-smi failed: {nerr or nout}")
                            f.write(f"{timestamp_now},{i},{line_with_cpu},,,,,\n")
                    else:
                        f.write(f"{timestamp_now},{i},{line_with_cpu}\n")
            except Exception as e:
                self.log(f"[{i}] ERROR writing CSV: {e}")
                return False

            #time.sleep(interval)

        # Attempt to remove container (non-fatal if fails)
        self.rm_container(p["container"])
        return True
        
    def run(self):
        p = self.params
    
        # Pre-flight checks
        if not docker_available():
            self.log("ERROR: 'docker' not found or not runnable. Please install Docker and ensure it is on PATH.")
            return
        if p["gpu_enabled"] and not nvidia_smi_available():
            self.log("ERROR: GPU mode selected, but 'nvidia-smi' not found. Install NVIDIA drivers/tooling or disable GPU.")
            return
    
        # Prepare output paths
        ts = now_stamp()
        base = f"stats_output_{ts}"
        out_dir = p["output_dir"] or os.getcwd()
        os.makedirs(out_dir, exist_ok=True)
    
        files = {
            "config": os.path.join(out_dir, f"{base}_config.json"),
            "csv": os.path.join(out_dir, f"{base}_{'with_gpu' if p['gpu_enabled'] else 'cpu_only'}.csv")
        }
    
        # CSV header
        try:
            self.ensure_csv_header(files["csv"], p["gpu_enabled"])
        except Exception as e:
            self.log(f"ERROR preparing CSV: {e}")
            return
    
        # Lista per tutte le frequenze raccolte
        self.list_cpu_curr = []
    
        self.log(f"Outputs:\n- Config: {files['config']}\n- CSV: {files['csv']}")
        self.log("Starting iterations...")
    
        for i in range(1, int(p["num_iterations"]) + 1):
            if self.stop_event.is_set():
                self.log("Stop requested. Halting before next iteration.")
                break
    
            self.log(f"Iteration {i}/{p['num_iterations']}")
            ok = self.run_one_iteration(i, files, p)
            if not ok:
                self.log(f"[{i}] Iteration aborted due to errors.")
                break
    
        # Tutte le iterazioni completate → calcolo media CPU
        self.log("All iterations completed. Calculating average CPU frequency...")
    
        # Otteniamo info CPU max and min
        # cpu_info = get_cpu_report(physical_core_id=p["cpuset_cpus"])
        physical_cores = [int(x) for x in p["cpuset_cpus"].split(',') if x.strip().isdigit()]
        # print('physical cores', physical_cores)
        cpu_info = get_cpu_report(physical_core_id=physical_cores[0] if physical_cores else None)

    
        # Calcoliamo media CPU MHz raccolta durante le iterazioni
        psutil_version = psutil.version_info
        if self.list_cpu_curr:
            if psutil_version == (5,9,0):
                avg_cpu_mhz = (sum(self.list_cpu_curr) / len(self.list_cpu_curr)) #*1000 
            else:
                avg_cpu_mhz = sum(self.list_cpu_curr) / len(self.list_cpu_curr)
        else:
            avg_cpu_mhz = cpu_info["cpu_mhz"]
    
        # Creiamo l’oggetto JSON finale
        config_obj = {
            "timestamp": ts,
            "output_basename": base,
            "container": {
                "name": p["container"],
                "image": p["name_image"],
                "gpu_enabled": p["gpu_enabled"],
                "bash_command": p["bash_file"]
            },
            "docker_stats": {
                "memory": p["memory"],
                "memory_reservation": p["memory_reservation"],
                "cpus": p["cpus"],
                "cpuset_cpus": p["cpuset_cpus"],
                "gpus": p["gpus"]
            },
            "sampling": {
                "interval_seconds": float(p["interval"]),
                "num_iterations": int(p["num_iterations"])
            },
            "Processor Information": {
                "cpu_mhz_avg": round(float(avg_cpu_mhz), 2),
                "cpu_clock_min_mhz": cpu_info["cpu_clock_min_mhz"],
                "cpu_clock_max_mhz": cpu_info["cpu_clock_max_mhz"],
                "cpu_cores_physical": cpu_info["cpu_cores_physical"],
                "cpu_cores_logical": cpu_info["cpu_cores_logical"],
                "cpu_model_name": cpu_info["cpu_model_name"],
                "cpu_power_watt": cpu_info["cpu_power_watt"],
            }
        }
    
        try:
            self.write_config(files["config"], config_obj)
            with open("cpu_info.json", "w", encoding="utf-8") as f:
                json.dump(cpu_info, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log(f"ERROR writing final config: {e}")
            return
    
        # self.log(f"Average CPU frequency over all iterations: {round(avg_cpu_mhz, 2)} MHz")
        self.log("Final JSON file saved successfully.")
        self.log("Done.")


# ----------------------------
# GUI
# ----------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Docker Stats Runner (GUI)")
        self.geometry("900x680")
        self.minsize(900, 680)

        self.stop_event = threading.Event()
        self.worker = None
        self.log_q = queue.Queue()

        self._build_widgets()
        self._poll_log_queue()

    def _build_widgets(self):
        pad = {"padx": 8, "pady": 6}

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        frm_general = ttk.Frame(notebook)
        frm_resources = ttk.Frame(notebook)
        frm_sampling = ttk.Frame(notebook)
        frm_output = ttk.Frame(notebook)
        notebook.add(frm_general, text="General")
        notebook.add(frm_resources, text="Resources")
        notebook.add(frm_sampling, text="Sampling")
        notebook.add(frm_output, text="Output")

        # General tab
        self.var_container = tk.StringVar(value="first_test")
        self.var_image = tk.StringVar(value="one/ad-base:v2")
        self.var_bash = tk.StringVar(value="source DemoAD_start.sh")
        self.var_gpu = tk.BooleanVar(value=False)
        self.var_gpuspec = tk.StringVar(value="device=0")

        row = 0
        ttk.Label(frm_general, text="Container name").grid(row=row, column=0, sticky="e", **pad)
        ttk.Entry(frm_general, textvariable=self.var_container, width=40).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        ttk.Label(frm_general, text="Image").grid(row=row, column=0, sticky="e", **pad)
        ttk.Entry(frm_general, textvariable=self.var_image, width=40).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        ttk.Label(frm_general, text="Bash command").grid(row=row, column=0, sticky="e", **pad)
        ttk.Entry(frm_general, textvariable=self.var_bash, width=40).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        ttk.Checkbutton(frm_general, text="Enable GPU (nvidia-smi required)", variable=self.var_gpu).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        ttk.Label(frm_general, text="--gpus").grid(row=row, column=0, sticky="e", **pad)
        ttk.Entry(frm_general, textvariable=self.var_gpuspec, width=20).grid(row=row, column=1, sticky="w", **pad)

        # Resources tab
        self.var_memory = tk.StringVar(value="1g")
        self.var_mem_res = tk.StringVar(value="999m")
        self.var_cpus = tk.StringVar(value="1")
        self.var_cpuset = tk.StringVar(value="2")

        row = 0
        ttk.Label(frm_resources, text="--memory").grid(row=row, column=0, sticky="e", **pad)
        ttk.Entry(frm_resources, textvariable=self.var_memory, width=15).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        ttk.Label(frm_resources, text="--memory-reservation").grid(row=row, column=0, sticky="e", **pad)
        ttk.Entry(frm_resources, textvariable=self.var_mem_res, width=15).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        ttk.Label(frm_resources, text="--cpus").grid(row=row, column=0, sticky="e", **pad)
        ttk.Entry(frm_resources, textvariable=self.var_cpus, width=15).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        ttk.Label(frm_resources, text="--cpuset-cpus").grid(row=row, column=0, sticky="e", **pad)
        ttk.Entry(frm_resources, textvariable=self.var_cpuset, width=15).grid(row=row, column=1, sticky="w", **pad)

        # Sampling tab
        self.var_interval = tk.StringVar(value="0.1")
        self.var_iterations = tk.StringVar(value="100")

        row = 0
        ttk.Label(frm_sampling, text="Interval (seconds)").grid(row=row, column=0, sticky="e", **pad)
        ttk.Entry(frm_sampling, textvariable=self.var_interval, width=10).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        ttk.Label(frm_sampling, text="Iterations").grid(row=row, column=0, sticky="e", **pad)
        ttk.Entry(frm_sampling, textvariable=self.var_iterations, width=10).grid(row=row, column=1, sticky="w", **pad)

        # Output tab
        self.var_outdir = tk.StringVar(value=os.path.join(os.getcwd(),'stats_output'))
        row = 0
        ttk.Label(frm_output, text="Output directory").grid(row=row, column=0, sticky="e", **pad)
        ent_out = ttk.Entry(frm_output, textvariable=self.var_outdir, width=50)
        ent_out.grid(row=row, column=1, sticky="w", **pad)
        ttk.Button(frm_output, text="Browse…", command=self._pick_dir).grid(row=row, column=2, sticky="w", **pad)

        # Control bar
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=6)
        self.btn_start = ttk.Button(bar, text="Start", command=self._on_start)
        self.btn_stop = ttk.Button(bar, text="Stop", command=self._on_stop, state="disabled")
        self.btn_start.pack(side="left")
        self.btn_stop.pack(side="left", padx=6)

        # Log area
        frm_log = ttk.LabelFrame(self, text="Log")
        frm_log.pack(fill="both", expand=True, padx=8, pady=6)
        self.txt = tk.Text(frm_log, height=16, wrap="word")
        self.txt.pack(fill="both", expand=True, padx=6, pady=6)
        self.txt.configure(state="disabled")

    def _pick_dir(self):
        d = filedialog.askdirectory(initialdir=self.var_outdir.get() or os.getcwd())
        if d:
            self.var_outdir.set(d)

    def _gather_params(self):
        try:
            interval = float(self.var_interval.get())
            iters = int(self.var_iterations.get())
            if interval <= 0 or iters <= 0:
                raise ValueError
        except Exception:
            raise ValueError("Interval must be a positive number and Iterations a positive integer.")

        return {
            "container": self.var_container.get().strip(),
            "name_image": self.var_image.get().strip(),
            "bash_file": self.var_bash.get().strip(),
            "gpu_enabled": bool(self.var_gpu.get()),
            "gpus": self.var_gpuspec.get().strip() or "device=0",
            "memory": self.var_memory.get().strip(),
            "memory_reservation": self.var_mem_res.get().strip(),
            "cpus": self.var_cpus.get().strip(),
            "cpuset_cpus": self.var_cpuset.get().strip(),
            "interval": interval,
            "num_iterations": iters,
            "output_dir": self.var_outdir.get().strip(),
        }

    def _on_start(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Running", "A run is already in progress.")
            return
        try:
            params = self._gather_params()
        except ValueError as e:
            messagebox.showerror("Invalid parameters", str(e))
            return

        if not params["container"]:
            messagebox.showerror("Invalid parameters", "Container name must not be empty.")
            return
        if not params["name_image"]:
            messagebox.showerror("Invalid parameters", "Image must not be empty.")
            return
        if not params["bash_file"]:
            messagebox.showerror("Invalid parameters", "Bash command must not be empty.")
            return

        self.stop_event.clear()
        self.worker = StatsWorker(params, self.log_q, self.stop_event)
        self.worker.start()
        self._set_running(True)
        self._log_to_ui("=== Run started ===")


    def _on_stop(self):
        if self.worker and self.worker.is_alive():
            self.stop_event.set()
            self._log_to_ui("Stop requested. Attempting to halt gracefully...")
    
        # Legge il nome del container dalla StringVar di Tkinter
        container_name = self.var_container.get().strip() if hasattr(self, "var_container") else None
    
        if container_name:
            try:
                self._log_to_ui(f"Stopping Docker container '{container_name}'...")
                subprocess.run(["docker", "stop", container_name], check=True)
                self._log_to_ui(f"Container '{container_name}' stopped successfully.")
            except subprocess.CalledProcessError as e:
                self._log_to_ui(f"Failed to stop container '{container_name}': {e}")
        else:
            self._log_to_ui("No container name defined — skipping Docker stop.")
    
        # Rimuove i container fermi (status=exited)
        try:
            self._log_to_ui("Removing stopped containers...")
            exited_containers = subprocess.check_output(
                ["docker", "ps", "-a", "-q", "-f", "status=exited"]
            ).decode().split()
    
            if exited_containers:
                for cid in exited_containers:
                    subprocess.run(["docker", "rm", cid], check=False)
                self._log_to_ui(f"Removed {len(exited_containers)} stopped container(s).")
            else:
                self._log_to_ui("No stopped containers to remove.")
        except Exception as e:
            self._log_to_ui(f"Failed to remove stopped containers: {e}")
    
        self._set_running(False)
    

    def _set_running(self, running: bool):
        self.btn_start.configure(state="disabled" if running else "normal")
        self.btn_stop.configure(state="normal" if running else "disabled")

    def _log_to_ui(self, msg: str):
        self.txt.configure(state="normal")
        self.txt.insert("end", msg + "\n")
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_q.get_nowait()
                self._log_to_ui(msg)
        except queue.Empty:
            pass
        # re-arm polling
        self.after(150, self._poll_log_queue)

if __name__ == "__main__":
    app = App()
    app.mainloop()
