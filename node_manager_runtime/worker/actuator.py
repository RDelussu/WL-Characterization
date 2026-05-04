import subprocess
import os

def get_governors_and_freqs():
    cpu_base = "/sys/devices/system/cpu/cpu0/cpufreq"
    result = {
        "governors": [],
        "userspace_frequencies": [],
        "userspace_available": False
    }
    if not os.path.exists(cpu_base):
        print("File cpufreq not available")
        return result
    try:
        with open(os.path.join(cpu_base, "scaling_available_governors")) as f:
            governors = f.read().split()
            allowed = {"performance", "powersave", "userspace"}
            filtered = [g for g in governors if g in allowed]
            result["governors"] = filtered
    except FileNotFoundError:
        print("File scaling_available_governors not found")
        return result
    if "userspace" in result["governors"]:
        result["userspace_available"] = True
        try:
            freq_file = os.path.join(cpu_base, "scaling_available_frequencies")
            if os.path.exists(freq_file):
                with open(freq_file) as f:
                    freqs = [int(x) for x in f.read().split()]
                    result["userspace_frequencies"] = [f / 1000  for f in freqs]
            else:
                result["userspace_frequencies"] = None
        except Exception as e:
            print("Error:", e)
    return result

def set_governor(governor):
    try:
        with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor") as f:
            current_governor = f.read().strip()
    except FileNotFoundError:
        print("Governor file not found")
        return
    if current_governor == governor:
        return
    cmd = f"echo {governor} | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.returncode == 0:
        print(f"Governor {governor} correctly applied")
    else:
        print("Error:", result.stderr.strip())

def set_frequency(freq):
    try:
        with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_setspeed") as f:
            current_freq = f.read().strip()
    except FileNotFoundError:
        print("Frequency file not found")
        return
    if current_freq == str(freq):
        return
    cmd = f"echo {freq} | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_setspeed"
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.returncode == 0:
        print(f"Frequency {freq} correctly applied")
    else:
        print("Error:", result.stderr.strip())
        
def apply_profile(governor, frequency=None):
    set_governor(governor)
    if governor == "userspace":
        set_frequency(frequency)
