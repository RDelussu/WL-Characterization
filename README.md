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
```text
Container name: first_test
Image: one/ad-base:v2
Bash command: source DemoAD_start.sh
Enable GPU: Disabled
```
In this example, the tool runs the DemoAD_start.sh workload inside a container .., without enabling the GPU.

These values are provided as an example and must be adapted to the selected image and workload. The command must be supported by the shell available inside the container, and any required scripts must be present in the image or mounted into it.

If GPU is required, enable the GPU option and specify the device, for example:
```text
Enable GPU: Enabled
--gpus: device=0
```
Make sure that the NVIDIA drivers and `nvidia-smi` are correctly configured.

## Resource 
Confifure Docker resource contraints:
- memory limit (--memory): sets the maximum amount of RAM that the container can use
- memory reservation (--memory-reservation): sets a soft memory limit 
- CPU limit (--cpus): sets the maximum CPU capacity available to the container
- --cpuset-cpus: specify the CPU cores on which the container is allowed to execute

Example configuration:
```text
Memory limit: 1g
Memory reservation: 999m
CPU limit: 1
--cpuset-cpus: 2
```

This configuration limits the container to one CPU equivalent and up to 1GB of memory, with CPU execution restricted to logical CPU 2. The memory reservation is a soft limit rather tha an additional memory allocation.

The selected CPU IDs must exist on the host. Resource contraints should be choisen accordingly to the workload and the objective of the experiment.

## Sampling
Configure the monitoring procedure:
- sampling interval: time between consecutive monitoring samples, in seconds.
- number of iterations: number of times the container is run during the experiment.

Example configuration
```text
Interval (seconds): 0.5
Iterations: 100
```

With this configuration, the tool runs the container up to 100 times, collecting resource-usage measurements at approximately 0.5-second intervals while each container execution is active. The number of samples collected for each execution depends on the workload duration and the monitoring execution time.

## Output
Select the directory in which experiment results will be saved. The tool creates the output directory if it does not exist.

Example confifuration
```text
Output directory: ./results
```

The **Start** button launches the monitoring procedure, while **Stop** requests termination of the current run. The log panel displays execution messages, warnings, and errors.

## Example experiment
The following configuration illustrates a complete CPU-only experiment:

| Parameter | Value |
| --- | --- |
| Container name | test |
| Image | one/ad-base:v2 |
| Bash command | source DemoAD_start.sh |
| Enable GPU | Disabled |
| Memory limit | 1g |
| Memory reservation | 999m |
| CPU limit | 1 |
| --cpuset-cpus | 2 |
| Interval (seconds) | 0.5 |
| Iterations | 100 |
| Output directory | ./results |


To reproduce the experiment, enter these values in the corresponding GUI tabs and click Start. Once the run has finished, inspect the generated CSV file to analyze the collected measurements and the JSON configuration file to verify the settings used.

For a GPU-enabled experiment, enable GPU monitoring and configure the GPU device appropriately. The resulting CSV file will include the additional GPU measurements when they are available.

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
Each run generates timestamped output files.
Example directory struture
```text
results/
|-- stats_output_20261023_103000_cpu_only.csv
|-- stats_output_20261023_103000_config.json
cpu_info.json
```
The filenames above are illustrative. 
- `stats_output_20261023_103000_cpu_only.csv`: contains the measurements collected during a CPU-only experiment.
- `stats_output_<timestamp>_with_gpu.csv`: contains the measurements collected when GPU monitoring is enabled.
- `stats_output_20261023_103000_config.json`:  records the experiment configuration and processor information.
- 'cpu_info.json': contains additional processor information. This file may be overwritten by subsequent runs.

The CSV files contain timestamped measurements associated with the container and its execution iterations. See the Collected Metrics section for a description of the recorded values.
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
