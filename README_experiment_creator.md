# HoMoPaD: Experiment Creator for Homopath Discovery

**Python file**: **`experiment_creator.py`**

This script coordinates the **high-level experiment workflow**, calling **`homopa.py`** (the core engine for homopath detection) under various **RAW** and **HASHED** configurations. It handles tasks like:
1. Generating or reusing sensor/network files.
2. Setting compression levels and thresholds.
3. Spawning subprocess calls to `homopa.py`.
4. Organizing outputs into experiment folders.

---

## Overview

1. **Launches and Monitors**  
   - Runs **`homopa.py`** (raw or hashed mode) with a set of parameters (threshold, path length, etc.).  
   - Monitors the script’s real-time output, capturing any final integer it prints.

2. **Manages Data and Files**  
   - **Raw data** is used first; if no homopath is found, it skips the next steps.  
   - **Hashed data**: Uses MinHash to approximate the network objects, applying a ±10% tolerance for the desired compression ratios.  
   - Copies or removes files to maintain a clean directory, optionally storing them in new experiment folders.

3. **Repeat Experiment**  
   - If `repeat_experiment=1`, it can re-run previous experiments by loading older sensor and network files from a named folder (e.g., `"Experiment_..."`), replicating or adjusting seeds/thresholds.

4. **File-by-File Processing**  
   - **`run_script(...)`** spawns the `homopa.py` process in a subprocess, capturing the last integer output.  
   - **`hash_data(...)`** transforms sensor data into a MinHash signature-based file.  
   - **`copy_file(...)`**, **`keep_specific_files_and_folders(...)`** manage local file I/O.  
   - Additional functions combine or parse logs, remove quotes, generate final CSV comparisons, etc.

5. **Final Archiving**  
   - After each complete run (RAW + multiple compress levels), logs, sensor data, or other outputs are **moved into a new folder** named with the experiment parameters (threshold, object count, timestamp, etc.), ensuring each run is self-contained.

---

## Main Sections & Key Functions

### 1. **`run_script(...)`**
**Purpose**:  
- Spawns `homopa.py` with arguments specifying raw/hashing, compression, threshold, etc.  
- Captures its real-time stdout, printing lines and trying to parse the **last integer** as a return value.

### 2. **`hash_data(...)`**
**Purpose**:  
- Reads a sensor file (e.g. `4_sensors.txt`), sorts lines, and applies **MinHash** with a given number of permutations.  
- Writes a new hashed sensor file (`4_sensors_HASHED.txt`) for subsequent runs.

### 3. **`copy_file(...)`** & **`keep_specific_files_and_folders(...)`**
**Purpose**:  
- Utility routines to handle copying specific files (e.g. from an older experiment folder) and removing unneeded files or directories.  
- `keep_specific_files_and_folders(...)` helps maintain a clean workspace, removing everything not in the keep list.

### 4. **Data Parsing & Merging**
- **`read_top_leader_file(...)`**: Reads CSV data from a top leader log.  
- **`read_compare_file(...)`**: Reads CSV data from a “compare” log (pairs discovered, etc.).  
- **`process_pairs(...)`**: Interprets bracketed pairs, extracting numeric IDs.  
- **`write_output_file(...)`** & **`create_testing_file_for_pairs(...)`**: Combine and output final pair-related data, removing quotes if needed.

### 5. **`extract_Infos_from_Experiment_folders(...)`** & **`copy_files(...)`**
**Purpose**:  
- If repeating an experiment (`repeat_experiment=1`), parse folder names like `Experiment_<edges>_<objs>_<threshold>_<path>_<map>_<timestamp>` to retrieve numeric info (seed, motions, sensors).  
- Copy relevant motion/sensor files into the current directory to replicate the older scenario.

### 6. **`main_function()`**  
**Central** driver:
- Defines arrays of thresholds, compression levels, path lengths, etc.  
- Loops over these configurations, first running **RAW** data with `run_script(...)`.  
- If homopaths are found, runs **HASHED** data with multiple compress ratios, applying **±10%** tolerance for real compression.  
- Archives logs after each threshold in a newly created “Experiment_...” folder.  
- Optionally loads older folder data if repeating (`repeat_experiment`).

---

## Usage

Below is a simplified example of calling **`experiment_creator.py`** directly:
python experiment_creator.py
( No additional command-line arguments are typically required because main_function() is invoked automatically at the end of the file. Parameters such as my_threshold_levels, my_numo_objs_levels, or repeat_experiment can be customized inside the script. )




## Output Files & Logs

- **`RESULTS.txt`, `ResultsOfExperiments.txt`**: Summaries or logs of raw/hashing runs.  
- **`Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_*.txt`**: Compare logs for pairs or path data.  
- **`Current_Experiment_Top_Leader_*`**: If the top leader logs are also kept in the same directory, they may be archived.  
- **`Experiment_<...>`** Folders: Created for each final run, storing relevant logs, sensors, and motion files.

## Dependencies

- [**OSMnx**](https://osmnx.readthedocs.io/)
- [**Folium**](https://python-visualization.github.io/folium/)
- [**NetworkX**](https://networkx.org/)
- [**NumPy**](https://numpy.org/)
- Standard libraries: `os`, `random`, `datetime`, `math`, `re`, etc.

Make sure to install or verify the needed packages (e.g., `pip install osmnx folium numpy networkx`) before running.

## Potential Extensions

- **Advanced Scheduling**: Automate multiple runs with different seeds or thresholds over HPC clusters.  
- **Adaptive Partitioning**: Instead of a fixed `depth`, dynamically partition or skip if certain conditions are met.  
- **Accuracy Metrics**: Further compare raw vs hashed discovered homopaths by writing additional aggregator scripts.

## Conclusion

The **`experiment_creator.py`** script is your **top-level experiment manager**. It calls **`homopa.py`** under multiple parameter scenarios, organizes the results into new folders, and optionally replays older experiments by copying files. For deeper homopath detection logic, see **`homopa.py`**. Feel free to tailor the ranges for thresholds, compression levels, or object counts to your dataset. 

**Thank you for using HoMoPaD’s Experiment Creator!** Open an issue or pull request for improvements or questions.







