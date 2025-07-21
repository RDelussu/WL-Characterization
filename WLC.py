import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import multiprocessing as mp
import re

def compute_wl_score(cpu_percent, mem_percent,
                     net_io_read, net_io_write,
                     block_io_read, block_io_write,
                     pids,
                     num_cores,
                     delta_t=10,
                     max_net_io=10*1024*1024,
                     max_block_io=20*1024*1024,
                     max_pids=128):

    cpu = min((cpu_percent / 100) / num_cores, 1.0)
    mem = min((mem_percent) / 100, 1.0)

    net_io = (parse_size(net_io_read) + parse_size(net_io_write)) / delta_t
    block_io = (parse_size(block_io_read) + parse_size(block_io_write)) / delta_t

    net_io_norm = min(net_io / max_net_io, 1.0)
    block_io_norm = min(block_io / max_block_io, 1.0)
    pid_norm = min(pids / max_pids, 1.0)

    score = (
        0.3 * cpu +
        0.3 * mem +
        0.15 * net_io_norm +
        0.15 * block_io_norm +
        0.1 * pid_norm
    )



    return round(score * 100, 2)

def classify_wl(score):
    # questo si può modificare a seconda delle classi di wl che vogliamo. Potrebbe essere una cosa utile per
    # l'orchestratore usando le info sui suoi nodi e lo score può decidere quale wl mandare
    if score < 20:
        return 'idle'
    elif score < 40:
        return 'light'
    elif score < 70:
        return 'medium'
    elif score < 90:
        return 'heavy'
    else:
        return 'extreme'

def detect_num_cores():
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, NotImplementedError):
        return os.cpu_count() or mp.cpu_count() or 1

def parse_size(size_str):
    size_str = size_str.strip().lower()
    match = re.match(r"([0-9.]+)\s*([kmgt]?b)?", size_str)
    if not match:
        return 0
    number, unit = match.groups()
    number = float(number)
    unit_multipliers = {
        None: 1,
        'b': 1,
        'kb': 1024,
        'mb': 1024**2,
        'gb': 1024**3,
        'tb': 1024**4
    }
    multiplier = unit_multipliers.get(unit, 1)
    return int(number * multiplier)

# ---------- PARAMETRI ----------
foler_path= '../../Downloads/'
CSV_FILE = os.path.join(foler_path,'stats_output_mem_cpu_limit.csv')
NUM_CORES = detect_num_cores()   # numero di core logici

# ---------- LETTURA CSV ----------
df = pd.read_csv(CSV_FILE, parse_dates=['Timestamp'])

# ---- prima di passare alla classificazione splitto i valori io
# df.rename(columns={'CPU %': 'cpu_percent'}, inplace=True)
# df.rename(columns={'Mem %': 'mem_percent'}, inplace=True)
df['cpu_percent'] = df['CPU %'].str.replace('%', '').str.replace('%', '').astype(float)
df['mem_percent'] = df['Mem %'].str.replace('%', '').str.replace('%', '').astype(float)
df[['net_io_read', 'net_io_write']] = df['Net I/O'].str.replace(' ', '').str.split('/', expand=True)
df[['block_io_read', 'block_io_write']] = df['Block I/O'].str.replace(' ', '').str.split('/', expand=True)

# ---------- SCORE E CLASSIFICAZIONE ----------
df['wl_score'] = df.apply(lambda row: compute_wl_score(
    row['cpu_percent'],
    row['mem_percent'],
    row['net_io_read'],
    row['net_io_write'],
    row['block_io_read'],
    row['block_io_write'],
    row['PIDs'],
    NUM_CORES
), axis=1)

df['wl_class'] = df['wl_score'].apply(classify_wl)

# ---------- STATISTICHE ----------
mean_score = round(df['wl_score'].mean(), 2)
std_score = round(df['wl_score'].std(), 2)
max_score = df['wl_score'].max()

print(f"WL Score medio: {mean_score}")
print(f"Deviazione standard: {std_score}")
print(f"Score massimo osservato: {max_score}")
print("\nDistribuzione classi workload:")
print(df['wl_class'].value_counts())

# ---------- GRAFICO ----------
plt.figure(figsize=(10, 5))
plt.plot(df['Timestamp'], df['wl_score'], marker='o', label='WL Score')
plt.title('Andamento WL Score nel tempo')
plt.xlabel('Timestamp')
plt.ylabel('Score')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

# ---------- SALVATAGGIO SU FILE ----------
OUTPUT_CSV = 'workload_scores_output.csv'
df.to_csv(OUTPUT_CSV, index=False)
print(f"\nFile salvato: {OUTPUT_CSV}")


# ---------- STATISTICHE AGGIUNTIVE ----------

# Media dei valori delle risorse principali
avg_cpu = round(df['cpu_percent'].mean(), 2)
avg_mem = round(df['mem_percent'].mean(), 2)

# Convertiamo Net/Block I/O in byte per sommare correttamente
avg_net_io = round((
    df['net_io_read'].apply(parse_size) +
    df['net_io_write'].apply(parse_size)
).mean() / 1024, 2)  # KB/s

avg_block_io = round((
    df['block_io_read'].apply(parse_size) +
    df['block_io_write'].apply(parse_size)
).mean() / 1024, 2)  # KB/s

# Calcolo della durata totale dell’osservazione
start_time = df['Timestamp'].min()
end_time = df['Timestamp'].max()
duration = end_time - start_time

print("\n--- Statistiche Risorse ---")
print(f"Media CPU%: {avg_cpu}")
print(f"Media Memoria%: {avg_mem}")
print(f"Media Net I/O totale: {avg_net_io} KB/s")
print(f"Media Block I/O totale: {avg_block_io} KB/s")

print("\n--- Durata osservazione ---")
print(f"Da: {start_time}")
print(f"A : {end_time}")
print(f"Durata totale: {duration}")
