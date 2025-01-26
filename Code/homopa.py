# Standard library imports
import os
import time
import re
import socket
import json
import threading
import sys
import shutil
import queue

# Third-party/data-science-related imports
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Switch the Matplotlib backend to a non-GUI one (Agg) before creating plots
import numpy as np

# Local imports from your 'preparation' module
# These are utility functions for file handling, network creation, partitioning, etc.
from preparation import (
    delete_files_except,
    create_network,
    find_connected_edges,
    create_motions,
    write_data_to_sensors_file,
    main_partitioning_map_,
    create_edgeConnections_and_sensorInfo_for_each_Region,
    get_size,
    write_results_from_Top_Leader_to_file,
    write_results_to_file_ResultsOfExperiments,
    create_RegionConnections_for_Top_Leader
)

# Maximum hash value used in certain minhash or Cohen-based cardinality computations
_max_hash = np.uint32((1 << 32) - 1)


# -------------------------------------------------------------------------
# GLOBAL VARIABLES & SHARED DATA STRUCTURES (for thread coordination)
# -------------------------------------------------------------------------

# Event and Condition for synchronization:
#   - all_regions_ready: an Event that can be set/cleared to indicate that 
#     all regional leaders are ready.
#   - all_regions_ready_condition: a Condition that notifies when each region 
#     signals readiness (or no-homopath found), and waits until they are all done.
all_regions_ready = threading.Event()
all_regions_ready_condition = threading.Condition()

# Lists to track which regions have homopaths, which do not, and a master list:
#   - regions_ready_counter: those that discovered homopaths.
#   - regions_without_Homopa_counter: those that found none.
#   - all_regions_counter: all region IDs (both with and without homopaths).
regions_ready_counter = []
regions_without_Homopa_counter = []
all_regions_counter = []

# A threading.Lock to ensure we don't simultaneously modify shared structures:
function_lock = threading.Lock()

# A placeholder for global homopath data. May be used to store or pass 
# homopath info across threads (not always required).
all_HOMOPATHS = None

# Variables to track how many threads have completed:
completed_threads = 0
lock = threading.Lock()  # Lock to guard the 'completed_threads' counter.


# -------------------------------------------------------------------------
# HELPER FUNCTIONS FOR THREAD MANAGEMENT
# -------------------------------------------------------------------------

def thread_complete():
    """
    Called by a thread upon completion of its task.
    Increments the 'completed_threads' counter in a thread-safe manner.
    """
    global completed_threads
    with lock:
        completed_threads += 1

def thread_init():
    """
    Resets the 'completed_threads' counter back to zero.
    Called before launching a new set of threads, ensuring 
    we start counting from a fresh state.
    """
    global completed_threads
    with lock:
        completed_threads = 0

def clear_lists():
    """
    Empties the three global region-related lists in a thread-safe manner.
    Typically used before starting a new round of region leaders, ensuring 
    there's no leftover data from previous runs.
    """
    global regions_ready_counter
    global regions_without_Homopa_counter
    global all_regions_counter
    with lock:
        regions_ready_counter.clear()
        regions_without_Homopa_counter.clear()
        all_regions_counter.clear()




def calculate_transmission_cost(data):
    """
    Calculates an approximate cost in bytes to transmit the given data over a network between Regional and Top Leader.

    :param data:
        The data structure to be measured (e.g., a dictionary, list, or any JSON-serializable object).
    :return:
        An integer representing the total size, in bytes, of the JSON-encoded version of 'data'.
    """

    # 1) Convert the data structure to a JSON-formatted string
    serialized_data = json.dumps(data)

    # 2) Encode this JSON string as UTF-8 and measure its length in bytes
    total_cost = len(serialized_data.encode('utf-8'))

    return total_cost

##################################################################################################################################
#--------------------------------------------- #
#               T O S S I M




##########   TOP LEADER   ##########
# 4.1
def start_Top_leader(regionids, all_connections, threshold, 
                     total_edges, current_compress, num_of_permutations, 
                     raw_or_hashed, seed, result_queue):
    """
    Main function that simulates the 'Top Leader' node, which:
      1. Waits until all relevant regional leaders (or those having homopaths) are ready.
      2. Collects 'homopaths' data or number-of-objs data from each regional leader.
      3. Attempts to find spanning homopaths across multiple regions if they exist.
      4. Records and writes results/statistics to files, then signals to conclude execution.
    """

    # Global variables presumably shared across threads
    global regions_ready_counter              # set or list of regions that have discovered homopaths
    global regions_without_Homopa_counter     # set or list of regions that have no homopaths
    global all_regions_counter                # set or list of all region IDs

    start_time1 = time.time()  # Start the timer to measure execution time

    # Wait for all regional leaders to be ready using a condition variable
    with all_regions_ready_condition:
        print(f"\tTop Leader is waiting for 'READY' signals'")
        # We wait until the combined size of 'regions_ready_counter' and 'regions_without_Homopa_counter' 
        # matches the total number of region IDs. This implies all regions have responded somehow.
        while (len(regions_ready_counter) + len(regions_without_Homopa_counter)) < len(regionids):
            #print(f"'Top Leader Counter' : {regions_ready_counter}")
            all_regions_ready_condition.wait()  # Release lock and wait for notify() from regions

    # Now we know that all regions have responded (ready or no homopath found).
    #print(f"Top Leader Counter: {regions_ready_counter}")

    # Data structures to hold homopaths, object sets, etc.
    all_hot_paths = {}         # Will store the homopaths from each region
    objOfRegion = {}           # For each region, a set of its local unique objects (if raw data used)
    totalUniqObjs = set()      # Union set of objects from all regions
    top_leader_integers_raw = 0
    top_leader_integers_hashed = 0
    first_level_total_integers = 0

    # This variable will track how many bytes are 'transmitted' (network cost).
    # The user code has a function `calculate_transmission_cost(...)` presumably 
    # to approximate or measure network usage.
    C2Base_Total_Bytes = 0

    # --------------------------------------------------------------------------
    # Stage 1: Collect data from each region:
    #   - If a region has homopaths, we request them (mode=3).
    #   - Otherwise, we only request the number of objects (mode=4).
    # --------------------------------------------------------------------------
    for region_id in all_regions_counter:
        local_unique_objs = set()
        with function_lock:  # Acquire a lock to ensure thread-safety on shared resources
            if region_id in regions_ready_counter:
                # Region that has homopaths: request actual homopath data
                received_data_chunk_dict = send_request_to_regional_leader(3, region_id, 3)  
                # get_size(...) = calculate the size of the payload in mbytes as json .
                size = get_size(received_data_chunk_dict)

                # Accumulate transmission cost
                C2Base_Total_Bytes += calculate_transmission_cost(received_data_chunk_dict)
    
                # Depending on raw_or_hashed, we keep track of how many integers we processed
                if raw_or_hashed == 0:
                    top_leader_integers_raw += size
                else:
                    top_leader_integers_hashed += size
            else:
                # Region that has NO homopaths: only request the number-of-objects info (mode=4).
                received_data_chunk_Objs = send_request_to_regional_leader(4, region_id, 4)
                size = get_size(received_data_chunk_Objs)

                # The data comes back presumably as a string like "[1,2,3,...]"
                # so we parse that to get a set of integer objects.
                values_list = received_data_chunk_Objs[1:-1].split(',')
                received_data_chunk_Objs_set = {int(value.strip()) for value in values_list}

                # For raw data, we add those objects to local + global sets.
                # For hashed data, we also add them, but the usage might differ.
                for element in received_data_chunk_Objs_set:
                    if raw_or_hashed == 0:
                        totalUniqObjs.add(element)
                        local_unique_objs.add(element)
                    else:
                        totalUniqObjs.add(element)
                # After we retrieve data from a region that has no homopath, 
                # we might optionally send a "shutdown" or "no further action" request 
                # using "send_request_to_regional_leader('[-1]', region_id, '[-1]')".

            # If this region DOES have homopaths:
            if region_id in regions_ready_counter:
                # Convert dictionary keys from string to int
                received_data_chunk_dict_int_keys = {int(k): v for k, v in received_data_chunk_dict.items()}
                all_hot_paths[region_id] = received_data_chunk_dict_int_keys

                # For debugging, also request the number of objects in that region (mode=4).
                # This helps unify object sets across the entire system.
                received_data_chunk_Objs = send_request_to_regional_leader(4, region_id, 4)
                size = get_size(received_data_chunk_Objs)

                # If we are dealing with raw data, add the cost for these transmissions.
                # If hashed, we might not strictly need them for union of objects, 
                # but here it’s also done for debugging.
                if raw_or_hashed == 0:
                    C2Base_Total_Bytes += calculate_transmission_cost(received_data_chunk_Objs)

                time.sleep(1)  # to mimic real-time network delay or avoid concurrency issues

                if region_id in regions_ready_counter:
                    top_leader_integers_raw += size

                # This request (mode=5) presumably asks for total number of transmitted integers
                # that region had from 1st-level sensors. Used for debugging/performance metrics.
                received_data_transmitted_integers = send_request_to_regional_leader(5, region_id, 5)
                # received_data_transmitted_integers has not UNIQUE objs , dont worry
                # has the total number of integers that the regional leaderX from 1st level  received from its corresponding sensors
                # received_data_transmitted_integers is coming as response from through other functions .
                # start function which produce the functitotal_information_integers is function prepare_data 
                # which returns here "total_information_integers += topic_information_integers" 
                
                
                # Multiply by 4 to convert 'count of integers' to approximate bytes
                first_level_total_integers += received_data_transmitted_integers * 4
                time.sleep(1)

                # Parse again the object info for local+global sets:
                values_list = received_data_chunk_Objs[1:-1].split(',')
                received_data_chunk_Objs_set = {int(value.strip()) for value in values_list}
        
                for element in received_data_chunk_Objs_set:
                    if raw_or_hashed == 0:
                        totalUniqObjs.add(element)
                        local_unique_objs.add(element)
                    else:
                        totalUniqObjs.add(element)

                # Keep track of what objects belong to which region
                objOfRegion[region_id] = local_unique_objs
            else:
                # If the region had no homopaths, we can send a final "no further action" request 
                # or finalize the communication with that region.
                send_request_to_regional_leader("[-1]", region_id, "[-1]")

    # At this point, we have:
    #   1) homopath data from all regions that have them in `all_hot_paths`
    #   2) sets of unique objects per region in `objOfRegion`
    #   3) a global union of objects in `totalUniqObjs`
    #   4) partial metrics on the cost and number of integers processed

    # Convert the global set of unique objects to a list for later operations
    totalUniqObjs = list(totalUniqObjs)

    # Write the raw or hashed homopath data + total unique objects to a file 
    # (for debugging, logging, or offline analysis).
    write_results_from_Top_Leader_to_file(
        raw_or_hashed, all_hot_paths, len(totalUniqObjs), current_compress,
        threshold, total_edges, num_of_permutations,
        "Current_Experiment_Top_Leader_flat_visualization_all_together.txt",
        "Current_Experiment_Top_Leader_flat_visualization_per_Region_brackets.txt"
    )

    # --------------------------------------------------------------------------
    # Stage 2: If we have homopaths from at least 2 different regions,
    #          try to find "spanning homopaths" across them.
    # --------------------------------------------------------------------------
    all_HOMOPATHS = {}
    number_of_HoMoPaths = 0

    if len(all_hot_paths) > 1:
        list_of_span_homopaths = []
        all_HOMOPATHS = {}
        # `all_HOMOPATHS` is a dictionary structure to store results of discovered spanning homopaths
        for region_id, c_hot_paths1 in all_hot_paths.items():
            if region_id not in all_HOMOPATHS:
                all_HOMOPATHS[region_id] = {}
            if region_id not in all_HOMOPATHS[region_id]:
                all_HOMOPATHS[region_id][region_id] = {}

            # For each (length, hot_paths1) in region_id's homopath dictionary
            for length, hot_paths1 in c_hot_paths1.items():
                if length > 0:
                    if not hot_paths1:
                        continue  # If no actual homopath data, skip

                    # Compare with another region's homopath data
                    for region_id2, c_hot_paths2 in all_hot_paths.items():
                        # If raw data, intersection of real object sets for threshold ratio
                        # If hashed, we might rely on permutations count for approximate usage
                        if raw_or_hashed == 0:
                            numberOfObjects = len(set(objOfRegion[region_id]).intersection(set(objOfRegion[region_id2])))
                        else:
                            numberOfObjects = num_of_permutations

                        # Initialize dictionary structure if missing
                        if region_id2 not in all_HOMOPATHS:
                            all_HOMOPATHS[region_id2] = {}
                        if region_id2 not in all_HOMOPATHS[region_id]:
                            all_HOMOPATHS[region_id][region_id2] = {}
                        if region_id2 not in all_HOMOPATHS[region_id2]:
                            all_HOMOPATHS[region_id2][region_id2] = {}

                        if region_id2 != region_id:
                            # For each path in region_id2's homopath dictionary
                            for length2, hot_paths2 in c_hot_paths2.items():
                                if length2 > 0:
                                    if not hot_paths2:
                                        continue

                                    # Attempt to link each path from region_id with each from region_id2
                                    for hot_path__1 in hot_paths1:
                                        hot_path1 = tuple(hot_path__1)  
                                        for hot_path2 in hot_paths2:
                                            hot_path_2 = tuple(hot_path2)

                                            # We check if there's a known adjacency between the last node 
                                            # of hot_path1 and the first node of hot_path2 across regions 
                                            # (region_id and region_id2) in all_connections.
                                            for_sure_intersected_objs = []
                                            if (region_id in all_connections 
                                                and region_id2 in all_connections[region_id]
                                                and hot_path1[-1] in all_connections[region_id][region_id2]
                                                and hot_path2[0] in all_connections[region_id][region_id2][hot_path1[-1]]):
                                                
                                                # If the paths are connected across the boundary of region_id -> region_id2,
                                                # we fetch the actual objects for path1
                                                objIDs_ofPath1 = send_request_to_regional_leader(1, region_id, hot_path1)
                                                size = get_size(objIDs_ofPath1)
                                                C2Base_Total_Bytes += calculate_transmission_cost(objIDs_ofPath1)

                                                if raw_or_hashed == 0:
                                                    top_leader_integers_raw += 4
                                                else:
                                                    top_leader_integers_hashed += 4

                                                # Accumulate how many integers are in objIDs_ofPath1
                                                for element in objIDs_ofPath1:
                                                    if raw_or_hashed == 0:
                                                        top_leader_integers_raw += 4
                                                    else:
                                                        top_leader_integers_hashed += 4

                                                intersected_objs = []
                                                edges_to_append = []
                                                not_appendedEdges2 = []
                                                count = 0

                                                # Now we iterate over each edge in path2 to progressively 
                                                # check intersection with the objects from path1.
                                                for edge_of_path2 in hot_path2:
                                                    new_intersected_objs = []
                                                    counter_substraction_path2 = 0

                                                    objIDs_ofEdge2 = send_request_to_regional_leader(2, region_id2, [edge_of_path2])
                                                    size = get_size(objIDs_ofEdge2)
                                                    C2Base_Total_Bytes += calculate_transmission_cost(objIDs_ofEdge2)

                                                    if raw_or_hashed == 0:
                                                        top_leader_integers_raw += 4
                                                    else:
                                                        top_leader_integers_hashed += 4
                                                        
                                                    for element in objIDs_ofEdge2:
                                                        if raw_or_hashed == 0:
                                                            top_leader_integers_raw += 4
                                                        else:
                                                            top_leader_integers_hashed += 4

                                                    # If it's the first edge in path2, we intersect with entire objIDs_ofPath1
                                                    # If not the first edge, we intersect with whatever intersection we had so far.
                                                    if count < 1:
                                                        ObjIDS_Path1 = objIDs_ofPath1
                                                    else:
                                                        ObjIDS_Path1 = intersected_objs

                                                    # Perform intersection between region1's path1 objects 
                                                    # and region2's current edge objects
                                                    for obj_of_path1 in ObjIDS_Path1:
                                                        for obj_of_edge2 in objIDs_ofEdge2:
                                                            if obj_of_path1 == obj_of_edge2:
                                                                new_intersected_objs.append(obj_of_path1)
                                                                intersected_objs = new_intersected_objs
                                                                break

                                                    
                                                    intersection = len(intersected_objs)
                                                    intersectionPercentage = (intersection / numberOfObjects)

                                                    # Decide whether the threshold is met to keep expanding
                                                    if intersectionPercentage >= threshold:
                                                        all_HOMOPATHS[region_id2][region_id2][hot_path_2] = -1
                                                        counter_substraction_path2 += 1
                                                        edges_to_append.append(edge_of_path2)
                                                        for_sure_intersected_objs = intersected_objs

                                                        # If we are at the last edge in path2, 
                                                        # then we have found a "spanning homopath" 
                                                        # that extends from region1 path to region2 path.
                                                        if edge_of_path2 == hot_path2[-1]:
                                                            key_hot_path1 = list(hot_path1) + edges_to_append
                                                            key_hot_path1 = tuple(key_hot_path1)
                                                            if key_hot_path1 not in all_HOMOPATHS[region_id][region_id2]:
                                                                all_HOMOPATHS[region_id][region_id2][key_hot_path1] = {}

                                                            all_HOMOPATHS[region_id][region_id2][key_hot_path1] = for_sure_intersected_objs
                                                            number_of_HoMoPaths += 1
                                                            list_of_span_homopaths.append(key_hot_path1)
                                                            break
                                                        else:
                                                            # If not the last edge, continue to next edge in the path
                                                            count = 1
                                                    else:
                                                        # If threshold is not met, we break out. 
                                                        # But first we might store partial intersection
                                                        # if some edges were valid up until now.
                                                        if for_sure_intersected_objs:
                                                            key_hot_path1 = list(hot_path1) + edges_to_append
                                                            key_hot_path1 = tuple(key_hot_path1)
                                                            if key_hot_path1 not in all_HOMOPATHS[region_id][region_id2]:
                                                                all_HOMOPATHS[region_id][region_id2][key_hot_path1] = {}
                                                            all_HOMOPATHS[region_id][region_id2][key_hot_path1] = for_sure_intersected_objs
                                                            number_of_HoMoPaths += 1
                                                            list_of_span_homopaths.append(key_hot_path1)
                                                        break

                                                # If we appended some edges for path2 but not all:
                                                if edges_to_append:
                                                    for edge_2 in hot_path2:
                                                        if edge_2 not in edges_to_append:
                                                            not_appendedEdges2.append(edge_2)

                                                    if not_appendedEdges2:
                                                        not_appendedEdges_2 = tuple(not_appendedEdges2)
                                                        if not_appendedEdges_2 not in all_HOMOPATHS[region_id2][region_id2]:
                                                            all_HOMOPATHS[region_id2][region_id2][not_appendedEdges_2] = {}
                                                        all_HOMOPATHS[region_id2][region_id2][not_appendedEdges_2] = 0
                                            else:
                                                # If the last node of path1 does not connect to the first node of path2,
                                                # we simply store path1 in region_id's dictionary (no spanning path).
                                                if hot_path1 not in all_HOMOPATHS[region_id][region_id]:
                                                    all_HOMOPATHS[region_id][region_id][hot_path1] = {}
                                                    all_HOMOPATHS[region_id][region_id][hot_path1] = list(hot_path1)

        end_time1 = time.time()  # End of the homopath spanning detection portion

        # total_sum is the sum of all discovered paths in all_HOMOPATHS
        total_sum = 0
        for regions in all_HOMOPATHS.values():
            for paths in regions.values():
                total_sum += len(paths)

        # Write the results to a file for experiments tracking
        write_results_to_file_ResultsOfExperiments(
            "ResultsOfExperiments.txt", number_of_HoMoPaths, total_sum,
            all_HOMOPATHS, end_time1, start_time1, threshold, current_compress)

        # Additional logging
        with open("Current_Experiment_Info.txt", 'a') as fileofexperiments:
            fileofexperiments.write(
                f"TOP LEADER\nSpan-HoMoPaths {number_of_HoMoPaths} , "
                f"Exec Time : {end_time1 - start_time1}\n{all_HOMOPATHS}\n\n\n"
            )

        # (Optional) The code after the triple quotes is commented out but presumably
        # draws or exports graphs if spanning homopaths exist.
        """if number_of_HoMoPaths>0:
            # Read the data file into a DataFrame
            data_file = "1_combined_nodes_edges.txt"
            df = pd.read_csv(data_file, header=None, names=['edge_id', 'node1', 'node2', 'x1', 'y1', 'x2', 'y2'])

            # Create the output directory for the graphs
            output_directory = "MapPictures_Hotmotionpaths_TOP_LEADER"
            #os.makedirs(output_directory)

            # Draw the graphs with the spanning homopaths
            for region_ID, nested_region in all_HOMOPATHS.items():
                if nested_region != region_ID:
                    color_dict = {}
                    for regionId2, paths in nested_region.items():
                        if regionId2 > 0 and regionId2 != region_ID:
                            for pathFull in paths:
                                onlypath = tuple(pathFull)
                                color_dict[onlypath] = {}
                                for edge in pathFull:
                                    for index, row in df.iterrows():
                                        if edge not in color_dict[onlypath]:
                                            color_dict[onlypath][edge] = {}
                                        if row['edge_id'] == edge:
                                            color_dict[onlypath][edge] = [row['node1'], row['node2'], "red"]
                    

                    for onlypath, edge_colors in color_dict.items():
                        G_new = nx.Graph()
                        set_of_nodes = set()
                        
                        for index, row in df.iterrows():
                            G_new.add_node(row['node1'], pos=(row['x1'], row['y1']))
                            G_new.add_node(row['node2'], pos=(row['x2'], row['y2']))
                            
                            edge_id = row['edge_id']
                            nodes_to_remove = (row['node2'], row['node1'])
                            nodes_to_remove2 = tuple(sorted(nodes_to_remove))
                            
                            if edge_id in onlypath:
                                for key2, values2 in edge_colors.items():
                                    if key2 == edge_id:
                                        edge_color = values2[-1]
                                        edge_width = 1.5
                                        set_of_nodes.add(nodes_to_remove2)
                                        
                                        if edge_id == onlypath[0]:
                                            edge_color = "green"
                                            edge_width = 2.5
                                        
                                        if edge_id == onlypath[-1] and len(onlypath) > 1:
                                            edge_color = "blue"
                                        
                                        G_new.add_edge(row['node1'], row['node2'], edge_id=edge_id, color=edge_color, width=edge_width)
                            else:
                                if nodes_to_remove2 not in set_of_nodes:
                                    edge_color = 'black'
                                    edge_width = 0.5
                                    G_new.add_edge(row['node1'], row['node2'], edge_id=edge_id, color=edge_color, width=edge_width)
                        
                        # Draw the graph
                        pos = nx.get_node_attributes(G_new, 'pos')
                        edges = G_new.edges(data=True)  # Get edges as tuples (u, v, data)
                        colors = [data['color'] for u, v, data in edges]
                        widths = [data['width'] for u, v, data in edges]
                        nx.draw_networkx_edges(G_new, pos, edgelist=edges, edge_color=colors, width=widths)
                        
                        # Save the graph as a PNG file in the created directory
                        #plt.savefig(os.path.join(output_directory, f"{onlypath[0]},{onlypath[-1]}.png"))
                        #plt.clf()  # Clear the figure for the next iteration
        """
      

    else:
        # If there is only 1 (or 0) region with homopaths, we cannot form a spanning path across regions
        print("\tTop Leader identified less than 2 Regions with Homopaths, therefore there are no Span-HoMoPaths")
        end_time2 = time.time()
        with open("ResultsOfExperiments.txt", 'a') as fileofexperiments:
            fileofexperiments.write(f"TOP LEADER\nSpan-HoMoPaths : 0\n")
            if all_HOMOPATHS:
                fileofexperiments.write(f"Exec Time : {end_time2 - start_time1}\n")
            fileofexperiments.write(f"#########################################################\n\n\n")

    # Prepare data for output about discovered spanning homopaths
    if 'list_of_span_homopaths' not in locals():
        list_of_span_homopaths = []

    # Format them in bracketed style for one of the experiment logs
    list_strings = ['[' + ','.join(map(str, sublist)) + ']' for sublist in list_of_span_homopaths]
    combinded_list_with_brackets = [
        str(len(totalUniqObjs)), str(threshold), str(total_edges),
        str(num_of_permutations), str(current_compress), str(0)] + list_strings
    line_to_write_with_brackets = ",".join(combinded_list_with_brackets)
    

    with open("seeds.txt", "a") as seedsfile:
        seedsfile.write(str(seed) + ";" + line_to_write_with_brackets + "\n")

    # Here we log more info about costs, including the total bytes at the top leader,
    # plus the first level total integers from region leaders.
    list_strings = ['[' + ','.join(map(str, sublist)) + ']' for sublist in list_of_span_homopaths]
    combinded_list_with_brackets = [
        str(len(totalUniqObjs)), str(C2Base_Total_Bytes), str(first_level_total_integers),
        str(threshold), str(total_edges), str(num_of_permutations), str(current_compress),
        str(0) ] + list_strings
    line_to_write_with_brackets = ",".join(combinded_list_with_brackets)

    with open("Current_Experiment_Top_Leader_Reg_Leader_span_HoMoPaths_costs.txt", "a") as filespanhomopaths:
        filespanhomopaths.write(line_to_write_with_brackets + "\n")

    # Now we compute how many integers were processed by the top leader 
    # (raw vs hashed).
    if raw_or_hashed == 0:
        top_leader_integers = top_leader_integers_raw
    else:
        top_leader_integers = top_leader_integers_hashed

    # Final logging: gather the edges that appear in all hot paths 
    # (for further experiment metrics).
    with open("Current_Experiment_Top_Leader_Reg_Leader_edges_costs.txt", "a") as all_values_file:
        line_values_all_together = [
            str(len(totalUniqObjs)), str(C2Base_Total_Bytes), str(first_level_total_integers),
            str(threshold), str(total_edges), str(num_of_permutations), str(current_compress),
            str(0)]
        dict_values_temp = []

        # Flatten out the nested lists in `all_hot_paths` to find all edges
        for key, value in all_hot_paths.items():
            for sub_values in value.values():
                for item in sub_values:
                    if all(isinstance(i, int) for i in item):
                        dict_values_temp.extend([str(num) for num in item])
                    else:
                        for sublist in item:
                            dict_values_temp.extend([str(num) for num in sublist])

        # Remove duplicates by turning them into a set
        set_items = set(dict_values_temp)
        dict_values_str = "[" + ",".join(set_items) + "]"
        line_values_all_together.append(dict_values_str)
        all_values_line = ",".join(line_values_all_together)

        if not all_values_line.endswith("]"):
            all_values_line += "]"

        all_values_file.write(all_values_line + "\n")


    # After collecting all final data, signal each region that we are done
    for region_id in regions_ready_counter:
        send_request_to_regional_leader("[-1]", region_id, "[-1]")
    # Potentially also signal regions without homopaths if needed
    # for region_id in regions_without_Homopa_counter:
    #     send_request_to_regional_leader("[-1]" , region_id , "[-1]")

    # Final result: number of regions that had homopaths
    result = len(regions_ready_counter)
    # print(f"Number of Regional Leaders with HoMoPaths : {result}")
    result_queue.put(result)  # Put the result in the queue for whoever is listening


# 4.2
def send_request_to_regional_leader(requestPathORedge, region, path_edge_ID):
    """
    This function establishes a socket connection to a given regional leader (identified by 'region'),
    sends a request about a path or edge, or requests specific data (homopath list, number of objects, etc.),
    and then receives and returns the appropriate response.

    :param requestPathORedge:
        - Could be an integer in {1,2,3,4,5} or the string "[-1]".
        - 1 or 2  => requesting either a PATH (1) or an EDGE (2) for a given 'path_edge_ID'
        - 3       => requesting the entire homopaths dictionary (Homopath_list)
        - 4       => requesting the set of unique objects (Homopath_NumberOfObjs)
        - 5       => requesting the total_information_integers for that region
        - "[-1]"  => signals to the region that we want to end communication
    :param region:
        The region ID used to compute the port for that regional leader.
    :param path_edge_ID:
        If (requestPathORedge == 1 or 2), this typically contains the list or single edge ID(s).
        Otherwise, it might be irrelevant or unused for requests 3,4,5.

    :return:
        - Varies depending on the request:
            For requests 1 or 2 (PATH/EDGE), returns a list of object IDs (or None if not found).
            For requests 3,4,5, returns the data relevant to that request (dictionary, string, or integer).
            For "[-1]" or on error, returns None.
    """

    # Construct the port the regional leader is listening on:
    port = region + 5000 + 11
    host = 'localhost'

    # Check that we're not sending a shutdown request ("[-1]"). 
    # If requestPathORedge is 1/2/3/4/5, it means we have valid data to request.
    if (requestPathORedge != "[-1]" 
        and (requestPathORedge == 1 or requestPathORedge == 2 
             or requestPathORedge == 3 or requestPathORedge == 4 
             or requestPathORedge == 5)):

        try:
            # Create a TCP socket and connect to the regional leader's server
            regional_leader_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            regional_leader_socket.connect((host, port))

            # Prepare data to send if we are requesting a path or edge (requests 1 or 2)
            data_to_send = {
                'path_edge_ID': path_edge_ID,
                'requestPathORedge': requestPathORedge
            }
            chunk_size = 1024

            # -------------------------------------------------------------------
            # CASE 1 or 2 => We request a specific path (1) or edge (2)
            # -------------------------------------------------------------------
            if requestPathORedge == 1 or requestPathORedge == 2:
                if requestPathORedge == 1:
                    string = "PRIMARY"
                    edge_path = "path"
                else:
                    string = "SECONDARY"
                    edge_path = "edge"

                # Example print statement for debugging:
                # print(f"Sending {string} request to region {int(region)} on port {port} for {edge_path}: {path_edge_ID}")

                # Serialize our dictionary into a JSON-formatted string
                json_string = json.dumps(data_to_send)

                # Send the JSON data in chunks
                for i in range(0, len(json_string), chunk_size):
                    chunk = json_string[i:i + chunk_size]
                    regional_leader_socket.send(chunk.encode('utf-8'))

                # Signal the end of our transmission with an empty byte string
                regional_leader_socket.send(b"")

                # Now we receive the JSON response from the regional leader in chunks
                received_data = b""
                while True:
                    chunk = regional_leader_socket.recv(1024)
                    if not chunk:
                        # If no more data is coming from the server, break
                        break
                    received_data += chunk

                # Convert the received bytes into a Python object via JSON
                response_data = json.loads(received_data.decode('utf-8'))
                return response_data

            # -------------------------------------------------------------------
            # CASE 3 => Requesting the entire homopaths dictionary (Homopath_list)
            # -------------------------------------------------------------------
            elif requestPathORedge == 3:
                string = "Homopath_list"
                # print(f"Sending {string} request to region {int(region)} on port {port}")
                regional_leader_socket.send(json.dumps(string).encode('utf-8'))

                received_data = ""
                while True:
                    chunk = regional_leader_socket.recv(1024).decode('utf-8')
                    if chunk == "-1":
                        # The region indicates no homopaths exist
                        received_data_chunk_dict = -1
                        break
                    else:
                        if not chunk:
                            # If nothing more is received, break
                            break
                        received_data += chunk

                        # If the data we have so far begins with '{' and ends with '}',
                        # we assume we've got a complete JSON object.
                        if received_data.endswith('}') and received_data.startswith('{'):
                            received_data_chunk_dict = json.loads(received_data)
                            break
                return received_data_chunk_dict

            # -------------------------------------------------------------------
            # CASE 4 => Requesting the set of unique objects (Homopath_NumberOfObjs)
            # -------------------------------------------------------------------
            elif requestPathORedge == 4:
                string = "Homopath_NumberOfObjs"
                # print(f"Sending {string} request to region {int(region)} on port {port}")
                regional_leader_socket.send(json.dumps(string).encode('utf-8'))

                received_data = ""
                while True:
                    chunk = regional_leader_socket.recv(1024).decode('utf-8')
                    if not chunk:
                        break
                    received_data += chunk

                # We return the raw string (which might look like "[obj1, obj2, ...]")
                return received_data

            # -------------------------------------------------------------------
            # CASE 5 => Requesting the total_information_integers
            # -------------------------------------------------------------------
            elif requestPathORedge == 5:
                string = "total_information_integers"
                # print(f"Sending {string} request to region {int(region)} on port {port}")
                regional_leader_socket.send(json.dumps(string).encode('utf-8'))

                received_data = ""
                while True:
                    chunk = regional_leader_socket.recv(1024).decode('utf-8')
                    if not chunk:
                        break
                    received_data += chunk

                # Convert the received string into an integer before returning
                received_integer = int(received_data)
                return received_integer

        except Exception as e:
            # If any error occurs, we catch it and return None
            # print(f"Error: {e}")
            return None

        finally:
            # Always close the socket in a finally block
            regional_leader_socket.close()

    else:
        # -----------------------------------------------------------------------
        # If requestPathORedge == "[-1]" => Top Leader is signaling 'FINISH'
        # -----------------------------------------------------------------------
        # print(f"Top Leader signal-FINISH to {port}")
        regional_leader_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        regional_leader_socket.connect((host, port))
        # Send the "[-1]" shutdown command
        regional_leader_socket.send(json.dumps("[-1]").encode('utf-8'))
        regional_leader_socket.close()
        return None


##########   regional leader   ##########
# 4.3
def start_regional_leader(region_ID, threshold, ready_event, raw_or_hashed, 
                          permutations, current_compress, length_of_permutations, 
                          help_for_jaccard, limitN):
    """
    Function that initializes a single Regional Leader's logic:
      1. Loads the local graph from a file (map{region_ID}.txt).
      2. Runs a 'process_region' function to discover local homopaths, collect unique objects, etc.
      3. Sets up a TCP server socket to communicate with the Top Leader:
         - Responds to requests for homopath data, unique objects, or total sensor data.
         - Waits until the Top Leader sends "[-1]" to indicate it can shut down.
      4. Signals to the Top Leader (via shared global counters + condition variable) that this region is ready or has no homopaths.
      5. Exits upon receiving a "close" command from the Top Leader.
    """

    # Acquire a global lock to ensure no conflicts with shared data structures
    with function_lock:
        # Global shared structures for multi-thread/ multi-region coordination
        global regions_ready_counter
        global regions_without_Homopa_counter
        global all_regions_counter

        # The local text file that describes this region's sub-graph, presumably in the format:
        # [edge_id, node1, node2, x1, y1, x2, y2]
        picturePath = f"map{region_ID}.txt"
        print(f"\tThread for RegionalLeaderID = {region_ID} , just started !")

        # Read the edges from the CSV (or TXT) file into a DataFrame
        df = pd.read_csv(picturePath, header=None, 
                         names=['edge_id', 'node1', 'node2', 'x1', 'y1', 'x2', 'y2'])

        # Create a graph (NetworkX) for visualization or local computations
        G = nx.Graph()

        # Populate the graph with nodes and edges
        for _, row in df.iterrows():
            G.add_node(row['node1'], pos=(row['x1'], row['y1']))
            G.add_node(row['node2'], pos=(row['x2'], row['y2']))
            edge_id = row['edge_id']
            # Set 'edge_id' as an attribute on the edge
            G.add_edge(row['node1'], row['node2'], edge_id=edge_id)

        # Retrieve node positions from the graph
        pos_removed = nx.get_node_attributes(G, 'pos')

        # Create a new plot, draw edges, and save the figure
        plt.figure(figsize=(10, 10))
        nx.draw_networkx_edges(G, pos_removed, width=2, edge_color='black')
        output_file_path = f"depth_{region_ID}.png"
        plt.savefig(output_file_path)
        # plt.show() or plt.close() can be used if needed

        # Now, process the region to discover local homopaths, unique objects, etc.
        # This function presumably does all the heavy-lifting of scanning edges, 
        # checking data from sensors, etc.
        regions_hot_paths, Uniqueobjs, only_Homopa_RAW_HASHED, transmission_cost, total_information_integers = (
            process_region(
                region_ID, threshold, raw_or_hashed, permutations, current_compress,
                length_of_permutations, help_for_jaccard, limitN
            )
        )

        # The 'regions_hot_paths' is a dictionary storing discovered homopaths by path length,
        # 'Uniqueobjs' is a set (or list) of the unique objects seen in this region,
        # 'only_Homopa_RAW_HASHED' might indicate whether the homopath data is raw or hashed,
        # 'transmission_cost' could track cost metrics, 
        # and 'total_information_integers' is the total number of sensor integers for this region.

        ########################################################################
        # (Optional) Visualization of discovered homopaths
        # The following code is commented out in your snippet, but it demonstrates
        # how you might color and save each local homopath path as an image.
        #
        # if regions_hot_paths:
        #     color_dict = {}
        #     for length, paths in regions_hot_paths.items():
        #         if length > 0:
        #             for path in paths:
        #                 onlypath = tuple(path[0])
        #                 color_dict[onlypath] = {}
        #                 # ...
        #     # Then you create a new Graph, highlight edges, save as PNG, etc.

        """ if regions_hot_paths:
            color_dict = {}
            for length, paths in regions_hot_paths.items():
                if length > 0:
                    for pathFull in paths:
                        onlypath = tuple(pathFull[0])
                        color_dict[onlypath]= {}
                        for edge in pathFull[0]:
                            for index, row in df.iterrows():
                                if edge not in color_dict[onlypath]:
                                    color_dict[onlypath][edge]= {}
                                if row['edge_id'] == edge:                     
                                    color_dict[onlypath][edge] = [row['node1'], row['node2'], "red"]
   
            directory_path = f"MapPictures_Hotmotionpaths{region_ID}"           # Path for the directory
            os.makedirs(directory_path)                                  # Create the directory


            for onlypath, edge_colors in color_dict.items():
                G_new = nx.Graph()
                setofnodes = set()
                # Iterate through the DataFrame rows
                for index, row in df.iterrows():
                    G_new.add_node(row['node1'], pos=(row['x1'], row['y1']))
                    G_new.add_node(row['node2'], pos=(row['x2'], row['y2']))
                    edge_id = row['edge_id']
                    nodes_to_remove = (row['node2'], row['node1'])
                    nodes_to_remove2 =tuple(sorted(nodes_to_remove))
                
                    if edge_id in onlypath:
                        for key2,values2 in edge_colors.items():
                            if key2 == edge_id:
                                edge_color = values2[-1]
                                edge_width = 1.5
                                setofnodes.add(nodes_to_remove2)
                                if edge_id == onlypath[0]:
                                    edge_color = "green"
                                    edge_width = 5
                                if edge_id == onlypath[-1] and len(onlypath)>1:
                                    edge_color = "blue"
                                G_new.add_edge(row['node1'], row['node2'], edge_id=edge_id, color=edge_color, width=edge_width)       
                    else:
                        if nodes_to_remove2 not in setofnodes:
                            edge_color = 'black'
                            edge_width = 4
                            G_new.add_edge(row['node1'], row['node2'], edge_id=edge_id, color=edge_color, width=edge_width)

                    

            # Draw the graph
                pos = nx.get_node_attributes(G_new, 'pos')
                edges = G_new.edges(data=True)  # Get edges as tuples (u, v, data)
                colors = [data['color'] for u, v, data in edges]
                widths = [data['width'] for u, v, data in edges]
                nx.draw_networkx_edges(G_new, pos, edgelist=edges, edge_color=colors, width=widths)
                # Save the graph as a PNG file in the created directory
                plt.savefig(os.path.join(directory_path, f"{region_ID}_{onlypath}.png"))
                plt.clf()  # Clear the figure for the next iteration"""

        ########################################################################

        # Next, we set up a TCP server socket, so the Top Leader can connect to 
        # this regional leader and request data (homopaths, object sets, etc.).
        regional_port = int(region_ID + 11) + 5000  # Example port assignment
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('localhost', regional_port))
        server_socket.listen(1)

        # Notify the Top Leader (via shared counters + condition variable) 
        # whether this region has found homopaths or not
        with all_regions_ready_condition:
            if regions_hot_paths:
                # We found at least one homopath, so mark this region as 'ready'
                regions_ready_counter.append(region_ID)
                all_regions_counter.append(region_ID)
                print(f"\tRegional Leader {region_ID} is ready and Top Leader is aware. Top Leader's Counter is updated: {regions_ready_counter}")
            else:
                # No homopath found here
                regions_without_Homopa_counter.append(region_ID)
                all_regions_counter.append(region_ID)
                print(f"No Homopaths from {region_ID}")

            # Notify all waiting threads (e.g., Top Leader) that we've updated counters
            all_regions_ready_condition.notify_all()

        # Also let the calling thread or external manager know we are 'up and running'
        ready_event.set()

    # Outside the 'function_lock', we enter an infinite loop to handle incoming requests
    # from the Top Leader until it signals a shutdown via "[-1]"
    while True:
        # Accept a single client connection (the Top Leader typically)
        client_socket, client_address = server_socket.accept()

        # Receive data in small chunks. Data is expected to be JSON-encoded.
        data = client_socket.recv(1024).decode('utf-8')
        received_data_check = json.loads(data)

        # If the Top Leader sends "[-1]", it indicates we should shut down
        if received_data_check == "[-1]":
            server_socket.close()
            #print("3. From Reg Leader/Thread To EXIT")
            break

        elif (received_data_check == "Homopath_list" or 
              received_data_check == "Homopath_NumberOfObjs" or
              received_data_check == "total_information_integers"):
            # The Top Leader is requesting some specific piece of data.

            if regions_hot_paths:
                # We have homopaths in this region
                if received_data_check == "Homopath_list":
                    # The Top Leader wants the dictionary of homopaths.
                    # We convert 'regions_hot_paths' into a JSON string,
                    # but note that each path is itself a list-of-lists, 
                    # so we grab just the first sub-list (path[0]) for each path entry.
                    serialized_data = json.dumps({
                        key: [path[0] for path in paths] 
                        for key, paths in regions_hot_paths.items()
                    })
                    # Send the data in chunks of size=1024 bytes
                    chunk_size = 1024
                    for i in range(0, len(serialized_data), chunk_size):
                        chunk = serialized_data[i:i + chunk_size]
                        client_socket.send(chunk.encode('utf-8'))

                elif received_data_check == "total_information_integers":
                    # The Top Leader wants the total sensor data integer count
                    # that we discovered in this region
                    chunk = str(total_information_integers)
                    client_socket.send(chunk.encode('utf-8'))

                else:
                    # "Homopath_NumberOfObjs" means the Top Leader wants 
                    # the unique objects from this region
                    set_str = str(Uniqueobjs)
                    chunk_size = 1024
                    for i in range(0, len(set_str), chunk_size):
                        chunk = set_str[i:i + chunk_size]
                        client_socket.send(chunk.encode('utf-8'))
                    # print(f"uniq objs : {chunk}")  # For debugging if needed
                    # x = input()
            else:
                # If no homopaths exist in this region
                if received_data_check == "Homopath_NumberOfObjs":
                    # The Top Leader only wants the unique objects (no homopaths here).
                    set_str = str(Uniqueobjs)
                    chunk_size = 1024
                    for i in range(0, len(set_str), chunk_size):
                        chunk = set_str[i:i + chunk_size]
                        client_socket.send(chunk.encode('utf-8'))
                else:
                    # Otherwise, respond with -1 to indicate 
                    # we do not have requested homopath data
                    chunk = "-1"
                    client_socket.send(chunk.encode('utf-8'))

        else:
            # Here, the Top Leader might be requesting specific path or edge data
            # for intersection checks or for verification of objects within a path.
            edge_path_id = data

            # Receive until we see a "}" indicating the JSON object ended
            while data.endswith("}") is False:
                data = client_socket.recv(1024).decode('utf-8')
                edge_path_id += data

            # Parse the final JSON object
            path_edge_ID = received_data_check['path_edge_ID']
            requestPathORedge = received_data_check['requestPathORedge']

            # This custom function will locate object IDs for either a path or an edge
            # within this region's discovered homopaths.
            obj_ids = find_obj_ids_for_edge_path(requestPathORedge, path_edge_ID, regions_hot_paths)

            # Convert to string and send back to the Top Leader
            client_socket.send(str(obj_ids).encode('utf-8'))

        client_socket.close()

    # Close the server socket after breaking from loop (shutdown command received)
    server_socket.close()


# 4.4
def process_region(region_ID, threshold, raw_or_hashed, permutations,
                   current_compress, length_of_permutations, help_for_jaccard, limitN):
    """
    This function is responsible for:
      1. Determining which sensor data file and edgeconnections file to load (based on region_ID and raw_or_hashed).
      2. Checking if the necessary files exist (sensors and edgeconnections).
      3. If they do, calling the HOMOPA(...) function to discover local homopaths, collect unique objects, etc.
      4. Logging various results (homopath dictionaries, unique objects, etc.) into different output files for offline or debugging use.
      5. Returning the processed information (homopath dictionary, unique object set, cost metrics, etc.).
    """

    # Decide which sensors file to read based on raw_or_hashed
    # If raw (0), we read "Regional_4_sensors{region_ID}.txt"
    # If hashed (1), we read "Regional_4_sensors_HASHED{region_ID}.txt"
    if raw_or_hashed == 0:
        sensors_file = f"Regional_4_sensors{region_ID}.txt"
        stringHashed = ""
    else:
        sensors_file = f"Regional_4_sensors_HASHED{region_ID}.txt"
        stringHashed = "_HASHED_"

    # Corresponding edge connections file for this region
    edgeconnections_file = f"Regional_2_edgeconnections{region_ID}.txt"

    # Optional debugging print for region_ID=10
    #if region_ID == 10:
        #print(f"In process_region {region_ID}")
        # print(sensors_file, edgeconnections_file)

    # Verify that both files exist before proceeding
    if os.path.exists(edgeconnections_file) and os.path.exists(sensors_file):
        # Start timing the homopath discovery process
        start_time1 = time.time()

        # Initialize dictionaries to keep track of homopath data (raw or hashed)
        only_Homopa_RAW_HASHED = {}
        only_Homopa_HASHED = {}

        # The HOMOPA(...) function presumably:
        #  - Loads and processes the edge connections and sensor data
        #  - Discovers homopaths meeting the given threshold
        #  - Returns stats such as number of unique objects, number of edges, etc.
        #  - Also returns a dictionary of found homopaths by path length
        UniqObjs, NumOfObjs, NumOfEdges, HoMoPaths_Dictionary, total_bytes, \
        transmission_cost, total_information_integers = HOMOPA(
            region_ID, current_compress, raw_or_hashed, permutations, edgeconnections_file, 
            sensors_file, threshold, length_of_permutations, help_for_jaccard, limitN )

        end_time1 = time.time()
        time1 = end_time1 - start_time1  # Compute total time taken

        # Handle edge or object counts that might be empty/None
        if not NumOfEdges:
            NumOfEdges = 0
        if not NumOfObjs or NumOfObjs == 0:
            NumOfObjs = -1

        # Count how many homopaths exist in total by summing counts across keys
        count_dict = {}
        Number_of_Homopaths = 0
        for key, value in HoMoPaths_Dictionary.items():
            count = len(value)  # number of homopaths under each 'length' key
            Number_of_Homopaths += count
            count_dict[key] = count

        # If the dictionary has found homopaths
        if HoMoPaths_Dictionary:
            # Write basic experiment info to "ResultsOfExperiments.txt"
            with open("ResultsOfExperiments.txt", 'a') as fileofexperiments:
                threshold_comparison = raw_or_hashed + 1

                # 'formatted_paths_all': a single string combining path edges in 
                # Homopaths except for the index=0 category if that is single-edge
                formatted_paths_all = ','.join([
                    '[{}]'.format(','.join(map(str, sub_paths_list[0])))
                    for index, complete_data in enumerate(HoMoPaths_Dictionary.values())
                    if index > 0  # skipping the index=0 group if desired
                    for sub_paths_list in complete_data
                ])

                # Similarly, but skip index <= 1 if we don't want single-edge or double-edge
                formatted_paths_allwithout_single = ','.join([
                    '[{}]'.format(','.join(map(str, sub_paths_list[0])))
                    for index, complete_data in enumerate(HoMoPaths_Dictionary.values())
                    if index > 1
                    for sub_paths_list in complete_data
                ])

                # We parse the 'formatted_paths_all' string to a list-of-lists of integers
                list_strings2_all = formatted_paths_all.strip('][').split('],[')
                formatted_list_all = [
                    [int(num) for num in sublist.split(',')]
                    for sublist in list_strings2_all
                    if sublist.strip() != ''
                ]

                # Maintain a dictionary storing either raw or hashed homopath data for this region
                if raw_or_hashed == 0:  # RAW
                    if region_ID not in only_Homopa_RAW_HASHED:
                        only_Homopa_RAW_HASHED[region_ID] = formatted_list_all
                else:  # HASHED
                    if region_ID not in only_Homopa_RAW_HASHED:
                        only_Homopa_RAW_HASHED[region_ID] = formatted_list_all

                # Write a small separator to the file
                fileofexperiments.write("\n--------------------------------------------------------\n")

            # Log more details about discovered paths in these additional files:
            with open("Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_all.txt", 'a') as fileofexperiments:
                # If we have any paths, log them, else log [0]
                if len(formatted_paths_all) > 0:
                    fileofexperiments.write(
                        f"{NumOfObjs},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},{formatted_paths_all}\n"
                    )
                else:
                    fileofexperiments.write(
                        f"{NumOfObjs},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},[0]\n"
                    )

            # Similar logging, but also includes transmission cost and total_bytes
            with open("Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_all_with_costs.txt", 'a') as fileofexperiments_withcosts:
                if len(formatted_paths_all) > 0:
                    fileofexperiments_withcosts.write(
                        f"{total_bytes},{transmission_cost},{NumOfObjs},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},{formatted_paths_all}\n"
                    )
                else:
                    fileofexperiments_withcosts.write(
                        f"{total_bytes},{transmission_cost},{NumOfObjs},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},[0]\n"
                    )

            # Also log paths excluding single-edge or double-edge (if index <=1)
            with open("Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_allwithout_single.txt", 'a') as fileofexperiments:
                if len(formatted_paths_allwithout_single) > 0:
                    fileofexperiments.write(
                        f"{NumOfObjs},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},{formatted_paths_allwithout_single}\n"
                    )
                else:
                    fileofexperiments.write(
                        f"{NumOfObjs},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},[0]\n"
                    )

            # Log additional info to a central file
            with open("Current_Experiment_Info.txt", 'a') as fileofexperiments:
                ratio_objs_edges = NumOfObjs / NumOfEdges if NumOfEdges != 0 else 0
                fileofexperiments.write(f"4_1. {NumOfEdges},{NumOfObjs},{ratio_objs_edges},{threshold}\n{HoMoPaths_Dictionary}\n")

        

    # Return the key data structures we created or computed:
    #   - HoMoPaths_Dictionary: dict of discovered homopaths by path length
    #   - UniqObjs: set or list of unique objects in this region
    #   - only_Homopa_RAW_HASHED: dict capturing either raw or hashed paths
    #   - transmission_cost: cost/bytes used in data transmissions
    #   - total_information_integers: total sensor integers read for this region
    return (
        HoMoPaths_Dictionary,
        UniqObjs,
        only_Homopa_RAW_HASHED,
        transmission_cost,
        total_information_integers
    )


# 4.5
def find_obj_ids_for_edge_path(requestPathORedge, request, region_hot_paths):
    """
    Looks up the object IDs associated with either:
      - A requested path (if requestPathORedge == 1)
      - A requested edge (if requestPathORedge == 2)

    :param requestPathORedge: 
        An integer flag indicating whether the request is for a path (1) or for an edge (2).
    :param request: 
        A list (for a path request) or a single item (for an edge request) 
        that we want to match within the stored homopaths.
    :param region_hot_paths: 
        A dictionary where keys are "path lengths" (e.g., 0 for edges, 1 for single-edge paths, 2 for multi-edge paths, etc.),
        and values are lists of homopath records. Each homopath record is typically a two-element list:
            [list_of_edges_or_edge, list_of_object_ids].
        Example:
            region_hot_paths = {
                0: [ [ [edge_id], objectIDs ], ...], 
                2: [ [ [edge_id1, edge_id2], objectIDs ], ...],
                3: [ [ [edge_id1, edge_id2, edge_id3], objectIDs ], ...],
                ...
            }

    :return:
        The matching list of object IDs if found, or None if no match exists.
    """

    # Iterate through each "path length" key and its list of homopaths
    for len_hot_paths1, hotpaths in region_hot_paths.items():

        # Decide whether we are looking for a path or an edge:
        #   - requestPathORedge == 1 => Looking for a PATH whose length matches len(request).
        #   - requestPathORedge == 2 => Looking for an EDGE, which we assume is stored under len_hot_paths1 == 0.
        if ((requestPathORedge == 1 and (len(request) == len_hot_paths1))
            or (requestPathORedge == 2 and (len_hot_paths1 == 0))):

            # Within this list of homopaths, each homopath is something like:
            #   hot_path1 = [ [edge(s)], [objectIDs] ]
            # where hot_path1[0] is the list of edge IDs or a single edge,
            # and hot_path1[1] is the set/list of objects.
            for hot_path1 in hotpaths:
                # If the edges match our 'request', return the associated object IDs
                if hot_path1[0] == request:
                    return hot_path1[1]

    # If no matching path/edge was found, Python implicitly returns None.
    return None




#############################################################
#--------------------------------------------- #
#              Calculating Homopaths
# hash_function: here ...............


# 5.1
def HOMOPA(region_ID, current_compress, raw_or_hashed, permutations,
           File_2_edgeconnections, sensors_file_path, threshold,
           length_of_permutations, help_for_jaccard, limitN):
    """
    Main function for discovering and returning homopaths in a specific region.

    :param region_ID:
        The identifier for this region/leader (e.g., 10, 11, etc.).
    :param current_compress:
        Parameter controlling how compressed data might be (not fully shown here).
    :param raw_or_hashed:
        0 => raw data, 1 => hashed data.
    :param permutations:
        Number of permutations used for minhashing when raw_or_hashed == 1,
        or a control value for raw data if raw_or_hashed == 0.
    :param File_2_edgeconnections:
        Path to the file describing edge connections in this region (e.g., "Regional_2_edgeconnections10.txt").
        The file typically has rows of the form:
            edge_id, connected_node_1, connected_node_2, ...
    :param sensors_file_path:
        Path to the file containing sensor data for this region (e.g., "Regional_4_sensors10.txt").
        The sensor data is used to build a structure that associates edges with object IDs.
    :param threshold:
        A threshold for intersection similarity, used in discovering homopaths.
    :param length_of_permutations:
        Additional parameter that might limit or specify how permutations are processed (not fully shown here).
    :param help_for_jaccard:
        Parameter indicating whether to use Jaccard or other similarity help in intersection checks.
    :param limitN:
        A limiting value for the maximum number of edges, objects, or some other bounding variable.

    :return:
        A tuple:
        (
            UniqObjs,                # Set or list of unique objects found across edges
            NumOfObjs,               # Total number of objects discovered or estimated
            NumOfEdges,              # Number of edges in this region
            HoMoPaths_Dictionary,    # Dictionary of discovered homopaths: { path_length: [ [ [edge], [objectIDs] ], ... ] }
            total_information_bytes, # Approximation of the byte-size of sensor info
            total_costs,             # Additional cost metric (likely for transmissions or computations)
            total_information_integers # The total raw integer count from sensors
        )
    """


    # -------------------------------------------------------------------------
    # 1) Read the region's edge connections (IDs and adjacency info) from a file
    # -------------------------------------------------------------------------
    edge_connections, NumOfEdges = Dict_Read_Edge_Connections_from_File(File_2_edgeconnections)

    # -------------------------------------------------------------------------
    # 2) Prepare data from the sensor file: 
    #    This builds a structure associating each edge with its set of objects.
    # -------------------------------------------------------------------------
    objs_in_edge, UniqObjs, NumOfObjs, total_information_bytes, \
    total_costs, total_information_integers = prepare_data_from_file(sensors_file_path)

    # For debug: 
    # print(f"-------------- For Region {region_ID}: total_information_integers = {total_information_integers}")

    # -------------------------------------------------------------------------
    # 3) If hashed data, compute the estimated number of objects using Cohen
    #    (i.e., applying minhash-based cardinality estimation).
    # -------------------------------------------------------------------------
    if raw_or_hashed == 1:
        # remove_extra_Integ = 0 => means data might be in the form [ [edge_id], number_of_Raw_ObjIDs, minhash_signature ]
        remove_extra_Integ = 0
        NumOfObjs = _Find_Cardinality_Cohen(objs_in_edge, permutations, remove_extra_Integ)
        #print(f" *** G-LESE (Cohen's Approach) estimated in Region {region_ID} , number of Objects = {NumOfObjs} *** ")

    # For debug:
    # print(f"raw_or_hashed={raw_or_hashed}, NumOfObjs={NumOfObjs}")

    # -------------------------------------------------------------------------
    # 4) Format the set of edge IDs (objs_in_edge is typically a list of items 
    #    where item[0][0] is the edge ID).
    #    This is primarily for logging or debugging.
    # -------------------------------------------------------------------------
    formatted_paths0 = set()
    for data in objs_in_edge:
        formatted_paths0.add(data[0][0])  # data[0] is [edge_id], so data[0][0] is edge_id

    formatted_paths = ','.join([f'[{item}]' for item in formatted_paths0])
    # e.g., "[101],[102],[115]" for edges 101,102,115

    # -------------------------------------------------------------------------
    # 5) Calculate homopaths by intersecting the object sets between edges 
    #    (and potentially chaining edges that meet threshold criteria).
    # -------------------------------------------------------------------------
    n = 1  # Possibly a parameter for recursion depth or chaining length
    HoMoPaths_Dictionary = calculate_obj_id_intersection(
        region_ID,
        raw_or_hashed,
        permutations,
        edge_connections,
        objs_in_edge,
        objs_in_edge,
        NumOfObjs,
        threshold,
        n,
        length_of_permutations,
        help_for_jaccard,
        NumOfEdges,
        limitN
    )

    # Return the key information discovered in this function
    return (UniqObjs, 
            NumOfObjs, 
            NumOfEdges, 
            HoMoPaths_Dictionary, 
            total_information_bytes, 
            total_costs, 
            total_information_integers)


# 5.2
def Dict_Read_Edge_Connections_from_File(file_path):
    """
    Reads a file that describes edges in the form:
        edge_id, connected_node1, connected_node2, ...
    and constructs a dictionary where each key is an edge ID and 
    the value is the list of connected nodes (or other IDs) for that edge.

    :param file_path:
        The path to the file containing edge connections.
        Example:
          100, 23, 24
          101, 25, 26
          ...
        Means edge 100 connects nodes (23, 24), edge 101 connects nodes (25, 26), etc.

    :return:
        A tuple: (Connections_Dict, number_of_edges)
          Connections_Dict => { 100: [23, 24], 101: [25, 26], ... }
          number_of_edges  => length of that dictionary (i.e., how many edges).
    """

    Connections_Dict = {}

    # Read the file line by line
    with open(file_path, 'r') as file:
        for line in file:
            # Each line is comma-separated integers
            values = list(map(int, line.strip().split(',')))
            key = values[0]     # The first integer is the edge ID
            Connections_Dict[key] = values[1:]  # The remainder are connected nodes or endpoints

    return Connections_Dict, len(Connections_Dict)



# 5.3
def prepare_data_from_file(sensors_file_path):
    """
    Reads sensor data from a file and constructs a list associating edges 
    with their object sets (raw or hashed), while also computing totals for 
    unique objects, information in bytes, and cost metrics.

    NOTE: This function references 'raw_or_hashed' as if it were a global 
          variable or defined elsewhere in the code. It determines how to 
          parse the file lines.

    :param sensors_file_path:
        The path to the file containing sensor data. 
        Each line typically follows one of two formats:
            If raw_or_hashed == 0:
                edge_id, obj_id_1, obj_id_2, ..., obj_id_n
            If raw_or_hashed == 1:
                edge_id, number_of_Raw_ObjIDs, hashed_obj_1, hashed_obj_2, ...
    :return:
        A tuple:
         ( combined_data,         # A list of structures describing each edge and its object IDs
           UniqObjs,              # A set of unique objects (raw or hashed) across all edges
           len(UniqObjs),         # The total count of unique objects
           total_information_bytes, # The total size in bytes (4 * number_of_integers_parsed)
           total_costs,           # A scaled cost metric (total_information_bytes * single_cost)
           total_information_integers ) # The total integer count processed
    """

    combined_data = []           # Will hold parsed data for each sensor line
    UniqObjs = set()            # Set of all distinct objects encountered
    UniqEdges = set()           # (Optional) Set of distinct edge IDs
    total_information_integers = 0  # Running total of integers parsed from file

    with open(sensors_file_path, 'r') as file:
        for line in file:
            # 'topic_information_integers' counts the number of integers in the current line
            topic_information_integers = 0

            # Split the line by commas
            parts = line.strip().split(',')

            # We assume 'raw_or_hashed' is defined globally or elsewhere
            if raw_or_hashed == 0:
                # Format: edge_id, obj_id_1, obj_id_2, ...
                edge_id = int(parts[0])
                topic_information_integers += 1
                UniqEdges.add(edge_id)

                # The rest are object IDs
                obj_ids = list(set(map(int, parts[1:])))  # Convert to int and remove duplicates
                for obj in obj_ids:
                    UniqObjs.add(obj)
                    topic_information_integers += 1

                # combined_data entry => [ [edge_id], [obj1, obj2, ...] ]
                combined_data.append([[edge_id], obj_ids])

            else:
                # raw_or_hashed == 1, meaning the file lines include a 'number_of_Raw_ObjIDs' 
                # plus hashed objects.
                hashed_objs = []
                edge_id = int(parts[0])
                topic_information_integers += 1

                number_of_Raw_ObjIDs = int(parts[1])
                topic_information_integers += 1

                UniqEdges.add(edge_id)

                # The remainder are hashed object IDs
                obj_ids = list(map(int, parts[2:]))
                for obj in obj_ids:
                    UniqObjs.add(obj)
                    hashed_objs.append(obj)
                    topic_information_integers += 1

                # combined_data entry => [ [edge_id], number_of_Raw_ObjIDs, [hashed_obj1, hashed_obj2, ...] ]
                combined_data.append([[edge_id], number_of_Raw_ObjIDs, obj_ids])

            # Update the global count of integers processed
            total_information_integers += topic_information_integers

            # Compute total size in bytes: 4 bytes per integer
            total_information_bytes = 4 * total_information_integers

            # Compute a "cost" metric using some per-byte cost factor (single_cost = 0.0001)
            single_cost = 0.0001
            total_costs = round((total_information_bytes * single_cost), 4)

    # Debug (optional):
    # print(f"Total unique objects: {len(UniqObjs)}")
    # print(f"Total sensor lines: {len(combined_data)}")
    # print(f"Total information integers: {total_information_integers}")

    return (combined_data, 
            UniqObjs, 
            len(UniqObjs), 
            total_information_bytes, 
            total_costs, 
            total_information_integers)



# 5.4
def calculate_obj_id_intersection(
    region_ID,
    raw_or_hashed,
    permutations,
    edge_connections,
    objs_in_edge,
    Single_Frequent_objs_in_edge,
    total_obj_count,
    threshold,
    n,
    length_of_permutations,
    help_for_jaccard,
    NumOfEdges,
    limit,
    HoMoPaths_Dictionary=None
):
    """
    Recursively discovers homopaths (i.e., chains of edges that meet a threshold 
    for object intersection) within a region.

    Key Points / Parameters:
    ------------------------
    :param region_ID:
        Unique identifier for this region. Used in debugging/logging (e.g., writing to files).
    :param raw_or_hashed:
        0 => "raw" object data is used (intersection ratio = intersection_of_objs / total_obj_count).
        1 => "hashed" data is used (intersection ratio uses minhash, e.g., intersection_of_objs / permutations).
    :param permutations:
        Number of minhash permutations if raw_or_hashed == 1. 
        If raw_or_hashed == 0, often not used for intersection ratio 
        (but still passed around for consistency).
    :param edge_connections:
        A dictionary that maps an edge_id to the list of neighboring edges or nodes it connects to.
        Example: { 100: [101, 110], 101: [100, 102], ... }
    :param objs_in_edge:
        The "vertical" axis set of edges (potentially already discovered in a previous round).
        Typically each element is of the form:
          - raw:   [[edge_id], list_of_objectIDs]
          - hashed: 
              if n==1 => [[edge_id], number_of_Raw_ObjIDs, list_of_hashed_objIDs]
              if n>1  => [[edge_id], list_of_hashed_objIDs]
    :param Single_Frequent_objs_in_edge:
        The "horizontal" axis for single frequent edges, used mainly in early phases 
        to compare or combine with existing paths. Often similar structure to objs_in_edge.
    :param total_obj_count:
        The total number of objects in the entire region (raw) OR an approximation 
        for hashed data. If raw_or_hashed == 1 and we're matching edges, 
        sometimes we use permutations as the denominator for the intersection ratio 
        instead of total_obj_count.
    :param threshold:
        Intersection threshold. 
        For raw => (intersection_of_objs / total_obj_count) >= threshold 
        For hashed => (intersection_of_objs / permutations) >= threshold 
        or similar logic.
    :param n:
        The current path length under consideration. 
        n=1 => single edges (homoedges). 
        n=2 => pairs of edges, 
        etc. 
        This increments recursively.
    :param length_of_permutations:
        Additional parameter potentially used for advanced logic, not fully demonstrated here.
    :param help_for_jaccard:
        Debug / special flag. If == 1, the function may read/write JSON files to check raw/hashing consistency.
    :param NumOfEdges:
        The total number of edges in the region (used in logs or thresholds).
    :param limit:
        A maximum recursion depth for how far we want to chain edges (avoid infinite recursion).
    :param HoMoPaths_Dictionary:
        A dictionary storing discovered paths keyed by path length:
           { 0: [ [[edge_id], [objects]], ... ],
             1: [ [[edge_id], [objects]], ... ],
             2: [ [[[edge1, edge2]], [objects_intersection]], ... ],
             ...
           }
        If None, we initialize it in this function.

    Returns:
    --------
    HoMoPaths_Dictionary:
        The updated dictionary that includes all discovered homopaths up to path length n.
    """

    # -------------------------------------------------------------------------
    # 1) Initialize the dictionary that will store discovered homopaths if none is provided.
    # -------------------------------------------------------------------------
    if HoMoPaths_Dictionary is None:
        HoMoPaths_Dictionary = {}

    # Boolean_HoMoPathway_Matrix will be our 2D "table" to mark intersections >= threshold.
    Boolean_HoMoPathway_Matrix = []

    # edge_connections_for_next_Lenght accumulates the edges that remain relevant for the
    # next recursion level (n+1).
    edge_connections_for_next_Lenght = {}

    # Edge_Object_Mapping will store newly discovered (path, object_set) pairs in this recursion step.
    # Edge_Object_Mapping_Single_Freq_Edges is the single-edge frequent edges (from n=1).
    Edge_Object_Mapping = []
    Edge_Object_Mapping_Single_Freq_Edges = []

    # obj_ids_on_edge: dictionary mapping 'edge_id' => [objIDs]
    # This helps quick lookup for each edge's object set.
    obj_ids_on_edge = {}
    for edge_data in objs_in_edge:
        edge_id = tuple(edge_data[0])  # We treat [edge_id] as a tuple for dict key
        if raw_or_hashed == 0:
            # raw => second element is the list of object IDs
            obj_ids = edge_data[1]
        else:
            # hashed => structure depends on n
            #   if n == 1 => [ [edge_id], number_of_Raw_ObjIDs, [hashed_objs] ]
            #   if n > 1  => [ [edge_id], [hashed_objs] ]
            if n == 1:
                num_real_obj_ids = edge_data[1]  # not used for intersection, but stored
                obj_ids = edge_data[2]
            else:
                obj_ids = edge_data[1]
        obj_ids_on_edge[edge_id] = obj_ids

    # obj_ids_on_edge_SingleFrequent: similar dictionary for the Single_Frequent_objs_in_edge list
    obj_ids_on_edge_SingleFrequent = {}
    for edge_data in Single_Frequent_objs_in_edge:
        edge_id = tuple(edge_data[0])
        if raw_or_hashed == 0:
            obj_ids = edge_data[1]
        else:
            if n == 1:
                num_real_obj_ids = edge_data[1]
                obj_ids = edge_data[2]
            else:
                obj_ids = edge_data[1]
        obj_ids_on_edge_SingleFrequent[edge_id] = obj_ids

    # -------------------------------------------------------------------------
    # 2) Prepare a list of all edge IDs from 'edge_connections' for the horizontal axis.
    #    We'll build a 2D matrix: 
    #      rows => items from objs_in_edge (vertical), 
    #      cols => edge_ids from edge_connections (horizontal).
    # -------------------------------------------------------------------------
    edge_ids = list(edge_connections.keys())

    # Build a matrix of size ( len(objs_in_edge)+1 ) x ( len(edge_ids)+1 ).
    # The first row/column are headers storing edge IDs or path IDs for reference.
    Boolean_HoMoPathway_Matrix = [
        [0 for _ in range(len(edge_ids) + 1)]
        for _ in range(len(objs_in_edge) + 1)
    ]

    # Fill the 2D matrix with appropriate row/column headers.
    for i in range(len(objs_in_edge) + 1):
        for j in range(len(edge_ids) + 1):
            if i == 0 and j != 0:
                # top row: store each edge_id from edge_ids
                Boolean_HoMoPathway_Matrix[i][j] = edge_ids[j - 1]
            if j == 0 and i != 0:
                # left column: store the "edge/path" from objs_in_edge
                Boolean_HoMoPathway_Matrix[i][j] = objs_in_edge[i - 1][0]

    # -------------------------------------------------------------------------
    # 3) Fill in the matrix:  check intersection ratio for each cell (i, j)
    # -------------------------------------------------------------------------
    #   - If n < 2 => we are dealing with single edges (i.e., "homoedges").
    #   - If n >= 2 => we try to chain edges from the vertical axis to the 
    #     newly considered edges in the horizontal axis.
    # -------------------------------------------------------------------------
    for i in range(1, len(objs_in_edge) + 1):    # Rows (vertical)
        for j in range(1, len(edge_ids) + 1):    # Columns (horizontal)
            intersected_objs = []
            paths_for_next_Round = []

            # -------------------------------------------------------------
            # CASE n < 2 => single-edge scenario (finding edges that meet threshold).
            # -------------------------------------------------------------
            if n < 2:
                # If the "row-edge" ID matches the "column-edge" ID
                if (Boolean_HoMoPathway_Matrix[i][0][0]
                        == Boolean_HoMoPathway_Matrix[0][j]):

                    obj_ids_edge_1 = obj_ids_on_edge[
                        tuple(Boolean_HoMoPathway_Matrix[i][0])
                    ]

                    # Intersection for single edges is effectively 
                    # just the number of objects on that edge
                    intersected_objs.append(obj_ids_edge_1)
                    intersection = len(set(obj_ids_edge_1))

                    # If hashed data, we might use "number_of_Raw_ObjIDs" 
                    # that we previously stored for single edges
                    if raw_or_hashed == 1:
                        for info_data in objs_in_edge:
                            if info_data[0][0] == Boolean_HoMoPathway_Matrix[0][j]:
                                intersection = info_data[1]  
                                threshold_final = threshold
                                break
                    else:
                        threshold_final = threshold

                    ratio = intersection / total_obj_count

                    # If the ratio >= threshold, we mark matrix cell as "1" (pass)
                    if ratio >= threshold_final:
                        Boolean_HoMoPathway_Matrix[i][j] = 1

                        # The path here is just the single edge
                        for path in Boolean_HoMoPathway_Matrix[i][0]:
                            paths_for_next_Round.append(path)

                        # Store the discovered "homoedge" in Edge_Object_Mapping
                        Edge_Object_Mapping.append([paths_for_next_Round, obj_ids_edge_1])

                        # If n==1, also store it under (n-1) => 0 
                        # so that the dictionary has single edges in the correct slot
                        if n == 1:
                            HoMoPaths_Dictionary.setdefault(n - 1, []).append(
                                [paths_for_next_Round, obj_ids_edge_1]
                            )

                        # Also store for n => 1
                        HoMoPaths_Dictionary.setdefault(n, []).append(
                            [paths_for_next_Round, obj_ids_edge_1]
                        )

                        # Keep track of single freq edges
                        Edge_Object_Mapping_Single_Freq_Edges.append(
                            [paths_for_next_Round, obj_ids_edge_1]
                        )

                        # Add the current edge to possible expansions 
                        # for next recursion step
                        for key in edge_connections:
                            if paths_for_next_Round[-1] == key:
                                edge_connections_for_next_Lenght[key] = edge_connections[key]

                        # We break after the match to not re-check the same cell
                        break

            # -------------------------------------------------------------
            # CASE n >= 2 => chain edges from path (vertical) to new edge (horizontal).
            # -------------------------------------------------------------
            else:
                # Reuse the single frequent edges from prior steps
                Edge_Object_Mapping_Single_Freq_Edges = Single_Frequent_objs_in_edge

                # For the path on the vertical axis, get the last edge
                # (the "tail" of the path) and see if it connects to 
                # the edge on the horizontal axis
                for key, values in edge_connections.items():
                    if key == Boolean_HoMoPathway_Matrix[i][0][-1]:
                        # 'key' is the last edge in the vertical path
                        for edgecon in values:
                            if edgecon == Boolean_HoMoPathway_Matrix[0][j]:
                                # We found that edgecon (horizontal) connects 
                                # to the last edge in vertical path
                                # so let's compute intersection
                                # Retrieve object sets for the vertical path
                                for info in objs_in_edge:
                                    if info[0] == Boolean_HoMoPathway_Matrix[i][0]:
                                        obj_ids_edge_1 = info[1]  # raw or hashed
                                        break

                                # object sets for the horizontal edge
                                for info in Single_Frequent_objs_in_edge:
                                    if info[0][0] == Boolean_HoMoPathway_Matrix[0][j]:
                                        obj_ids_edge_2 = info[1]
                                        break

                                # For raw data => intersect sets directly
                                # For hashed => we store hashed signature (or partial).
                                # The code below does direct element-by-element comparison 
                                # but for hashed minhash, typically you'd do a Jaccard estimate. 
                                # Here, the user code lumps it as "if raw/hashing => compute differently".
                                for obj1 in obj_ids_edge_1:
                                    for obj2 in obj_ids_edge_2:
                                        if obj1 == obj2:
                                            intersected_objs.append(obj1)
                                            break

                                # Decide the denominator for intersection ratio
                                if raw_or_hashed == 1:
                                    # For hashed, we treat 'permutations' as denominator
                                    x = permutations
                                else:
                                    # For raw, we treat 'total_obj_count' as denominator
                                    x = total_obj_count

                                intersection = len(intersected_objs)
                                if (intersection / x) >= threshold:
                                    Boolean_HoMoPathway_Matrix[i][j] = 1

                                    # Avoid loops: 
                                    # if the new edge is already in the path, skip
                                    if (key != edgecon and
                                        Boolean_HoMoPathway_Matrix[0][j]
                                        in Boolean_HoMoPathway_Matrix[i][0]):
                                        continue

                                    # Build the extended path
                                    for path in Boolean_HoMoPathway_Matrix[i][0]:
                                        paths_for_next_Round.append(path)
                                    paths_for_next_Round.append(Boolean_HoMoPathway_Matrix[0][j])

                                    # Save the new path in the dictionary
                                    HoMoPaths_Dictionary.setdefault(n, []).append(
                                        [paths_for_next_Round, intersected_objs]
                                    )

                                    # Keep track to extend further in next recursion
                                    Edge_Object_Mapping.append([paths_for_next_Round, intersected_objs])

                                    # Mark the connection relevant for the next round
                                    for key1 in edge_connections:
                                        if len(paths_for_next_Round) > 0:
                                            if paths_for_next_Round[-1] == key1:
                                                edge_connections_for_next_Lenght[key1] = edge_connections[key1]

    # -------------------------------------------------------------------------
    # 4) If 'help_for_jaccard == 1' and we have raw vs hashed validations:
    #    There's code to dump/load JSON from files to reconcile data 
    #    for certain region IDs. This is mostly debugging or cross-check logic.
    # -------------------------------------------------------------------------
    if help_for_jaccard == 1 and raw_or_hashed == 0 and n == 1:
        # If region_ID in {11,21,10,122,222,112,212}, we save certain data structures.
        # This code writes out the discovered edges/paths to JSON for analysis.
        if region_ID == 11:
            #print(help_for_jaccard,raw_or_hashed ,n)
            with open('correcthomoedges111.json', 'w') as file:
                json.dump(HoMoPaths_Dictionary, file)
            with open('correcthomoedges112.json', 'w') as file:
                json.dump(Edge_Object_Mapping_Single_Freq_Edges, file)
            with open('correcthomoedges113.json', 'w') as file:
                json.dump(Edge_Object_Mapping, file)
        if region_ID == 21:
            #print(help_for_jaccard,raw_or_hashed ,n)
            with open('correcthomoedges211.json', 'w') as file:
                json.dump(HoMoPaths_Dictionary, file)
            with open('correcthomoedges212.json', 'w') as file:
                json.dump(Edge_Object_Mapping_Single_Freq_Edges, file)
            with open('correcthomoedges213.json', 'w') as file:
                json.dump(Edge_Object_Mapping, file)
        if region_ID == 10:
            #print(help_for_jaccard,raw_or_hashed ,n)
            with open('correcthomoedges101.json', 'w') as file:
                json.dump(HoMoPaths_Dictionary, file)
            with open('correcthomoedges102.json', 'w') as file:
                json.dump(Edge_Object_Mapping_Single_Freq_Edges, file)
            with open('correcthomoedges103.json', 'w') as file:
                json.dump(Edge_Object_Mapping, file)
        if region_ID == 122:
            #print(help_for_jaccard,raw_or_hashed ,n)
            with open('correcthomoedges1221.json', 'w') as file:
                json.dump(HoMoPaths_Dictionary, file)
            with open('correcthomoedges1222.json', 'w') as file:
                json.dump(Edge_Object_Mapping_Single_Freq_Edges, file)
            with open('correcthomoedges1223.json', 'w') as file:
                json.dump(Edge_Object_Mapping, file)
        if region_ID == 222:
            #print(help_for_jaccard,raw_or_hashed ,n)
            with open('correcthomoedges2221.json', 'w') as file:
                json.dump(HoMoPaths_Dictionary, file)
            with open('correcthomoedges2222.json', 'w') as file:
                json.dump(Edge_Object_Mapping_Single_Freq_Edges, file)
            with open('correcthomoedges2223.json', 'w') as file:
                json.dump(Edge_Object_Mapping, file)
        if region_ID == 112:
            #print(help_for_jaccard,raw_or_hashed ,n)
            with open('correcthomoedges1121.json', 'w') as file:
                json.dump(HoMoPaths_Dictionary, file)
            with open('correcthomoedges1122.json', 'w') as file:
                json.dump(Edge_Object_Mapping_Single_Freq_Edges, file)
            with open('correcthomoedges1123.json', 'w') as file:
                json.dump(Edge_Object_Mapping, file)
        if region_ID == 212:
            #print(help_for_jaccard,raw_or_hashed ,n)
            with open('correcthomoedges2121.json', 'w') as file:
                json.dump(HoMoPaths_Dictionary, file)
            with open('correcthomoedges2122.json', 'w') as file:
                json.dump(Edge_Object_Mapping_Single_Freq_Edges, file)
            with open('correcthomoedges2123.json', 'w') as file:
                json.dump(Edge_Object_Mapping, file)
        #print(f"After First if for id = {region_ID}")
        #print(f"After First if for id = {region_ID}")
        

    #username = input("\n A:")
    # Prunning all the n
    if int(n) > 1 and int(n) in HoMoPaths_Dictionary:
        for path in HoMoPaths_Dictionary[int(n)]:
            for i in range(len(path[0]) - (int(n) - 1)):
                sub_shinglees = [path[0][i:i + int(n) - 1] for i in range(len(path[0]) - (int(n) - 2))]
                for sub_shingle in sub_shinglees:
                    for path2 in HoMoPaths_Dictionary[int(n) - 1]:
                        if sub_shingle == path2[0]:
                            HoMoPaths_Dictionary[int(n) - 1].remove(path2)

    # Similarly, if help_for_jaccard == 1 and raw_or_hashed == 1 and n == 1, 
    # the code attempts to load raw data from JSON and align it with hashed data,
    # effectively cross-verifying the correctness of hashed edges. 
    # There's a large block of code for each region_ID to manipulate 
    # Edge_Object_Mapping, etc.

    if help_for_jaccard == 1 and raw_or_hashed ==1 and int(n)==1:

        temp_Edge_Object_Mapping = []
        temp_HoMoPaths_Dictionary = {}
        #print(f"2. Important : {region_ID}")            
        if region_ID == 11:
            with open("correcthomoedges113.json", 'r') as file:
                Edge_Object_Mapping = json.load(file)
                for data in objs_in_edge:
                    for data2 in Edge_Object_Mapping:
                        
                        if data[0][0] == data2[0][0]:
                            #print(data , data2)
                            temp_Edge_Object_Mapping.append([data[0], data[2]])
                            #print("YES 1")
                Edge_Object_Mapping = temp_Edge_Object_Mapping
                Edge_Object_Mapping_Single_Freq_Edges = temp_Edge_Object_Mapping
                
                with open("correcthomoedges111.json", 'r') as file:
                    HoMoPaths_Dictionary_raw = json.load(file)
                    HoMoPaths_Dictionary = {int(key): value for key, value in HoMoPaths_Dictionary_raw.items()}

                    for data in temp_Edge_Object_Mapping:
                        for n in HoMoPaths_Dictionary:
                            if int(n) not  in temp_HoMoPaths_Dictionary : 
                                temp_HoMoPaths_Dictionary[n]=[]
                            for path in HoMoPaths_Dictionary[n]:
                                
                                if path[0][0] == data[0][0]:
                                    #print(path , data)

                                    #print(" Yes 20")
                                    temp_HoMoPaths_Dictionary[n].append([data[0],data[1]])
                    HoMoPaths_Dictionary = temp_HoMoPaths_Dictionary

        if region_ID == 21:
            temp_Edge_Object_Mapping = []
            temp_HoMoPaths_Dictionary = {}
            with open("correcthomoedges213.json", 'r') as file:
                Edge_Object_Mapping = json.load(file)
                for data in objs_in_edge:
                    for data2 in Edge_Object_Mapping:
                        
                        if data[0][0] == data2[0][0]:
                            #print(data , data2)
                            temp_Edge_Object_Mapping.append([data[0], data[2]])
                            #print("YES 1")
                Edge_Object_Mapping = temp_Edge_Object_Mapping
                Edge_Object_Mapping_Single_Freq_Edges = temp_Edge_Object_Mapping
                
                with open("correcthomoedges211.json", 'r') as file:
                    HoMoPaths_Dictionary_raw = json.load(file)
                    HoMoPaths_Dictionary = {int(key): value for key, value in HoMoPaths_Dictionary_raw.items()}

                    for data in temp_Edge_Object_Mapping:
                        for n in HoMoPaths_Dictionary:
                            if int(n) not  in temp_HoMoPaths_Dictionary : 
                                temp_HoMoPaths_Dictionary[n]=[]
                            for path in HoMoPaths_Dictionary[n]:
                                
                                if path[0][0] == data[0][0]:
                                    #print(path , data)

                                    #print(" Yes 20")
                                    temp_HoMoPaths_Dictionary[n].append([data[0],data[1]])
                    HoMoPaths_Dictionary = temp_HoMoPaths_Dictionary

        if region_ID == 10:
            with open("correcthomoedges103.json", 'r') as file:
                Edge_Object_Mapping = json.load(file)
                for data in objs_in_edge:
                    for data2 in Edge_Object_Mapping:
                        
                        if data[0][0] == data2[0][0]:
                            #print(data , data2)
                            temp_Edge_Object_Mapping.append([data[0], data[2]])
                            #print("YES 1")
                Edge_Object_Mapping = temp_Edge_Object_Mapping
                Edge_Object_Mapping_Single_Freq_Edges = temp_Edge_Object_Mapping
                
                with open("correcthomoedges101.json", 'r') as file:
                    HoMoPaths_Dictionary_raw = json.load(file)
                    HoMoPaths_Dictionary = {int(key): value for key, value in HoMoPaths_Dictionary_raw.items()}

                    for data in temp_Edge_Object_Mapping:
                        for n in HoMoPaths_Dictionary:
                            if int(n) not  in temp_HoMoPaths_Dictionary : 
                                temp_HoMoPaths_Dictionary[n]=[]
                            for path in HoMoPaths_Dictionary[n]:
                                
                                if path[0][0] == data[0][0]:
                                    #print(path , data)

                                    #print(" Yes 20")
                                    temp_HoMoPaths_Dictionary[n].append([data[0],data[1]])
                    HoMoPaths_Dictionary = temp_HoMoPaths_Dictionary

        if region_ID == 222:
            with open("correcthomoedges2223.json", 'r') as file:
                Edge_Object_Mapping = json.load(file)
                for data in objs_in_edge:
                    for data2 in Edge_Object_Mapping:
                        
                        if data[0][0] == data2[0][0]:
                            #print(data , data2)
                            temp_Edge_Object_Mapping.append([data[0], data[2]])
                            #print("YES 1")
                Edge_Object_Mapping = temp_Edge_Object_Mapping
                Edge_Object_Mapping_Single_Freq_Edges = temp_Edge_Object_Mapping
                
                with open("correcthomoedges2221.json", 'r') as file:
                    HoMoPaths_Dictionary_raw = json.load(file)
                    HoMoPaths_Dictionary = {int(key): value for key, value in HoMoPaths_Dictionary_raw.items()}

                    for data in temp_Edge_Object_Mapping:
                        for n in HoMoPaths_Dictionary:
                            if int(n) not  in temp_HoMoPaths_Dictionary : 
                                temp_HoMoPaths_Dictionary[n]=[]
                            for path in HoMoPaths_Dictionary[n]:
                                
                                if path[0][0] == data[0][0]:
                                    #print(path , data)

                                    #print(" Yes 20")
                                    temp_HoMoPaths_Dictionary[n].append([data[0],data[1]])
                    HoMoPaths_Dictionary = temp_HoMoPaths_Dictionary
        
        if region_ID == 212:
            with open("correcthomoedges2123.json", 'r') as file:
                Edge_Object_Mapping = json.load(file)
                for data in objs_in_edge:
                    for data2 in Edge_Object_Mapping:
                        
                        if data[0][0] == data2[0][0]:
                            #print(data , data2)
                            temp_Edge_Object_Mapping.append([data[0], data[2]])
                            #print("YES 1")
                Edge_Object_Mapping = temp_Edge_Object_Mapping
                Edge_Object_Mapping_Single_Freq_Edges = temp_Edge_Object_Mapping
                
                with open("correcthomoedges2121.json", 'r') as file:
                    HoMoPaths_Dictionary_raw = json.load(file)
                    HoMoPaths_Dictionary = {int(key): value for key, value in HoMoPaths_Dictionary_raw.items()}

                    for data in temp_Edge_Object_Mapping:
                        for n in HoMoPaths_Dictionary:
                            if int(n) not  in temp_HoMoPaths_Dictionary : 
                                temp_HoMoPaths_Dictionary[n]=[]
                            for path in HoMoPaths_Dictionary[n]:
                                
                                if path[0][0] == data[0][0]:
                                    #print(path , data)

                                    #print(" Yes 20")
                                    temp_HoMoPaths_Dictionary[n].append([data[0],data[1]])
                    HoMoPaths_Dictionary = temp_HoMoPaths_Dictionary
        
            
        
        if region_ID == 112:
            with open("correcthomoedges1123.json", 'r') as file:
                Edge_Object_Mapping = json.load(file)
                for data in objs_in_edge:
                    for data2 in Edge_Object_Mapping:
                        
                        if data[0][0] == data2[0][0]:
                            #print(data , data2)
                            temp_Edge_Object_Mapping.append([data[0], data[2]])
                            #print("YES 1")
                Edge_Object_Mapping = temp_Edge_Object_Mapping
                Edge_Object_Mapping_Single_Freq_Edges = temp_Edge_Object_Mapping
                
                with open("correcthomoedges1121.json", 'r') as file:
                    HoMoPaths_Dictionary_raw = json.load(file)
                    HoMoPaths_Dictionary = {int(key): value for key, value in HoMoPaths_Dictionary_raw.items()}

                    for data in temp_Edge_Object_Mapping:
                        for n in HoMoPaths_Dictionary:
                            if int(n) not  in temp_HoMoPaths_Dictionary : 
                                temp_HoMoPaths_Dictionary[n]=[]
                            for path in HoMoPaths_Dictionary[n]:
                                
                                if path[0][0] == data[0][0]:
                                    #print(path , data)

                                    #print(" Yes 20")
                                    temp_HoMoPaths_Dictionary[n].append([data[0],data[1]])
                    HoMoPaths_Dictionary = temp_HoMoPaths_Dictionary
        
        if region_ID == 122:
            with open("correcthomoedges1223.json", 'r') as file:
                Edge_Object_Mapping = json.load(file)
                for data in objs_in_edge:
                    for data2 in Edge_Object_Mapping:
                        
                        if data[0][0] == data2[0][0]:
                            #print(data , data2)
                            temp_Edge_Object_Mapping.append([data[0], data[2]])
                            #print("YES 1")
                Edge_Object_Mapping = temp_Edge_Object_Mapping
                Edge_Object_Mapping_Single_Freq_Edges = temp_Edge_Object_Mapping
                
                with open("correcthomoedges1221.json", 'r') as file:
                    HoMoPaths_Dictionary_raw = json.load(file)
                    HoMoPaths_Dictionary = {int(key): value for key, value in HoMoPaths_Dictionary_raw.items()}

                    for data in temp_Edge_Object_Mapping:
                        for n in HoMoPaths_Dictionary:
                            if int(n) not  in temp_HoMoPaths_Dictionary : 
                                temp_HoMoPaths_Dictionary[n]=[]
                            for path in HoMoPaths_Dictionary[n]:
                                
                                if path[0][0] == data[0][0]:
                                    #print(path , data)

                                    #print(" Yes 20")
                                    temp_HoMoPaths_Dictionary[n].append([data[0],data[1]])
                    HoMoPaths_Dictionary = temp_HoMoPaths_Dictionary


        temp_edge_connections_for_next_Lenght ={}
        for key in edge_connections:
            key=int(key)
            for data in Edge_Object_Mapping :
                if data[0][-1] == key and  len(data[1])>0 :
                    #print(data[0][-1] , key)
                    temp_edge_connections_for_next_Lenght[key] = edge_connections[key]
        edge_connections_for_next_Lenght =  temp_edge_connections_for_next_Lenght          

        #print(f"Final Test : {HoMoPaths_Dictionary} \n {Edge_Object_Mapping} \n {Edge_Object_Mapping_Single_Freq_Edges}\n")


    # -------------------------------------------------------------------------
    # 5) Additional formatting for single-edge or pair-of-edges if n==1 or n==2, 
    #    appended to "Current_Experiment_Compare_RAW_HASh_NEW..." logs
    # -------------------------------------------------------------------------
    # E.g., writing discovered single edges or pairs to a text file 
    # for offline analysis.
    if help_for_jaccard != 1 and n ==1 :
        formatted_paths_single = ','.join(['[{}]'.format(','.join(map(str, sub_paths_list[0]))) for index, complete_data in enumerate(HoMoPaths_Dictionary.values()) if index == 1  for sub_paths_list in complete_data ])
        #fileofexperiments.write(formatted_paths_single)
        
        with open("Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_single.txt", 'a') as fileofexperiments:
            if len(formatted_paths_single)>0:
                fileofexperiments.write(f"{total_obj_count},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},{formatted_paths_single}\n")
            else:
                fileofexperiments.write(f"{total_obj_count},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},{[0]}\n")
    if  n ==2 :    
        formatted_paths_pairs = ','.join(['[{}]'.format(','.join(map(str, sub_paths_list[0]))) for index, complete_data in enumerate(HoMoPaths_Dictionary.values()) if index == 2  for sub_paths_list in complete_data ])
        #fileofexperiments.write(formatted_paths_pairs)
        with open("Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_pairs.txt", 'a') as fileofexperiments:
            if len(formatted_paths_pairs)>0:
                fileofexperiments.write(f"{total_obj_count},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},{formatted_paths_pairs}\n")
            else: 
                fileofexperiments.write(f"{total_obj_count},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},{[0]}\n")
 



    # -------------------------------------------------------------------------
    # 6) RECURSION: If we discovered new paths (Edge_Object_Mapping not empty),
    #    and haven't hit the 'limit', recursively call the function with n+1 
    #    to attempt to chain edges further.
    # -------------------------------------------------------------------------
    time.sleep(1)  # Simulate or slow down recursion for debug
    
    limit =100
    if len(Edge_Object_Mapping) > 0 and n < limit:
        calculate_obj_id_intersection(
            region_ID, raw_or_hashed, permutations, edge_connections_for_next_Lenght,
            Edge_Object_Mapping, Edge_Object_Mapping_Single_Freq_Edges,
            total_obj_count, threshold,int(n) + 1, length_of_permutations,
            help_for_jaccard, NumOfEdges, limit, HoMoPaths_Dictionary
        )
    else:
        # Once no more new edges or we exceed recursion limit, we finalize.
        print(f"\tMax length of HoMoPaths for Regional Leader {region_ID} is :  {n - 1}")

    return HoMoPaths_Dictionary








#   C O H E N    2  #

def _Find_Cardinality_Cohen(combined_data, num_perm, remove_extra_Integ):
    """
    Computes the approximate cardinality of a set of objects using Cohen's method 
    over minhash signatures.

    :param combined_data: 
        A list of items that contain minhash signatures. Each item can be structured in one of two ways:
          1) If remove_extra_Integ == 1, each item is: [edge_id_list, obj_ids]
          2) If remove_extra_Integ == 0, each item is: [edge_id_list, number_of_Raw_ObjIDs, obj_ids]
        The 'obj_ids' portion in these structures is expected to be a minhash signature array 
        (length = num_perm) for that edge's or path's object set.
    :param num_perm:
        The number of permutations (or number of hash functions) used in the minhashing process.
    :param remove_extra_Integ:
        A flag indicating which structure 'combined_data' follows:
            - 1 => items have the form [[edge_id], obj_ids]
            - 0 => items have the form [[edge_id], number_of_Raw_ObjIDs, obj_ids]
    :return:
        An integer representing the estimated cardinality of the union of object sets 
        across all items in 'combined_data'.
    """

    listOfMinhash_sign = []

    # Iterate over each item in 'combined_data' to extract its minhash signature
    for item in combined_data:
        if remove_extra_Integ == 1:
            # Example structure: [ [edge_id], obj_ids ]
            # 'obj_ids' here is assumed to be the entire minhash signature for that set
            if len(item) == 2:  # Safety check
                minHashSignatures = item[1] % (1 << 32)  # Possibly ensuring 32-bit
                listOfMinhash_sign.append(minHashSignatures)
        else:
            # Example structure: [ [edge_id], number_of_Raw_ObjIDs, obj_ids ]
            # We skip the 'number_of_Raw_ObjIDs' and go straight to 'obj_ids'
            if len(item) == 3:  # Safety check
                minHashSignatures = item[2]
                listOfMinhash_sign.append(minHashSignatures)

    # Once we accumulate all minhash signatures, we call _Cohen to compute the cardinality
    cardinality = _Cohen(listOfMinhash_sign, num_perm)

    # Return as an integer (coerced from float if needed)
    return int(cardinality)


def _Cohen(listOfMinhash_sign, num_perm):
    """
    Uses Cohen's method to estimate the cardinality of a dataset from its minhash signatures.

    :param listOfMinhash_sign:
        A list of minhash signatures, where each signature is typically an array of length 'num_perm'. 
        For example:
            listOfMinhash_sign = [
                [hashValue1, hashValue2, ..., hashValueN],  # for item 1
                [hashValue1, hashValue2, ..., hashValueN],  # for item 2
                ...
            ]
    :param num_perm:
        The number of hash permutations used to compute each minhash signature (length of each signature).
    :return:
        A float approximating the cardinality of the union of all sets from which the minhash signatures 
        were derived. (Typically, you'll cast or convert to int.)
    """

    # First, we transpose the list so each column of 'listOfMinhash_sign' becomes a row in 'transposed_matrix'.
    # That is, we regroup the Nth hash values from each signature into one column.
    transposed_matrix = list(zip(*listOfMinhash_sign))

    # For each column in the transposed matrix, find the minimum value.
    # (In Cohen's method, we use these column-minimums as a basis for the estimate.)
    min_values = [min(column) for column in transposed_matrix]

    # Sum those minimum values
    total_sum = sum(min_values)

    # `_max_hash` is presumably a global or previously defined constant indicating
    # the maximum possible 32-bit integer (e.g., 2^32 - 1). 
    # The formula: cardinality = num_perm / ( (sum_of_mins / _max_hash ) ) - 1
    # is a key part of Cohen's cardinality estimation:
    #     cardinality = (num_perm / average_of_min) - 1
    # but scaled by _max_hash to handle typical hashing ranges.
    cardinality = num_perm / (total_sum / _max_hash) - 1

    return cardinality






##############################################################################################################
#--------------------------------------------- #
            # MAIN
        
def main(raw_or_hashed, seed, current_compress, permutations, num_objs, length_of_path,
         threshold, depth, help_for_jaccard, choice_place,
         run_once, repeat_experiment, limitN, folderOfRepeatExperiment):
    """
    Main function that:
      1. Sets up or reuses data files describing the global road network, edge connections, and sensor data.
      2. Partitions the network into sub-regions if 'depth' > 0.
      3. Creates and starts threads:
         - One thread for the Top Leader.
         - One thread per Regional Leader (4 in your experiments, but can vary).
      4. Waits for all threads to finish, gathers the result, and returns it.
    
    The function is typically invoked by 'experiment_creator.py' (via subprocess) 
    to run a single experimental trial, or repeated for multiple trials.

    :param raw_or_hashed:
        0 => raw data, 1 => hashed data. Affects how sensor data is parsed and how intersections are computed.
    :param seed:
        An integer seed used in certain naming/ports or random generation (not fully shown here).
    :param current_compress:
        A compression or sampling level used by certain HOMOPA computations.
    :param permutations:
        If using hashed data (1), the number of minhash permutations. Otherwise can be an unused parameter.
    :param num_objs:
        The number of objects (or load) to simulate in each region or motion file.
    :param length_of_path:
        The length parameter used to generate motions (e.g. how far each object can travel).
    :param threshold:
        Intersection threshold for deciding if two edges (or paths) share enough objects to form a homopath.
    :param depth:
        The partition depth for subdividing the map into multiple regions. Depth=0 => no partition.
    :param help_for_jaccard:
        A debug flag. If 1, additional reading/writing of JSONs to verify raw vs. hashed edges is performed.
    :param choice_place:
        Identifies which geographic location or map is being used. 
        The function chooses the correct road network, bounding box, etc. for that place.
    :param run_once:
        0 => this is a fresh experiment run (files can be deleted/overwritten).
        1 => re-run the same experiment with existing files (do not delete).
    :param repeat_experiment:
        Used to control whether the same motion/sensor files are reused or re-generated 
        (and potentially re-copied from a saved folder).
    :param limitN:
        A limit on the maximum recursion depth for homopath discovery (beyond n edges).
    :param folderOfRepeatExperiment:
        If `repeat_experiment` is 1, the code tries to locate and copy certain files 
        from this folder to replicate the exact conditions.

    :return:
        resultttt => an integer representing the final result from the Top Leader (e.g., number of regions 
                     that found homopaths). Also written to 'output.txt'.

    Note: The script expects to be called from the command line with these arguments, 
    and the final integer result is printed and also written to 'output.txt' for the 'experiment_creator.py' script.
    """


    # 1) Define names of key files used throughout the experiment
    File_1_combined_nodes_edges = "1_combined_nodes_edges.txt"
    File_2_edgeconnections = "2_edgeconnections.txt"
    File_3_Motions_file = "3_Motions.txt"
    File_4_sensors_FILE = "4_sensors.txt"
    File_4_sensors_HASHED_FILE = "4_sensors_HASHED.txt"

    # Prefixes for creating region-specific files or map images
    prefix_file_Name_map = "map"
    prefix_file_Name_Regional = "Regional"
    prefix_file_Name_Picture = "Picture"

    # Some additional file references for logging/results
    results_all = "ResultsOfExperiments.txt"
    experiment_creator = "experiment_creator.py"
    homopa_python_code = "homopa.py"
    History7z = "History.7z"

    # Decide which sensor file to use: raw or hashed
    if raw_or_hashed == 0:
        file_sensor = File_4_sensors_FILE
    else:
        file_sensor = File_4_sensors_HASHED_FILE


    # 2) Check if threshold is > 0.01 as a minimal condition(feel free to adjust it); else skip building
    if threshold > 0.01:
        if raw_or_hashed == 0:
            # RAW data mode
            if run_once == 0:
                # => fresh run of the experiment, so we might optionally delete old files (commented out here).
                
                # Create the global network (graph) from File_1_combined_nodes_edges if needed
                G, north, south, east, west, place_name = create_network(
                    File_1_combined_nodes_edges,
                    prefix_file_Name_Picture,
                    choice_place
                )
                # After we have the network, find how many edges exist in total
                total_edges = find_connected_edges(File_1_combined_nodes_edges, File_2_edgeconnections)

                # If we're not repeating the experiment, we create new motions and sensor data
                if repeat_experiment == 0:
                    create_motions(G, length_of_path, num_objs, File_1_combined_nodes_edges, File_3_Motions_file)
                    write_data_to_sensors_file(
                        File_3_Motions_file,
                        File_4_sensors_FILE,
                        num_objs,
                        total_edges,
                        north, south, east, west,
                        place_name
                    )
                else:
                    # If repeating, we might re-copy old motion data from folderOfRepeatExperiment
                    write_data_to_sensors_file(
                        File_3_Motions_file,
                        File_4_sensors_FILE,
                        num_objs,
                        total_edges,
                        north, south, east, west,
                        place_name
                    )
                    found_folder = None
                    for folder in os.listdir('.'):
                        if folder == folderOfRepeatExperiment:
                            parts = folder.split('_')
                            if len(parts) == 7:
                                # e.g., "some_prefix_{numOfEdges}_{numOfObjs}_{threshold}_{lengthOfPaths}_{mapid}_{dateTimeStamp}"
                                _, folder_numOfEdges, folder_numOfObjs, folder_Threshold, folder_lengthOfPaths, folder_mapid, folder_dateTimeStamp = parts
                                if int(folder_numOfObjs) == num_objs and int(folder_mapid) == choice_place:
                                    found_folder = folder
                                    break

                    # If we found the matching folder, copy the motions and sensor files from it
                    if found_folder:
                        source_3_Motions_file = os.path.join(found_folder, File_3_Motions_file)
                        source_4_sensors_file = os.path.join(found_folder, File_4_sensors_FILE)
                        if os.path.exists(source_3_Motions_file) and os.path.exists(source_4_sensors_file):
                            shutil.copy(source_3_Motions_file, File_3_Motions_file)
                            shutil.copy(source_4_sensors_file, File_4_sensors_FILE)

                # Now partition the global map into regions if depth > 0
                main_partitioning_map_(
                    File_1_combined_nodes_edges,
                    prefix_file_Name_map,
                    prefix_file_Name_Regional,
                    prefix_file_Name_Picture,
                    depth
                )

            else:
                # => run_once == 1 => we are re-running an experiment with the same files
                total_edges = find_connected_edges(File_1_combined_nodes_edges, File_2_edgeconnections)
                main_partitioning_map_(
                    File_1_combined_nodes_edges,
                    prefix_file_Name_map,
                    prefix_file_Name_Regional,
                    prefix_file_Name_Picture,
                    depth
                )

            # For raw data, we might fix length_of_permutations = 1 (since minhash permutations are not used).
            length_of_permutations = 1

        else:
            # => raw_or_hashed == 1 => hashed data mode
            total_edges = find_connected_edges(File_1_combined_nodes_edges, File_2_edgeconnections)
            length_of_permutations = permutations

            # Possibly delete some files except certain key ones (cleanup from prior runs)
            delete_files_except(
                run_once,
                History7z,
                threshold,
                homopa_python_code,
                "4_1.py",
                experiment_creator,
                results_all,
                File_4_sensors_HASHED_FILE,
                File_1_combined_nodes_edges,
                File_2_edgeconnections,
                File_3_Motions_file,
                File_4_sensors_FILE
            )

        

        # 3) Now that the network is set up, we have the partitioned regional data.
        #    We create the region IDs -> sensor data for each region -> any further config.
        #    Then we gather them in a list 'regionids'.
        if depth != 0:
            regionids = create_edgeConnections_and_sensorInfo_for_each_Region(
                File_2_edgeconnections,
                file_sensor,
                prefix_file_Name_map
            )
        else:
            regionids = create_edgeConnections_and_sensorInfo_for_each_Region(
                File_2_edgeconnections,
                file_sensor,
                prefix_file_Name_map
            )
            regionids = [10]  # Hard-code a single region if depth=0

        # We clean regionids by removing any that might be zero or not matching certain criteria
        clean_regionids = []
        for region in regionids:
            if int(region / (10 ** depth)) > 0:
                clean_regionids.append(region)

        # This dictionary describes how each region connects to others at a higher scale
        all_connections = create_RegionConnections_for_Top_Leader()

        # Convert raw_or_hashed to a human-readable string if needed
        if raw_or_hashed == 0:
            raw_or_hashed_string = "RAW"
        else:
            raw_or_hashed_string = "HASHED"

        # 4) Launch the Top Leader in its own thread
        result_queue = queue.Queue()
        top_leader_thread = threading.Thread(
            target=start_Top_leader,
            args=(clean_regionids, all_connections, threshold, total_edges,
                  current_compress, permutations, raw_or_hashed, seed, result_queue)
        )
        top_leader_thread.start()

    

        # Clear any shared global lists or counters before starting regional threads
        clear_lists()

        # 5) Create a thread for each Regional Leader
        regional_threads = []
        for regionID in clean_regionids:
            # Each region thread runs start_regional_leader(...) 
            # which sets up a server socket and processes local homopaths.
            regional_thread = threading.Thread(
                target=start_regional_leader,
                args=(regionID, threshold, threading.Event(), raw_or_hashed,
                      permutations, current_compress, length_of_permutations,
                      help_for_jaccard, limitN)
            )
            regional_thread.start()
            regional_threads.append(regional_thread)

        # Some sleeps to ensure the threads fully start, or to let them proceed 
        # in the correct order
        if raw_or_hashed == 0:
            time.sleep(10)
        else:
            time.sleep(5)

        # 6) Wait for all regional threads to finish
        for thread in regional_threads:
            thread_complete()    # Possibly a method that signals "thread done"
            time.sleep(1)
            thread.join()
            time.sleep(1)

        # 7) Now wait for the Top Leader thread to finish
        top_leader_thread.join()
        thread_complete()

        # 8) Retrieve the result from the Top Leader
        resultttt = result_queue.get()
        thread_init()  # Possibly re-initialize any global counters after threads

        if raw_or_hashed == 0:
            time.sleep(2)
        else:
            time.sleep(2)

        #print(f"Result in main in homopa : {resultttt}")

    else:
        # If threshold <= 0.01, skip the entire thread creation logic and set a default result
        resultttt = 1

    return resultttt


if __name__ == "__main__":
    # The script reads the command-line arguments, 
    # calls main(...) with them, 
    # then writes the final result to 'output.txt'.

    raw_or_hashed = int(sys.argv[1])
    seed = int(sys.argv[2])
    current_compress = int(sys.argv[3])
    num_of_permutations = int(sys.argv[4])
    num_objs = int(sys.argv[5])
    length_of_path = int(sys.argv[6])
    threshold = float(sys.argv[7])
    depth = int(sys.argv[8])
    help_for_jaccard = int(sys.argv[9])
    choice_place = int(sys.argv[10])
    run_once = int(sys.argv[11])
    repeat_experiment = int(sys.argv[12])
    limitN = int(sys.argv[13])
    folderOfRepeatExperiment = str(sys.argv[14])

    resultttt = main(raw_or_hashed, seed, current_compress, num_of_permutations, 
                     num_objs, length_of_path, threshold, depth, help_for_jaccard, 
                     choice_place, run_once, repeat_experiment, limitN, folderOfRepeatExperiment)

    # Write the result to output.txt (for experiment_creator.py) and print it.
    with open('output.txt', 'w') as f:
        f.write(str(resultttt))
    print(f"\tNumber of Regional Leaders with detetected HoMoPaths : {resultttt}. This 'print' executed in 'homopa.py'")  # Optionally still print it
