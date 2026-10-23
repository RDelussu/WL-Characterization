import pandas as pd
import os
import csv

folder_path = 'results_test/'
PODS_LOG = os.path.join(folder_path, 'pods_log.csv')
CONTAINER_LOG = os.path.join(folder_path, 'container_log.csv')
CATEGORIES = os.path.join(folder_path, 'categories.csv')

CPU_HIGH = 80
CPU_MED = 50

RAM_HIGH = 80
RAM_MED = 50


def non_zero_stats(series):
    filtered = series[series != 0]
    if filtered.empty:
        return 0, 0, 0
    return (
        filtered.mean(),
        filtered.min(),
        filtered.max()
    )

df = pd.read_csv(PODS_LOG)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values(["pod_name", "timestamp"])

def aggregate_pod(group):
    start_time = group["timestamp"].iloc[0]
    end_time = group["timestamp"].iloc[-1]
    duration = (end_time - start_time).total_seconds()

    avg_cpu, min_cpu, max_cpu = non_zero_stats(group["pod_cpu"])
    avg_ram, min_ram, max_ram = non_zero_stats(group["pod_ram"])

    avg_freq, min_freq, max_freq = non_zero_stats(group["frequency"])
    avg_voltage, min_voltage, max_voltage = non_zero_stats(group["voltage"])
    avg_current, min_current, max_current = non_zero_stats(group["current"])
    avg_power, min_power, max_power = non_zero_stats(group["power"])

    avg_net_read, min_net_read, max_net_read = non_zero_stats(group["net_read"])
    avg_net_write, min_net_write, max_net_write = non_zero_stats(group["net_write"])

    avg_block_read, min_block_read, max_block_read = non_zero_stats(group["block_read"])
    avg_block_write, min_block_write, max_block_write = non_zero_stats(group["block_write"])

    result = {
        "end_time": end_time,
        "device": group["device"].iloc[0],
        "os": group["os"].iloc[0],
        "pods_running": group["pods_running"].iloc[0],
        "pod_name": group.name,
        "image": group["image"].iloc[0],
        "governor": group["governor"].iloc[0],
        "cpu_usage_start": group["device_cpu"].iloc[0],

        "avg_cpu": avg_cpu,
        "min_cpu": min_cpu,
        "max_cpu": max_cpu,

        "avg_ram": avg_ram,
        "min_ram": min_ram,
        "max_ram": max_ram,

        "avg_freq": avg_freq,
        "min_freq": min_freq,
        "max_freq": max_freq,

        "avg_voltage": avg_voltage,
        "min_voltage": min_voltage,
        "max_voltage": max_voltage,

        "avg_current": avg_current,
        "min_current": min_current,
        "max_current": max_current,

        "avg_power": avg_power,
        "min_power": min_power,
        "max_power": max_power,

        "avg_net_read": avg_net_read,
        "min_net_read": min_net_read,
        "max_net_read": max_net_read,

        "avg_net_write": avg_net_write,
        "min_net_write": min_net_write,
        "max_net_write": max_net_write,

        "avg_block_read": avg_block_read,
        "min_block_read": min_block_read,
        "max_block_read": max_block_read,

        "avg_block_write": avg_block_write,
        "min_block_write": min_block_write,
        "max_block_write": max_block_write,

        "duration": duration,
        "energy_used": avg_power * duration,  # usa avg_power già filtrato
        "parameters": group["parameters"].iloc[0],
    }

    return pd.Series(result)


# monitor_cpu: già con esclusione degli 0
cpu_non_zero = df["monitor_cpu"][df["monitor_cpu"] != 0]
cpu_min = cpu_non_zero.min() if not cpu_non_zero.empty else 0
cpu_max = cpu_non_zero.max() if not cpu_non_zero.empty else 0
cpu_avg = cpu_non_zero.mean() if not cpu_non_zero.empty else 0

print(f"Min monitor cpu: {cpu_min:.2f}")
print(f"Max monitor cpu: {cpu_max:.2f}")
print(f"Avg monitor cpu: {cpu_avg:.2f}")


# monitor_ram: anche qui tolgo gli 0
ram_non_zero = df["monitor_ram"][df["monitor_ram"] != 0]
ram_min = ram_non_zero.min() if not ram_non_zero.empty else 0
ram_max = ram_non_zero.max() if not ram_non_zero.empty else 0
ram_avg = ram_non_zero.mean() if not ram_non_zero.empty else 0

print(f"Min monitor ram: {ram_min:.2f}")
print(f"Max monitor ram: {ram_max:.2f}")
print(f"Avg monitor ram: {ram_avg:.2f}")


result_df = (
    df.groupby("pod_name")
      .apply(aggregate_pod, include_groups=False)
      .reset_index(drop=True)
)

result_df = result_df.sort_values("end_time").drop(columns=["end_time"])
result_df = result_df.round(2)

result_df.to_csv(CONTAINER_LOG, index=False)
print(f"Saved file in {CONTAINER_LOG}")


df = pd.read_csv(CONTAINER_LOG)
print(f"Total rows: {len(df)}")


def classify_pod(row):
    cpu = row['avg_cpu']
    ram = row['avg_ram']

    if cpu >= CPU_HIGH:
        return "cpu-intensive-high"
    elif ram >= RAM_HIGH:
        return "memory-intensive-high"
    elif cpu >= CPU_MED:
        return "cpu-intensive-medium"
    elif ram >= RAM_MED:
        return "memory-intensive-medium"
    else:
        return "cpu-intensive-low"


df['category'] = df.apply(classify_pod, axis=1)

df.to_csv(CATEGORIES, index=False)

print(f"Saved file in {CATEGORIES}")
print(df)
