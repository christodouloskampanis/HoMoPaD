# HoMoPaD: Homopath Discovery and Top/Regional Leader Coordination

**Python file**: **`homopa.py`**

This script coordinates the **Top Leader** and **Regional Leaders** to discover and analyze **Homopaths** across a subdivided road network. It is typically called by **`experiment_creator.py`** (via subprocess), or you may run it manually with the required command-line arguments.

---



## Overview

1. **Top Leader Thread**  
   - Waits for all regional leaders (threads) to signal readiness (or no-homopath).  
   - Collects homopath data or object information from each region (including various request modes).  
   - Attempts to discover **spanning homopaths** that cross multiple regions.  
   - Logs and saves results (e.g., cost metrics, edges used, discovered paths).

2. **Regional Leader Threads** (one per region)  
   - Each loads its own sub-map (e.g., **`map10.txt`**, **`map21.txt`**, **`map122.txt`**, etc.) according to the partition depth and region ID scheme:
     - If `depth == 0`, then **2^0 = 1** part, so only **`map10.txt`**.  
     - If `depth == 1`, then **2^1 = 2** parts, i.e. **`map11.txt`** and **`map21.txt`** (IDs = 1 or 2; appended with depth=1).  
     - If `depth == 2`, then **2^2 = 4** parts. First split → IDs 1,2; then each splits again → 11,12 for part 1, and 21,22 for part 2. So files might be **`map112.txt`**, **`map122.txt`**, **`map212.txt`**, **`map222.txt`**, and so on.  
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
2. **Requests** and **collects** homopath data or unique objects from each region:
   - **Mode 1**: Request a *path* (lists object IDs for a path).  
   - **Mode 2**: Request an *edge* (lists object IDs for a single edge).  
   - **Mode 3**: Request the *full homopath dictionary* from a region.  
   - **Mode 4**: Request the *unique object set* for a region.  
   - **Mode 5**: Request the total sensor integer count from a region.  
   - **"[-1]"**: Instructs the region to shut down.  
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
  - **Raw data** => \((|\text{intersection}| / \text{total\_obj\_count}) \geq \text{threshold}\).  
  - **Hashed data** => \((|\text{intersection}| / \text{permutations}) \geq \text{threshold}\).  
- **For** `n=1`: searching for **homoedges**. Here, each sensor uses an “extra counter” (Counter Cardinality MinHash — CCM approach), sending the minhash signature **plus** an integer for the real number of objects. Then we compare \(\frac{\text{intersection}}{\text{Cohen's global estimate}}\).  
- **For** `n >= 2`: tries to extend existing paths with new edges (so building multi-edge homopaths).  
- Continues until no new paths or a recursion limit is reached.

### 8. **Minhash & Cohen’s Method**  
**`_Find_Cardinality_Cohen(...)`** extracts minhash signatures from sensor lines, then **`_Cohen(...)`** applies the formula:
- cardinality = num_perm / ((sum_of_min_values / _max_hash)) - 1
- This estimates the union cardinality of objects in hashed data.

### 9. **`main(...)`** (Script Entry Point)  
- **Parses** command-line arguments.  
- If `threshold <= 0.01`, returns a default result (1). Otherwise:
  - Possibly builds a global network, motions, sensor data.  
  - Partitions the map if `depth > 0`.  
  - Spawns **Top Leader** and **Regional Leaders** as threads.  
  - Waits for them to complete.  
  - Writes **`output.txt`** with the final integer result (so `experiment_creator.py` can read it).

---


## Usage

**Example**:
python homopa.py 0 42 1 50 100 10 0.2 1 0 1.0 123 0 0 5 "folderRepeatExp"

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

- **Standard Libraries**:  
  - `os`, `time`, `re`, `socket`, `json`, `threading`, `sys`, `shutil`, `queue`

- **Third-Party / Data Science**:
  - [**datasketch**](https://github.com/ekzhu/datasketch) *(provides MinHash functionality)*
  - [**pandas**](https://pandas.pydata.org/) *(for DataFrame manipulation)*
  - [**networkx**](https://networkx.org/) *(for graph operations)*
  - [**matplotlib**](https://matplotlib.org/) *(for plotting, with Agg backend)*
  - [**numpy**](https://numpy.org/) *(array handling, numeric computations)*

Before running, ensure all third-party libraries are installed (e.g., `pip install datasketch pandas networkx matplotlib numpy`) and that the listed standard libraries are available in your Python environment.



## Potential Extensions
- Scalability: For very large networks, consider asynchronous concurrency or distributed architectures.
- Intersection Strategy: Enhance the hashing approach or explore alternative cardinality estimation methods.
- Visualization: Provide more debug plots of multi-edge homopaths or color-coded spanning paths.


## Conclusion
homopa.py orchestrates a Top Leader and multiple Regional Leaders for local path discovery. It supports both raw and hashed data with minhash cardinality checks, building homopaths recursively and aggregating them for cross-region “spanning paths.” The main function is typically invoked by experiment_creator.py with a set of command-line arguments, generating detailed logs and a final integer result.

Thank you for using HoMoPaD! Please open an issue or a pull request for improvements or questions.

