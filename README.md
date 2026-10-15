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
- GPU monitoring: optionally collect GPU power consumption, temperature, utilization, and memory usage using NVIDIA monitoring tools.
- Configurable sampling: specify the monitoring interval and the number of workload execution iterations.
- Experiment configuration: save execution parameters and processor information in JSON files.
- CSV data export: store timestamped resource measurements for subsequent analysis.
- Workload analysis: use the collected measurements to investigate resource behavior, execution duration, and power and energy-related characteristics where supported.

## General
Configure the Docker container and workload execution:
- container name
- Docker image
- Bash command executed inside the container
- Optional GPU support

## Resource 
Confifure Docker resource contraints:
- memory limit (--memory) set the maximum amount of RAM that the container can use
- memory reservation (--memory-reservation) sets a soft memory limit 
- CPU limit (--cpus) sets the maximum CPU capacity available to the container
- --cpuset-cpus: specify the CPU cores on which the container is allowed to execute

## Sampling
- sampling interval (in seconds)
- number of iterations

## Output
Select the directory in which experiment outputs are stored.
The Start button launches the monitoring procedure, while Stop requests termination of the current run. The log panel displays execution messages, warnings, and errors.

## Collected metrics
Depending on the selected configuration and the availabily of the underlying monitored tools, the application collects metrics including CPU utilization, memory usage, network I/O, block I/O, and process counts.

## Ouput files
Each monitoring run generates timestamped output files in the selected output directory.
- CSV file: contains timestamped measurements collected during workload execution. Its name distinguishes GPU-enabled experiments from CPU-only experiments.
- Configuration JSON: records the container image, execution command, resource constraints, sampling interval, number of iterations, and processor information.
- CPU information JSON: stores processor information obtained during the experiment.

## Requirements
- Python3
- Tkinter
- psutil
- Docker

## Licence
...

## Citation
..
