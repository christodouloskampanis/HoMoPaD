import subprocess
import time
import csv
import pandas as pd
import os
import shutil
from datetime import datetime
from datasketch import MinHash
import csv
import re
import random
# Open the file in write mode
with open("Current_Experiment_Compare_RAW_HASh_NEW.txt", "w") as file:
    # No need to write anything, just opening it in write mode creates an empty file
    pass



# list = ['Experiment_651_16000_15_35_14_20241031075046','Experiment_651_32000_15_37_14_20241031172057','Experiment_651_16000_15_35_14_20241031115753' , 'Experiment_651_16000_15_37_14_20241031095400' , 'Experiment_651_16000_15_37_14_20241101023924' , 'Experiment_651_32000_3_35_14_20241030225652', ]

#####################################################################################################
#--------------------------------------------- #
#               E X P E R I M E N T  


def run_script(raw_or_hashed, seed, current_compress, permutation, num_objs, length_of_path, threshold, depth, help_for_jaccard, factor_forDBscan, choice_place, run_once, repeat_experiment, limitN, subfolder):
    script_path = "homopa.py"
    
    # Start the subprocess
    process = subprocess.Popen(
        ["python", script_path, str(raw_or_hashed), str(seed), str(current_compress), str(permutation), str(num_objs), str(length_of_path), str(threshold), str(depth), str(help_for_jaccard), str(factor_forDBscan), str(choice_place), str(run_once), str(repeat_experiment), str(limitN), str(subfolder)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,  # Handle strings instead of bytes
        bufsize=1  # Line buffered
    )
    
    last_output = None  # Initialize last_output

    # Read output line by line
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())  # Print the output as it is generated
            try:
                last_output = int(output.strip())  # Try to capture the last printed integer
            except ValueError:
                pass  # Ignore lines that aren't integers

    # Wait for the subprocess to finish
    process.wait()
    
    # Check if the script executed successfully
    if process.returncode == 0:
        if last_output is not None:
            print("Last output from the script:", last_output)
            return last_output
        else:
            print("No integer output received from the script.")
            return None
    else:
        print("Script failed with error:", process.stderr.read())
        return None






def copy_file(source_file, destination_file):
    print("In copyFile function")
    try:
        shutil.copyfile(source_file, destination_file)
        print(f"File {source_file} successfully copied to {destination_file}")
    except IOError as e:
        print(f"Unable to copy file. {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")











def hash_data(file_path, num_perm, seed, File_4_sensors_HASHED_FILE, threshold):
    with open(file_path, 'r') as file:  # Read data from file
        lines = file.readlines()
    lines_with_values = [(line, [int(value) for value in line.strip().split(',')]) for line in lines]
    sorted_lines_with_values = sorted(lines_with_values, key=lambda x: x[1][1])
    sorted_lines = [line for line, _ in sorted_lines_with_values]
    lines = sorted_lines
    hashed_data = []
    
    for line in lines:  # Process each line
        line = line.strip().split(',')
        sensor_id = line[0]
        obj_ids = line[1:]
        number_of_Raw_ObjIDS = len(obj_ids)
        new_m = []
        
        if len(obj_ids) >= 1:
            data = set(obj_ids)  # Create data set
            #print(f"In hash function: seed: {seed}, numPermutations: {num_perm}, first obj {obj_ids[0]}")
            m = MinHash(seed=seed, num_perm=num_perm)  # Initialize MinHash object
            
            for d in data:
                m.update(d.encode('utf8'))
            
            # Convert each hash value to a 64-bit value
            for value in m.hashvalues:
                value64 = int(value) & ((1 << 32) - 1)  # Ensure 64-bit hash value
                new_m.append(value64)
            
            hashed_data.append((sensor_id, number_of_Raw_ObjIDS, new_m))
    
    # Write hashed data to the specified file
    with open(File_4_sensors_HASHED_FILE, 'w') as out_file:
        for entry in hashed_data:
            out_file.write(f"{entry[0]},{entry[1]},{','.join(map(str, entry[2]))}\n")
    
    return hashed_data



def keep_specific_files_and_folders(run_once, repeat_experiment):
    current_directory = os.getcwd()
    if run_once ==0 and repeat_experiment == 0:
        files_to_keep = {'analysis.py', 'experiment_creator.py', 'homopa.py', 'RESULTS.txt',"testing_pairs.py" ,"preparation.py"}
    elif run_once == 0 and repeat_experiment==1:
        files_to_keep = {'analysis.py', 'experiment_creator.py', 'homopa.py', 'RESULTS.txt', "3_Motions.txt", "4_sensors.txt","testing_pairs.py","preparation.py", "1_combined_nodes_edges.txt" ,"2_edgeconnections.txt"}

    else:
        files_to_keep = {'analysis.py', 'experiment_creator.py', 'homopa.py', "testing_pairs.py", 'RESULTS.txt', "4_sensors.txt" , "preparation.py","1_combined_nodes_edges.txt", "2_edgeconnections.txt", "3_Motions.txt" ,"7_ConnectionsBetween_Regions.txt"}
    for item in os.listdir(current_directory):
        item_path = os.path.join(current_directory, item)
        if os.path.isfile(item_path) and item not in files_to_keep:           # Check if it's a file and not in the list of files to keep
            os.remove(item_path)
            #print(f"Deleted file: {item}")
        elif os.path.isdir(item_path) and item not in files_to_keep:                  # Check if it's a directory and not in the list of files to keep
            if  item.startswith("Experiment_") :
                    continue
            shutil.rmtree(item_path)
            #print(f"Deleted folder: {item}")


    


def read_top_leader_file(file_path):
    top_leader_dict = {}
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            threshold = float(row[3])
            permutation = int(row[5])
            key = (threshold, permutation)
            top_leader_dict[key] = row
    return top_leader_dict

def read_compare_file(file_path):
    compare_dict = {}
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            threshold = float(row[1])
            permutation = int(row[3])
            key = (threshold, permutation)
            pairs = row[6:]
            if key not in compare_dict:
                compare_dict[key] = []
            for pair in pairs:
                pair = pair.strip()
                if pair != '[0]':
                    compare_dict[key].append(pair)
    return compare_dict

def process_pairs(pairs_list):
    processed_list = []
    all_numbers = []

    # Extract all integers from the pairs
    for pair in pairs_list:
        numbers = re.findall(r'\d+', pair)
        all_numbers.extend(numbers)

    # Form pairs of integers
    for i in range(0, len(all_numbers), 2):
        if i + 1 < len(all_numbers):
            first, second = all_numbers[i], all_numbers[i + 1]
            processed_pair = f"{first.zfill(3)}000{second.zfill(3)}"
            processed_list.append(processed_pair)

    return processed_list

def write_output_file(file_path, top_leader_dict, compare_dict):
    with open(file_path, 'w', newline='') as file:
        writer = csv.writer(file)
        for key, top_leader_row in top_leader_dict.items():
            if key in compare_dict:
                processed_pairs = process_pairs(compare_dict[key])
                # Join processed pairs into a string with brackets
                processed_pairs_str = '[' + ','.join(processed_pairs) + ']'
                # Create new row with processed pairs
                new_row = top_leader_row[:8] + [processed_pairs_str]
                writer.writerow(new_row)
            else:
                new_row = top_leader_row[:8] + ['']
                writer.writerow(new_row)

def remove_double_quotes_from_file(file_path):
    lines = []
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip().replace('"', '')
            lines.append(line)
    
    with open(file_path, 'w') as file:
        for line in lines:
            file.write(line + '\n')

def create_testing_file_for_pairs(compare_file_path, top_leader_file_path, output_file_path):
    # Read files and process data
    top_leader_dict = read_top_leader_file(top_leader_file_path)
    compare_dict = read_compare_file(compare_file_path)

    # Write the output file
    write_output_file(output_file_path, top_leader_dict, compare_dict)

    # Remove double quotes from each line of the output file
    remove_double_quotes_from_file(output_file_path)







def extract_Infos_from_Experiment_folders(folder):
    # Get the current working directory
    current_directory = os.getcwd()
    
    folder_pattern = re.compile(r'Experiment_(\d+)_(\d+)_(\d+)_(\d+)_(\d+)_.*')
    
    # Construct the full path to the folder
    folder_path = os.path.join(current_directory, folder)
    
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        # Extract variables from the folder name
        match = folder_pattern.match(folder)
        if match:
            num_of_edges = int(match.group(1))
            num_of_objs = int(match.group(2))
            threshold = int(match.group(3))
            avg_length_path = int(match.group(4))
            map_id = int(match.group(5))
            
            print(f"Folder: {folder}")
            print(f"num_of_edges: {num_of_edges}")
            print(f"num_of_objs: {num_of_objs}")
            print(f"threshold: {threshold}")
            print(f"avg_length_path: {avg_length_path}")
            print(f"map_id: {map_id}")
            
            # Path to the seeds.txt file
            seeds_file = os.path.join(folder_path, 'seeds.txt')
            
            if os.path.exists(seeds_file):
                with open(seeds_file, 'r') as file:
                    lines = file.readlines()
                    if len(lines) > 1:
                        seed = int(lines[1].split(';')[0])
                        if seed >= 0:
                            print(f"First value of the second line in seeds.txt: {seed}")
                            
                            # Paths to the specific files to be copied
                            motion_file = os.path.join(folder_path, '3_Motions.txt')
                            sensor_file = os.path.join(folder_path, '4_sensors.txt')
                            
                            # Check if files exist before copying
                            if os.path.exists(motion_file):
                                shutil.copy(motion_file, current_directory)
                                print(f"Copied {motion_file} to {current_directory}")
                            else:
                                print(f"{motion_file} does not exist")
                                
                            if os.path.exists(sensor_file):
                                shutil.copy(sensor_file, current_directory)
                                print(f"Copied {sensor_file} to {current_directory}")
                            else:
                                print(f"{sensor_file} does not exist")
                        else:
                            print(f"First value of the second line in {seeds_file} is negative: {seed}")
                    else:
                        print(f"{seeds_file} does not have enough lines")
            else:
                print(f"{seeds_file} does not exist")
        else:
            print(f"Folder name {folder} does not match the expected pattern")
    else:
        print(f"Folder {folder_path} does not exist or is not a directory")


    return num_of_edges , num_of_objs , threshold , avg_length_path , map_id , seed



def copy_files(subfolder, file1, file2 , file3,  target_file='all_with_costs.txt'):
    # Get the current directory
    initial_directory = os.getcwd()
    
    # Construct the path to the subfolder within the current directory
    source_folder = os.path.join(initial_directory, subfolder)
    
    extracted_data = {}  # Dictionary to store results

    try:
        # Navigate to the subfolder
        os.chdir(source_folder)
        
        # Copy the two files back to the initial directory
        shutil.copy(file1, initial_directory)
        shutil.copy(file2, initial_directory)
        shutil.copy(file3, initial_directory)
        print(f"Successfully copied {file1} and {file2} and {file3}  back to {initial_directory}")
        print(file2)
        
        # Check if the target file exists
        if os.path.exists(target_file):
            print(f"Found {target_file}. Extracting information...")
            
            # Flag to track whether to start processing lines
            processing = False
            
            # Open and read the target file
            with open(target_file, 'r') as file:
                line_counter =0
                prev_col7 = -1
                prev_col6 = -1
                for line in file:
                    # Split the line by commas
                    fields = line.strip().split(',')
                    
                    # Parse the 6th and 7th columns
                    
                    col6 = int(fields[5])  # 6th column (index 5)
                    col7 = int(fields[6])  # 7th column (index 6)
                    #print(col6,col7)
                    
                    # Start processing if we find a line with both values == -1
                    if col6 == -1 and col7 == -1:
                        if line_counter != 0:
                            if prev_col6 == -1 and prev_col7 == -1:
                                continue
                            else:
                                if processing:  # If already processing, break out of the loop
                                    break
                                processing = True  # Start processing

                        else : 
                            prev_col6 == -1
                            prev_col7 == -1
                            continue



                        
                    
                    # If we're in the processing phase, add entries to the dictionary
                    else:
                        extracted_data[col7] = col6  # Key: 7th col, Value: 6th col
                        processing = True  # Start processing


                    prev_col6 = col6
                    prev_col7 = col7
                    line_counter = line_counter + 1
            
            print("Extraction complete.")
            print(extracted_data)
            #stop = input ()
        
        else:
            print(f"Error: {target_file} not found in {source_folder}")

        
    
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    finally:
        # Return to the initial directory
        os.chdir(initial_directory)
    
    return extracted_data



   


#####################################################################################################
#--------------------------------------------- #
#               m a i n 

def main_function():
    analysis_File      = "Current_Experiment_Compare_RAW_HASh_NEW.txt"
    csv_results        = "Current_Experiment_Compare_RAW_HASh_NEW.csv"
    File_4_sensors_HASHED_FILE = "4_sensors_HASHED.txt"
    File_4_sensors = "4_sensors.txt"
    with open(analysis_File, 'w') as file:
        file.write("\n")
    threshold_real = 0 
    
    

    if __name__ == "__main__":

        
        limitN = 1000000
        
        #places =[1,2,3,4,5]
        #maps =[7,13,14]
        # small_maps = [16,17,18]
        #maps =[13]
        maps =[16]
        #maps =[1]
        listof_Seeds = []
        # Experiment Infos
        depth  = 0
        number_of_repetitions = 1

        #my_compression_levels = [128,64,32,16,8,4,2]
        my_compression_levels = [128,64,32,16,8,4,2]
        #my_compression_levels = [64,32,16,8,4,2]

        #my_compression_levels = [2]
        

        my_length_of_pathh_levels = [10,20,40]
        my_length_of_pathh_levels = [20]
        #my_length_of_pathh_levels = [38]
        #my_threshold_levels = [20,19,5,6,10,11,7,18,14,15,17,16,13,12,9,8,4,3]
        my_threshold_levels = [80,75,70,65,60,55,50,45,40,35,30,25,20,15,10]
        #my_threshold_levels = [60]
        #my_threshold_levels = [10]
        #my_threshold_levels = [20,19]

        #my_threshold_levels = [20,5]

        my_numo_objs_levels = [1000,2500,5000,10000,25000,50000]
        
        #my_numo_objs_levels = [2500,5000,10000,15000,20000,25000,30000,40000,50000]

        my_numo_objs_levels = [1000]
        

        #proceed = int(input("Proceed with next experiment?"))
        

        # Analayis Infos
        #jaccard_threshold  = 0.1
        #verlap_threshold  = 0.1
        factor_forDBscan = 5.5
        #seed = 255436 #7mpaid
        #seed = 5671 #13mapid
        #seed = 123456 #13mapid
        #seed = 2356489 #7mpaid
        #seed = 235456
        #seed = 235456
        seed = 12345

        
        folders_for_specific_repetition_for_checking_pairs = [
        'Experiment_601_4000_4_38_13_20240609155320', 'Experiment_601_8000_3_38_13_20240528015232', 'Experiment_601_16000_3_38_13_20240616055250','Experiment_601_32000_3_39_13_20240615173842', 
        'Experiment_651_4000_4_38_14_20240607090400', 'Experiment_651_8000_4_38_14_20240607193129','Experiment_651_16000_4_39_14_20240608085817', 'Experiment_651_32000_4_39_14_20240608161946', 
        'Experiment_650_4000_4_35_7_20240609213351','Experiment_650_8000_2_35_7_20240521171059', 'Experiment_650_16000_3_35_7_20240525054805', 'Experiment_650_32000_3_38_7_20240613151237',]
        

        #folders_for_specific_repetition_for_checking_pairs = ['Experiment_651_4000_4_38_14_20240607090400']
        
        
        #folders_for_specific_repetition_for_checking_pairs = ['Experiment_1_1000_10_10_16_20241106023533']

        for folder in os.listdir():
            if folder.startswith('Experiment_183'):
                if folder.endswith("NO"):
                    continue
                else:
                    folders_for_specific_repetition_for_checking_pairs.append(folder)
        print(folders_for_specific_repetition_for_checking_pairs)
        #folders_for_specific_repetition_for_checking_pairs = ['Experiment_1_5000_10_10_16_20241106040814']
        folders_for_specific_repetition_for_checking_pairs = ['Experiment_1_1000_10_20_16_20241115235246',
                                                              "Experiment_1_2500_10_20_16_20241116174427", 
                                                              "Experiment_1_5000_10_20_16_20241117011944",
                                                              "Experiment_1_10000_10_20_16_20241117185024",
                                                              "Experiment_1_25000_10_20_16_20241118095336"]


        folders_for_specific_repetition_for_checking_pairs = ['Experiment_180_2500_10_20_19_20241209023148']
        testing_pairs = 0
        repeat_experiment = 0
        help_for_jaccard = 0

        if repeat_experiment == 1:
            #if testing_pairs == 1 :
            range_of_repetitions = len(folders_for_specific_repetition_for_checking_pairs)
            range_of_repetitions = 50

            places = folders_for_specific_repetition_for_checking_pairs
           
            #elif testing_pairs == 0:
                #range_of_repetitions = 100
                #places = folders_for_specific_repetition_for_checking_pairs
                
        else:
            range_of_repetitions = 20
            places = maps
            
        run_once=0
        for i in range(0,15):
            if i<2:
                repeat_experiment = 0
                help_for_jaccard = 0
            else:
                repeat_experiment = 1
                help_for_jaccard = 1


            subfolder = places[0]
            #subfolder = 'Experiment_651_4000_4_38_14_20240607090400'
            #subfolder ='Experiment_601_4000_3_38_13_20240526222737'
            file1 =  '1_combined_nodes_edges.txt'
            file2 =  '2_edgeconnections.txt'
            file3 = '3_Motions.txt'
            file4 = '4_sensors.txt'
            
            if repeat_experiment ==1:
                dictionaryWithComprAndPermut = copy_files(subfolder, file1, file2 , file3)
                print("User must put files for Motion and Sensor. In case it will fail, please check if these files are available")
            for choice_place_to_run in places: #places[:0]
                #if choice_place == 7:
                    #seed = 1234
                #else:
                    #seed = 12345
                #if testing_pairs == 1 and repeat_experiment == 1:
                if  repeat_experiment == 1:
                    num_of_edges , num_of_objs , threshold , avg_length_path , map_id, seed_init = extract_Infos_from_Experiment_folders(choice_place_to_run)
                    
                    
                    if repeat_experiment ==1:
                        if i<11:
                            seed = random.randint(2000, 30000)
                            while seed in listof_Seeds:
                                seed = random.randint(2000, 30000)
                        else:
                            seed = random.randint(30001, 60000)
                            while seed in listof_Seeds:
                                seed = random.randint(30001, 60000)

                    my_length_of_pathh_levels = [avg_length_path]
                    my_numo_objs_levels = [num_of_objs]
                    choice_place = map_id
                else : 
                    choice_place = choice_place_to_run
                if repeat_experiment == 1:
                    my_length_of_pathh_levels =[avg_length_path]
                for length_of_path in my_length_of_pathh_levels:
                    num_objects_dict = {}
                    if repeat_experiment == 1:
                        my_numo_objs_levels =[num_of_objs]
                    for numo_objs in my_numo_objs_levels:
                        if repeat_experiment==0:
                            run_once=0
                        
                        #seed = random.randint(123, 2000)
                        #while seed in listof_Seeds:
                            #seed = random.randint(1, 2000)
                        #listof_Seeds.append(seed)
                        #    "Munich": {"north": 48.148, "south": 48.061, "east": 11.522, "west": 11.460}    

                        keep_specific_files_and_folders(run_once, repeat_experiment)
                        permutations_calculated = False
                        #print(choice_place)
                        #x =input()
                        
                        for threshold in my_threshold_levels:
                            print(f"Current threshold : {threshold}")
                            threshold_real = threshold*0.01
                            if numo_objs not in num_objects_dict:
                                num_objects_dict[numo_objs]={}
                            if choice_place == 5:
                                numOfEdges =  3750
                            elif choice_place == 1:
                                numOfEdges = 1306

                            elif choice_place ==4:
                                numOfEdges = 657
                            elif choice_place ==2:
                                numOfEdges = 500
                            elif choice_place ==6:
                                numOfEdges = 1750
                            elif choice_place ==7:
                                numOfEdges = 650
                            elif choice_place ==8:
                                numOfEdges = 500    
                            elif choice_place ==9:
                                numOfEdges = 120
                            elif choice_place ==10:
                                numOfEdges = 5000  # super case for completelly different networks
                            elif choice_place ==11:
                                numOfEdges =  6000  # super case for completelly different networks
                            elif choice_place ==12:
                                numOfEdges =  182  # super case for completelly different networks
                            elif choice_place ==13:
                                numOfEdges =  806  # super case for completelly different networks
                            elif choice_place ==14:
                                numOfEdges =  651  # super case for completelly different networks
                            elif choice_place ==15:
                                numOfEdges =  0  # super case for completelly different networks
                            elif choice_place ==16:
                                numOfEdges =  1  # super case for completelly different networks
                            elif choice_place ==17:
                                numOfEdges =  183  # super case for completelly different networks
                            elif choice_place ==19:
                                numOfEdges =  180  # super case for completelly different networks
                            else:
                                numOfEdges = 0

                            print ("HEEE")
                            #print (num_of_edges , num_of_objs , threshold , avg_length_path , map_id, seed)
                            #stop = input()
                            
                            
                            
                            raw_or_hashed , permutation  , current_compress = 0 , -1 , -1
                            print(raw_or_hashed, seed, current_compress, permutation , numo_objs , length_of_path , threshold_real , depth, help_for_jaccard , factor_forDBscan,choice_place ,run_once, repeat_experiment,limitN,subfolder)
                            
                            
                            print("run")
                            result_running = run_script(raw_or_hashed, seed, current_compress, permutation , numo_objs , length_of_path , threshold_real , depth, help_for_jaccard , factor_forDBscan,choice_place ,run_once, repeat_experiment,limitN,subfolder)
                            run_once = 1
                            if result_running == 0:
                                print("No homopaths with this threshold. We continue to the next one")
                                continue
                            #x =input()
                            
                            #print(result)
                            print(f"first running happened with result {result_running}")
                            raw_file_size = os.path.getsize(File_4_sensors)
                            #stop = input()
                            #seed = 1234
                            listof_Seeds.append(seed)
                            raw_or_hashed = 1 
                            retain_numberOfPermutation = False
                            permutation = 0
                            
                            signal_to_delete_files_which_help_only_similarity_testing = 0
                            compress_struct = {}
                            
                            for current_compress in my_compression_levels:
                                #seed = current_compress
                                
                                
                                #if repeat_experiment ==1:
                                    #print(dictionaryWithComprAndPermut.keys())
                                    #if current_compress not in dictionaryWithComprAndPermut.keys() and repeat_experiment ==1 :
                                        #continue


                                if retain_numberOfPermutation == False:
                                    permutation +=1
                                max_accepted_real_compress = current_compress + current_compress*0.22
                                min_accepted_real_compress = current_compress - current_compress*0.28
                                counter = 0
                                #print("Lets go for the next")
                                #print(f"Current Compress: {current_compress} , NumofPermutations = {permutation}")

                                
                                
                                for repetition in range(number_of_repetitions):
                                    File_4_sensors_HASHED_FILE_for_current_compress = f"4_sensors_HASHED_{current_compress}.txt"
                                    
                                    #factor_forDBscan = num_objs*(1-threshold_real)*(1-threshold_real)/(638*threshold_real*threshold_real) #
                                    
                                    raw_sensors_file = "4_sensors.txt"
                                    hashed_sensors_file = "4_sensors_HASHED.txt"
                                    #print ("here before if")
                                    if repeat_experiment ==1:
                                        #print(f"here:1")
                                        #print(dictionaryWithComprAndPermut)
                                        for compr in dictionaryWithComprAndPermut:
                                            #print(2)
                                            if current_compress in dictionaryWithComprAndPermut:
                                                #print(3)
                                            
                                                if current_compress == int(compr): 
                                                    #print(4)
                                                    #time.sleep(1) 
                                                    permutation = dictionaryWithComprAndPermut[compr]
                                                    print(f"Permutations for repeating are : {permutation}")
                                                    #stop = input()
                                                    hash_data(File_4_sensors, permutation, seed, File_4_sensors_HASHED_FILE, threshold)
                                                    hashed_file_size = os.path.getsize(File_4_sensors_HASHED_FILE)
                                                    real_compress = ( raw_file_size / hashed_file_size )
                                                    print(real_compress,raw_file_size,hashed_file_size)
                                                    experiment_run = True
                                                    print(compr, current_compress)
                                                    print(f"2. Current Compress: {current_compress} , real_compress = {real_compress}")
                                                    print(f"3. Current Compress: {current_compress} , real_compress = {real_compress}")

                                            else: 
                                                print(5)
                                                experiment_run =False
                                                continue    

                                    else : 
                                        #seed_hashed = current_compress
                                        hash_data(File_4_sensors, permutation, seed, File_4_sensors_HASHED_FILE, threshold)
                                        
                                        hashed_file_size = os.path.getsize(File_4_sensors_HASHED_FILE)
                                        real_compress = ( raw_file_size / hashed_file_size )
                                    
                                    
                                        if real_compress > max_accepted_real_compress or real_compress < min_accepted_real_compress:
                                            print(f"1. Current Compress: {current_compress} , real_compress = {real_compress}")
                                            if real_compress < min_accepted_real_compress: 
                                                retain_numberOfPermutation = True
                                                experiment_run = False
                                                print("will break 0")
                                                continue

                                            else: 
                                                if permutations_calculated == True:
                                                    if current_compress==64:
                                                        permutation = permutation64
                                                    elif current_compress ==32:
                                                        permutation = permutation32
                                                    elif current_compress ==16:
                                                        permutation = permutation16
                                                    elif current_compress ==8:
                                                        permutation = permutation8
                                                    elif current_compress ==4:
                                                        permutation = permutation4
                                                    elif current_compress ==2:
                                                        permutation = permutation2
                                                    elif current_compress ==128:
                                                        permutation = permutation128
                                                    hash_data(File_4_sensors, permutation, seed, File_4_sensors_HASHED_FILE, threshold)
                                                    hashed_file_size = os.path.getsize(File_4_sensors_HASHED_FILE)
                                                    real_compress = ( raw_file_size / hashed_file_size )
                                                    #if real_compress < min_accepted_real_compress:
                                                        #retain_numberOfPermutation = True
                                                        #experiment_run = False
                                                        #print("will break_1")
                                                        #break 
                                                else:
                                                    if current_compress == my_compression_levels[0]:
                                                        while real_compress > max_accepted_real_compress :
                                                            print(f"2. Current Compress: {current_compress} , real_compress = {real_compress}")
                                                            print(f"permutation : {permutation}")
                                                            retain_numberOfPermutation = False
                                                            if real_compress/current_compress >=4:
                                                                print(1)
                                                                addition = int(1*permutation)
                                                                if addition == 0:
                                                                    addition=2
                                                                permutation += 1
                                                            elif real_compress/current_compress <4 and real_compress/current_compress>=3:
                                                                print(2)
                                                                addition = int(0.2*permutation)
                                                                if addition == 0:
                                                                    addition=2
                                                                permutation += 1
                                                            elif real_compress/current_compress <3 and real_compress/current_compress>=2:
                                                                print(3)
                                                                addition = int(0.1*permutation)
                                                                if addition == 0:
                                                                    addition=1
                                                                permutation += 1
                                                            elif real_compress/current_compress >=1.6 and real_compress/current_compress<2:
                                                                print(4)
                                                                addition = int(0.1*permutation)
                                                                if addition == 0:
                                                                    addition=1
                                                                permutation += 1
                                                            elif real_compress/current_compress >=1.1 and real_compress/current_compress<1.6:
                                                                print(5)
                                                                addition = int(0.09*permutation)
                                                                if addition == 0:
                                                                    addition=1
                                                                permutation += 1
                                                            else:
                                                                print(6)
                                                                permutation +=1
                                                            hash_data(File_4_sensors, permutation, seed, File_4_sensors_HASHED_FILE, threshold)
                                                            hashed_file_size = os.path.getsize(File_4_sensors_HASHED_FILE)
                                                            real_compress = ( raw_file_size / hashed_file_size )
                                                            if real_compress < min_accepted_real_compress:
                                                                retain_numberOfPermutation = True
                                                                experiment_run = False
                                                                print("will break_2")
                                                                break 
                                                        previous_compress = current_compress
                                                    
                                                    else:
                                                        if previous_compress in compress_struct:
                                                            if real_compress> previous_compress*1.25:
                                                                permutation = int(compress_struct[previous_compress] *2.9)   
                                                            elif real_compress< previous_compress*0.7:
                                                                permutation = int(compress_struct[previous_compress] *1.5)
                                                            else:
                                                                permutation = int(compress_struct[previous_compress] *2)

                                                            print(f"2. Current Compress: {current_compress} , real_compress = {real_compress}")
                                                            print(f"permutation : {permutation}")
                                                            hash_data(File_4_sensors, permutation, seed, File_4_sensors_HASHED_FILE, threshold)
                                                            hashed_file_size = os.path.getsize(File_4_sensors_HASHED_FILE)
                                                            real_compress = ( raw_file_size / hashed_file_size )
                                                            if real_compress < min_accepted_real_compress:
                                                                retain_numberOfPermutation = True
                                                                experiment_run = False
                                                                print("will break_2")
                                                                break 
                                                    print(f"3. Current Compress: {current_compress} , real_compress = {real_compress}")


                                        #time.sleep(1) 
                                        experiment_run = True
                                    if current_compress not in compress_struct:
                                        compress_struct[current_compress]=permutation
                                        previous_compress = current_compress
                                    print(f"permutation : {permutation}")
                                    #seed_hashed=current_compress
                                    if experiment_run == True : 
                                        if current_compress==64:
                                            permutation64 =permutation
                                        elif current_compress ==32:
                                            permutation32 =permutation
                                        elif current_compress ==16:
                                            permutation16 =permutation
                                        elif current_compress ==8:
                                            permutation8 =permutation
                                        elif current_compress ==4:
                                            permutation4 =permutation
                                        elif current_compress ==2:
                                            permutation2 =permutation
                                        elif current_compress ==128:
                                            permutation128 =permutation
                                        print(f"\n\n*******************                 Repetition: {repetition}  : Compress {current_compress} achieved with {real_compress} !      ********************************") 
                                        
                                        copy_file(File_4_sensors_HASHED_FILE, File_4_sensors_HASHED_FILE_for_current_compress)
                                        #print(File_4_sensors_HASHED_FILE_for_current_compress)
                                        #x = input ()
                                        run_script(raw_or_hashed, seed, current_compress, permutation , numo_objs , length_of_path , threshold_real , depth, help_for_jaccard,  factor_forDBscan, choice_place, run_once, repeat_experiment,limitN,subfolder)
                                        if threshold == my_threshold_levels[-1] :
                                            File_Regional_4_sensors_HASHED_FILE_112 = f"Regional_4_sensors_HASHED112.txt"
                                            File_Regional_4_sensors_HASHED_FILE_122 = f"Regional_4_sensors_HASHED122.txt"
                                            File_Regional_4_sensors_HASHED_FILE_212 = f"Regional_4_sensors_HASHED212.txt"
                                            File_Regional_4_sensors_HASHED_FILE_222 = f"Regional_4_sensors_HASHED222.txt"
                                            File_Regional_4_sensors_HASHED_FILE_112_for_current_compress_ = f"Regional_4_sensors_HASHED112_{current_compress}.txt"
                                            File_Regional_4_sensors_HASHED_FILE_122_for_current_compress_ = f"Regional_4_sensors_HASHED122_{current_compress}.txt"
                                            File_Regional_4_sensors_HASHED_FILE_212_for_current_compress_ = f"Regional_4_sensors_HASHED212_{current_compress}.txt"
                                            File_Regional_4_sensors_HASHED_FILE_222_for_current_compress_ = f"Regional_4_sensors_HASHED222_{current_compress}.txt"
                                            copy_file(File_Regional_4_sensors_HASHED_FILE_112, File_Regional_4_sensors_HASHED_FILE_112_for_current_compress_)
                                            copy_file(File_Regional_4_sensors_HASHED_FILE_122, File_Regional_4_sensors_HASHED_FILE_122_for_current_compress_)
                                            copy_file(File_Regional_4_sensors_HASHED_FILE_212, File_Regional_4_sensors_HASHED_FILE_212_for_current_compress_)
                                            copy_file(File_Regional_4_sensors_HASHED_FILE_222, File_Regional_4_sensors_HASHED_FILE_222_for_current_compress_)
                                        #print(result)
                                        #time.sleep(5) 
                                        if current_compress not in num_objects_dict[numo_objs]:
                                            num_objects_dict[numo_objs][current_compress] = {}
                                        raw_or_hashed = 1
                                        Total_Real_compress = 0
                                    
                                        raw_file_size = os.path.getsize(raw_sensors_file)
                                        hashed_file_size = os.path.getsize(hashed_sensors_file)
                                        real_compress = int(round((raw_file_size/hashed_file_size),2))
                                        Total_Real_compress += real_compress
                                        #avg_real_compress = Total_Real_compress/number_of_repetitions


                                        
                                    time.sleep (2+ (numo_objs/(current_compress**threshold)*(1-run_once)/1000))
                                    num_objects_dict[numo_objs][current_compress] =  current_compress
                                    

                                filename = "results.txt"
                                parent_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
                                file_path = os.path.join(parent_dir, filename)
                                print(file_path)
                                """jaccard_dict_result , overlap_dict = analysis(jaccard_threshold ,overlap_threshold, analysis_File , number_of_repetitions, current_compress, numo_objs , threshold_real, length_of_path)
                                with open(file_path, 'a') as fileofexperiments:
                                    fileofexperiments.write(f"Place: {choice_place}\nlength_of_pathh: {length_of_path},  threshold: {threshold}%,  numo_objs: {numo_objs}\nReps per compress level : {number_of_repetitions} ")
                                    fileofexperiments.write(f"\nCompress: Estim - Real : ")
                                    json.dump(num_objects_dict, fileofexperiments)
                                    fileofexperiments.write("\nJaccard :                ")
                                    json.dump(jaccard_dict_result, fileofexperiments)
                                    fileofexperiments.write("\nOverlap :           
                                    )
                                    json.dump(overlap_dict, fileofexperiments)
                                    fileofexperiments.write("\n\n")"""
                                #print(f"File written to {file_path}")

                            signal_to_delete_files_which_help_only_similarity_testing = 1
                            #for file in os.listdir():
                                #if  file =="correcthomoedges111.json"or file =="correcthomoedges112.json"or file =="correcthomoedges113.json"or file =="correcthomoedges211.json"or file =="correcthomoedges212.json"or file =="correcthomoedges213.json":
                                    # os.remove(file)
                                    #print("must delete the files succesfully ")
                            permutations_calculated = True
                        #time.sleep(1) 
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")               # Get the current timestamp
                        print(f"Experiment finished ,  for {length_of_path}, {threshold}, {numo_objs}  ")
                        # File paths
                        compare_file_path = 'Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_pairs.txt'
                        top_leader_file_path = 'Current_Experiment_Top_Leader_Reg_Leader_edges_costs.txt'
                        output_file_path = 'Current_Experiment_Top_Leader_Reg_Leader_pairs_costs.txt'
                        create_testing_file_for_pairs(compare_file_path, top_leader_file_path, output_file_path)
                        if repeat_experiment ==1 and testing_pairs ==1 : 
                            if help_for_jaccard == 0:
                                folder_name = f"Experiment_{numOfEdges}_{numo_objs}_{threshold}_{length_of_path}_{choice_place}_{timestamp}RepeatForPairsHelpNO"     # Create a new folder with the experiment name
                            else:
                                folder_name = f"Experiment_{numOfEdges}_{numo_objs}_{threshold}_{length_of_path}_{choice_place}_{timestamp}RepeatForPairsHelpYES"     # Create a new folder with the experiment name
                        
                        elif repeat_experiment ==1 and testing_pairs ==0 : 
                            if help_for_jaccard == 0:
                                folder_name = f"Experiment_{numOfEdges}_{numo_objs}_{threshold}_{length_of_path}_{choice_place}_{timestamp}RepeatForEdgesHelpNO"     # Create a new folder with the experiment name
                            else:
                                folder_name = f"Experiment_{numOfEdges}_{numo_objs}_{threshold}_{length_of_path}_{choice_place}_{timestamp}RepeatForEdgesHelpYES"     # Create a new folder with the experiment name
                        
                        else:
                            folder_name = f"Experiment_{numOfEdges}_{numo_objs}_{threshold}_{length_of_path}_{choice_place}_{timestamp}"     # Create a new folder with the experiment name
                        
                        os.mkdir(folder_name)
                        for file in os.listdir():

                            if file == "RESULTS.txt"  or file =="ResultsOfExperiments.txt"or file=="Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_pairs.txt" or file =="Current_Experiment_Top_Leader_Reg_Leader_pairs_costs.txt" or (file.startswith("depth_") and file.endswith(".png")) or file=="Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_all.txt"  or  file=="Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_allwithout_single.txt" or file=="Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_all_with_costs.txt" or file=="Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_single.txt" or file =="correcthomoedges111.json"or file =="correcthomoedges112.json"or file =="correcthomoedges113.json"or file =="correcthomoedges211.json"or file =="correcthomoedges212.json"or file =="correcthomoedges213.json" or file =="correcthomoedges2.json"or file =="correcthomoedges3.json" or file=="Current_Experiment_Info.txt" or file =="depth_11.png" or file =="depth_21.png" or file =="depth_112.png" or file =="depth_212.png" or file =="depth_111.png" or file =="depth_211.png" or file =="7_ConnectionsBetween_Regions.txt" or file =="3_Motions.txt" or file=="Current_Experiment_Top_Leader_flat_visualization_per_Region_brackets.txt"  or file=="Current_Experiment_Top_Leader_flat_visualization_all_together.txt" or  file== "all_with_costs.txt" or file =="Current_Experiment_Top_Leader_Reg_Leader_edges_costs.txt" or file =="Current_Experiment_Top_Leader_Reg_Leader_paths_costs.txt"or file=="Current_Experiment_Top_Leader_span_homopaths_brackets.txt" or file=="seeds.txt" or file=="4_sensors_HASHED.txt"  or file=="4_sensors.txt" or file=="3_Motions.txt" or file.startswith("4_sensors_HASHED_") or file.startswith("Regional_4_sensors_")  or file.startswith("1_combined_nodes_edges.txt") or file.startswith("2_edgeconnections.txt"):
                                source_path = os.path.join(os.getcwd(), file)
                                if os.path.isfile(source_path):
                                    destination_path = os.path.join(os.getcwd(), folder_name, file)
                                    shutil.move(source_path, destination_path)
                                    print(f"File: {file} moved to {folder_name}")
                                    
   
    return threshold_real

    #Experiment_analysis(jaccard_threshold , analysis_File, csv_results)

threshold = main_function()
experiment_code    = "experiment_creator.py"
homopa_python_code = "homopa.py"
History7z          = "History.7z"

