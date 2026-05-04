import pandas as pd
import numpy as np
import joblib
import os
import csv
from rapidfuzz import process, fuzz
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

DATA_PATH = "results_test_pc/categories.csv"

governor_map = {"powersave": 0, "userspace": 1, "performance": 2}
category_map = {"cpu-intensive-high": 0, "memory-intensive-high": 1, "cpu-intensive-medium": 2, "memory-intensive-medium": 3, "cpu-intensive-low": 4, "block-intensive":5, "net-intensive":6}
DEVICE_MAP = {"kria": "kria", "pc": "christian-ms-7c56"}
MODEL_PATHS = {"kria": "energy_model_kria.pkl", "pc": "energy_model_pc.pkl"}
BASE_FEATURES = ["category", "pods_running", "cpu_usage_start", "avg_freq", "governor", "device", "os"]

def parse_parameters(param_str):
    if not isinstance(param_str, str):
        return {}
    out = {}
    for item in param_str.split(";"):
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k == "duration":
            continue
        try:
            out[k] = float(v)
        except:
            pass
    return out

def clean_pod_name(pod_name):
    if not isinstance(pod_name, str):
        return pod_name
    return pod_name.rsplit("-", 1)[0]
    
def get_category(pod_name, parameters):
    candidates = []
    category_map = {}
    try:
        with open(DATA_PATH, newline='') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                key = row["pod_name"].strip()
                candidates.append(key)
                category_map[key] = row["category"]
    except Exception as e:
        print(f"[ERROR] CSV non leggibile: {e}")
        return "cpu-intensive-low"
    if pod_name in category_map:
        print(f"[Category] Match esatto: {pod_name}")
        return category_map[pod_name]
    match, score, _ = process.extractOne(
        pod_name,
        candidates,
        scorer=fuzz.ratio
    )
    if score < 60:
        print(f"[WARN] Match debole pod_name: {match} (score={score})")
    else:
        print(f"[Category] Match pod_name: {match} (score={score})")
    best_category = category_map[match]
    if parameters and score < 70:
        match_p, score_p, _ = process.extractOne(
            parameters,
            candidates,
            scorer=fuzz.partial_ratio
        )
        if score_p > score:
            print(f"[Category] Match migliore da parameters: {match_p} (score={score_p})")
            best_category = category_map[match_p]
    return best_category    
    
def train_model(device):
    df = pd.read_csv(DATA_PATH)
    df["device"] = df["device"].astype(str).str.strip().str.lower()
    real_device = DEVICE_MAP[device].lower()
    print("Available devices:", df["device"].unique())
    df = df[df["device"] == real_device]
    if df.empty:
        raise ValueError(f"No data found for device '{device}'")
    df["pod_name"] = df["pod_name"].apply(clean_pod_name)
    df["category"] = df["category"].map(category_map)
    df["governor"] = df["governor"].map(governor_map)
    param_df = df["parameters"].apply(parse_parameters).apply(pd.Series)
    df = pd.concat([df, param_df], axis=1)
    df = pd.get_dummies(df, columns=["os"])
    base_features = [
        "category",
        "pods_running",
        "cpu_usage_start",
        "avg_freq",
        "governor"
    ]
    os_features = [c for c in df.columns if c.startswith("os_")]
    param_features = list(param_df.columns)
    features = base_features + os_features + param_features
    X = df[features]
    y = df["energy_used"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=42)
    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)
    model.feature_columns = features
    model.device = device
    y_pred = model.predict(X_test)
    print(df["governor"].value_counts())
    print(f"\n===== MODEL {device.upper()} =====")
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    y_range = y_test.max() - y_test.min()    
    mae_norm = mae / y_range
    rmse_norm = rmse / y_range
    print("MAE:", mae)
    print("RMSE:", rmse)
    print("NMAE:", mae_norm)
    print("NRMSE:", rmse_norm)
    print("R²:", r2_score(y_test, y_pred))
    abs_errors = np.abs(y_test - y_pred)
    perc_errors = (abs_errors / y_test) * 100
    print("Min error %:", np.min(perc_errors))
    print("Max error %:", np.max(perc_errors))
    print("Avg error %:", np.mean(perc_errors))
    test_results = X_test.copy()
    test_results["Real_Value"] = y_test.values
    test_results["Predicted_Value"] = y_pred
    test_results["Absolute_Error"] = np.abs(test_results["Real_Value"] - test_results["Predicted_Value"])
    test_results["Percentage_Error"] = (test_results["Absolute_Error"] / test_results["Real_Value"]) * 100
    pd.set_option("display.max_columns", None)
    print("\n===== TEST SET =====")
    print(test_results.sort_values(by="Absolute_Error", ascending=False).head(10))
    joblib.dump(model, MODEL_PATHS[device])
    print("Model saved as", MODEL_PATHS[device])
    importances = model.feature_importances_
    feature_importance_df = pd.DataFrame({"feature": features, "importance": importances}).sort_values(by="importance", ascending=False)
    print("\n===== FEATURE IMPORTANCE =====")
    print(feature_importance_df)
    candidate_freqs = None
    candidate_governors = ["powersave", "performance"]
    return model, X_test, y_test 

def load_model(device):
    path = MODEL_PATHS[device]
    if not os.path.exists(path):
        print(f"Model for {device} not found, training...")
        return train_model(device)
    print(f"Loading model for {device}")
    return joblib.load(path)

def prepare_candidates(rows, model):
    df = pd.DataFrame(rows)
    param_df = df["parameters"].apply(parse_parameters).apply(pd.Series)
    df = pd.concat([df.drop(columns=["parameters"]), param_df], axis=1)
    df = pd.get_dummies(df)
    df = df.reindex(columns=model.feature_columns, fill_value=0)
    return df

def choose_best_frequency(model, category, n_pod_running, cpu_usage_start, os, parameters, candidate_freqs=None, candidate_governors=None):
    if candidate_governors is None:
        candidate_governors = ["powersave", "performance"]
    if candidate_freqs is None:
        candidate_freqs = []
    print(candidate_freqs)
    print(candidate_governors)     
    rows = []
    combos = []
    userspace_freqs = []
    if len(candidate_freqs) > 2:
        userspace_freqs = sorted(candidate_freqs)[1:-1]
    for g in candidate_governors:
        if g == "userspace":
            freqs = userspace_freqs
        else:
            freqs = [None]
        for f in freqs:
            rows.append({
                "category": category_map[category],
                "pods_running": n_pod_running,
                "cpu_usage_start": cpu_usage_start,
                "avg_freq": f,
                "governor": governor_map[g],
                "os": os,
                "parameters": parameters
            })
            combos.append((f, g))
    X_candidates = prepare_candidates(rows, model)
    energies = model.predict(X_candidates)
    best_index = np.argmin(energies)
    min_energy = energies[best_index]
    perf_index = None
    for i, (f, g) in enumerate(combos):
        if g == "performance":
            perf_index = i
            break
    if perf_index is not None:
        perf_energy = energies[perf_index]
        guadagno = perf_energy - min_energy
        percentuale = (guadagno / perf_energy) * 100 if perf_energy != 0 else 0
        print(f"Performance governor energy: {perf_energy:.2f}")
        print(f"Best choice energy ({combos[best_index][1]}): {min_energy:.2f}")
        print(f"Estimated gain: {guadagno:.2f} ({percentuale:.2f}%)")
        print(energies)
        print(parameters)
    return combos[best_index][0], combos[best_index][1], energies

def predict_best_governor(model, pod_name, n_pod_running, cpu_usage_start, device, os, parameters, candidate_freqs, candidate_governors):
    pod_name = clean_pod_name(pod_name)
    category = get_category(pod_name, parameters)
    best_freq, governor, energies = choose_best_frequency(model, category, n_pod_running, cpu_usage_start, os, parameters, candidate_freqs, candidate_governors)
    print("Energies:", energies)
    print("Governor:", governor)
    print("Freq:", best_freq)
    return governor, best_freq

def benchmark_test_set(model, X_test, y_test, candidate_freqs, candidate_governors):
    if candidate_freqs is None:
        candidate_freqs = []
    if candidate_governors is None:
        candidate_governors = ["powersave", "performance"]
    total_perf_energy = 0
    total_min_energy = 0
    count = 0
    print("\n===== BENCHMARK RISPARMIO ENERGETICO (X_TEST BASED) =====")
    for i in range(len(X_test)):
        riga_base = X_test.iloc[i].copy()
        candidates = []
        combos = []
        for g_name in candidate_governors:
            g_val = governor_map[g_name]
            if g_name == "userspace" and len(candidate_freqs) > 2:
                u_freqs = sorted(candidate_freqs)[1:-1]
                for f in u_freqs:
                    cand = riga_base.copy()
                    cand["governor"] = g_val
                    cand["avg_freq"] = f
                    candidates.append(cand)
                    combos.append((f, g_name))
            else:
                cand = riga_base.copy()
                cand["governor"] = g_val
                cand["avg_freq"] = np.nan # o il valore None usato nel training
                candidates.append(cand)
                combos.append((None, g_name))
        X_cand = pd.DataFrame(candidates)
        preds = model.predict(X_cand)
        best_idx = np.argmin(preds)
        min_e = preds[best_idx]
        perf_e = None
        for idx, (f, g) in enumerate(combos):
            if g == "performance":
                perf_e = preds[idx]
                break
        if perf_e is not None:
            total_perf_energy += perf_e
            total_min_energy += min_e
            count += 1
    if count > 0:
        risparmio_totale = ((total_perf_energy - total_min_energy) / total_perf_energy) * 100
        print(f"{count} values considered")
        print(f"Total energy for performance: {total_perf_energy:.2f}")
        print(f"Total energy for model:  {total_min_energy:.2f}")
        print(f"Estimated gain: {risparmio_totale:.2f}%")

if __name__ == "__main__":
    '''model, X_test, y_test = train_model("kria")
    freqs = [333333, 444444, 666666, 1333333]  
    govs = ["powersave", "userspace", "performance"]'''
    model, X_test, y_test = train_model("pc")    
    freqs = None
    govs = ["powersave", "performance"]
    benchmark_test_set(model, X_test, y_test, freqs, govs)
    choose_best_frequency(model, "cpu-intensive-low", 0.0, 19.07, "Ubuntu 22.04.5 LTS", "exec_time=4000;idle_time=0", freqs, govs)   
