# HoMoPaD: Homopath Discovery and Top/Regional Leader Coordination

**Python file**: **`homopa.py`**

This script coordinates the **Top Leader** and **Regional Leaders** to discover and analyze **Homopaths** across a subdivided road network. It is typically called by **`experiment_creator.py`** (via subprocess), or you may run it manually with the required command-line arguments.

---

## Overview

1. **Top Leader Thread**  
   - Waits for all regional leaders (threads) to signal readiness.  
   - Collects homopath data or object information from each region.  
   - Attempts to discover **spanning homopaths** that cross multiple regions.  
   - Logs and saves results (e.g., cost metrics, edges used, discovered paths).

2. **Regional Leader Threads** (one per region)  
   - Each loads its own sub-map (e.g., **`map10.txt`**, **`map20.txt`**).  
   - Discovers local homopaths or edges meeting a threshold using the **`process_region`** workflow.  
   - Sets up a **TCP socket server** to respond to Top Leader’s queries (homopath requests, object sets, etc.).  
   - Signals “ready” if homopaths are found, or “no homopaths” otherwise.

3. **Data Flow**  
   - Sensor data and edge connections are loaded from region-specific files (**`Regional_4_sensors<regionID>.txt`**, etc.).  
   - A global lock + condition variables ensure we manage concurrency safely.  

4. **Results**  
   - The final output from Top Leader is an integer (e.g., how many regions discovered homopaths).  
   - Multiple log files track the homopath structure, cost, and other statistics.

---

## Main Sections & Key Functions

### 1. **Globals and Setup**

In `homopa.py`, there are several global variables and concurrency primitives:

- **`all_regions_ready`**, **`all_regions_ready_condition`** (for synchronization)  
- **`regions_ready_counter`**, **`regions_without_Homopa_counter`**, **`all_regions_counter`** (to track which regions have homopaths)  
- **`function_lock`** (a threading lock)  
- **`thread_complete()`**, **`thread_init()`** (for counting completed threads)  
- **`clear_lists()`** (resets global counters before each experiment)

### 2. **`start_Top_leader(...)`**  
**Purpose**: The Top Leader:
1. **Waits** for all regions (either ready or no-homopath) using a condition variable.  
2. **Requests** and **collects** homopath data (mode=3) or unique objects (mode=4) from each region.  
3. Aggregates a union of raw object sets if `raw_or_hashed == 0`.  
4. If multiple regions have homopaths, attempts to build **spanning homopaths** across regions.  
5. Logs final data:  
   - Discovered spanning paths  
   - Transmission cost metrics  
   - Edge usage  
6. **Signals** each region to shut down by sending `[-1]`.

### 3. **`send_request_to_regional_leader(...)`**  
**Purpose**: A helper function to contact a region’s TCP server.  
- Sends a **JSON** request specifying:
  - Path/edge request (1 or 2)  
  - Homopath dictionary (3)  
  - Number of objects (4)  
  - Total sensor integers (5)  
  - Or **`[-1]`** for shutdown  
- Receives and decodes the response (dictionary, string, or integer).

### 4. **`start_regional_leader(...)`**  
Each **Regional Leader**:
1. Loads its region’s map from `map<regionID>.txt`.  
2. Calls **`process_region(...)`** to parse sensor data and local edges, discovering homopaths.  
3. Opens a **socket** to listen for Top Leader’s requests.  
4. If homopaths exist, marks itself as “ready” in shared counters; otherwise “no homopath.”  
5. Upon `[-1]`, closes socket and ends.

### 5. **`process_region(...)`**  
- Determines which files to load (`Regional_4_sensors<regionID>.txt` vs. hashed).  
- Calls **`HOMOPA(...)`** for local homopath discovery.  
- Logs the results in text files for debugging or analysis.  
- Returns:
  - The local homopath dictionary, unique objects, cost metrics, etc.

### 6. **`HOMOPA(...)`**  
**Core** function for reading edges & sensors:
1. Loads **edge connections** from `Regional_2_edgeconnections<regionID>.txt`.  
2. Prepares sensor data with **`prepare_data_from_file(...)`**.  
3. If hashed (`raw_or_hashed == 1`), uses **Cohen** to estimate total objects (`_Find_Cardinality_Cohen`).  
4. Calls **`calculate_obj_id_intersection(...)`** to produce the local homopath dictionary.  
5. Returns all relevant data (unique objects, number of edges, discovered paths, etc.).

### 7. **`calculate_obj_id_intersection(...)`**  
**Recursive** procedure:
- Builds a matrix (rows = current paths/edges, columns = possible next edges).  
- **Intersection** threshold check:
  - Raw data => `(|intersection| / total_obj_count) >= threshold`.  
  - Hashed data => `(|intersection| / permutations) >= threshold`.  
- For **n=1**, single edges. For **n >= 2**, tries to extend existing paths with new edges.  
- Continues until no new paths or recursion **limit** is reached.

### 8. **Minhash & Cohen’s Method**  
**_Find_Cardinality_Cohen(...)** extracts minhash signatures from sensor lines, then **`_Cohen(...)`** applies the formula:
Maps to:
- `raw_or_hashed=0`
- `seed=42`
- `current_compress=1`
- `num_of_permutations=50`
- `num_objs=100`
- `length_of_path=10`
- `threshold=0.2`
- `depth=1`
- `help_for_jaccard=0`
- `factor_forDBscan=1.0`
- `choice_place=123`
- `run_once=0`
- `repeat_experiment=0`
- `limitN=5`
- `folderOfRepeatExperiment="folderRepeatExp"`

The script will log progress, spawn threads, and produce a final integer result in **`output.txt`** so that **`experiment_creator.py`** can track this experiment's outcome.

---

## Output Files & Logs

- **`ResultsOfExperiments.txt`**: Summaries of homopath discoveries, times, etc.  
- **`Current_Experiment_Info.txt`**: Detailed region-by-region or top-level logs.  
- **`Current_Experiment_Compare_RAW_HASh_*.txt`**: Logs for raw vs hashed debugging.  
- **`Current_Experiment_Top_Leader_*`**: Top Leader specifics (e.g., spanning homopath details, transmission costs).  
- **`output.txt`**: The final integer result, for the calling script (`experiment_creator.py`).

---

## Dependencies

- **`numpy`**, **`pandas`**, **`networkx`**, **`matplotlib`**  
- Standard libraries: `os`, `threading`, `json`, `socket`, etc.

Ensure these are installed before running, e.g.:
```bash
pip install numpy pandas networkx matplotlib




## Potential Extensions
Scalability: For very large networks, consider asynchronous concurrency or distributed architectures.
Intersection Strategy: Enhance the hashing approach or explore alternative cardinality estimation methods.
Visualization: Provide more debug plots of multi-edge homopaths or color-coded spanning paths.
Conclusion
homopa.py orchestrates a Top Leader and multiple Regional Leaders for local path discovery. It supports both raw and hashed data with minhash cardinality checks, building homopaths recursively and aggregating them for cross-region “spanning paths.” The main function is typically invoked by experiment_creator.py with a set of command-line arguments, generating detailed logs and a final integer result.

Thank you for using HoMoPaD! Please open an issue or a pull request for improvements or questions.
