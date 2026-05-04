import pandas as pd

# Percorso del file CSV
file_csv = "results_test666/device_log.csv"  # cambia con il nome del tuo file

# Legge il CSV
df = pd.read_csv(file_csv)

# Calcola la potenza media per ciascun valore di pods_running
media_potenza = df.groupby("pods_running")["power"].mean()

# Estrae i valori specifici
potenza_media_0 = media_potenza.get(0, None)
potenza_media_1 = media_potenza.get(1, None)

# Stampa i risultati
print(f"Potenza media con pods_running = 0: {potenza_media_0:.2f} W")
print(f"Potenza media con pods_running = 1: {potenza_media_1:.2f} W")
