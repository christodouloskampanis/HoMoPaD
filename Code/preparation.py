
import os , random  , shutil , matplotlib , json ,re ,sys
matplotlib.use('Agg')  # Set the backend to Agg before importing pyplot
import osmnx as ox
from datetime import datetime
import numpy as np
import folium




# 0





#############################################################
#--------------------------------------------------- #
#          T  A  S  K    1   :     Create the Network and the Motions

                    

# 1.1 
def create_network(File_1_combined_nodes_edges_toWrite, prefix_file_Name_Picture, choice_place):
    """
    Creates a network graph based on the selected location, assigns weights to edges based on their proximity to the center,
    and saves the edge information to a file.

    Parameters:
    - File_1_combined_nodes_edges_toWrite: Path to the file where the edges will be saved.
    - prefix_file_Name_Picture: Prefix for naming any output visualization files.
    - choice_place: Integer indicating the location choice, which determines the geographical area for the graph.
    
    Returns:
    - graph_copy: The processed graph with weights assigned to edges.
    - north, south, east, west: Bounding box coordinates for the selected location.
    - place_name: Name of the selected location.
    """

    # Define bounding box coordinates and location name based on `choice_place`

    if choice_place==1: 
        place_name = "Outer Sunset, San Francisco, CA, USA"
        north, south, east, west = 37.77, 37.745, -122.48, -122.51 #1306
    elif choice_place == 2:
        place_name = "Outer Sunset, San Francisco, CA, USA"
        north, south, east, west = 37.75, 37.765, -122.485, -122.50
    elif choice_place == 3:
        place_name = "Outer Sunset, San Francisco, CA, USA"
        north, south, east, west = 37.74, 37.77, -122.48, -122.50
    elif choice_place == 4:
        place_name = "Piraeus, Greece"
        north, south, east, west = 37.9701, 37.9573, 23.68, 23.66


    elif choice_place ==5:
        place_name = "Chania_GR5"
        north, south, east, west = 35.531, 35.501, 24.05, 24.00 # 3727
    elif choice_place ==6:
        place_name = "Chania_GR6"
        north, south, east, west = 35.531, 35.505, 24.04, 24.01 #1761
    elif choice_place ==7:
        place_name = "Chania_GR7"
        north, south, east, west = 35.531, 35.51, 24.033, 24.015 #641
    elif choice_place ==8:
        place_name = "Chania_GR8"
        north, south, east, west = 35.532, 35.505, 24.04, 24.032 #499
    elif choice_place ==9:
        place_name = "Chania_GR9"
        north, south, east, west = 35.521, 35.505, 24.05, 24.045 #4120
    elif choice_place ==10:
        place_name = "Chania_GR10"
        north, south, east, west = 35.531, 35.501, 24.08, 24.00 # 5019 
    elif choice_place ==11:
        place_name = "Chania_GR11"
        north, south, east, west = 35.531, 35.500, 24.12, 24.00 # 6007 

    elif choice_place == 12:
        place_name = "Outer Sunset, San Francisco, CA, USA"
        north, south, east, west = 37.75, 37.76, -122.49, -122.50

    elif choice_place == 13:
        place_name = "Munich1"
        north , south , east , west = 48.105 , 48.065,  11.490  , 11.450

    elif choice_place == 14:
        place_name = "Thessaloniki, Greece"
        north, south, east, west = 40.6655, 40.66, 22.99, 22.9475

    elif choice_place == 15:
        place_name = "Munich2"
        north , south , east , west = 48.105 , 48.090,  11.480  , 11.465

    elif choice_place == 16:
        place_name = "Munich3"
        north, south, east, west = 48.1395, 48.136, 11.593, 11.575
    elif choice_place == 17:
        place_name = "Munich4"
        north , south , east , west = 48.185 , 48.177,  11.534  , 11.519
    elif choice_place ==18:
        place_name = "Chania_small"
        north, south, east, west = 35.510, 35.505, 24.039, 24.032 #499

    elif choice_place == 19:
        place_name = "Outer Sunset, San Francisco, CA, USA"
        north, south, east, west = 37.75, 37.76, -122.493, -122.503
       
    else:
        place_name = "Casablanca, Morocco"
        north, south, east, west = 33.5613, 33.5533, -7.5997, -7.6137

    # Get the road network graph from OpenStreetMap within the bounding box
    graph_pure = ox.graph_from_bbox(north, south, east, west, network_type='drive', simplify=True)

    # Create a copy of the graph for further processing
    graph_cop = graph_pure.copy()

    # Optionally rotate the graph (e.g., for alignment purposes)
    graph = rotate_graph(graph_cop, -5)

    # Visualize the network and save it as an HTML file
    visualize_network(graph, north, south, east, west, place_name)

    # Create another copy of the graph for processing
    graph_copy = graph.copy()

    # Initialize variables to track the bounding box of the graph
    min_x = float('inf')
    max_x = float('-inf')
    min_y = float('inf')
    max_y = float('-inf')

    # Determine the bounding box of the graph (min and max coordinates)
    for node, data in graph_copy.nodes(data=True):
        x, y = data['x'], data['y']
        min_x = min(min_x, x)
        max_x = max(max_x, x)
        min_y = min(min_y, y)
        max_y = max(max_y, y)

    # Calculate split lines (center of the graph) for assigning weights
    splitx = (max_x + min_x) / 2
    splity = (max_y + min_y) / 2

    # Define percentages for different weight sections
    percentage_section1 = 60
    percentage_section2 = 40
    percentage_section3 = 20

    # Assign weights to edges based on their proximity to the center
    for u, v, data in graph_copy.edges(data=True):
        # Calculate the midpoint of the edge
        mid_x = (graph_copy.nodes[u]['x'] + graph_copy.nodes[v]['x']) / 2
        mid_y = (graph_copy.nodes[u]['y'] + graph_copy.nodes[v]['y']) / 2

        # Calculate distances of the midpoint from the center as a percentage of the range
        distance_to_center_x = abs(mid_x - splitx) / (max_x - min_x)
        distance_to_center_y = abs(mid_y - splity) / (max_y - min_y)

        # Assign weights based on distance to the center
        if distance_to_center_x <= percentage_section3 / 100 and distance_to_center_y <= percentage_section3 / 100:
            data['weighttt'] = 3  # Closest to the center
        elif distance_to_center_x <= percentage_section2 / 100 and distance_to_center_y <= percentage_section2 / 100:
            data['weighttt'] = 2  # Medium proximity
        elif distance_to_center_x <= percentage_section1 / 100 and distance_to_center_y <= percentage_section1 / 100:
            data['weighttt'] = 1  # Farthest from the center
        else:
            data['weighttt'] = 0  # Default weight for edges outside defined sections


    # Avoid assigning specific IDs to edges due to technical reasons (e.g., avoiding collisions in a multithreaded process)
    # If `new_edge_id` matches any of the problematic IDs (1,112, 212, 222, 122, 1), increment it further. This is why the first edge id
    # has the value 2 
    new_edge_id = 2

    # Write edge data to the specified file
    with open(File_1_combined_nodes_edges_toWrite, 'w') as file:
        for u, v, data in graph_copy.edges(data=True):
            # Increment edge ID for each edge
            new_edge_id += 1

            # Avoid assigning reserved edge IDs
            if new_edge_id in {1, 112, 122, 212, 222}:
                new_edge_id += 1

            # Scale the x and y coordinates of the start and end nodes by a large factor
            # This is likely done to convert floating-point coordinates to integers (for precision or compatibility reasons)
            factor = 100000000  # Scaling factor
            start_x, start_y = int(graph_copy.nodes[u]['x'] * factor), int(graph_copy.nodes[u]['y'] * factor)
            end_x, end_y = int(graph_copy.nodes[v]['x'] * factor), int(graph_copy.nodes[v]['y'] * factor)

            # Write edge information in the format: `new_edge_id,start_node,end_node,start_x,start_y,end_x,end_y,weight`
            file.write(f"{new_edge_id},{u},{v},{start_x},{start_y},{end_x},{end_y},{data['weighttt']}\n")

    # Return the processed graph, bounding box, and place name
    return graph_copy, north, south, east, west, place_name


# 1.2
def find_connected_edges(File_1_combined_nodes_edges_toRead, File_2_edge_connections_toWrite):
    """
    Finds and records the connected edges in a graph based on the input file.

    Parameters:
    - File_1_combined_nodes_edges_toRead: Input file containing edge details (edge_id, start_node, end_node, etc.).
    - File_2_edge_connections_toWrite: Output file where the connected edges for each edge will be written.

    Returns:
    - The number of main edges processed.
    """

    # Dictionaries to store start and end nodes for each edge
    endNodeOfEdge = {}  # Maps edge_id to its end node
    startNodeoFEdge = {}  # Maps edge_id to its start node
    edges = set()  # Set to store all edge IDs

    # Step 1: Read the input file and populate the dictionaries
    with open(File_1_combined_nodes_edges_toRead, 'r') as infile:
        for line in infile:
            # Parse each line of the file
            parts = line.strip().split(',')
            edge_id = int(parts[0])  # Extract edge ID
            edges.add(edge_id)  # Add edge ID to the set
            node_start = int(parts[1])  # Extract start node
            node_end = int(parts[2])  # Extract end node
            startNodeoFEdge[edge_id] = node_start  # Map edge ID to its start node
            endNodeOfEdge[edge_id] = node_end  # Map edge ID to its end node
            # Weight (not used in this function) is extracted here for future use
            weight = int(parts[7])

    # Step 2: Initialize a dictionary to store connected edges for each main edge
    mainEdge = {edge: set() for edge in edges}  # Each edge starts with an empty set of connections

    # Step 3: Find connected edges by comparing node connections
    with open(File_1_combined_nodes_edges_toRead, 'r') as infile:
        # Skip the header line (if present)
        next(infile)
        for line in infile:
            parts = line.strip().split(',')
            current_edge_id = int(parts[0])  # Extract the current edge ID
            current_node_start = int(parts[1])  # Extract the start node of the current edge
            current_node_end = int(parts[2])  # Extract the end node of the current edge

            # Compare each main edge to the current edge to find connections
            for mainedge in edges:
                # If the start node of the current edge matches the end node of the main edge,
                # add the current edge as a connected edge to the main edge
                if current_node_start == endNodeOfEdge[mainedge]:
                    mainEdge[mainedge].add(current_edge_id)

    # Step 4: Write the results to the output file
    with open(File_2_edge_connections_toWrite, 'w') as outfile:
        for edge_id, connected_edge_ids in mainEdge.items():
            # Convert connected edge IDs to a comma-separated string
            connected_edge_ids = [str(id) for id in connected_edge_ids if id is not None]
            if connected_edge_ids:
                outfile.write(f"{edge_id},{','.join(connected_edge_ids)}\n")
            else:
                # If no connected edges, write only the edge ID
                outfile.write(f"{edge_id}\n")

    # Return the number of main edges processed
    return len(mainEdge)


# 1.3
def create_motions(graph, num_edges, num_objs, File_1_combined_nodes_edges_toRead, File_3_Motions_file_ToWrite):
    percentage_of_objs_central = 0.8
    percentage_of_central_edges = 0.08
    percentage_of_objs_right = 0.3
    percentage_of_right_edges = 0.2
    percentage_of_objs_left = 0.3
    percentage_of_right_left = 0.2
    # Load the edge information from the file
    edge_info = {}
    with open(File_1_combined_nodes_edges_toRead, 'r') as f:
        for line in f:
            edge_id, start_node, end_node, start_x, start_y, end_x, end_y, weight = line.strip().split(",")
            edge_info[(int(start_node), int(end_node))] = int(edge_id)

    # Calculate the geometric center of the graph to determine central edges
    all_x_coords = [graph.nodes[node]['x'] for node in graph.nodes()]
    all_y_coords = [graph.nodes[node]['y'] for node in graph.nodes()]
    center_x = sum(all_x_coords) / len(all_x_coords)
    center_y = sum(all_y_coords) / len(all_y_coords)

    edge_distances = {}
    for edge in graph.edges():
        u, v = edge
        edge_mid_x = (graph.nodes[u]['x'] + graph.nodes[v]['x']) / 2
        edge_mid_y = (graph.nodes[u]['y'] + graph.nodes[v]['y']) / 2
        distance = ((center_x - edge_mid_x) ** 2 + (center_y - edge_mid_y) ** 2) ** 0.45
        edge_distances[edge] = distance
    sorted_edges_by_distance = sorted(edge_distances, key=edge_distances.get)

    # Here we have the Final Central Edges based on the "percentage_of_central_edges" value.
    central_edges = sorted_edges_by_distance[:int(percentage_of_central_edges * num_edges)]  

    all_x_coords = [graph.nodes[node]['x'] for edge in graph.edges() for node in edge]
    max_x = max(all_x_coords)
    min_x = min(all_x_coords)

    # Calculate the split x coordinate as the midpoint between max_x and min_x. This is how we know where to plit vertically our network
    split_x = 0.5 * (max_x + min_x) 

    most_visited_edges_general = set()
    max_size_of_mostVisited_Edges = 30


    # Start to assign moving objects on the edges . First obje takes id=1 , second id=2 , etc ... .
    all_results = []
    for obj_id in range(1, num_objs + 1):
        if obj_id <= int(percentage_of_objs_central * num_objs):
            # Assign the first "percentage_of_objs_central"% of objects to central edges
            random_edge = random.choice(central_edges)
        else:
            # Assign the remaining objects to random edges
            random_edge = random.choice(list(graph.edges()))


        # In order to simulate the time-based sensors, we will force each moving objs to traverse 
        # a random number of connected edges in a range [1,num_edges)
        individual_max_length = int(random.uniform(num_edges * 1, num_edges))


        u, v, edge_weight = random_edge[0], random_edge[1], graph.get_edge_data(*random_edge, default={}).get(0, {}).get('weighttt', None)

        # Start traversing from the random edge
        current_edge = random_edge 

        # Check on which side in the network , right or left , is the moving obj assigned 
        is_left_side = graph.nodes[random_edge[0]]['x'] < split_x

        # Force to move on the other side . This is how we force the spans
        if is_left_side:
            direction = 'right'
        elif graph.nodes[random_edge[0]]['x'] == split_x:
            # If x is exactly equal to split_x, randomly choose direction . In this case we force always to the left
            direction = random.choice(['left'])
        else:
            direction = 'left'

        # Initialize the visited edges . 
        visited_edges = set()

        # Initialize the path with the current edge .
        path = [current_edge]  


        # Track the number of traversed edges .
        count = 1   

        # Create the path for each obj . Each path will have a the random length individual_max_length -> random integer in [1,num_edges)
        while current_edge and count < individual_max_length: 

            # Check if the variable `most_visited_edges_general` is not empty or None
            if most_visited_edges_general:
                # Convert `most_visited_edges_general` to a list (if it's not already a list)
                most_visited_edges_general = list(most_visited_edges_general)
                
                # Randomly shuffle the elements in `most_visited_edges_general`
                # `random.sample` creates a new list with all elements randomly ordered
                most_visited_edges_general = random.sample(most_visited_edges_general, len(most_visited_edges_general))

            # Convert `most_visited_edges_general` back to a set
            # This ensures that all elements remain unique, as sets cannot have duplicates
            most_visited_edges_general = set(most_visited_edges_general)


            u, v = current_edge   # Process the current edge
            visited_edges.add(current_edge)   # Mark the current edge as visited
            count += 1

            # Get the x coordinate of the current edge's start and end nodes
            x1 = graph.nodes[u]['x']
            x2 = graph.nodes[v]['x']


            
            # Check the direction , the moving obj should follow 
            if direction == 'right':

                # Retrieve all edges connected to the node `v` from the graph
                # `graph.edges(v)` returns an iterable of all edges where node `v` is one of the endpoints
                # Convert this iterable into a list to allow further processing
                neighboring_edges = list(graph.edges(v))

                # Sort the neighboring edges based on their 'weighttt' attribute in descending order
                # Each `edge` is a tuple of two nodes (e.g., `(u, v)`), representing an edge in the graph
                # `graph.get_edge_data(*edge, default={})` retrieves the edge's metadata as a dictionary
                # `.get(0, {})` accesses nested data for the specific key `0` in the edge's metadata (if it exists)
                # `.get('weighttt', 0)` fetches the value associated with the 'weighttt' key (default is 0 if it doesn't exist)
                # `reverse=True` ensures the edges with the highest 'weighttt' come first in the sorted list
                neighboring_edges.sort(key=lambda edge: graph.get_edge_data(*edge, default={}).get(0, {}).get('weighttt', 0), reverse=True)
                
                # Filter and keep only the edges which have the `v` node as startnode , eg : `(v, whatever)`
                right_edges = [
                    edge for edge in neighboring_edges
                    if edge[0] == v and edge[1] != u and edge not in visited_edges and graph.nodes[edge[1]]['x'] > x2
                ]

                # Sort the right_edges based on weight. The "weight" is actually our decision in previous step. It may the same for all edges.
                right_edges.sort(key=lambda edge: graph.get_edge_data(*edge, default={}).get(0, {}).get('weighttt', 0), reverse=True)

                # If there is at least one edge for direction=right .
                if right_edges:
                    # Random Selection from the available edges
                    current_edge = random.choice(right_edges)

                    # Tracking the most visited edges
                    if len(most_visited_edges_general) < max_size_of_mostVisited_Edges : 
                        most_visited_edges_general.add(current_edge)

                # At this point if moving object can not move to the right , it will try to move to the left. 
                else:
                    left_edges = [edge for edge in neighboring_edges if edge[0] == v and edge[1] != u and edge not in visited_edges]
                    if left_edges:
                        current_edge = random.choice(left_edges)
                        if len(most_visited_edges_general) < max_size_of_mostVisited_Edges:
                            most_visited_edges_general.add(current_edge)
                    
                    # if there also no edge on the left then we break. At this case the moving obj traversed only one edge.
                    else:
                        break
                    
            # Same process for the left direction                
            elif direction == 'left':
                neighboring_edges = list(graph.edges(v))
                left_edges = [
                    edge for edge in neighboring_edges
                    if edge[0] == v and edge[1] != u and edge not in visited_edges and graph.nodes[edge[1]]['x'] < x2
                ]

                left_edges.sort(key=lambda edge: graph.get_edge_data(*edge, default={}).get(0, {}).get('weighttt', 0), reverse=True)
                if left_edges:
                    current_edge = random.choice(left_edges)
                    if len(most_visited_edges_general) < max_size_of_mostVisited_Edges : 
                        most_visited_edges_general.add(current_edge)
                else:
                    right_edges = [edge for edge in neighboring_edges if edge[0] == v and edge[1] != u and edge not in visited_edges]
                    if right_edges:
                        current_edge = random.choice(right_edges)
                        if len(most_visited_edges_general) < max_size_of_mostVisited_Edges:
                            most_visited_edges_general.add(current_edge)
                    else: 
                        break

            
            # Add the current edge to the path
            if current_edge:
                path.append(current_edge)  

        # Store the results-> moving obj and its path
        all_results.append((obj_id, path))  
            


    # Replace all node pairs with edge IDs in the paths
    all_results_with_edge_ids = []
    for obj_id, path in all_results:
        edge_id_path = []
        for edgeid in path :
            #if int(edge_id) >645:
                #print(edgeid)
            edge_id = int(edge_info[edgeid])
            edge_id_path.append(edge_id)
        all_results_with_edge_ids.append((obj_id, edge_id_path))

    # Write all paths to the file with edge IDs
    with open(File_3_Motions_file_ToWrite, "a") as f:
        for obj_id, path in all_results_with_edge_ids:
            path_str = ",".join(str(edge_id) for edge_id in path)
            f.write(f"{obj_id},{path_str}\n")


# 1.4
def write_data_to_sensors_file(File_4_DFSMottions_toRead, File_4_sensors_toWrite, num_objs, total_edges, north, south, east, west, place_name):
    """
    Reads object-to-edge mappings from an input file, processes the data, and writes it to output files.

    Parameters:
    - File_4_DFSMottions_toRead: Input file containing object IDs and associated edge IDs.
    - File_4_sensors_toWrite: Output file to store edge IDs and their corresponding object IDs.
    - num_objs: Total number of objects (used for naming the output file).
    - total_edges: Total number of edges (used for naming the output file).
    - north, south, east, west: Coordinates defining the geographical area.
    - place_name: Name of the place (used for naming the output file).

    Outputs:
    - Writes two files: one with the processed object-to-edge mappings and another named based on the network details.
    """

    # Step 1: Create a dictionary to store edge IDs and their associated object IDs
    edge_sensors = {}

    # Step 2: Read the input file and populate the dictionary
    with open(File_4_DFSMottions_toRead, 'r') as infile:
        for line in infile:
            # Split the line into object ID and associated edge IDs
            values = line.strip().split(',')
            obj_id = values[0]  # First value is the object ID
            edge_ids = values[1:]  # Remaining values are edge IDs

            # Assign the object ID to each edge ID
            for edge_id in edge_ids:
                # Initialize the list for the edge if it doesn't exist
                if edge_id not in edge_sensors:
                    edge_sensors[edge_id] = []
                # Add the object ID to the list for this edge if it's not already present
                if obj_id not in edge_sensors[edge_id]:
                    edge_sensors[edge_id].append(obj_id)

    # Step 3: Generate a timestamped file name based on the input parameters
    current_datetime = datetime.now().strftime("%Y%m%dT%H%M%S")  # Get the current date and time in the format YYYYMMDDTHHMMSS
    file_name = f"network_{num_objs}_{total_edges}_{place_name}_{north}_{south}_{east}_{west}_{current_datetime}.txt"

    # Determine the parent directory for saving the file
    parent_dir = os.path.dirname(os.getcwd())
    full_path = os.path.join(parent_dir, file_name)

    # Step 4: Write the edge-object mappings to the timestamped output file
    with open(full_path, 'w') as outfile1:
        for edge_id, obj_ids in edge_sensors.items():
            # Write each edge ID and its associated object IDs as a comma-separated line
            outfile1.write(edge_id + ',' + ','.join(obj_ids) + '\n')

    # Step 5: Write the edge-object mappings to the main output file
    with open(File_4_sensors_toWrite, 'w') as outfile:
        for edge_id, obj_ids in edge_sensors.items():
            # Write each edge ID and its associated object IDs as a comma-separated line
            outfile.write(edge_id + ',' + ','.join(obj_ids) + '\n')



# Helper-Functions for Task 1
def get_coordinates(place_name):
    # Geocode the place name to get its latitude and longitude
    geocode_result = ox.geocoder.geocode(place_name)
    return geocode_result


def rotate_graph(graph, angle):
    angle_rad = np.radians(angle)
    rotation_matrix = np.array([[np.cos(angle_rad), -np.sin(angle_rad)],
                                [np.sin(angle_rad), np.cos(angle_rad)]])
    for _, data in graph.nodes(data=True):
        x, y = data['x'], data['y']
        data['x'], data['y'] = np.dot(rotation_matrix, np.array([x, y]))
    return graph


def visualize_network(graph, north, south, east, west, place_name):
    # Create a base folium map centered around the area
    m = folium.Map(location=[(north + south) / 2, (east + west) / 2], zoom_start=14)

    # Plot the OSMNx graph on the map
    ox.plot_graph_folium(graph, map=m, popup_attribute='length', edge_color='blue')

    # Show bounding box for reference
    folium.Rectangle(
        bounds=[[south, west], [north, east]],
        color='red',
        fill=False
    ).add_to(m)

    # Add a marker for the center of the map
    folium.Marker(
        location=[(north + south) / 2, (east + west) / 2],
        popup=f"{place_name} Center",
        icon=folium.Icon(color="green")
    ).add_to(m)

    # Save the map to an HTML file or display it
    m.save("network_visualization.html")
    print("Map saved as network_visualization.html")
    return m







#__________Map Partitioning_________#
            
# 2.1        
def main_partitioning_map_(File_1_combined_nodes_edges_toRead, prefix_file_Name_map, prefix_file_Name_Regional, prefix_file_Name_Picture, depth):  
    """
    Main function to partition and map a network recursively.

    Parameters:
    - File_1_combined_nodes_edges_toRead: Input file containing network data (edges and nodes).
    - prefix_file_Name_map: Prefix for naming the output partitioned map files.
    - prefix_file_Name_Regional: Prefix for naming regional map files (not used directly in this function).
    - prefix_file_Name_Picture: Prefix for naming picture files (not used directly in this function).
    - depth: Depth of recursion for partitioning the network.

    Outputs:
    - Partitions the map recursively and deletes unnecessary maps, keeping the longest one.
    """

    # Step 1: Set the initial recursion level
    # If depth is 0 (base case), start with `i = 0`; otherwise, initialize `i = 1`
    if depth == 0:
        i = 0
    else:   
        i = 1

    # Step 2: Initialize the total sum of lines (used in recursive mapping)
    total_sum_of_lines = 0

    # Step 3: Call the recursive partitioning function
    # This function handles the actual partitioning of the network based on the input depth and prefix
    recursively_map_partition(File_1_combined_nodes_edges_toRead, prefix_file_Name_map, depth, i, total_sum_of_lines)

    # Step 4: Delete unnecessary map files, keeping only the longest partition
    delete_maps_except_longest()

# 2.2 
def recursively_map_partition(File_1_combined_nodes_edges_toRead, prefix_file_Name_map, depth, i, total_sum_of_lines, numberOfEdgesinInitialFile=None):
    """
    Recursively partitions a network map into smaller sub-maps based on a splitting condition.

    Parameters:
    - File_1_combined_nodes_edges_toRead: Input file containing network data (edges and nodes).
    - prefix_file_Name_map: Prefix for naming the partitioned output files.
    - depth: Maximum depth of recursion for partitioning.
    - i: Current recursion level.
    - total_sum_of_lines: Running total of lines across all partitioned files.
    - numberOfEdgesinInitialFile: Optional, total number of edges in the initial input file.

    Outputs:
    - Writes partitioned sub-maps to files with names based on the recursion depth and partition.
    """

    # Base case: Stop recursion if the current depth exceeds the maximum depth
    if i > depth:
        return

    # Step 1: Read and parse the input file
    data = []  # List to store edge records
    with open(File_1_combined_nodes_edges_toRead, 'r') as file:
        lines = file.readlines()  # Read all lines from the file
        for line in lines:
            # Split each line into values and create a dictionary for the edge record
            values = line.strip().split(',')
            record = {
                'edgeID': int(values[0]),  # Edge ID
                'nodeID1': int(values[1]),  # Start node ID
                'nodeID2': int(values[2]),  # End node ID
                'x1': int(values[3]),  # Start node X-coordinate
                'y1': int(values[4]),  # Start node Y-coordinate
                'x2': int(values[5]),  # End node X-coordinate
                'y2': int(values[6])   # End node Y-coordinate
            }
            data.append(record)

    # Step 2: Store the total number of edges in the initial file if it's the first recursion level
    if i == 1:
        numberOfEdgesinInitialFile = len(lines)

    # Step 3: Find the midpoint of the X-coordinates to split the data
    min_x = min(min(record['x1'], record['x2']) for record in data)  # Minimum X value
    max_x = max(max(record['x1'], record['x2']) for record in data)  # Maximum X value
    split_x = (min_x + max_x) / 2  # Midpoint for splitting the data

    # Special case: If depth is 0, set split_x to 0 and process the data without recursion
    if depth == 0:
        split_x = 0
        right_left = 0  # Only one partition for this case
        right_left_data = partition_data(data, split_x, depth)  # Partition the data
        subfile_path = f'{prefix_file_Name_map}{right_left}{i}.txt'  # File path for the partition
        subfile_prefix = f'{prefix_file_Name_map}{right_left}'  # Prefix for the file name

        # Write the partitioned data to the output file
        for right_left, records in right_left_data.items():
            output_file_path = f'{prefix_file_Name_map}{right_left}{i}.txt'  # File path
            count = 0  # Counter for lines written
            with open(output_file_path, 'w') as output_file:
                for record in records:
                    # Write each record as a comma-separated line
                    line = ','.join(str(value) for value in record.values()) + '\n'
                    output_file.write(line)
                    count += 1
            # Update the total sum of lines across partitions
            total_sum_of_lines += count

    else:
        # Step 4: Partition the data into left and right subsets based on split_x
        right_left_data = partition_data(data, split_x, depth)

        # Step 5: Write each partition to its respective file
        for right_left, records in right_left_data.items():
            subfile_path = f'{prefix_file_Name_map}{right_left}{i}.txt'  # File path for the partition
            subfile_prefix = f'{prefix_file_Name_map}{right_left}'  # Prefix for the file name
            output_file_path = f'{prefix_file_Name_map}{right_left}{i}.txt'  # File path
            count = 0  # Counter for lines written
            with open(output_file_path, 'w') as output_file:
                for record in records:
                    # Write each record as a comma-separated line
                    line = ','.join(str(value) for value in record.values()) + '\n'
                    output_file.write(line)
                    count += 1
            # Update the total sum of lines across partitions
            total_sum_of_lines += count

        # Step 6: Recursively partition each subset
        for right_left in right_left_data:
            if right_left_data[right_left]:  # If the partition is not empty
                subfile_path = f'{prefix_file_Name_map}{right_left}{i}.txt'  # File path for the subset
                subfile_prefix = f'{prefix_file_Name_map}{right_left}'  # Prefix for the file name
                # Recursive call with increased depth
                recursively_map_partition(subfile_path, subfile_prefix, depth, i + 1, total_sum_of_lines, numberOfEdgesinInitialFile)


# 2.3 
def partition_data(data, split_x, depth):
    """
    Partitions the input data (edges) into left and right subsets based on the x-coordinate midpoint (split_x).

    Parameters:
    - data: List of edge records, where each record is a dictionary containing edge and node details.
    - split_x: The x-coordinate value used as the midpoint to divide the data into two partitions.
    - depth: The depth of recursion; determines if partitioning happens or not.

    Returns:
    - A dictionary containing the partitioned data:
        - '1': Edges in the left partition.
        - '2': Edges in the right partition (only if depth > 0).
    """

    # Initialize lists to store edges in the left and right partitions
    city_left_edges = []
    city_right_edges = []

    # Case 1: If depth is 0, all edges are added to the left partition
    if depth == 0:
        for record in data:
            city_left_edges.append(record)
        # Return a dictionary with only the left partition
        right_left_data = {
            '1': city_left_edges
        }

    # Case 2: Partition the edges into left and right subsets based on their x-coordinates
    else:
        for record in data:
            # Extract the x-coordinates of the start and end nodes for the current edge
            x1, x2 = record['x1'], record['x2']

            # If both nodes are to the left of split_x, add the edge to the left partition
            if x1 <= split_x and x2 <= split_x:
                city_left_edges.append(record)
            # If both nodes are to the right of split_x, add the edge to the right partition
            elif x1 > split_x and x2 > split_x:
                city_right_edges.append(record)
            # If the edge crosses the split_x line
            else:
                # Calculate the distance of each node from the split_x line
                distance_node1 = abs(x1 - split_x)
                distance_node2 = abs(x2 - split_x)

                # Decide which partition to place the edge based on the distance of the nodes from split_x
                if distance_node1 >= distance_node2:
                    # Place the edge in the right partition if the farthest node is to the right
                    if x1 > x2:
                        city_right_edges.append(record)
                    else:
                        city_left_edges.append(record)
                else:
                    # Place the edge in the right partition if the closest node is to the right
                    if x2 > x1:
                        city_right_edges.append(record)
                    else:
                        city_left_edges.append(record)

        # Return a dictionary with both left and right partitions
        right_left_data = {
            '1': city_left_edges,
            '2': city_right_edges,
        }

    # Return the dictionary containing partitioned data
    return right_left_data
 

# 2.4
def delete_maps_except_longest():
    """
    Deletes all map files in the current directory except those with the longest numerical suffix
    or files explicitly listed to be kept.

    Assumptions:
    - Map files follow a naming pattern like "mapXXX.txt", where XXX is the numerical suffix.
    """

    # Step 1: Get all files starting with "map" in the current directory
    map_files = [file_name for file_name in os.listdir() if file_name.startswith("map")]
    
    
    
    # Step 2: Find the length of the longest numerical suffix
    # Subtract 7 from the length to exclude the "map" prefix and ".txt" extension
    max_length = max(len(file_name) - 7 for file_name in map_files)
    
    # Step 3: Identify files with the longest numerical suffix
    
    keep_files = [file_name for file_name in map_files if len(file_name) - 7 == max_length]

    for file_name in os.listdir() :
        if file_name.startswith("Regional_4_sensors"):
            keep_files.append(file_name)

    # Step 4: Explicitly add specific files to the list of files to keep , if you want
    keep_files.extend([
        "map111.txt", "map112.txt", "map211.txt", "map212.txt",
        "map21.txt", "map11.txt"
    ])

    # Step 5: Delete files not in the list of files to keep
    for file_name in map_files:
        if file_name not in keep_files:
            # Construct the full path of the file
            file_path = os.path.join(os.getcwd(), file_name)
            # Remove the file
            os.remove(file_path)
            # Uncomment the line below to see which files are being deleted
            # print(f"Deleted: {file_path}")














#__________Create edgeNetwork infos for the Top leader after _________#

# 3.1
def create_edgeConnections_and_sensorInfo_for_each_Region(File_2_edgeconnections, File_4_sensors_FILE, prefix_file_Name_map):
    """
    Creates edge connections and sensor information files for each region based on the map files in the current directory.

    Parameters:
    - File_2_edgeconnections: Template string for edge connections output file (formatted with region number).
    - File_4_sensors_FILE: Template string for sensor information output file (formatted with region number).
    - prefix_file_Name_map: Prefix for identifying map files in the directory.

    Returns:
    - regionids: A list of region IDs (numerical suffixes of the map files).
    """

    regionids = []  # Initialize a list to store region IDs

    # Step 1: Iterate through all files in the current directory
    for file_name in os.listdir():
        # Check if the file name starts with the specified prefix and ends with ".txt"
        if file_name.startswith(prefix_file_Name_map) and file_name.endswith(".txt"):
            # Extract the numerical suffix from the file name using regular expressions
            number_match = re.search(r'\d+', file_name)

            # Step 2: Create edge connections and sensor information files
            if number_match:
                # Format and create the regional edge connections file
                create_regional_edgeconnections(file_name, File_2_edgeconnections.format(number=number_match.group()))
                # Format and create the regional sensor information file
                create_regional_edgeconnections(file_name, File_4_sensors_FILE.format(number=number_match.group()))

                # Step 3: Add the matched region ID to the list
                matched_digits_str = number_match.group()  # Extract the matched digits as a string
                matched_digits_int = int(matched_digits_str)  # Convert the string to an integer
                regionids.append(matched_digits_int)  # Add the region ID to the list

    # Return the list of region IDs
    return regionids

# 3.2    
def create_regional_edgeconnections(map_filename, File_for_RegionalEdgeConnenctios_or_RegionalSensors_toRead):
    """
    Filters and creates a regional edge connections or sensors file based on the specified map file.

    Parameters:
    - map_filename: The name of the map file containing a list of edge IDs.
    - File_for_RegionalEdgeConnenctios_or_RegionalSensors_toRead: The file containing all edge connections or sensor data.

    Outputs:
    - Creates a new regional file named "Regional_<base_filename><map_number>.txt" containing only relevant lines.
    """

    # Step 1: Read edge IDs from the map file
    with open(map_filename, 'r') as map_file:
        map_lines = map_file.readlines()  # Read all lines from the map file
        # Extract the first value (edge ID) from each line and store it in a list
        map_first_values = [line.split(',')[0].strip() for line in map_lines]

    # Step 2: Read the edge connections or sensor information file
    with open(File_for_RegionalEdgeConnenctios_or_RegionalSensors_toRead, 'r') as edge_connections_file:
        edge_connections_lines = edge_connections_file.readlines()  # Read all lines from the file

    # Step 3: Generate the name for the new regional file
    # Extract the numerical suffix from the map file name (e.g., "map123.txt" -> "123")
    map_number = map_filename.split('map')[1].split('.')[0]
    # Extract the base name of the input file without the extension
    nameOfFile = os.path.splitext(File_for_RegionalEdgeConnenctios_or_RegionalSensors_toRead)[0]
    # Construct the new regional file name
    new_edge_connections_filename = f"Regional_{nameOfFile}{map_number}.txt"

    # Step 4: Write filtered lines to the new regional file
    with open(new_edge_connections_filename, 'w') as new_edge_connections_file:
        for line in edge_connections_lines:
            # Check if the first value (edge ID) of the current line matches any edge ID from the map file
            if line.split(',')[0].strip() in map_first_values:
                new_edge_connections_file.write(line)  # Write the matching line to the new file

# 3,3 
def create_RegionConnections_for_Top_Leader(file_prefix="Regional_2_edgeconnections", file_extension=".txt"):
    """
    Identifies and records connections between regions by analyzing edge connection files.

    Parameters:
    - file_prefix: The prefix of the files containing regional edge connections.
    - file_extension: The file extension for the regional edge connection files.

    Outputs:
    - Writes the connections between regions to a file named "7_ConnectionsBetween_Regions.txt".
    - Returns a dictionary mapping regions to their connections.
    """

    # Step 1: Initialize a dictionary to store connections between regions
    Connections_between_Regions = {}

    # Step 2: Get all files in the current directory that match the file prefix and extension
    files = [f for f in os.listdir('.') if f.startswith(file_prefix) and f.endswith(file_extension)]

    # Step 3: Iterate through each regional file
    for file in files:
        # Extract the numeric ID of the current file
        file_id = int(file[len(file_prefix):-len(file_extension)])

        # Open the current file for reading
        with open(file, 'r') as f:
            # Initialize a dictionary to store connections for the current region
            Connections_between_Regions[file_id] = {}

            # Step 4: Process each line in the current file
            for line in f:
                # Extract the numeric values from the line (comma-separated)
                values = [int(val) for val in line.strip().split(',')]
                first_value = values[0]  # The first value represents the main edge

                # Step 5: Check if the remaining values connect to other regions
                for next_value in values[1:]:
                    found = False

                    # Step 6: Check other files for connections involving the `next_value`
                    for other_file in files:
                        if other_file != file:  # Skip the current file
                            # Extract the numeric ID of the other file
                            other_file_id = int(other_file[len(file_prefix):-len(file_extension)])

                            # Ensure the dictionary for the other region is initialized
                            if other_file_id not in Connections_between_Regions[file_id]:
                                Connections_between_Regions[file_id][other_file_id] = {}

                            # Open the other file for reading
                            with open(other_file, 'r') as f2:
                                # Process each line in the other file
                                for line2 in f2:
                                    # Extract numeric values from the line
                                    values2 = [int(val2) for val2 in line2.strip().split(',')]
                                    if values2[0] == next_value:
                                        # If a connection is found, record it in the dictionary
                                        Connections_between_Regions[file_id][other_file_id].setdefault(first_value, []).append(next_value)
                                        found = True
                                        # Uncomment if you'd like to break on the first match
                                        # break

                                # Uncomment if you'd like to stop checking after a match
                                # if found:
                                #     break

    # Step 7: Write the connections between regions to an output file
    output_file = "7_ConnectionsBetween_Regions.txt"
    with open(output_file, "w") as file:
        # Iterate over the regions and their connections
        for file_id, connections in Connections_between_Regions.items():
            for other_file_id, values in connections.items():
                for mainedge, connected_edge in values.items():
                    # Write the region connections to the output file
                    file.write(f"Region: {file_id}, connects with region: {other_file_id}, Connections: {mainedge} ")
                    file.write(", ".join(str(value) for value in connected_edge))
                    file.write("\n")

    # Return the dictionary containing all region connections
    return Connections_between_Regions








##################################################################################################################################
#__________Tracking Results &  Helper Function_________#


def delete_files_except(run_once, History7z , threshold, f1, f2, f3, f4, f5, f6, f7, f8, f9):
    # Get the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Create a new folder with the experiment name
    folder_name = f"Experiment{timestamp}_withHashed_{threshold}"
    os.mkdir(folder_name)
    # Get a list of files in the current directory
    files = [f for f in os.listdir('.') if f.startswith("map") and f.endswith(".txt")]

    for file in os.listdir():
        if (run_once == 1 and file=="4_sensors.txt")or file=="Current_Experiment_Info.txt" or file.startswith("Regional_4_sensors") or file.startswith("4_sensors_HASHED_") or file.startswith("Regional_4_sensors_HASHED") or file =="ResultsOfExperiments.txt"  or (file.startswith("depth_") and file.endswith(".png")) or file =="Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_all_with_costs.txt" or file == "RESULTS.txt" or file=="Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_pairs.txt" or file=="Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_single.txt" or file=="Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_all.txt"  or file=="Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_allwithout_single.txt" or file=="Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_all_with_costs" or file =="correcthomoedges111.json"or file =="correcthomoedges112.json"or file =="correcthomoedges113.json"or file =="correcthomoedges211.json"or file =="correcthomoedges212.json"or file =="correcthomoedges213.json" or file =="correcthomoedges2.json"or file =="correcthomoedges3.json"or file =="correcthomoedges103.json" or file =="correcthomoedges102.json"or file =="correcthomoedges101.json"or file =="correcthomoedges2222.json"or file =="correcthomoedges2223.json"or file =="correcthomoedges2221.json" or file =="correcthomoedges1122.json"or file =="correcthomoedges1123.json"or file =="correcthomoedges1121.json" or file =="correcthomoedges1222.json"or file =="correcthomoedges1223.json"or file =="correcthomoedges1221.json" or file =="correcthomoedges2122.json"or file =="correcthomoedges2123.json"or file =="correcthomoedges2121.json"  or  file=="Current_Experiment_Top_Leader_flat_visualization_all_together.txt" or file =="Current_Experiment_Top_Leader_Reg_Leader_edges_costs.txt" or file =="Current_Experiment_Top_Leader_Reg_Leader_span_HoMoPaths_costs.txt"  or file=="all_with_costs.txt" or file=="seeds.txt" or file=="Current_Experiment_Top_Leader_flat_visualization_per_Region_brackets.txt" or file == History7z or file == f1 or file ==f2 or file == f3 or file == f4 or file == f5 or file == f6 or file == f7 or file == f8 or  file == f9  or file in files or file == "analysis.py" or file=="seeds.txt" or file =="preparation.py":
            #print(f"File: {file} remained untouched")
            continue
        else:
            if file.startswith("Regional_4_sensors"):
                continue
            source_path = os.path.join(os.getcwd(), file)
            if os.path.isfile(source_path):
                destination_path = os.path.join(os.getcwd(), folder_name, file)
                shutil.move(source_path, destination_path)
                #print(f"File: {file} moved to {folder_name}")
            elif os.path.isdir(source_path):
                if  file.startswith("Experiment") or file.startswith("Regional_4_sensors") or source_path.startswith("Experiment") or file.startswith("All_Experiments") or source_path.startswith("All_Experiments"):
                    continue
                    #print(f"File/Folder: {file} starts with 'Experiment' and excluded")
                # To move directories, we have to use shutil.move with destination_path
                # instead of os.rename
                else:
                    destination_path = os.path.join(os.getcwd(), folder_name, file)
                    shutil.move(source_path, destination_path)
                    #print(f"Folder: {file} moved to {folder_name}")


def write_results_to_file_ResultsOfExperiments(filename ,number_of_HoMoPaths , total_sum, all_HOMOPATHS, end_time1, start_time1 , threshold , current_compress):
    with open(filename, 'a') as fileofexperiments:
        fileofexperiments.write(f"TOP LEADER\nTotal number of Span-HoMoPaths: {number_of_HoMoPaths}\nTotal number of HoMoPaths : {total_sum}")
        fileofexperiments.write(f"\nHoMoPaths Span Regions : \nExec Time : {end_time1 - start_time1}\nThreshold: {threshold} , Compress:{current_compress}\n")
        for main_region, regions in all_HOMOPATHS.items():
            fileofexperiments.write(f"{main_region}\n")
            for region, paths in regions.items():
                fileofexperiments.write(f"    {region}: ")
                for path, value in paths.items():
                    if value != -1:
                        fileofexperiments.write(f"{json.dumps(path)},")
                fileofexperiments.write(f"\n\n\n")


def write_results_from_Top_Leader_to_file(raw_or_hashed , data, num_of_objs , compress, threshold, num_of_edges, num_of_permutations, file_path_all_together, file_path_with_brackets):
    with open(file_path_with_brackets, "a") as file_with_brackets:
         for key, value in data.items():
            formatted_paths_all = ','.join(['[{}]'.format(','.join(map(str, sublist))) for nested_key, sub_values in value.items() if nested_key >0 for sublist in sub_values])
            line_with_brackets = ','.join([str(num_of_objs), str(threshold), str(num_of_edges), str(num_of_permutations) , str(compress), str(key), formatted_paths_all])
            file_with_brackets.write(line_with_brackets + "\n")
    
    # After processing all keys, write the accumulated values to another file
    with open(file_path_all_together, "a") as all_values_file:
        line_values_all_together = [str(num_of_objs), str(threshold), str(num_of_edges), str(num_of_permutations) , str(compress), str(0)]        
        dict_values_temp = []        
        for key, value in data.items():
            for sub_values in value.values():
                for item in sub_values:
                    if all(isinstance(i, int) for i in item):  # Single list
                        dict_values_temp.extend([str(num) for num in item])
                    else:  # Nested list
                        for sublist in item:
                            dict_values_temp.extend([str(num) for num in sublist])
        set_items = set(dict_values_temp)
        dict_values_str = "[" + ",".join(set_items ) + "]"
        line_values_all_together.append(dict_values_str)        
        all_values_line = ",".join(line_values_all_together)        
        if not all_values_line.endswith("]"):
            all_values_line += "]"
        all_values_file.write(all_values_line + "\n")


    """with open("all_with_costs.txt", "a") as all_values__with_costs_file:
        cost_per_byte=0.0001
        size_of_integer=4
        if raw_or_hashed == 1:
            total_packet = num_of_objs +2 # signature(or num_of_objs) + id + raw
        else:
            total_packet =num_of_objs +1 # signature(or num_of_objs) + id
        total_bytes = total_packet * size_of_integer
        transmission_cost = round((total_bytes * cost_per_byte),4)
        line_values_all_together = [str(total_bytes),str(transmission_cost),str(num_of_objs), str(threshold), str(num_of_edges), str(num_of_permutations) , str(compress), str(0)]        
        dict_values_temp = []        
        for key, value in data.items():
            for sub_values in value.values():
                for item in sub_values:
                    if all(isinstance(i, int) for i in item):  # Single list
                        dict_values_temp.extend([str(num) for num in item])
                    else:  # Nested list
                        for sublist in item:
                            dict_values_temp.extend([str(num) for num in sublist])
        set_items = set(dict_values_temp)
        dict_values_str = "[" + ",".join(set_items ) + "]"
        line_values_all_together.append(dict_values_str)        
        all_values_line = ",".join(line_values_all_together)        
        if not all_values_line.endswith("]"):
            all_values_line += "]"
        all_values__with_costs_file.write(all_values_line + "\n")
"""

def get_size(obj, seen=None):
    """Recursively find the size of objects, including contained objects."""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Mark as seen
    seen.add(obj_id)
    
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    
    return size












#### other way to create paths

# DFS appoach to create the paths 
def dfs_find_path(graph, current_node, direction, depth, split_x, visited=set()):
    if depth == 0:
        return None
    if direction == 'right':
        condition = lambda x: x > split_x
    else:
        condition = lambda x: x < split_x
    
    paths = []
    for neighbor in graph.neighbors(current_node):
        if neighbor in visited:
            continue
        next_x = graph.nodes[neighbor]['x']
        if condition(next_x):
            paths.append([neighbor])
        else:
            visited.add(neighbor)
            sub_path = dfs_find_path(graph, neighbor, direction, depth - 1, split_x, visited)
            if sub_path:
                paths.extend([[neighbor] + path for path in sub_path])
    return paths if paths else None

