# Creating the Network, Motions, and Map Partitions

**python** **file** : **preparation.py**

This task set focuses on:
1. Generating a road network from OpenStreetMap data for a specified location.
2. Finding connected edges.
3. Simulating motions of objects on the network.
4. Producing sensor files with object-edge relationships.
5. Partitioning the resulting network map into smaller sub-maps , creating the “Regional Leader” (RL) overview. 
6. Creating region-based edge connections for a “Top Leader” (TL) overview.


---

## Overview

1. **Create the Network**  
   - Retrieve road data from OpenStreetMap for a given bounding box (location).
   - Assign weights to edges based on proximity to the center.
   - Save edges with unique IDs and coordinates to a file.

2. **Find Connected Edges**  
   - Determine which edges lead directly into which others.
   - Generate an edge-connection file.

3. **Create Motions**  
   - Simulate objects traveling across the network, each with a path of connected edges.
   - Write these object-to-edge paths to a file.

4. **Write Sensor Data**  
   - Convert object-based paths into edge-based lists of objects passing through each edge.
   - Write these lists to both a timestamped file and a main sensor file.

5. **Map Partitioning**  
   - Recursively split the network map into sub-maps (e.g., left/right) based on X-coordinates.
   - Optionally remove unneeded map files, keeping only the most relevant partitions.

---

## Main Functions

### 1. `create_network(File_1_combined_nodes_edges_toWrite, prefix_file_Name_Picture, choice_place)`
- **Purpose**  
  Retrieves a road network from OpenStreetMap for a chosen location. Assigns weights to edges according to proximity to the network’s center.
- **Key Steps**  
  1. Select bounding box coordinates based on `choice_place`.  
  2. Use **OSMnx** to download the road network within these coordinates.  
  3. Optionally rotate the graph for alignment.  
  4. Assign weights to each edge based on distance from the center.  
  5. Write edge information (ID, nodes, coordinates, weight) to a file.
- **Outputs**  
  - Returns the processed graph and bounding box details.  
  - Creates an HTML visualization of the network (`network_visualization.html`).  
  - Saves edges with assigned weights to `File_1_combined_nodes_edges_toWrite`.

### 2. `find_connected_edges(File_1_combined_nodes_edges_toRead, File_2_edge_connections_toWrite)`
- **Purpose**  
  Identifies edges that directly connect in a sequence (i.e., the end node of one edge is the start node of another).
- **Key Steps**  
  1. Read the network file (`File_1_combined_nodes_edges_toRead`).  
  2. For each edge, map its start and end nodes.  
  3. Determine any edge whose start node matches the end node of another edge.  
  4. Write these connectivity relationships to `File_2_edge_connections_toWrite`.
- **Output**  
  - Returns the number of edges processed.  
  - Produces a file listing, for each edge, the edges that can be traversed next.

### 3. `create_motions(graph, num_edges, num_objs, File_1_combined_nodes_edges_toRead, File_3_Motions_file_ToWrite)`
- **Purpose**  
  Simulates objects moving through the network, assigning random paths of connected edges to each object.
- **Key Steps**  
  1. Read edge information to identify edge IDs.  
  2. Determine “central edges” and “split lines” to influence object direction.  
  3. For each object:
     - Start from a central or random edge.  
     - Traverse a sequence of connected edges in a particular direction (left or right).  
     - Keep track of the edges visited by that object.
  4. Write the resulting paths (object ID → list of edge IDs) to `File_3_Motions_file_ToWrite`.
- **Output**  
  - A file containing each object’s traversed edges.

### 4. `write_data_to_sensors_file(File_4_DFSMottions_toRead, File_4_sensors_toWrite, num_objs, total_edges, north, south, east, west, place_name)`
- **Purpose**  
  Reads object-to-edge mappings from the motions file and inverts them to create edge-to-object sensor data files.
- **Key Steps**  
  1. Parse the file of object IDs and edges.  
  2. For each edge, accumulate the list of objects passing through it.  
  3. Generate a timestamped file for archival and a main sensor file (`File_4_sensors_toWrite`).
- **Outputs**  
  - Two files, one named based on the network details and a second one containing edge-object data.

---

## Map Partitioning

### 5. `main_partitioning_map_(File_1_combined_nodes_edges_toRead, prefix_file_Name_map, prefix_file_Name_Regional, prefix_file_Name_Picture, depth)`
- **Purpose**  
  Partitions a network map into sub-maps recursively and manages files by keeping only the largest partition.
- **Key Steps**  
  1. Determine initial recursion level (`i`) based on `depth`.  
  2. Call `recursively_map_partition` to do the actual partitioning.  
  3. Remove unneeded map files, keeping only the partition with the longest numerical suffix.

### 6. `recursively_map_partition(File_1_combined_nodes_edges_toRead, prefix_file_Name_map, depth, i, total_sum_of_lines, numberOfEdgesinInitialFile=None)`
- **Purpose**  
  Recursively splits a network map by X-coordinates (left/right) until a specified `depth` is reached.
- **Key Steps**  
  1. Read network edges from file.  
  2. Calculate midpoint (`split_x`), and separate edges into left/right subsets.  
  3. Write subsets to new files.  
  4. Recursively process each subset until `depth` is exceeded.

### 7. `partition_data(data, split_x, depth)`
- **Purpose**  
  Given a list of edges, partition them into left and right subsets based on a specified `split_x`.
- **Key Steps**  
  1. If `depth` = 0, all edges go into the left partition.  
  2. Otherwise, compare the edge coordinates (`x1`, `x2`) with `split_x` and assign to left or right.  
  3. Handle edges that cross the midpoint by comparing distances.

### 8. `delete_maps_except_longest()`
- **Purpose**  
  Deletes all map files in the current directory except those with the largest numerical suffix and any explicitly specified files to keep.
- **Key Steps**  
  1. Collect all files starting with `"map"`.  
  2. Determine the suffix length (excluding `"map"` and `".txt"`).  
  3. Keep only files with the longest suffix (plus optional files).  
  4. Delete the rest.

---

## Additional Region Connections (Top Leader)

### 9. `create_edgeConnections_and_sensorInfo_for_each_Region(File_2_edgeconnections, File_4_sensors_FILE, prefix_file_Name_map)`
- **Purpose**  
  Creates edge connections and sensor information files for each region based on map files in the current directory.
- **Key Steps**  
  1. Iterate over all `.txt` files that start with `prefix_file_Name_map`.  
  2. For each file, extract a numerical suffix.  
  3. Generate and filter regional edge connections and sensor info files by calling `create_regional_edgeconnections`.  
  4. Store the numerical suffixes (region IDs) in a list.
- **Output**  
  - Returns a list of region IDs (numerical suffixes) that were processed.

### 10. `create_regional_edgeconnections(map_filename, File_for_RegionalEdgeConnenctios_or_RegionalSensors_toRead)`
- **Purpose**  
  Creates a filtered regional edge-connection or sensor file by matching edge IDs from a map file against a master file.
- **Key Steps**  
  1. Read edge IDs from `map_filename`.  
  2. Read lines from the master connections/sensor file.  
  3. Generate a new filename in the format `Regional_<base_filename><map_number>.txt`.  
  4. Write only those lines whose first value (edge ID) is present in the map file’s edge list.
- **Output**  
  - Creates a new file containing only the relevant edges for the specified region.

### 11. `create_RegionConnections_for_Top_Leader(file_prefix="Regional_2_edgeconnections", file_extension=".txt")`
- **Purpose**  
  Identifies and records connections between regions by analyzing the newly created regional edge-connection files.
- **Key Steps**  
  1. Collect all regional files matching `file_prefix` and `file_extension`.  
  2. For each file, record the region ID (extracted from the filename).  
  3. Compare edge IDs across different regional files to see if they connect.  
  4. Build a nested dictionary showing how regions connect to one another.  
  5. Write these inter-region connections to `7_ConnectionsBetween_Regions.txt`.
- **Outputs**  
  - Writes an output file listing connections between regions.  
  - Returns a dictionary mapping each region to its connected regions/edges.

---

## General

1. **Create the Network (`create_network`)**  
   - Specify a location (`choice_place`) and generate the network, saving edges and coordinates.

2. **Find Connected Edges (`find_connected_edges`)**  
   - Use the saved edge file to build a connectivity file.

3. **Create Motions (`create_motions`)**  
   - Load the graph, simulate object motions, and write out their traveled paths.

4. **Generate Sensor Data (`write_data_to_sensors_file`)**  
   - Invert object-based paths to produce edge-based lists of objects.

5. **Partition the Map (`main_partitioning_map_` and Friends)**  
   - Split the edge file into multiple sub-maps.
   - Optionally remove extraneous sub-map files, keeping only the most significant partition.

6. **Regional Edge Connections (Top Leader)**  
   - Create region-specific edge and sensor data files.
   - Combine multiple region files to identify and record inter-region connections.

---

## Dependencies

- [**OSMnx**](https://osmnx.readthedocs.io/)
- [**Folium**](https://python-visualization.github.io/folium/)
- [**NetworkX**](https://networkx.org/)
- [**NumPy**](https://numpy.org/)
- Standard libraries: `os`, `random`, `datetime`, `math`, `re`, etc.

Make sure to install OSMnx, Folium, NetworkX, NumPy, and any other dependencies before running these scripts. For example:

pip install osmnx folium numpy networkx




## Workflow

 - Create the Network and the Motions
    - Generates network edges.
    - Finds connections.
    - Simulates motions.
    - Produces sensor data files.
  
 - Partition the Network
    - Splits the network edges into sub-maps.
    - Deletes unnecessary map files, retaining only the most relevant partition.
  
 - Generate Regional Connections
    - For each sub-map, create filtered edge and sensor files.
    - Identify how different sub-maps (regions) connect.


## Possible Improvements
 - Dynamic Input/Output Handling
   - Instead of hardcoding file paths and bounding box coordinates, consider using a config file or command-line arguments.
 - Parallelization
   - If the network is large, parallelizing the edge-connectivity or motion-creation steps might improve performance.
 - Analytics
   - You could add additional metrics—such as total distance traveled by each object, or average edge usage—to gain insights into network usage.


## Thank you for reading preparation.py!
Feel free to customize the scripts to suit your project’s needs and share your improvements. If you have ideas or suggestions, please open an issue or submit a pull request.
