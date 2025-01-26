# HoMoPaD: Overview of Experiment and Scripts

HoMoPaD (Homopath Discovery and Partitioning) is a system designed to:
1. Create and partition a **road network** (from OSM data),
2. Simulate **object motions** and produce sensor data,
3. Coordinate **Regional Leaders** that detect **local homopaths**,
4. Orchestrate a **Top Leader** that collects and combines these regional homopaths (potentially forming **spanning homopaths**).

Below is an overview of the **three main Python scripts** in this repository and how they interconnect:

---

## 1. `experiment_creator.py`: Top-Level Experiment Manager

**Location**: `experiment_creator.py`  
**Purpose**: Orchestrates **high-level experiment workflows** by:
- Generating or reusing sensor/network files,
- Setting **compression levels** (for hashed data) and **thresholds** (intersection),
- Spawning subprocess calls to `homopa.py` (both **RAW** and **HASHED** modes),
- Organizing results into experiment folders.

### Key Points

- **RAW & Hashed Flows**: Runs a **RAW** pass first. If homopaths exist, continues with **hashed** passes for multiple compression ratios (±10% tolerance).  
- **Repeat Experiments**: If `repeat_experiment=1`, can re-run an older experiment folder (e.g. `Experiment_...`) to replicate or tweak seeds/thresholds.  
- **Archiving**: After finishing for a given threshold/param set, logs and sensor data are **moved** into a new experiment folder named with the experiment parameters.

### Main Components

1. **`run_script(...)`**  
   - Spawns `homopa.py` as a subprocess with the chosen parameters.
   - Captures real-time output, returning the last integer printed by `homopa.py`.

2. **`hash_data(...)`**  
   - Reads a raw sensor file, applies **MinHash** to produce `4_sensors_HASHED.txt`.

3. **File Management**  
   - **`copy_file(...)`** and **`keep_specific_files_and_folders(...)`** to copy or remove files.

4. **Data Parsing** (Pairs, Leader Output)  
   - **`read_top_leader_file(...)`**, **`read_compare_file(...)`** parse CSV logs.
   - **`process_pairs(...)`, `write_output_file(...)`,** and **`create_testing_file_for_pairs(...)`** finalize pair-based data.

5. **`extract_Infos_from_Experiment_folders(...)`** & **`copy_files(...)`**  
   - For repeated experiments: parse folder names, copy older sensor or motion files.

6. **`main_function()`**  
   - Central driver that loops over thresholds, object counts, etc., performing RAW then hashed runs of `homopa.py`.

### Usage

`python experiment_creator.py`

No extra CLI args are needed; `main_function()` is invoked at script end. You can edit arrays like `my_threshold_levels` in the code.

### Output Files & Logs...

- **`RESULTS.txt`, `ResultsOfExperiments.txt`**: Summaries or logs of raw/hashing runs.  
- **`Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_*.txt`**: Compare logs for pairs or path data.  
- **`Current_Experiment_Top_Leader_*`**: If the top leader logs are also kept in the same directory, they may be archived.  
- **`Experiment_<...>`**: For each final run, a new folder is created with logs, sensors, etc.

### Dependencies...

- **Standard Libraries**:  
  - `subprocess`, `time`, `csv`, `os`, `shutil`, `datetime`, `re`, `random`
- **Third-Party / Data Science**:
  - [datasketch](https://github.com/ekzhu/datasketch) (provides MinHash functionality)

Install third-party libraries via `pip install datasketch`.

### Potential Extensions

- **Advanced Scheduling**: Automate runs with varied seeds or thresholds on HPC.  
- **Adaptive Partitioning**: Dynamically partition or skip.  
- **Accuracy Metrics**: Compare raw vs hashed homopaths with aggregator scripts.

### Conclusion

`experiment_creator.py` is the top-level manager for multi-parameter runs, archiving results in `Experiment_<...>` folders. It calls `homopa.py`, organizes final logs, and can repeat older experiments. For deeper detection logic, see **`homopa.py`**.

---

## 2. `homopa.py`: Homopath Discovery & Leader Coordination

**Location**: `homopa.py`  
**Purpose**: Coordinates a **Top Leader** and multiple **Regional Leaders**:
1. Top Leader aggregates homopath data or object sets from each region.
2. Regional Leaders discover local homopaths from sensor data.

### Key Points

- **Top Leader** waits for regions, then fetches data (modes 1–5) or shuts them down (`"[-1]"`).  
- **Regional Leader** loads `map<regionID>.txt`, runs `process_region(...)`, sets up a socket server to respond.

### Usage

`python homopa.py [raw_or_hashed] [seed] [current_compress] [num_permutations] ...`

Typically invoked by `experiment_creator.py`.

### Output Files & Logs...

- **`ResultsOfExperiments.txt`**: Summaries of homopath discoveries, times, etc.  
- **`Current_Experiment_Info.txt`**: Region-by-region logs.  
- **`Current_Experiment_Compare_RAW_HASh_*.txt`**: Compare logs.  
- **`Current_Experiment_Top_Leader_*`**: Top Leader details.  
- **`output.txt`**: Final integer result for the caller.

### Dependencies...

- **Standard Libraries**:  
  - `os`, `time`, `re`, `socket`, `json`, `threading`, `sys`, `shutil`, `queue`
- **Third-Party / Data Science**:
  - [pandas](https://pandas.pydata.org/)
  - [networkx](https://networkx.org/)
  - [matplotlib](https://matplotlib.org/)
  - [numpy](https://numpy.org/)

Install via `pip install networkx matplotlib numpy pandas`.

### Conclusion

`homopa.py` runs the top/regional leaders, performing local raw/hashed homopath detection and optionally building spanning homopaths across region boundaries.

---

## 3. `preparation.py`: Network Creation, Motion Simulation, and Partitioning

**Location**: `preparation.py`  
**Purpose**: Prepares the **road network** and **sensor data**:
1. Creates an OSM-based network, finds connected edges.
2. Simulates object motions and inverts them into sensor data.
3. Partitions the map if `depth>0`, labeling sub-maps (e.g., `map11.txt`).

### Main Steps

- **`create_network(...)`**: Uses OSMnx to fetch road data, writes edges.
- **`find_connected_edges(...)`**: Identifies sequential edges by node IDs.
- **`create_motions(...)` / `write_data_to_sensors_file(...)`**: Simulates object paths → sensor data (`4_sensors.txt`).
- **Partitioning**: `recursively_map_partition(...)` splits edges by x-coord, `delete_maps_except_longest()` optionally prunes partitions.
- **Regional/Top Leader Connections**: `create_edgeConnections_and_sensorInfo_for_each_Region(...)`, `create_RegionConnections_for_Top_Leader(...)`.

### Dependencies...

- **Standard Libraries**:  
  - `matplotlib`, `sys`, `os`, `shutil`, `json`, `re`, `random`
- **Third-Party / Data Science**:
  - [OSMnx](https://osmnx.readthedocs.io/)
  - [Folium](https://python-visualization.github.io/folium/)
  - [networkx](https://networkx.org/)
  - [numpy](https://numpy.org/)

Install with `pip install osmnx folium numpy networkx`.

### Conclusion

`preparation.py` sets up the entire map environment, from raw OSM data to final sub-map edges. Typically invoked before or within `homopa.py`.

---

## Putting It All Together

A typical flow is:
1. **`preparation.py`**: Build the map, generate motions (`4_sensors.txt`), partition into sub-maps (`map11.txt`, etc.).
2. **`experiment_creator.py`**:
   - Possibly loads older experiments (if repeating),
   - Runs `homopa.py` in RAW mode, checks homopaths,
   - Runs `homopa.py` in hashed mode for multiple compress ratios,
   - Archives logs in an **`Experiment_<...>`** folder.
3. **`homopa.py`**:
   - Spawns a **Top Leader** thread & multiple **Regional Leaders**,
   - Each region does local detection, top leader aggregates final results,
   - Prints an integer result for the experiment.

**Result**: You get an `Experiment_<...>` folder containing logs, sensor data, adjacency, and final top-leader outputs.

**Thank you for exploring HoMoPaD** – if you have feedback or wish to contribute, please open an issue or a pull request!
