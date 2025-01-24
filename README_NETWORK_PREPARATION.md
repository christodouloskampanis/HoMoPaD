# Task 1: Creating the Network and Motions

This task focuses on generating a road network from OpenStreetMap data for a specified location, finding connected edges, simulating motions of objects on the network, and finally producing sensor files containing object-edge relationships.

---

## Overview

1. **Create the Network**: 
   - Given a geographical bounding box, retrieve road data from OpenStreetMap.
   - Assign weights to edges based on proximity to the center.
   - Save all edges (with unique IDs, node coordinates, and assigned weights) to a file.

2. **Find Connected Edges**:
   - Based on the generated network file, determine which edges lead into which other edges.
   - Save this connectivity information to a separate file.

3. **Create Motions**:
   - Simulate moving objects traveling along connected edges.
   - Each object is randomly assigned a path of edges.
   - Save the object-to-edge paths to a file.

4. **Write Sensor Data**:
   - Process the paths file and create edge-to-object mappings.
   - Write these mappings to both a timestamped file (for archival) and a main sensor file.

---

## Main Functions

### 1. `create_network(File_1_combined_nodes_edges_toWrite, prefix_file_Name_Picture, choice_place)`
- **Purpose**  
  Retrieves a road network from OpenStreetMap for a chosen location. Assigns weights to edges according to their proximity to the network’s center.
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

## Helper Functions

1. **`get_coordinates(place_name)`**  
   - Uses **OSMnx**’s geocoder to retrieve latitude/longitude for a location. (Currently not heavily used in these scripts.)

2. **`rotate_graph(graph, angle)`**  
   - Rotates the graph’s node coordinates by a given angle in degrees. Useful for aligning the network.

3. **`visualize_network(graph, north, south, east, west, place_name)`**  
   - Creates and saves an interactive Folium map with the bounding box, center marker, and the OSMnx graph overlay.
   - Saved as `network_visualization.html`.

---

## General Workflow

1. **Create the Network (`create_network`)**  
   - Specify a location (`choice_place`) to define bounding box coordinates.  
   - Generate the network and save its edges.

2. **Find Connected Edges (`find_connected_edges`)**  
   - Use the saved edge file to determine connectivity and produce a connectivity file.

3. **Create Motions (`create_motions`)**  
   - Load the graph and edge details, simulate objects traversing the edges, and write motions to file.

4. **Generate Sensor Data (`write_data_to_sensors_file`)**  
   - Convert object-based motions into edge-based lists of objects.  
   - Save results to a main sensor file and a timestamped archival file.

---

## Dependencies

- [**OSMnx**](https://osmnx.readthedocs.io/)
- [**Folium**](https://python-visualization.github.io/folium/)
- [**NetworkX**](https://networkx.org/)
- [**NumPy**](https://numpy.org/)
- Standard libraries: `os`, `random`, `datetime`, `math`, etc.

Make sure to install OSMnx, Folium, and other dependencies before running these scripts. For example:


 - pip install osmnx folium numpy networkx




## General Workflow
 - The script will create:
    - A file with all edges and their weights.
    - A file listing connected edges.
    - A motions file mapping objects to edges.
    - A sensors file mapping edges to objects.
    - An HTML map visualization of the network.


## Possible Improvements
 - Dynamic Input/Output Handling
   - Instead of hardcoding file paths and bounding box coordinates, consider using a config file or command-line arguments.
 - Parallelization
   - If the network is large, parallelizing the edge-connectivity or motion-creation steps might improve performance.
 - Analytics
   - You could add additional metrics—such as total distance traveled by each object, or average edge usage—to gain insights into network usage.


## Thank you for using Task 1!
Feel free to customize the scripts to suit your project’s needs and share your improvements. If you have ideas or suggestions, please open an issue or submit a pull request.
