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

```bash
python experiment_creator.py
