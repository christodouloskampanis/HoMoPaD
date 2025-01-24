
import os, time , re , socket ,json , threading 
import pandas as pd
import shutil
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Set the backend to Agg before importing pyplot
import sys
import numpy as np
#from sklearn.cluster import DBSCAN
from scipy.spatial.distance import pdist, squareform
import queue

from preparation import delete_files_except , create_network , find_connected_edges , create_motions, write_data_to_sensors_file , main_partitioning_map_ 
from preparation import create_edgeConnections_and_sensorInfo_for_each_Region , get_size , write_results_from_Top_Leader_to_file , write_results_to_file_ResultsOfExperiments, create_RegionConnections_for_Top_Leader
_max_hash = np.uint32((1 << 32) - 1)





all_regions_ready = threading.Event()                      # Create an event to signal that regional threads are ready
all_regions_ready_condition = threading.Condition()        # Create a condition to signal that all regional threads are ready
regions_ready_counter = []                                 #  global list for the regions with  homopaths
regions_without_Homopa_counter = []                        #  global list for the regions WITHOUT  homopaths
all_regions_counter = [] 
function_lock = threading.Lock()                           # lock the critical parts when all the regions are running in their own threads
all_HOMOPATHS = None
completed_threads = 0  # Track the number of completed threads
lock = threading.Lock()  # Lock to synchronize access to the counter variable

def thread_complete():
    global completed_threads
    with lock:
        completed_threads += 1

def thread_init():
    global completed_threads
    with lock:
        completed_threads =0

def clear_lists():
    global regions_ready_counter
    global regions_without_Homopa_counter
    global all_regions_counter
    with lock:
        regions_ready_counter.clear()
        regions_without_Homopa_counter.clear()
        all_regions_counter.clear()






def calculate_transmission_cost(data):
    """
    Calculate the total cost of transmitting the data in bytes.

    Parameters:
    - data: The original data to be transmitted (e.g., dictionary, list, etc.).

    Returns:
    - Total transmission cost in bytes.
    """
    # Serialize the data to JSON
    serialized_data = json.dumps(data)

    # Measure serialized size in bytes
    total_cost = len(serialized_data.encode('utf-8'))

    return total_cost

##################################################################################################################################
#--------------------------------------------- #
#               T O S S I M


##########   TOP LEADER   ##########
# 4.1
def start_Top_leader(regionids, all_connections, threshold , total_edges , current_compress ,num_of_permutations ,raw_or_hashed , seed , result_queue):
    global regions_ready_counter
    global regions_without_Homopa_counter
    global all_regions_counter
    start_time1 = time.time()
    # Wait for all regional threads to be ready

    with all_regions_ready_condition:
        #print(f" all region condition : {all_regions_ready_condition}")
        print(f"Top Leader is waiting for 'READY' signals'")
        while (len(regions_ready_counter) + len(regions_without_Homopa_counter)) < len(regionids):
            print(f"'Top Leader Counter' : {regions_ready_counter}")
            all_regions_ready_condition.wait() 
    print(f"Top Leader Counter: {regions_ready_counter}")
    #print("All regional leaders or at least 2 are ready to start communication ,  and Top Leader knows it.\n\n")  

    all_hot_paths ={}
    objOfRegion = {}
    totalUniqObjs = set()
    counter_of_objs = 0
    start_time1 = time.time()
    top_leader_integers_raw = 0
    top_leader_integers_hashed = 0
    first_level_total_integers = 0

    C2Base_Total_Bytes = 0
    for region_id in all_regions_counter:
        local_unique_objs = set()
        with function_lock:
            if region_id in regions_ready_counter:
                received_data_chunk_dict = send_request_to_regional_leader(3, region_id, 3)  # Top Leader wakes up RegionX to send  only Homopaths
            
                size = get_size(received_data_chunk_dict)

                C2Base_Total_Bytes = C2Base_Total_Bytes +  calculate_transmission_cost(received_data_chunk_dict)
            #print (received_data_chunk_dict , size)
            #choice = input("What do you want to delete?\n1 for based on numOfObjs\n2 for based on threshold\n")
    
                if raw_or_hashed == 0:
                    top_leader_integers_raw =+ size
                else:
                    top_leader_integers_hashed =+ size
            else:
                received_data_chunk_Objs = send_request_to_regional_leader(4, region_id, 4)  # Top Leader wakes up RegionX to send the number of Objs 
                size = get_size(received_data_chunk_Objs)

                values_list = received_data_chunk_Objs[1:-1].split(',')
                x = len(values_list)
                #print(len(values_list))
                received_data_chunk_Objs_set = {int(value.strip()) for value in values_list}
                for element in received_data_chunk_Objs_set:
                    if raw_or_hashed == 0:
                        totalUniqObjs.add(element)
                        local_unique_objs.add(element)
                    else:
                        totalUniqObjs.add(element)
                #send_request_to_regional_leader("[-1]" , region_id , "[-1]")
            
            if region_id in regions_ready_counter:
                received_data_chunk_dict_int_keys = {int(k): v for k, v in received_data_chunk_dict.items()}
                all_hot_paths[region_id] = received_data_chunk_dict_int_keys

                #print(f" ****------*******------- {received_data_chunk_dict_int_keys}")
                
                # i do it also for hashed data only for debugging . Normally that happens only for raw
                received_data_chunk_Objs = send_request_to_regional_leader(4, region_id, 4)  # Top Leader wakes up RegionX to send the number of Objs 
                size = get_size(received_data_chunk_Objs)
                if raw_or_hashed == 0: # we need the received_data_chunk_Objs only for raw in order to identify the union. For hashed we use the "permutation"
                    C2Base_Total_Bytes = C2Base_Total_Bytes +  calculate_transmission_cost(received_data_chunk_Objs)

                #print (received_data_chunk_Objs , size)
                #choice = input("What do you want to delete?\n1 for based on numOfObjs\n2 for based on threshold\n")
                time.sleep(1)
                if region_id in regions_ready_counter:
                    top_leader_integers_raw =+ size

                received_data_transmitted_integers = send_request_to_regional_leader(5, region_id, 5)  # Top Leader wakes up RegionX to send transmitted integers -debugging purposes
                # received_data_transmitted_integers has not UNIQUE objs , dont worry
                # has the total number of integers that the regional leaderX from 1st level  received from its corresponding sensors
                # received_data_transmitted_integers is coming as response from through other functions .
                # start function which produce the functitotal_information_integers is function prepare_data 
                # which returns here "total_information_integers += topic_information_integers" 
                
                
                #print(f"-------------- received_data_transmitted_integers from level 1 from Reg Leader {region_id} in Top Leader : {received_data_transmitted_integers}")
                first_level_total_integers += received_data_transmitted_integers * 4
                #choice = input("What do you want to delete?\n1 for based on numOfObjs\n2 for based on threshold\n")
    
                

                time.sleep(1)
                
                values_list = received_data_chunk_Objs[1:-1].split(',')
                x = len(values_list)
                #print(len(values_list))
                received_data_chunk_Objs_set = {int(value.strip()) for value in values_list}
                
                #print(all_hot_paths)
                
                for element in received_data_chunk_Objs_set:
                    if raw_or_hashed == 0:
                        totalUniqObjs.add(element)
                        local_unique_objs.add(element)
                    else:
                        totalUniqObjs.add(element)
                objOfRegion[region_id] = local_unique_objs
            else:
                send_request_to_regional_leader("[-1]" , region_id , "[-1]")
    
    
    #print(f"All hot paths : {all_hot_paths} , nofObj : {len(totalUniqObjs)} . All regional leaders have sent their data. Proceed with the program.")
    all_HOMOPATHS = {}
    number_of_HoMoPaths =0
    #print(f"PERMUTATIONS : {num_of_permutations}")
    #print(f"Total_NofObjs = {len(totalUniqObjs)}")
    #x = input ()
    #print(len(totalUniqObjs), current_compress , threshold, total_edges, num_of_permutations) 
    totalUniqObjs = list(totalUniqObjs)
    #print(totalUniqObjs)
    #print(len(totalUniqObjs))
    #x =input ()
    """#if raw_or_hashed ==0:
        #for i in range(1, 32001):
            #print(i)
            #if i not in totalUniqObjs :
                #print(f"{i} not found in the unique objs list")
                #c=input ()"""
    write_results_from_Top_Leader_to_file(raw_or_hashed , all_hot_paths ,len(totalUniqObjs), current_compress , threshold, total_edges, num_of_permutations, "Current_Experiment_Top_Leader_flat_visualization_all_together.txt" , "Current_Experiment_Top_Leader_flat_visualization_per_Region_brackets.txt")

    if len(all_hot_paths) > 1:
        list_of_span_homopaths = []
        
        all_HOMOPATHS = {}   # Iterate over all combinations of hot paths from different regions
        for region_id, c_hot_paths1 in all_hot_paths.items():
            if region_id not in all_HOMOPATHS:
                all_HOMOPATHS[region_id] = {} 
            if region_id not in all_HOMOPATHS[region_id]:
                all_HOMOPATHS[region_id][region_id] = {}
            for length, hot_paths1 in c_hot_paths1.items():
                if length >0:
                    if not hot_paths1:
                        continue  # Skip empty hot paths
                    for region_id2, c_hot_paths2 in all_hot_paths.items():
                        if raw_or_hashed == 0:
                            numberOfObjects = len(set(objOfRegion[region_id]).intersection(set(objOfRegion[region_id2])))
                        else:
                            numberOfObjects = num_of_permutations 
                        
                        #numberOfObjects = len(totalUniqObjs)
                        if region_id2 not in all_HOMOPATHS:
                            all_HOMOPATHS[region_id2] = {}
                        if region_id2 not in all_HOMOPATHS[region_id]:
                                all_HOMOPATHS[region_id][region_id2] = {}
                        if region_id2 not in all_HOMOPATHS[region_id2]:
                                all_HOMOPATHS[region_id2][region_id2] = {}

                        if region_id2 != region_id:
                            for length2, hot_paths2 in c_hot_paths2.items():
                                if length2 > 0:
                                    if not hot_paths2:
                                        continue  # Skip empty hot paths  
                                    for hot_path__1 in hot_paths1:                                   
                                        hot_path1 = tuple(hot_path__1)                              
                                        for hot_path2 in hot_paths2:  
                                            hot_path_2 = tuple(hot_path2)
                                            for_sure_intersected_objs = []
                                            if region_id in all_connections and region_id2 in all_connections[region_id] and hot_path1[-1] in all_connections[region_id][region_id2]:
                                                if hot_path2[0] in all_connections[region_id][region_id2][hot_path1[-1]]:
                                                    #print("\n - - - - -  - - - - -  - - - - -  - - - - -  - - - - -  - - - - -  - - - - -  - - - - -  - - - - - ")
                                                    #print(f"\n - - - - - Path {hot_path1} - {hot_path2} span Regions {region_id} - {region_id2} - - - - - ") # work until here   

                                                    #with function_lock:
                                                    objIDs_ofPath1 = send_request_to_regional_leader(1 , region_id , hot_path1) # Top Leader wakes up Region1
                                                    size = get_size(objIDs_ofPath1)
                                                    C2Base_Total_Bytes = C2Base_Total_Bytes +  calculate_transmission_cost(objIDs_ofPath1)
                                                    if raw_or_hashed == 0:
                                                        top_leader_integers_raw += 4
                                                    else:
                                                        top_leader_integers_hashed += 4

                                                    for element in objIDs_ofPath1:
                                                        if raw_or_hashed == 0:
                                                            top_leader_integers_raw += 4
                                                        else:
                                                            top_leader_integers_hashed += 4

                                                    intersected_objs = []
                                                    edges_to_append = []
                                                    not_appendedEdges2 =[]

                                                    count =0
                                                    for edge_of_path2 in hot_path2:
                                                        new_intersected_objs =[] 
                                                        counter_substraction_path2 =0        
                                                        objIDs_ofEdge2 = send_request_to_regional_leader(2 , region_id2 , [edge_of_path2])  # Top Leader wakes up Region2  
                                                        size = get_size(objIDs_ofEdge2)
                                                        C2Base_Total_Bytes = C2Base_Total_Bytes +  calculate_transmission_cost(objIDs_ofEdge2)
                                                        if raw_or_hashed == 0:
                                                            top_leader_integers_raw += 4
                                                        else:
                                                            top_leader_integers_hashed += 4
                                                            
                                                        for element in objIDs_ofEdge2:
                                                            if raw_or_hashed == 0:
                                                                top_leader_integers_raw += 4
                                                            else:
                                                                top_leader_integers_hashed += 4

                                                        if count<1:
                                                            ObjIDS_Path1 = objIDs_ofPath1
                                                            #print(f"Path {hot_path1 } objs :ObjIDS_Path1 -- Edge {edge_of_path2} of path hot_path2 objs : objIDs_ofEdge2")
                                                        else:
                                                            ObjIDS_Path1 = intersected_objs
                                                            #print(f"Path {hot_path1}+{edges_to_append} objs :ObjIDS_Path1 -- Edge {edge_of_path2} of path hot_path2 objs : objIDs_ofEdge2")
                                                
                                                        for obj_of_path1 in ObjIDS_Path1:
                                                            for obj_of_edge2 in objIDs_ofEdge2:
                                                                if obj_of_path1 == obj_of_edge2:           
                                                                    new_intersected_objs.append(obj_of_path1)
                                                                    intersected_objs = new_intersected_objs
                                                                    break
                    
                                                        intersection = len(intersected_objs)
                                                        
                                                        intersectionPercentage =(intersection / numberOfObjects)
                                                        #print(f" *** Intersection's cardinality:{intersection}, Percentage:{intersectionPercentage} ? {threshold}, Intersected_objs: {intersected_objs}. " )
                                                        if (intersectionPercentage) >= threshold:
                                                            all_HOMOPATHS[region_id2][region_id2][hot_path_2] = -1
                                                            counter_substraction_path2 +=1
                                                            #print(f"Pass :{intersectionPercentage} >= {threshold}")
                                                            edges_to_append.append(edge_of_path2)    
                                                            for_sure_intersected_objs = intersected_objs

                                                            if edge_of_path2 == hot_path2[-1]:                
                                                                #print(f"We reached the length . Append the {edges_to_append} to the dict ")
                                                                key_hot_path1 = list(hot_path1) + edges_to_append
                                                                key_hot_path1 = tuple(key_hot_path1)
                                                                if key_hot_path1 not in all_HOMOPATHS[region_id][region_id2]:
                                                                    all_HOMOPATHS[region_id][region_id2][key_hot_path1] = {}
                                                                all_HOMOPATHS[region_id][region_id2][key_hot_path1]=for_sure_intersected_objs                                                                         
                                                                number_of_HoMoPaths +=1
                                                                
                                                                list_of_span_homopaths.append(key_hot_path1)
                                                                break

                                                            else:
                                                                #print(f"Continue to the next edge of the path {hot_path2}")
                                                                count=1
                                                            
                                                            #print(f"New homopa {hot_path1} + {edge_of_path2} of {hot_path2} - append the edge(s){edges_to_append}")
                                                        else:
                                                                    #print(f"Failed :{intersectionPercentage} < {threshold}")
                                                                    if for_sure_intersected_objs :
                                                                        key_hot_path1 = list(hot_path1) + edges_to_append
                                                                        key_hot_path1 = tuple(key_hot_path1)  
                                                                        if key_hot_path1 not in all_HOMOPATHS[region_id][region_id2]:
                                                                            all_HOMOPATHS[region_id][region_id2][key_hot_path1] = {}
                                                                        all_HOMOPATHS[region_id][region_id2][key_hot_path1] = for_sure_intersected_objs
                                                                        number_of_HoMoPaths +=1
                                                                        list_of_span_homopaths.append(key_hot_path1)
                                                                        #print(f"Intersection {key_hot_path1} - {edge_of_path2}= {intersection}, Percentage {intersectionPercentage}<{threshold} .Stop-append-move to next homopa") 
                                                                    #print("End for this compariosn")
                                                                    break 
                                                        
                                                        

                                                    
                                                    
                                                    if edges_to_append:  # Edges
                                                        for edge_2 in hot_path2  : 
                                                            if edge_2 not in edges_to_append:
                                                                not_appendedEdges2.append(edge_2)
                                                        

                                                        if not_appendedEdges2:
                                                            not_appendedEdges_2 = tuple(not_appendedEdges2)
                                                            if not_appendedEdges_2 not in all_HOMOPATHS[region_id2][region_id2]:
                                                                all_HOMOPATHS[region_id2][region_id2][not_appendedEdges_2] = {}
                                                            all_HOMOPATHS[region_id2][region_id2][not_appendedEdges_2] = 0
                                            else:
                                                if hot_path1 not in all_HOMOPATHS[region_id][region_id]:
                                                        all_HOMOPATHS[region_id][region_id][hot_path1] = {}
                                                        all_HOMOPATHS[region_id][region_id][hot_path1] = list(hot_path1)

            # 0.1 Here ended up all the possible connections for path1 so we check if we have found something(If yes then whitelisted = True)
            # If it is True means that "hot_path_1" is part of a Spanning-Homopath and it is not necessary to be here
        end_time1 = time.time()
        #print(f"Exec Time : {end_time1 - start_time1}")
        total_sum =0
        for regions in all_HOMOPATHS.values():
            for paths in regions.values():
                total_sum += len(paths)
        write_results_to_file_ResultsOfExperiments("ResultsOfExperiments.txt" ,number_of_HoMoPaths , total_sum, all_HOMOPATHS, end_time1, start_time1 ,threshold , current_compress)
        with open("Current_Experiment_Info.txt", 'a') as fileofexperiments:
            fileofexperiments.write(f"TOP LEADER\nSpan-HoMoPaths {number_of_HoMoPaths} , Exec Time : {end_time1 - start_time1}\n{all_HOMOPATHS}\n\n\n")
        
        
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
        print("Less than 2 Regions with Homopaths")
        end_time2 = time.time()  
        with open("ResultsOfExperiments.txt", 'a') as fileofexperiments:
            fileofexperiments.write(f"TOP LEADER\nSpan-HoMoPaths : 0\n")
            if all_HOMOPATHS:
                fileofexperiments.write(f"Exec Time : {end_time2 - start_time1}\n")
            fileofexperiments.write(f"#########################################################\n\n\n")
    count = 0

    # Flatten the list and prepare the line to write
    if 'list_of_span_homopaths' not in locals():
        list_of_span_homopaths = []
    list_strings = ['[' + ','.join(map(str, sublist)) + ']' for sublist in list_of_span_homopaths]
    combinded_list_with_brackets = [str(len(totalUniqObjs)), str(threshold), str(total_edges),str(num_of_permutations), str(current_compress), str(0)] + list_strings
    line_to_write_with_brackets = ",".join(combinded_list_with_brackets)
    
    with open("Current_Experiment_Top_Leader_span_homopaths_brackets.txt", "a") as filespanhomopaths:
        filespanhomopaths.write(line_to_write_with_brackets + "\n")

    with open("seeds.txt", "a") as seedsfile:
        seedsfile.write(str(seed) + ";" + line_to_write_with_brackets + "\n")

    
    list_strings = ['[' + ','.join(map(str, sublist)) + ']' for sublist in list_of_span_homopaths]
    if raw_or_hashed==0:
        top_leader_integers= top_leader_integers_raw
    else:
        top_leader_integers= top_leader_integers_hashed
    combinded_list_with_brackets = [str(len(totalUniqObjs)),str(C2Base_Total_Bytes),str(first_level_total_integers), str(threshold), str(total_edges),str(num_of_permutations), str(current_compress), str(0)] + list_strings
    line_to_write_with_brackets = ",".join(combinded_list_with_brackets)
    with open("Current_Experiment_Top_Leader_Reg_Leader_paths_costs.txt", "a") as filespanhomopaths:
        filespanhomopaths.write(line_to_write_with_brackets + "\n")


    if raw_or_hashed==0:
        top_leader_integers= top_leader_integers_raw
    else:
        top_leader_integers= top_leader_integers_hashed
    # After processing all keys, write the accumulated values to another file
    with open("Current_Experiment_Top_Leader_Reg_Leader_edges_costs.txt", "a") as all_values_file:
        line_values_all_together = [str(len(totalUniqObjs)),str(C2Base_Total_Bytes),str(first_level_total_integers), str(threshold), str(total_edges),str(num_of_permutations), str(current_compress), str(0)]      
        #combinded_list_with_brackets = [str(top_leader_integers),str(first_level_total_integers), str(threshold), str(total_edges),str(num_of_permutations), str(current_compress), str(0)] + list_strings
        dict_values_temp = []        
        for key, value in all_hot_paths.items():
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
    



    print()
                                       
    for region_id in  regions_ready_counter:
        send_request_to_regional_leader("[-1]" , region_id , "[-1]")
    #for region_id in  regions_without_Homopa_counter:
        #send_request_to_regional_leader("[-1]" , region_id , "[-1]")

    result = len(regions_ready_counter)
    print(f"Result in top leader : {result}")
    result_queue.put(result)  # Place the result in the queue
    
    

# 4.2
def send_request_to_regional_leader(requestPathORedge, region, path_edge_ID):
    port = region + 5000+11
    host = 'localhost'
    if requestPathORedge != "[-1]" and (requestPathORedge == 1 or requestPathORedge ==2 or requestPathORedge ==3 or requestPathORedge ==4 or requestPathORedge ==5):                               # Break condition sending from the Top Leader after ending with all the possible HomoPaths
        try:
            regional_leader_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            regional_leader_socket.connect((host, port))
            data_to_send = {                                      # Combine values into a dictionary
                'path_edge_ID': path_edge_ID,
                'requestPathORedge': requestPathORedge
            }
            chunk_size = 1024                                        # Send the data in chunks
            if requestPathORedge == 1 or requestPathORedge ==2: 
                if requestPathORedge == 1:
                    string ="PRIMARY"
                    edge_path= "path"
                else:
                    string = "SECONDARY"
                    edge_path= "edge"
                #print(f"2. We are in the client function and we will send {string} request to Region {int(region)}(port: {port}) for the {edge_path} :  {path_edge_ID}") 
                json_string = json.dumps(data_to_send)                # Convert the dictionary to a JSON-formatted string                   
                for i in range(0, len(json_string), chunk_size):
                    chunk = json_string[i:i + chunk_size]
                    regional_leader_socket.send(chunk.encode('utf-8'))
    
                regional_leader_socket.send(b"")                      # Signal the end of the data        
                received_data = b""                                   # Receive the JSON-formatted response in chunks
                while True:
                    chunk = regional_leader_socket.recv(1024)
                    if not chunk:
                        break                                         # No more data to receive
                    received_data += chunk      
                response_data = json.loads(received_data.decode('utf-8') )
                return response_data

            else:
                if requestPathORedge ==3:
                    string = "Homopath_list"
                    #print(f"1. We are in the client function and we will send {string} request to Region {int(region)}(port: {port})")
                    regional_leader_socket.send(json.dumps(string).encode('utf-8'))        
                    received_data = ""
                    while True:
                        chunk = regional_leader_socket.recv(1024).decode('utf-8')
                        if chunk == "-1":
                            #print(f"No homopaths for {port} ({chunk})")
                            received_data_chunk_dict = -1
                            break
                        else:    
                            if not chunk:
                                break
                            received_data += chunk
                            if received_data.endswith('}') and received_data.startswith('{'):
                                received_data_chunk_dict = json.loads(received_data)
                                break
                    return received_data_chunk_dict
                if requestPathORedge ==4:
                    string = "Homopath_NumberOfObjs"
                    #print(f"1. We are in the client function and we will send {string} request to Region {int(region)}(port: {port})\n")
                    regional_leader_socket.send(json.dumps(string).encode('utf-8'))        
                    received_data = ""                                   # Receive the JSON-formatted response in chunks
                    while True:
                        chunk = regional_leader_socket.recv(1024).decode('utf-8')
                        #print("Stop")
                        #print(chunk)
                        #x = input()
                        if not chunk:
                            break                                         # No more data to receive
                        received_data += chunk   
                    #print(f"from sendreq uniq objs : {received_data}")
                    return received_data 
                if requestPathORedge ==5:
                    string = "total_information_integers"
                    #print(f"1. We are in the client function and we will send {string} request to Region {int(region)}(port: {port})\n")
                    regional_leader_socket.send(json.dumps(string).encode('utf-8'))        
                    received_data = ""                                   # Receive the JSON-formatted response in chunks
                    while True:
                        chunk = regional_leader_socket.recv(1024).decode('utf-8')
                        if not chunk:
                            break  # No more data to receive
                        received_data += chunk

                    # Convert the received string back to an integer
                    received_integer = int(received_data)
                    #print(f"from sendreq uniq objs : {received_data}")
                    #x =input()
                    return received_integer 
                            
        except Exception as e:
            #print(f"Error: {e}")
            return None
        finally:
            regional_leader_socket.close()
    else:
        #print(f"Top Leader signal-FINISH to {port}")
        regional_leader_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        regional_leader_socket.connect((host, port))
        regional_leader_socket.send(json.dumps("[-1]").encode('utf-8'))
        regional_leader_socket.close()   
        return None



##########   regional leader   ##########
# 4.3
def start_regional_leader(region_ID, threshold, ready_event, raw_or_hashed, permutations, current_compress,length_of_permutations,help_for_jaccard , factor_forDBscan, limitN):
    with function_lock:
        global regions_ready_counter
        global regions_without_Homopa_counter
        global all_regions_counter

        picturePath =f"map{region_ID}.txt"
        print(f"In start regional leader , RegionalLeaderID = {region_ID}")
        #file_path = "nodes_edges.txt"
        df = pd.read_csv(picturePath, header=None, names=['edge_id', 'node1', 'node2', 'x1', 'y1', 'x2', 'y2'])
        G = nx.Graph()                                                          # Create a graph
        for _, row in df.iterrows():                                            # Add nodes with their x, y coordinates
            G.add_node(row['node1'], pos=(row['x1'], row['y1']))
            G.add_node(row['node2'], pos=(row['x2'], row['y2']))                                                                   
            edge_id = row['edge_id']                                            
            G.add_edge(row['node1'], row['node2'], edge_id=edge_id)             # Ensure edge ID is set as an attribute
        pos_removed = nx.get_node_attributes(G, 'pos')
        plt.figure(figsize=(10, 10))                                            # Draw the graph with real-world coordinates
        nx.draw_networkx_edges(G, pos_removed, width=2, edge_color='black')   # Draw only the edges
        output_file_path = f"depth_{region_ID}.png"                             # Save the plot as a PNG file in the current directory
        plt.savefig(output_file_path)                                           # Display the plot without blocking"""
        #print(f"Reg Leader '{region_ID}' is searching for Homopaths") 
        regions_hot_paths, Uniqueobjs , only_Homopa_RAW_HASHED ,transmission_cost , total_information_integers =  process_region(region_ID , threshold, raw_or_hashed, permutations , current_compress, length_of_permutations, help_for_jaccard , factor_forDBscan, limitN)
        #print(Uniqueobjs)
        #x=input("Uniqueobjs")
        # total_information_integers in function prepare_data returns here "total_information_integers += topic_information_integers" the total number of 
        # integers that the regional leaderX from 1st level  received from its corresponding sensors

        
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

        # In your socket setup code
        # Set the regional port based on region_ID
        regional_port = int(region_ID + 11) + 5000
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow reuse of the address
        server_socket.bind(('localhost', regional_port))
        server_socket.listen(1)


        # Signal that the regional thread is ready
        with all_regions_ready_condition:
            if regions_hot_paths:
                regions_ready_counter.append(region_ID)
                all_regions_counter.append(region_ID)
                print(f"Regional Leader {region_ID} is ready. Counter: {regions_ready_counter}")
            else:
                regions_without_Homopa_counter.append(region_ID) 
                all_regions_counter.append(region_ID)
                print(f"No Homopaths from {region_ID}")
            
            all_regions_ready_condition.notify_all()
        ready_event.set()


    while True: 
        client_socket, client_address = server_socket.accept()             # Ask Regional Leader to send objs based on the request of the Top Leader via socket
        data = client_socket.recv(1024).decode('utf-8')                   # Receiving data in chunks(Chunk size = 1024 bytes)
        received_data_check = json.loads(data)
        if received_data_check == "[-1]":                                 # Top Leader closes/breaks the communication by sending ("[-1]")
            server_socket.close() 
            print("3.From Reg Leader/Thread To EXIT")
            break
        elif  received_data_check == "Homopath_list" or received_data_check == "Homopath_NumberOfObjs" or  received_data_check == "total_information_integers": 
            if regions_hot_paths :
                if received_data_check == "Homopath_list":
                    # Convert the dictionary to a string representation
                    serialized_data = json.dumps({key: [path[0] for path in paths] for key, paths in regions_hot_paths.items()})
                    chunk_size = 1024
                    for i in range(0, len(serialized_data), chunk_size):
                        chunk = serialized_data[i:i + chunk_size]
                        client_socket.send(chunk.encode('utf-8'))
                elif received_data_check == "total_information_integers":
                    chunk = str(total_information_integers)
                    client_socket.send(chunk.encode('utf-8'))


                else:
                    # Convert the set to a string representation
                    set_str = str(Uniqueobjs)

                    chunk_size = 1024
                    for i in range(0, len(set_str), chunk_size):
                        chunk = set_str[i:i + chunk_size]
                        client_socket.send(chunk.encode('utf-8'))
                    #print(f"uniq objs :{chunk}")
                    #x =input()
            else:
                if received_data_check == "Homopath_NumberOfObjs":
                    # Convert the set to a string representation
                    set_str = str(Uniqueobjs)

                    chunk_size = 1024
                    for i in range(0, len(set_str), chunk_size):
                        chunk = set_str[i:i + chunk_size]
                        client_socket.send(chunk.encode('utf-8'))
                else:
                    chunk="-1"
                    client_socket.send(chunk.encode('utf-8'))
                
                

        else:
            #print("2.From Reg Leader/Thread to send paths or edges")
            edge_path_id = data
            while data.endswith("}") is False:                                # We know that all data have been arrived if we receive ("}")
                data = client_socket.recv(1024).decode('utf-8')
                edge_path_id += data                                                                   
            path_edge_ID = received_data_check['path_edge_ID']
            requestPathORedge = received_data_check['requestPathORedge']                                                                 
            obj_ids = find_obj_ids_for_edge_path(requestPathORedge, path_edge_ID, regions_hot_paths) # Process the received data and find obj IDs
            #print(f"AA : Objs: {obj_ids}")
            #x =input()
            client_socket.send(str(obj_ids).encode('utf-8'))                  # Send obj_ids Top Leader                                               
        
        client_socket.close()
    server_socket.close()
    
# 4.4
def process_region(region_ID , threshold, raw_or_hashed, permutations , current_compress,length_of_permutations,help_for_jaccard,factor_forDBscan,limitN):
    if raw_or_hashed==0:  
        sensors_file = f"Regional_4_sensors{region_ID}.txt"
        stringHashed = f""
    else:
        sensors_file = f"Regional_4_sensors_HASHED{region_ID}.txt"
        stringHashed = f"_HASHED_"
    edgeconnections_file = f"Regional_2_edgeconnections{region_ID}.txt"

    if region_ID==10:
        print(f"In process_region {region_ID}")
        #print(sensors_file)
        #print(edgeconnections_file)

    

    # Check if both files exist before processing
    if os.path.exists(edgeconnections_file) and os.path.exists(sensors_file):
        # Apply the HOMOPA function to each pair
        start_time1 = time.time()
        only_Homopa_RAW_HASHED ={}
        only_Homopa_HASHED= {}
        UniqObjs, NumOfObjs, NumOfEdges, HoMoPaths_Dictionary, total_bytes , transmission_cost, total_information_integers = HOMOPA(region_ID,current_compress,raw_or_hashed, permutations,edgeconnections_file, sensors_file, threshold,length_of_permutations,help_for_jaccard,factor_forDBscan,limitN)


        
        #print(HoMoPaths_Dictionary)
        #print(NumOfEdges,len(sensors_file),sensors_file)
        end_time1 = time.time()
        time1 = end_time1 - start_time1
        if not NumOfEdges: 
            NumOfEdges =0
        if not NumOfObjs or NumOfObjs == 0 :
            NumOfObjs =-1


        count_dict = {}
        Number_of_Homopaths = 0
        for key, value in HoMoPaths_Dictionary.items():
            # Get the count of values for each key
            count = len(value)
            Number_of_Homopaths += count
            count_dict[key] = count

        #print(f" *. Region:{region_ID}, Objs/Edges:{NumOfObjs}/{NumOfEdges}={NumOfObjs/NumOfEdges}, Time:{time1} , Threshold:{threshold}")
        if HoMoPaths_Dictionary:
            with open("ResultsOfExperiments.txt", 'a') as fileofexperiments:
                #fileofexperiments.write(f"Version: 4_1 . Checking length of objsid before checking Intersection in TopLeader \nRegion:{region_ID}\n")
                #fileofexperiments.write(f"Objects,{NumOfObjs},Edges,{NumOfEdges},objs/edge,{NumOfObjs/NumOfEdges},NumOfHoMoPaths,{Number_of_Homopaths}\n")
                #fileofexperiments.write(f"Threshold,{100*threshold}%,Exec Time,{time1}\n")
                threshold_comparison = raw_or_hashed +1
                #formatted_paths = ','.join(['[{}]'.format(','.join(map(str, sub_paths_list[0]))) for index, complete_data in enumerate(HoMoPaths_Dictionary.values()) if index != 0 for sub_paths_list in complete_data ])
                
                
                formatted_paths_all = ','.join(['[{}]'.format(','.join(map(str, sub_paths_list[0]))) for index, complete_data in enumerate(HoMoPaths_Dictionary.values()) if index >0  for sub_paths_list in complete_data ])
                formatted_paths_allwithout_single = ','.join(['[{}]'.format(','.join(map(str, sub_paths_list[0]))) for index, complete_data in enumerate(HoMoPaths_Dictionary.values()) if index >1  for sub_paths_list in complete_data ])
                #formatted_paths_pairs = ','.join(['[{}]'.format(','.join(map(str, sub_paths_list[0]))) for index, complete_data in enumerate(HoMoPaths_Dictionary.values()) if index ==2  for sub_paths_list in complete_data ])
                #formatted_paths_threes = ','.join(['[{}]'.format(','.join(map(str, sub_paths_list[0]))) for index, complete_data in enumerate(HoMoPaths_Dictionary.values()) if index ==3  for sub_paths_list in complete_data ])
                #formatted_paths_fourth = ','.join(['[{}]'.format(','.join(map(str, sub_paths_list[0]))) for index, complete_data in enumerate(HoMoPaths_Dictionary.values()) if index ==4  for sub_paths_list in complete_data ])
                #formatted_paths_fives = ','.join(['[{}]'.format(','.join(map(str, sub_paths_list[0]))) for index, complete_data in enumerate(HoMoPaths_Dictionary.values()) if index ==5  for sub_paths_list in complete_data ])

                                                                                                                                                         # here to make index >2 and to stop the recursion when n>2-> so i will have only thirties                            
                list_strings2_all = formatted_paths_all.strip('][').split('],[')              # Remove brackets and split into individual strings
                list_strings_all_without_single = formatted_paths_allwithout_single.strip('][').split('],[')              # Remove brackets and split into individual strings
                #list_strings2 = formatted_paths_allwithout_single.strip('][').split('],[')
                #list_strings3 = formatted_paths_allwithout_single.strip('][').split('],[')
                #list_strings4 = formatted_paths_allwithout_single.strip('][').split('],[')
                #list_strings5 = formatted_paths_allwithout_single.strip('][').split('],[')
                
                formatted_list_all = [[int(num) for num in sublist.split(',')] for sublist in list_strings2_all]      # Convert each string to a list of integers
 
                if raw_or_hashed == 0:  # for RAW
                    if region_ID not in only_Homopa_RAW_HASHED:
                        only_Homopa_RAW_HASHED[region_ID]={}
                        only_Homopa_RAW_HASHED[region_ID] = formatted_list_all
                else: # for HASHED
                    if region_ID not in only_Homopa_RAW_HASHED:
                        only_Homopa_RAW_HASHED[region_ID]={}
                        only_Homopa_RAW_HASHED[region_ID] = formatted_list_all   
                        """if repetition != 1:
                            repetition -= 1"""
                
                #fileofexperiments.write(formatted_paths_all)
                #fileofexperiments.write(formatted_paths_allwithout_single)
                fileofexperiments.write("\n--------------------------------------------------------\n")
            #print(NumOfObjs)

            # calculation for extra integer in hashed+ sensorID and SensorID for raw has been made in prepare_data function
            with open("Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_all.txt", 'a') as fileofexperiments:
                if len(formatted_paths_all)>0:
                    fileofexperiments.write(f"{NumOfObjs},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},{formatted_paths_all}\n")
                else:
                    fileofexperiments.write(f"{NumOfObjs},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},{[0]}\n")

            with open("Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_all_with_costs.txt", 'a') as fileofexperiments_withcosts:
                if len(formatted_paths_all)>0:
                    fileofexperiments_withcosts.write(f"{total_bytes},{transmission_cost},{NumOfObjs},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},{formatted_paths_all}\n")
                else:
                    fileofexperiments_withcosts.write(f"{total_bytes},{transmission_cost},{NumOfObjs},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},{[0]}\n")




            with open("Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_allwithout_single.txt", 'a') as fileofexperiments:
                if len(formatted_paths_allwithout_single)>0:
                    fileofexperiments.write(f"{NumOfObjs},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},{formatted_paths_allwithout_single}\n")
                else:
                    fileofexperiments.write(f"{NumOfObjs},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},{[0]}\n")

           

            with open("Current_Experiment_Info.txt", 'a') as fileofexperiments:
                fileofexperiments.write(f"4_1. {NumOfEdges},{NumOfObjs},{NumOfObjs/NumOfEdges},{threshold}\n{HoMoPaths_Dictionary}\n")
        else:
            with open("Current_Experiment_Compare_RAW_HASh_NEW.txt", 'a') as fileofexperiments:
                fileofexperiments.write(f"{NumOfObjs},{threshold},{NumOfEdges},{permutations},{current_compress},{region_ID},[]\n")

    return HoMoPaths_Dictionary, UniqObjs , only_Homopa_RAW_HASHED , transmission_cost , total_information_integers

# 4.5
def find_obj_ids_for_edge_path(requestPathORedge, request, region_hot_paths):
    for len_hot_paths1, hotpaths in region_hot_paths.items(): 
        if (requestPathORedge == 1 and (len(request) == len_hot_paths1)) or (requestPathORedge == 2 and (len_hot_paths1 == 0) ) :   # Looking for PATH   
            for hot_path1 in hotpaths:
                if hot_path1[0] == request:
                    return hot_path1[1]
   



#############################################################
#--------------------------------------------- #
#              Calculating Homopaths

# hash_function: here ...............
# 5.1
def HOMOPA(region_ID,current_compress, raw_or_hashed, permutations, File_2_edgeconnections, sensors_file_path, threshold, length_of_permutations,help_for_jaccard,factor_forDBscan,limitN):
    print(f"Homopa for Leader : {region_ID}")
    n=1
    edge_connections, NumOfEdges = Dict_Read_Edge_Connections_from_File(File_2_edgeconnections)   # Idea : we are now in re the Reg Leader and he upnoads his edge_connections
    objs_in_edge, UniqObjs, NumOfObjs , total_information_bytes , total_costs, total_information_integers  = prepare_data_from_file(sensors_file_path) # Idea: This simulates the data that the sensros sent. Structure of sensor file: sensorid,objI,..,..,objN
    #print(f"-------------- received_data_transmitted_integers for level 1 for Reg Leader {region_ID}  in Homopa : {total_information_integers}")
    if raw_or_hashed ==1:
        """factor_forDBscan = NumOfObjs*(1-threshold)*(1-threshold)/(NumOfEdges)
        objs_in_edge = heuristic_to_estimate_hot_motion_edge(objs_in_edge,factor_forDBscan)"""
        #NumOfObjs = reduce_list(objs_in_edge, threshold)
        ####################################################
        #     h e r e   to add the mfitem logic from idea6
        id =1
        remove_extra_Integ = 0
        NumOfObjs = _Find_Cardinality_Cohen(objs_in_edge, permutations , remove_extra_Integ)
        print(f" *** Calculated by Cohen : Objs {region_ID} : {NumOfObjs} *** ")
        #hotlist_Cohen_2 = _HoMoEdges(id,Estimation_Cohen_2, remove_extra_Integ , all_data_in_list_form , raw_or_hashed , num_permutations, threshold, compr)
        


    #print(raw_or_hashed,NumOfObjs)

    formatted_paths0 = set()
    for data in objs_in_edge:
            formatted_paths0.add(data[0][0])
    """    formatted_paths
    for data in formatted_paths0 :
        temp_list =[]
        temp_list.append(data)"""
    #print(formatted_paths0)

    formatted_paths = ','.join([f'[{item}]' for item in formatted_paths0])

    """if permutations != -1 :
        # Now, writing into the file without enclosing formatted_paths in another list
        with open("Current_Experiment_Compare_RAW_HASh_NEW.txt", 'a') as fileofexperiments:
            fileofexperiments.write(f"{permutations},{current_compress},{region_ID},{formatted_paths}\n")"""
    
    HoMoPaths_Dictionary  = calculate_obj_id_intersection(region_ID , raw_or_hashed, permutations, edge_connections, objs_in_edge, objs_in_edge, NumOfObjs, threshold,n,length_of_permutations, help_for_jaccard ,NumOfEdges, limitN) # Idea: here we find the homopaths
    return UniqObjs, NumOfObjs , NumOfEdges , HoMoPaths_Dictionary , total_information_bytes , total_costs, total_information_integers



# 5.2
def Dict_Read_Edge_Connections_from_File(file_path):
    Connections_Dict = {}

    with open(file_path, 'r') as file:
        for line in file:
            values = list(map(int, line.strip().split(',')))
            key = values[0]
            Connections_Dict[key] = values[1:]

    return Connections_Dict ,  len(Connections_Dict)


# 5.3
def prepare_data_from_file(sensors_file_path):
    combined_data = []
    UniqObjs = set()
    UniqEdges = set()
    total_information_integers = 0
    with open(sensors_file_path, 'r') as file:
        for line in file:
            topic_information_integers = 0
            parts = line.strip().split(',')
            if raw_or_hashed ==0 :   
                edge_id = int(parts[0])
                topic_information_integers += 1
                UniqEdges.add(edge_id)
                obj_ids = list(set(map(int, parts[1:])))
                for obj in obj_ids:
                    UniqObjs.add(obj)
                    topic_information_integers += 1
                combined_data.append([[edge_id], obj_ids])               # both edge_id and obj_ids are lists
            else:
                hashed_objs = []
                edge_id = int(parts[0])
                topic_information_integers += 1
                number_of_Raw_ObjIDs = int(parts[1])
                topic_information_integers += 1
                #print(number_of_Raw_ObjIDs)
                UniqEdges.add(edge_id)
                obj_ids = list(map(int, parts[2:]))
                for obj in obj_ids:
                    UniqObjs.add(obj)
                    hashed_objs.append(obj)
                    topic_information_integers += 1
                combined_data.append([[edge_id],number_of_Raw_ObjIDs,obj_ids])               # both edge_id and obj_ids are lists

            total_information_integers += topic_information_integers
            total_information_bytes = 4*total_information_integers
            single_cost = 0.0001
            total_costs = round((total_information_bytes * single_cost),4)
    #print(f"-------------- received_data_transmitted_integers for level 1 for Reg Leader in prepare_data function : {total_information_integers}")


    #print(f"Total Number of Objs : {len(UniqObjs)}")
    #print(f"Total Number of Sensors : {len(combined_data)}")
    
    return combined_data, UniqObjs, len(UniqObjs) , total_information_bytes , total_costs, total_information_integers


# 5.4
def calculate_obj_id_intersection(region_ID , raw_or_hashed, permutations, edge_connections, objs_in_edge, Single_Frequent_objs_in_edge, total_obj_count, threshold, n, length_of_permutations, help_for_jaccard ,NumOfEdges,limit,HoMoPaths_Dictionary=None):
    
    #print(f"\n\n################################              Round {n}               ###################################")

    if HoMoPaths_Dictionary is None:            # Create a dictionary to store homopaths and their obj IDs 
        HoMoPaths_Dictionary = {}
    #print(help_for_jaccard,raw_or_hashed,n)


        #print("Results:")
        #print(HoMoPaths_Dictionary)
        #print(Single_Frequent_objs_in_edge)
        #print(objs_in_edge)


        
    Boolean_HoMoPathway_Matrix = []             # Boolean Matrix . Vertic Axe are the paths , Horiz Axe are the single homoedges    
    edge_connections_for_next_Lenght = {}       # In order to keep only edge connections which is possible to produce HoMoPaths. Update at the end, before new recursive call.
    Edge_Object_Mapping = []                    # Update this list in every call - contains the homopaths and their objects (will populate the vertical axe of Boolean Matrix)
    Edge_Object_Mapping_Single_Freq_Edges = []  # Update this list only in the first Call - contains the single frequent edges and their objects (will populate the horizontal axe of Boolean Matrix)


    # Create the 2 following dictionaries in order use their keys and avoid many for loops . Will need here "obj_ids_edge_1 = obj_ids_on_edge[Boolean_HoMoPathway_Matrix[i][0][0]]""
    obj_ids_on_edge = {}                        # Store in a dictionary the list objs_in_edge  [[path1],[obj1,obj2..objN]], [[path2],[obj1,obj2..objN]],......, [[pathX],[obj1,obj2..objN]] ]


    #print(f"objs_in_edge {region_ID} : {objs_in_edge}")

    for edge_data in objs_in_edge:              # objs_in_edge will populate the vertical axe und we use it in order to create a dictionary obj_ids_on_edge 
        edge_id = tuple(edge_data[0])
        if raw_or_hashed == 0:
            obj_ids = edge_data[1]
        else:
            if n==1:
                num_real_obj_ids = edge_data[1]
                obj_ids = edge_data[2]
            else:
                obj_ids = edge_data[1]
        obj_ids_on_edge[edge_id] = obj_ids

    obj_ids_on_edge_SingleFrequent = {}        # Use this dictionary only for phase 2, for the frequent edges
    for edge_data in Single_Frequent_objs_in_edge:
        edge_id = tuple(edge_data[0])
        if raw_or_hashed == 0:
            obj_ids = edge_data[1]
        else:
            if n==1:
                num_real_obj_ids = edge_data[1]
                obj_ids = edge_data[2]
            else:
                obj_ids = edge_data[1]
        obj_ids_on_edge_SingleFrequent[edge_id] = obj_ids


    edge_ids = list(edge_connections.keys())
    # Next loop creates the Boolean Matrix               
    # Initialize a list of edge IDs , will populate the horizontal axis. 
    # Initialize the intersection table with edge IDs in the first row and first column
    # Horizontal Axis pupulates from the single frequent Items which are still in the game(edge_ids) - Vertical Axis populates from the homopaths of the previous call(objs_in_edge)
    Boolean_HoMoPathway_Matrix = [[0 for j in range(len(edge_ids) + 1)] for i in range(len(obj_ids_on_edge) + 1)]
    for i in range(len(objs_in_edge) + 1):
        for j in range(len(edge_ids) + 1):
            if i == 0 and j != 0:
                Boolean_HoMoPathway_Matrix[i][j] = edge_ids[j - 1]
            if j == 0 and i != 0:
                Boolean_HoMoPathway_Matrix[i][j] = objs_in_edge[i - 1][0]

    #print(Boolean_HoMoPathway_Matrix)
    #print(objs_in_edge)
        # 2 for loops in order to check the 2-D Boolean matrix
    for i in range(1, len(objs_in_edge) + 1):    # Vertical                              
        for j in range(1, len(edge_ids) + 1):    # Horizontal   
            intersected_objs = []
            paths_for_next_Round = []
            if n <2:     
                                        # if n<2 means that we are checking the diagonal -> to find the single frequent edges (HoMoEdges)
                if Boolean_HoMoPathway_Matrix[i][0][0] == Boolean_HoMoPathway_Matrix[0][j]: # edgeid
                    

                    
                    obj_ids_edge_1 = obj_ids_on_edge[tuple(Boolean_HoMoPathway_Matrix[i][0])] # objs of edgeid
                    
                    intersected_objs.append(obj_ids_edge_1)
                    
                    intersection = len(set(obj_ids_edge_1))
                    if raw_or_hashed == 1:
                        for info_data in objs_in_edge:
                            #print(info_data, Boolean_HoMoPathway_Matrix[0][j])
                            if info_data[0][0] == Boolean_HoMoPathway_Matrix[0][j]:
                                intersection = info_data[1]
                                #print(intersection)
                                threshold_final = threshold
                                break

                    else:
                        threshold_final = threshold
                    
                    
                    x = ( intersection/total_obj_count )
                    #print(x,intersection,total_obj_count)
                    
                    
                    

                    if x >= threshold_final :#-(threshold_final*0.01):
                        Boolean_HoMoPathway_Matrix[i][j] = 1
                        for path in Boolean_HoMoPathway_Matrix[i][0]:
                            paths_for_next_Round.append(path)
                        Edge_Object_Mapping.append([paths_for_next_Round, obj_ids_edge_1])
                        if n==1:
                            HoMoPaths_Dictionary.setdefault(n-1, []).append([paths_for_next_Round,obj_ids_edge_1])
                            
                        #if raw_or_hashed == 0 :   # # # # # # # # #   ONLY  to debugg jaccard . I take the real homopaths and i test the jaccard index
                            # HoMoPaths_Dictionary_with_corrct_single_HomoEdges.setdefault(n, []).append([paths_for_next_Round,obj_ids_edge_1])
                        
                    


                        HoMoPaths_Dictionary.setdefault(n, []).append([paths_for_next_Round,obj_ids_edge_1])
                        
                        Edge_Object_Mapping_Single_Freq_Edges.append([paths_for_next_Round, obj_ids_edge_1])

                        for key in edge_connections:
                            if paths_for_next_Round[-1] == key:
                                edge_connections_for_next_Lenght[key] = edge_connections[key]
                        break

                
            if n >1:
                
                Edge_Object_Mapping_Single_Freq_Edges = Single_Frequent_objs_in_edge
                for key, values in edge_connections.items():
                    if key == Boolean_HoMoPathway_Matrix[i][0][-1]:                   # key = Last edge of each path on the vertical axis boolean matrix 
                        for edgecon in values:                                        # itterate through the 
                            if edgecon == Boolean_HoMoPathway_Matrix[0][j]:
                                for info in objs_in_edge:
                                    if info[0] == Boolean_HoMoPathway_Matrix[i][0]:
                                        #if raw_or_hashed == 0:
                                        obj_ids_edge_1 = info[1]
                                        #else:
                                            #obj_ids_edge_1 = info[2]
                                        break

                                for info in Single_Frequent_objs_in_edge:
                                    if info[0][0] == Boolean_HoMoPathway_Matrix[0][j]:
                                        obj_ids_edge_2 = info[1]
                                        break

                                for obj1 in obj_ids_edge_1:
                                    for obj2 in obj_ids_edge_2:
                                        if obj1 == obj2:
                                            intersected_objs.append(obj1)
                                            break

                                if raw_or_hashed == 1:
                                    x = permutations
                                else:
                                    x= total_obj_count
                                intersection = len(intersected_objs)
                                if (intersection/x)  >= threshold:
                                    Boolean_HoMoPathway_Matrix[i][j] = 1
                                    if key != edgecon:
                                        if Boolean_HoMoPathway_Matrix[0][j] in Boolean_HoMoPathway_Matrix[i][0]: # this "if" helps to avoid loops
                                            #print(f"Avoid Loop : Intersected objs table vlaue o j  {Boolean_HoMoPathway_Matrix[0][j]} , {Boolean_HoMoPathway_Matrix[i][0]}")
                                            continue
                                        for path in Boolean_HoMoPathway_Matrix[i][0]:
                                            paths_for_next_Round.append(path)
                                        paths_for_next_Round.append(Boolean_HoMoPathway_Matrix[0][j])
                                        HoMoPaths_Dictionary.setdefault(n, []).append([paths_for_next_Round,intersected_objs])
                                        Edge_Object_Mapping.append([paths_for_next_Round, intersected_objs])
                                    for key1 in edge_connections:
                                        #print(paths_for_next_Round)
                                        if len(paths_for_next_Round)>0 :
                                            if paths_for_next_Round[-1] == key1 :
                                                edge_connections_for_next_Lenght[key1] = edge_connections[key1]

            
    #print(f"1. Important : {region_ID}")        
    if help_for_jaccard == 1 and raw_or_hashed ==0 and n==1 :
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
    if int(n) > 1 and int(n) in HoMoPaths_Dictionary:
        for path in HoMoPaths_Dictionary[int(n)]:
            for i in range(len(path[0]) - (int(n) - 1)):
                sub_shinglees = [path[0][i:i + int(n) - 1] for i in range(len(path[0]) - (int(n) - 2))]
                for sub_shingle in sub_shinglees:
                    for path2 in HoMoPaths_Dictionary[int(n) - 1]:
                        if sub_shingle == path2[0]:
                            HoMoPaths_Dictionary[int(n) - 1].remove(path2)



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



    #username = input("\n B:")
    #print(HoMoPaths_Dictionary)
    #for path in HoMoPaths_Dictionary:
        #print(path)

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
 
    time.sleep(1)

    limit =100
    if len(Edge_Object_Mapping) > 0 and n <limit:
        #print(f" Print the HoMoPaths_Dictionary before recursion \n , limit : {limit}")
        calculate_obj_id_intersection(region_ID , raw_or_hashed, permutations , edge_connections_for_next_Lenght, Edge_Object_Mapping, Edge_Object_Mapping_Single_Freq_Edges, total_obj_count, threshold, int(n)+1 ,length_of_permutations, help_for_jaccard, NumOfEdges,limit,  HoMoPaths_Dictionary)
    else:
        print(f"Max length of HoMoPath = {n-1}")  
    

    return HoMoPaths_Dictionary


#   C O H E N    2  #
def _Find_Cardinality_Cohen(combined_data, num_perm, remove_extra_Integ):
    listOfMinhash_sign = []

    for item in combined_data:
        if remove_extra_Integ == 1:
            # When remove_extra_Integ == 1, the structure is [[edge_id], obj_ids]
            if len(item) == 2:  # Ensuring the structure matches expectation
                minHashSignatures = item[1] % (1 << 32)
                listOfMinhash_sign.append(minHashSignatures)
        else:
            # When remove_extra_Integ == 0, the structure includes the extra integer: [[edge_id], number_of_Raw_ObjIDs, obj_ids]
            if len(item) == 3:  # Ensuring the structure matches expectation
                minHashSignatures = item[2]
                listOfMinhash_sign.append(minHashSignatures)

    cardinality = _Cohen(listOfMinhash_sign, num_perm)
    
    return int(cardinality)
    


def _Cohen(listOfMinhash_sign , num_perm):
    # Transpose the matrix to work with columns as if they were rows
    transposed_matrix = list(zip(*listOfMinhash_sign))
    min_values = [min(column) for column in transposed_matrix]
    total_sum = sum(min_values)
    cardinality = num_perm / (total_sum/_max_hash) - 1
    return cardinality



import osmnx as ox


##############################################################################################################
#--------------------------------------------- #
            # MAIN

def main(raw_or_hashed, seed, current_compress, permutations, num_objs, length_of_path, threshold, depth, help_for_jaccard, factor_forDBscan, choice_place, run_once, repeat_experiment, limitN , folderOfRepeatExperiment):
    print(f"place in main : {choice_place}")

    File_1_combined_nodes_edges = "1_combined_nodes_edges.txt"
    File_2_edgeconnections = "2_edgeconnections.txt"
    File_3_Motions_file = "3_Motions.txt"
    File_4_sensors_FILE = "4_sensors.txt"
    File_4_sensors_HASHED_FILE = "4_sensors_HASHED.txt"
    prefix_file_Name_map, prefix_file_Name_Regional, prefix_file_Name_Picture = "map", "Regional", "Picture"
    analysis_File = "Current_Experiment_Compare_RAW_HASh_NEW.txt"
    results_all = "ResultsOfExperiments.txt"
    experiment_creator = "experiment_creator.py"
    homopa_python_code = "homopa.py"
    History7z = "History.7z"
    #repeat_experiment = 1  # Assuming repeat_experiment is a function argument

    if raw_or_hashed == 0:
        file_sensor = File_4_sensors_FILE
    else:
        file_sensor = File_4_sensors_HASHED_FILE
    print("hey1")

    if threshold > 0.01 :
        #print(f"Threshold = {threshold}")
        if raw_or_hashed == 0:
            if run_once == 0:
                # delete_files_except(run_once, History7z ,threshold, experiment_creator , homopa_python_code , "4_1.py", analysis_File , "correcthomoedges.json","4_sensors.txt",None,None,None,None)
                #print("1. delete files of prev experiment : DONE")
                #print(choice_place)
                G, north, south, east, west, place_name = create_network(File_1_combined_nodes_edges, prefix_file_Name_Picture, choice_place)
                #print(place_name)
                #print("2. Create Network : DONE")
                total_edges = find_connected_edges(File_1_combined_nodes_edges, File_2_edgeconnections)
                #print("3. Find Connected Edges : DONE")

                if repeat_experiment == 0: # these files i dont have to create them again
                    create_motions(G, length_of_path, num_objs, File_1_combined_nodes_edges, File_3_Motions_file)
                    #print("4. Create Motions : DONE")
                    #x = input()
                    write_data_to_sensors_file(File_3_Motions_file, File_4_sensors_FILE, num_objs, total_edges, north, south, east, west, place_name)
                    #print("5. Write data to sensors file : DONE")
                else:
                    write_data_to_sensors_file(File_3_Motions_file, File_4_sensors_FILE, num_objs, total_edges, north, south, east, west, place_name)
                    # Logic to search for the appropriate folder and copy files
                    found_folder = None
                    for folder in os.listdir('.'):
                        
                        if folder == folderOfRepeatExperiment:
                            #print(folder,folderOfRepeatExperiment)
                            #stop = input()
                            parts = folder.split('_')
                            if len(parts) == 7:
                                _, folder_numOfEdges, folder_numOfObjs, folder_Threshold, folder_lengthOfPaths, folder_mapid, folder_dateTimeStamp = parts
                                if int(folder_numOfObjs) == num_objs and int(folder_mapid) == choice_place:
                                    found_folder = folder
                                    break

                    if found_folder:
                        #print(f"Found folder: {found_folder}")
                        source_3_Motions_file = os.path.join(found_folder, File_3_Motions_file)
                        source_4_sensors_file = os.path.join(found_folder, File_4_sensors_FILE)
                        if os.path.exists(source_3_Motions_file) and os.path.exists(source_4_sensors_file):
                            shutil.copy(source_3_Motions_file, File_3_Motions_file)
                            shutil.copy(source_4_sensors_file, File_4_sensors_FILE)
                            #print("Files copied successfully")
                        #else:
                            #print("Required files not found in the folder")
                    #else:
                        #print("No matching folder found")

                main_partitioning_map_(File_1_combined_nodes_edges, prefix_file_Name_map, prefix_file_Name_Regional, prefix_file_Name_Picture, depth)

            else:
                #print("1. Running the same experiment")
                total_edges= find_connected_edges(File_1_combined_nodes_edges , File_2_edgeconnections)
                main_partitioning_map_(File_1_combined_nodes_edges, prefix_file_Name_map , prefix_file_Name_Regional , prefix_file_Name_Picture, depth)
            
            length_of_permutations =1
            

        else:

            total_edges= find_connected_edges(File_1_combined_nodes_edges , File_2_edgeconnections)

    
    
            length_of_permutations = permutations
            delete_files_except(run_once , History7z ,threshold, homopa_python_code , "4_1.py", 
                                experiment_creator, results_all, analysis_File , File_4_sensors_HASHED_FILE, 
                                File_1_combined_nodes_edges , File_2_edgeconnections, File_3_Motions_file , File_4_sensors_FILE )
            
    
            
        print("hey2")
        
        
        """
        #-------------    Plot Graph without Motions    -------------#
        df = pd.read_csv(File_1_combined_nodes_edges, header=None, names=['edge_id', 'node1', 'node2', 'x1', 'y1', 'x2', 'y2'])
        G = nx.Graph()                                                          # Create a graph
        for _, row in df.iterrows():                                            # Add nodes with their x, y coordinates
            G.add_node(row['node1'], pos=(row['x1'], row['y1']))
            G.add_node(row['node2'], pos=(row['x2'], row['y2']))                                                                   
            edge_id = row['edge_id']                                            
            G.add_edge(row['node1'], row['node2'], edge_id=edge_id)             # Ensure edge ID is set as an attribute
        pos_removed = nx.get_node_attributes(G, 'pos')
        plt.figure(figsize=(10, 10))                                            # Draw the graph with real-world coordinates
        nx.draw_networkx_edges(G, pos_removed, width=0.1, edge_color='black')   # Draw only the edges
        output_file_path = f"depth_map.png"                                        # Save the plot as a PNG file in the current directory
        plt.savefig(output_file_path)                                           # Display the plot without blocking

        
        with open("Current_Experiment_Info.txt", 'a') as fileofexperiments:
            fileofexperiments.write(f"NumOfEdges,NumOfObjs,ratio,threshold,Number_of_Homopaths\n")
        """

        
        print("hey3")
        if depth != 0:
            regionids = create_edgeConnections_and_sensorInfo_for_each_Region(File_2_edgeconnections, file_sensor, prefix_file_Name_map)
            #print(regionids)
        else:
            regionids = create_edgeConnections_and_sensorInfo_for_each_Region(File_2_edgeconnections, file_sensor, prefix_file_Name_map)
            
            regionids = [10]
        clean_regionids = []
        for region in regionids:
            #print (region)
            #print(region/(10**depth))
            if int((region/(10**depth))) > 0:
                clean_regionids.append(region)

        all_connections = create_RegionConnections_for_Top_Leader()

        if raw_or_hashed == 0:
            raw_or_hashed_string = f"RAW"
        else: 
            raw_or_hashed_string = f"HASHED"
        #print(f"-------------------")
        #print(f"\n\nNew Round : \nData is : {raw_or_hashed_string}\nThreshold: {threshold}\nSeed: {seed} , Compress: {current_compress} , Permutations: {permutations}\n")
        #print(f"Objects: {num_objs}")

    #-------------         -------------#
        #print("\nTOP LEADER ON - Thread ")
        result_queue = queue.Queue()
        top_leader_thread = threading.Thread(target=start_Top_leader, args=(clean_regionids, all_connections, threshold , total_edges ,  current_compress , permutations , raw_or_hashed , seed , result_queue))
        top_leader_thread.start()
        #print(f"Top Leader Started : {top_leader_thread} ")

        # Create a Queue to hold the result
        print("hey3")
        clear_lists()
        regional_threads = []
        for regionID in clean_regionids: 
            port=regionID+seed
            #print(f"Region id : {regionID}")
            # THREADING  -  here begins the regional threads
            regional_thread = threading.Thread(target=start_regional_leader, args=(regionID, threshold, threading.Event(), raw_or_hashed, permutations, current_compress,length_of_permutations,help_for_jaccard,factor_forDBscan , limitN))
            regional_thread.start()
            #print(f"Reg Leader Started : {regional_thread} ")
            regional_threads.append(regional_thread)              # Store the thread object in the list
        
        if raw_or_hashed == 0 :
            time.sleep(10)
        else:
            time.sleep(5)
        for thread in regional_threads:   
            thread_complete()                                  # Wait for all regional threads to finish
            time.sleep(1)
            thread.join()
            time.sleep(1)
        top_leader_thread.join()  
        thread_complete()
        resultttt = result_queue.get()
        #print(f"Result in main in homopa : {resultttt}")
        #x =input()


        #while completed_threads < len(clean_regionids) + 1:
            #print(f"Complete Threads : {completed_threads}")   

        thread_init()           
        if raw_or_hashed == 0 :
            time.sleep(2)  
        else:
            time.sleep(2)  

        #print("All threads have finished.")
        print(f"Result in main in homopa : {resultttt}")
    else:
        resultttt = 1
    return resultttt


    

if __name__ == "__main__":
    raw_or_hashed = int(sys.argv[1])
    seed = int(sys.argv[2])
    current_compress = int(sys.argv[3])
    num_of_permutations = int(sys.argv[4])
    num_objs = int(sys.argv[5])
    length_of_path = int(sys.argv[6])
    threshold = float(sys.argv[7])
    depth = int(sys.argv[8])
    help_for_jaccard=  int(sys.argv[9])
    factor_forDBscan=  float(sys.argv[10])
    choice_place = int(sys.argv[11])
    run_once = int(sys.argv[12])
    repeat_experiment = int(sys.argv[13])
    limitN = int(sys.argv[14])
    folderOfRepeatExperiment = str(sys.argv[15])


resultttt = main(raw_or_hashed, seed, current_compress , num_of_permutations, num_objs, length_of_path, threshold, depth, help_for_jaccard,  factor_forDBscan, choice_place , run_once, repeat_experiment ,limitN , folderOfRepeatExperiment)
# Example of your last printed output
with open('output.txt', 'w') as f:
    f.write(str(resultttt))
print(resultttt)  # Optionally still print it