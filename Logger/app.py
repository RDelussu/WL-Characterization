# api_server.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
import subprocess
import json
import time

app = FastAPI()

class Config(BaseModel):
    container: str
    image: str
    bashFile: str
    gpu: bool
    memory: str
    memoryReservation: str
    cpus: str
    cpusetCpus: str
    gpus: str
    interval: float
    iterations: int

@app.post("/run")
async def run_docker_stats(config: Config):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    config_file = f"stats_output_{timestamp}_config.json"

    with open(config_file, "w") as f:
        json.dump(config.dict(), f, indent=2)

    # Esegui il file Python passando il path al JSON
    subprocess.Popen(["python3", "your_script.py", config_file])
    return {"status": "started", "config_file": config_file}
