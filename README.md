# WLC - Workload Characterization
## Overview
WLC is a Python-based tool for workload characterization through Docker container monitoring. It provides a graphical user interface (GUI) to configure container execution parameters, monitor resource usage, and collect measurements during workload execution.

The collected data can subsequently be processed to analyze workload behavior, compare resource usage, and generate quantitative workload profiles.

The tool is designed to support both controlled experiments, in which workloads target specific resources, and experiments involving realistic applications.

## Main Features
- Graphical User Interface: configure and launch workload monitoring experiments without manually constructing Docker commands.
- Docker container execution: select a Docker image, specify the container name and execution command, and configure container resource constraints.
- Resource monitoring: collect container statistics, including CPU utilization, memory usage, network I/O, block I/O, and process counts.
- CPU monitoring: record current, minimum, and maximum CPU frequencies, together with processor information.
- Energy monitoring: collect CPU energy consumption and calculate average CPU power.
- GPU monitoring: optionally collect GPU power consumption, temperature, utilization, and memory usage using NVIDIA monitoring tools.
- Configurable sampling: specify the monitoring interval and the number of workload execution iterations.
- Experiment configuration: save execution parameters and processor information in JSON files.
- CSV data export: store timestamped resource measurements for subsequent analysis.
- Workload analysis: use the collected measurements to investigate resource behavior, execution duration, and power and energy-related characteristics where supported.

## General
Configure the Docker container and workload execution:
- Container name: name assigned to the Docker container
- Docker image: image used to run the workload
- Bash command: command executed inside the container
- GPU support: optionally enable GPU access and GPU monitoring

Example configuration:
Container name: test
Image: one/ad-base:v2
Bash command: source DemoAD_start.sh
Enable GPU: Disable

## Resource 
Confifure Docker resource contraints:
- memory limit (--memory): sets the maximum amount of RAM that the container can use
- memory reservation (--memory-reservation): sets a soft memory limit 
- CPU limit (--cpus): sets the maximum CPU capacity available to the container
- --cpuset-cpus: specify the CPU cores on which the container is allowed to execute

## Sampling
Configure the monitoring procedure:
- sampling interval: time between consecutive monitoring samples, in seconds.
- number of iterations: number of workload execution repetitions.

## Output
Select the directory in which experiment outputs are stored.
The **Start** button launches the monitoring procedure, while **Stop** requests termination of the current run. The log panel displays execution messages, warnings, and errors.

## Collected metrics
Depending on the selected configuration and the availabily of the underlying monitored tools, the application collects metrics including:
- CPU: utilization and frequency.
- Memory: container memory usage and utilization percentage.
- Network: data received and transmitted by the container.
- Block I/O: amount of data read from and written to block devices by the container.
- Processes: number of processes running in the container.
- CPU energy and power: energy consumption and average power, where supported by Linux.
- GPU: power, temperature, utilization, and memory usage when GPU monitoring is enabled.

## Ouput files
Each monitoring run generates timestamped output files in the selected output directory.
- CSV file: contains timestamped measurements collected during workload execution. Its name distinguishes GPU-enabled experiments from CPU-only experiments.
- Configuration JSON: records the container image, execution command, resource constraints, sampling interval, number of iterations, and processor information.
- CPU information JSON: stores processor information obtained during the experiment.

## Requirements
- Linux
- Python3
- Tkinter
- psutil
- Docker
- Jupyter Notebook

## Running WLC
WLC is launched through the Jupyter Notebook 'runDockerStats_GUI.ipynb', which initializes the GUI.
1. Open 'runDockerStats_GUI.ipynb' in Jupyter Notebook or JupyterLab.
2. Execute the notebook cell to launch the GUI.
3. Configure the experiment using General, Resources, Sampling and Output tabs.
4. Click Start to begin the monitoring.

Before launching the notebook, make sure that Python, Tkinter, psutil, and Docker are installed and properly configured.

Note: The GUI requires a graphical desktop environment. If you are using Jupyter remotely or in an environment without a graphical display, the interface may not open correctly.

## Licence
...

## Citation
..
