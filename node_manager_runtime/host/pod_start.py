import csv
import subprocess
import yaml
import os
import re
import time
from datetime import datetime

YAML_FOLDER = "yamls"
INPUT_FILE = "parameters_test_category.csv"

def generate_pod_name(name):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{name}-{timestamp}"

def parse_parameters(param_string):
    params = {}
    if not param_string:
        return params
    pairs = param_string.split(";")
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"Parametro non valido: {pair}")
        key, value = pair.split("=", 1)
        params[key.strip()] = value.strip()
    return params

def load_yaml_template(yaml_name):
    file_path = os.path.join(YAML_FOLDER, yaml_name + ".yaml")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Template non trovato: {file_path}")
    with open(file_path) as f:
        return yaml.safe_load(f)

def update_env(container, parameters):
    if "env" not in container:
        container["env"] = []
    env_list = container["env"]
    env_map = {env["name"]: env for env in env_list}
    for key, value in parameters.items():
        if key in env_map:
            env_map[key]["value"] = str(value)
        else:
            env_list.append({
                "name": key,
                "value": str(value)
            })

def modify_manifest(manifest, yaml_name, parameters):
    pod_name = generate_pod_name(yaml_name)
    manifest["metadata"]["name"] = pod_name
    manifest["metadata"]["labels"]["app"] = pod_name
    container = manifest["spec"]["containers"][0]
    return manifest
    
def modify_manifest(manifest, yaml_name, parameters):
    pod_name = generate_pod_name(yaml_name)
    manifest.setdefault("metadata", {})
    manifest["metadata"]["name"] = pod_name
    manifest["metadata"].setdefault("labels", {})
    manifest["metadata"]["labels"]["app"] = pod_name
    containers = manifest.get("spec", {}).get("containers", [])
    if not containers:
        raise ValueError(f"Nessun container trovato nel YAML {yaml_name}")
    for container in containers:
        update_env(container, parameters)
    return manifest

def apply_manifest(manifest):
    yaml_manifest = yaml.dump(manifest)
    process = subprocess.Popen(["sudo", "kubectl", "apply", "-f", "-"], stdin=subprocess.PIPE, text=True)
    process.communicate(yaml_manifest)

def main():
    with open(INPUT_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yaml_name = row['yaml_name']
            param_string = row["parameters"]
            wait_time = int(row["wait"])
            print(f"\nAspetto {wait_time} secondi prima del deploy di {yaml_name}...")
            time.sleep(wait_time)
            parameters = parse_parameters(param_string)
            base_manifest = load_yaml_template(yaml_name)
            modified_manifest = modify_manifest(base_manifest, yaml_name, parameters)
            print(f"Deploy del pod {modified_manifest['metadata']['name']}")
            apply_manifest(modified_manifest)

if __name__ == "__main__":
    main()
