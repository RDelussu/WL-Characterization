import pandas as pd
import numpy as np
import re
import json
import os
import multiprocessing as mp

def detect_num_cores():
    """detect the number of cpu cores available to the process """
    # todo: Move this detection to the data acquisition script (more appropriate)
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, NotImplementedError):
        return os.cpu_count() or mp.cpu_count() or 1

def parse_size(size_str):
    """ convert a human-readable size string into bytes"""
    if pd.isna(size_str):
        return 0
    s = str(size_str).strip().lower()
    # supported format "123", "123b", "1.2kb", "1 MB", "1M", "1 KiB" ecc.
    m = re.match(r"([0-9.]+)\s*([kmgt]i?b|[kmgt]|b)?", s)
    if not m:
        return 0
    n, u = m.groups()
    n = float(n)
    if not u:
        return int(n)
    u = u.replace("ib","b")  # kiB -> kb
    mul = {
        'b':1,
        'k':1024,
        'kb':1024,
        'm':1024**2,
        'mb':1024**2,
        'g':1024**3,
        'gb':1024**3,
        't':1024**4,
        'tb':1024**4
    }.get(u, 1)
    return int(n * mul)

def assign_wl_type(df, num_cores, max_net_io=10*1024*1024, max_block_io=100*1024*1024):
    """
    assign a workload type to each row based on resource usage
    df: DataFrame con medie per iteration
    num_cores: numero di core
    max_net_io: banda massima Net I/O in MB/s
    max_block_io: soglia Block I/O MB/s
    """
    wl_types = []

    for _, row in df.iterrows():
        cpu_norm = row['cpu_percent'] / num_cores
        cpu_intensive = cpu_norm >= 0.8  # soglia 80%
        mem_intensive = row['mem_percent'] >= 80
        io_intensive = row['block_io_MBps'] >= max_block_io
        net_intensive = row['net_io_MBps'] >= 0.8 * (max_net_io / (1024*1024))  # converto se max_net_io era in byte
        gpu_mem_intensive = row['gpu_mem_percent'] >= 80

        if cpu_intensive:
            wl_types.append("cpu-intensive")
        elif mem_intensive:
            wl_types.append("memory-intensive")
        elif io_intensive:
            wl_types.append("io-intensive")
        elif net_intensive:
            wl_types.append("network-intensive")
        elif gpu_mem_intensive:
            wl_types.append("gpu-memory intensive")
        else:
            wl_types.append("other")

    df['wl_type'] = wl_types
    return df

# ---------- CONFIG ----------
#folder_path= '../../Downloads/'
#CSV_FILE = os.path.join(folder_path,'stats_output_20250912_112249_cpu_only.csv')

folder_path= 'Logger/'
CSV_FILE = os.path.join(folder_path,'stats_output_20250918_160318_with_gpu.csv')

# sampling interval in seconds
ASSUME_DELTA_T = 0.1  # set to None to estimate it automatically from the timestamp column
NUM_CORES = 1 # detect_num_cores()
# ---------- LOAD DATA ----------
df = pd.read_csv(CSV_FILE, parse_dates=['Timestamp'])
print(f"Total rows of csvv: {len(df)}")

# ---------- DEBUG / VALIDATION ----------
print("dtype iteration:", df['Iteration'].dtype)
print("unique iterations (n):", df['Iteration'].nunique())
print("groupby ngroups:", df.groupby('Iteration').ngroups)

# ---------- NORMALIZE ITERATION VLUES ----------
# convert iteration values to numeric integers.
# Invalid or missing values are handled below
df['Iteration'] = pd.to_numeric(df['Iteration'], errors='coerce').astype(pd.Int64Dtype())

# remove rows with missing iteration values, if any.
if df['Iteration'].isna().any():
    df = df[df['Iteration'].notna()].copy()
    df['Iteration'] = df['Iteration'].astype(int)

# extract container name
container_name = df['Container'].iloc[0] # todo: verify how the container name is recorded, as coome values may be unexpected

# ---- RENAME AND PREPARE COLUMNS ---- #
df['cpu_percent'] = df['CPU %'].str.replace('%', '').str.replace('%', '').astype(float)
df['mem_percent'] = df['Mem %'].str.replace('%', '').str.replace('%', '').astype(float)
df[['net_io_read', 'net_io_write']] = df['Net I/O'].str.replace(' ', '').str.split('/', expand=True)
df[['block_io_read', 'block_io_write']] = df['Block I/O'].str.replace(' ', '').str.split('/', expand=True)
df[['gpu_mem_used', 'gpu_mem_total']] = df['GPU Memory Usage'].str.replace(' ', '').str.split('/', expand=True)


# ---------- ESTIMATE SAMPLING INTERVAL (OPTIONAL) ----------
if ASSUME_DELTA_T is None:
    # estimate the mefian time interval between consecutive samples.
    # grouping by container avoids mixing timestamps from different containers
    dt_seconds = []
    for _, g in df.groupby('container'):
        t = g['Timestamp'].sort_values().dropna()
        if len(t) > 1:
            diffs = t.diff().dt.total_seconds().dropna()
            if len(diffs):
                dt_seconds.append(diffs.median())
    if len(dt_seconds):
        delta_t = int(np.median(dt_seconds))
    else:
        delta_t = 10  # fallback
else:
    delta_t = ASSUME_DELTA_T

if delta_t <= 0:
    delta_t = 10
print("Sampling interval used (seconds):", delta_t)

# ---------- PARSE I/O e GPU (vettoriale) ----------
# columns: net_io_read, net_io_write, block_io_read, block_io_write
for col in ['net_io_read','net_io_write','block_io_read','block_io_write']:
    if col in df.columns:
        df[col + '_bytes'] = df[col].apply(parse_size)
    else:
        df[col + '_bytes'] = 0

# MB/s
df['net_io_MBps'] = (df['net_io_read_bytes'] + df['net_io_write_bytes']) / (delta_t * 1024 * 1024)
df['block_io_MBps'] = (df['block_io_read_bytes'] + df['block_io_write_bytes']) / (delta_t * 1024 * 1024)

# GPU memory percent (se presente)
if 'GPU Memory Usage' in df.columns:
    def try_split_gpu(x):
        try:
            used, tot = str(x).split('/')
            return parse_size(used), parse_size(tot)
        except Exception:
            return 0, 1
    gpu_parsed = df['GPU Memory Usage'].apply(lambda x: try_split_gpu(x))
    df['gpu_mem_used'] = [t[0] for t in gpu_parsed]
    df['gpu_mem_total'] = [t[1] for t in gpu_parsed]
    df['gpu_mem_percent'] = np.where(df['gpu_mem_total'] > 0, df['gpu_mem_used'] / df['gpu_mem_total'] * 100, 0)
else:
    # set GPU memory utilization to zero when GPU is unavailable
    df['gpu_mem_percent'] = 0.0

# ensure CPU and mem utilization valies are numeric
df['cpu_percent'] = pd.to_numeric(df['cpu_percent'], errors='coerce')
df['mem_percent'] = pd.to_numeric(df['mem_percent'], errors='coerce')

# ---------- AGGREGATE METRICS BY ITERATION ----------
# Create one row per iteration by averaging the resource usage measurements.
agg_funcs = {
    'cpu_percent': 'mean',
    'mem_percent': 'mean',
    'net_io_MBps': 'mean',
    'block_io_MBps': 'mean',
    'gpu_mem_percent': 'mean'
}
#
if 'wl_type' in df.columns:
    #
    grouped_pair = df.groupby(by=['Iteration'])
    agg_df = grouped_pair.agg(agg_funcs).reset_index()
    #
    mode_wl = grouped_pair['wl_type'].agg(lambda x: x.value_counts().idxmax()).reset_index(name='wl_type')
    agg_df = agg_df.merge(mode_wl, on=['Iteration'])
else:
    agg_df = df.groupby(by=['Iteration'], as_index=False).agg(agg_funcs)

print("Rows after aggregation:", len(agg_df))
print("Unique iterations after aggregation:", agg_df['Iteration'].nunique())

# ----------  ----------
agg_per_iteration = agg_df.groupby('Iteration', as_index=False).agg({
    'cpu_percent':'mean',
    'mem_percent':'mean',
    'net_io_MBps':'mean',
    'block_io_MBps':'mean',
    'gpu_mem_percent':'mean'   # average
})

agg_per_iteration = assign_wl_type(agg_per_iteration, NUM_CORES)

#
if 'wl_type' in agg_per_iteration.columns:
    dominant_wl = agg_per_iteration.groupby('Iteration')['wl_type'].agg(lambda x: x.value_counts().idxmax()).to_dict()
else:
    dominant_wl = {}

# ---------- Output JSON: dizionario per iteration ----------
# output = {}
# for _, r in agg_per_iteration.iterrows():
#     it = int(r['Iteration'])
#     output[it] = {
#         'avg_cpu_percent': round(float(r['cpu_percent']),2) if not pd.isna(r['cpu_percent']) else None,
#         'avg_mem_percent': round(float(r['mem_percent']),2) if not pd.isna(r['mem_percent']) else None,
#         'avg_net_io_MBps': round(float(r['net_io_MBps']),4) if not pd.isna(r['net_io_MBps']) else None,
#         'avg_block_io_MBps': round(float(r['block_io_MBps']),4) if not pd.isna(r['block_io_MBps']) else None,
#         'gpu_mem_intensive': bool(r['gpu_mem_percent'] >= 80),
#         'workload_type': dominant_wl.get(it, None)
#     }
#
# print(json.dumps(output, indent=2))

import json

#
selected_iteration = agg_per_iteration['Iteration'].max()  #

#
row = agg_per_iteration[agg_per_iteration['Iteration'] == selected_iteration].iloc[0]

# build the final json
output = {
    'iteration': int(row['Iteration']),
    'container': container_name,
    'avg_cpu_percent': round(float(row['cpu_percent']), 2) if not pd.isna(row['cpu_percent']) else None,
    'avg_mem_percent': round(float(row['mem_percent']), 2) if not pd.isna(row['mem_percent']) else None,
    'avg_net_io_MBps': round(float(row['net_io_MBps']), 4) if not pd.isna(row['net_io_MBps']) else None,
    'avg_block_io_MBps': round(float(row['block_io_MBps']), 4) if not pd.isna(row['block_io_MBps']) else None,
    'gpu_mem_intensive': round(float(row['gpu_mem_percent']), 4) if not pd.isna(row['gpu_mem_percent']) else None,
    'workload_type': row['wl_type'] if 'wl_type' in row else None
}

# print JSON
print(json.dumps(output, indent=2))

# ---- SAVE JSON TO FILE -----
# todo: uncomment this section when the output format is finalized
# with open("selected_iteration.json", "w") as f:
#     json.dump(output, f, indent=2)
