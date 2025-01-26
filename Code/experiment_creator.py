import subprocess
import time
import csv
import os
import shutil
from datetime import datetime
from datasketch import MinHash
import re
import random




##############################################################################
#                       E X P E R I M E N T   C R E A T O R
##############################################################################

def run_script(raw_or_hashed, seed, current_compress, permutation, 
               num_objs, length_of_path, threshold, depth, 
               help_for_jaccard, choice_place, run_once, repeat_experiment,
               limitN, Experiment_for_Repetition):
    """
    Launches 'homopa.py' as a subprocess with the specified parameters, capturing 
    real-time output and returning the last integer printed by 'homopa.py' if any.

    :param raw_or_hashed: 0 => raw data, 1 => hashed data
    :param seed: Random seed for consistent hashing or other reproducibility
    :param current_compress: The target compression ratio (2,4,8,...)
    :param permutation: Number of minhash permutations for the hashed approach
    :param num_objs: How many objects to simulate in the sensor data
    :param length_of_path: The path length used in motions
    :param threshold: Intersection threshold (0 to 1.0) used for homopath detection
    :param depth: Map partition depth (0 => single region, 1 => 2 regions, etc.)
    :param help_for_jaccard: Debug/analysis flag for raw vs. hashed accuracy
    :param choice_place: Identifies which map or location ID we're using
    :param run_once: Indicates if we should skip regenerating the network/sensors
    :param repeat_experiment: 1 => we are re-running a previous experiment folder
    :param limitN: A large recursion or object limit used internally by 'homopa.py'
    :param Experiment_for_Repetition: The folder name referencing a past experiment
    :return: The last integer printed by 'homopa.py' if the script completes successfully
             and prints an integer. Otherwise, returns None.
    """

    script_path = "homopa.py"

    # Build the command to call homopa.py with the arguments
    process = subprocess.Popen(
        [
            "python", script_path, 
            str(raw_or_hashed), str(seed), str(current_compress), str(permutation),
            str(num_objs), str(length_of_path), str(threshold), str(depth), 
            str(help_for_jaccard), str(choice_place), str(run_once), 
            str(repeat_experiment), str(limitN), str(Experiment_for_Repetition)
        ],
        stdout=subprocess.PIPE,  # Capture stdout
        stderr=subprocess.PIPE,  # Capture stderr
        text=True,               # Decode bytes => strings
        bufsize=1                # Line buffering
    )
    
    last_output = None  # Will hold the last integer printed by homopa.py

    # Read output line by line in real-time
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())     # Echo the line in real time
            try:
                # Attempt to parse the line as an integer
                last_output = int(output.strip())
            except ValueError:
                # If it's not an integer, ignore
                pass

    # Wait for the subprocess to finish
    process.wait()
    
    # Check the return code for success/failure
    if process.returncode == 0:
        # If there's a last_output integer, return it. Else None.
        if last_output is not None:
            return last_output
        else:
            return None
    else:
        # Something went wrong; read the stderr
        print("Script 'homopa.py' failed with error:", process.stderr.read())
        return None


def hash_data(file_path, num_perm, seed, File_4_sensors_HASHED_FILE, threshold):
    """
    Reads sensor data from 'file_path' (e.g. '4_sensors.txt'), converts each line's 
    object IDs into a MinHash signature, and writes hashed results to 
    'File_4_sensors_HASHED_FILE'.

    :param file_path: The file containing sensor data (edge_id, obj1, obj2, ...)
    :param num_perm: Number of permutations (hash functions) used by MinHash
    :param seed: Random seed to initialize MinHash for reproducibility
    :param File_4_sensors_HASHED_FILE: Output file name for hashed sensor data
    :param threshold: (Not used internally here, but included for traceability)
    :return: The list of hashed data rows for optional debugging
    """

    # Read lines from the raw sensor file
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Sort lines by the second element (some logic to ensure consistent ordering)
    lines_with_values = [(line, [int(value) for value in line.strip().split(',')]) 
                         for line in lines]
    sorted_lines_with_values = sorted(lines_with_values, key=lambda x: x[1][1])
    sorted_lines = [line for line, _ in sorted_lines_with_values]
    lines = sorted_lines

    hashed_data = []
    
    for line in lines:
        line = line.strip().split(',')
        sensor_id = line[0]
        obj_ids = line[1:]
        number_of_Raw_ObjIDS = len(obj_ids)
        new_m = []

        # Only proceed if there's at least 1 object
        if len(obj_ids) >= 1:
            data = set(obj_ids)  # Unique object IDs
            # Initialize MinHash object
            m = MinHash(seed=seed, num_perm=num_perm)

            # Update MinHash with each object
            for d in data:
                m.update(d.encode('utf8'))
            
            # Convert each X-bit hashvalue to 32-bit (if needed)
            for value in m.hashvalues:
                value64 = int(value) & ((1 << 32) - 1)
                new_m.append(value64)
            
            hashed_data.append((sensor_id, number_of_Raw_ObjIDS, new_m))
    
    # Write hashed data to the specified output file
    with open(File_4_sensors_HASHED_FILE, 'w') as out_file:
        for entry in hashed_data:
            out_file.write(f"{entry[0]},{entry[1]},{','.join(map(str, entry[2]))}\n")
    
    return hashed_data


def copy_file(source_file, destination_file):
    #print("In copyFile function")
    try:
        shutil.copyfile(source_file, destination_file)
        #print(f"File {source_file} successfully copied to {destination_file}")
    except IOError as e:
        print(f"Unable to copy file. {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")



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
    """
    Reads a CSV file containing top leader information and creates a dictionary keyed by 
    (threshold, permutation). Each row in the CSV is stored as a list in the dictionary.

    :param file_path: Path to the CSV file (e.g., 'Current_Experiment_Top_Leader_Reg_Leader_edges_costs.txt').
    :return: A dictionary { (threshold, permutation): row_list }
    """
    top_leader_dict = {}
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            # Convert the threshold from string to float, and permutation from string to int
            threshold = float(row[3])
            permutation = int(row[5])
            key = (threshold, permutation)
            top_leader_dict[key] = row
    return top_leader_dict

def read_compare_file(file_path):
    """
    Reads a CSV file containing compare data. Each row includes threshold, permutation, 
    and a list of pairs from index 6 onward (representing discovered homopath pairs or similar).

    :param file_path: Path to the CSV file (e.g., 'Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_pairs.txt').
    :return: A dictionary { (threshold, permutation): [list_of_pair_strings, ...] }
    """
    compare_dict = {}
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            # row[1] => threshold (float), row[3] => permutation (int)
            threshold = float(row[1])
            permutation = int(row[3])
            key = (threshold, permutation)

            # Starting from index 6, the rest are pair-like strings
            pairs = row[6:]
            if key not in compare_dict:
                compare_dict[key] = []

            # Add each pair to the dictionary under the identified key
            for pair in pairs:
                pair = pair.strip()
                if pair != '[0]':  # If it's not the placeholder [0]
                    compare_dict[key].append(pair)
    return compare_dict

def process_pairs(pairs_list):
    """
    Converts a list of bracketed pairs into a specialized "compressed" string format.
    Example:
        If pairs_list = ["[123,456]", "[789,101112]"],
        we extract the numbers (123, 456, 789, 101112), then pair them in twos, 
        and form a new string f"{first.zfill(3)}000{second.zfill(3)}".

    :param pairs_list: e.g. ["[123,456]", "[789,101112]"] or similar
    :return: A list of processed pair strings, each zero-padded and combined.
    """
    processed_list = []
    all_numbers = []

    # Extract all numeric substrings from each pair (123,456, etc.)
    for pair in pairs_list:
        numbers = re.findall(r'\d+', pair)
        all_numbers.extend(numbers)

    # We then form 'pairs' from these extracted numbers in sequential order
    for i in range(0, len(all_numbers), 2):
        if i + 1 < len(all_numbers):
            first, second = all_numbers[i], all_numbers[i + 1]
            # Zero-pad to at least 3 digits, then join with '000' in between
            processed_pair = f"{first.zfill(3)}000{second.zfill(3)}"
            processed_list.append(processed_pair)

    return processed_list

def write_output_file(file_path, top_leader_dict, compare_dict):
    """
    Creates a new CSV file based on the top_leader_dict rows. 
    If a (threshold, permutation) key also exists in compare_dict, 
    we process its pairs and append the processed pairs to the new row.

    :param file_path: Path to the output file to write.
    :param top_leader_dict: Dictionary from read_top_leader_file()
    :param compare_dict: Dictionary from read_compare_file()
    """
    with open(file_path, 'w', newline='') as file:
        writer = csv.writer(file)
        for key, top_leader_row in top_leader_dict.items():
            if key in compare_dict:
                # Process the pairs associated with this key
                processed_pairs = process_pairs(compare_dict[key])
                # Convert them into a bracketed, comma-joined string
                processed_pairs_str = '[' + ','.join(processed_pairs) + ']'
                # top_leader_row[:8] => first 8 columns from the original row
                # plus the processed pairs as a single column
                new_row = top_leader_row[:8] + [processed_pairs_str]
                writer.writerow(new_row)
            else:
                # If there's no pair data for this key, append an empty string
                new_row = top_leader_row[:8] + ['']
                writer.writerow(new_row)

def remove_double_quotes_from_file(file_path):
    """
    Strips any double quotes from each line of the given file and overwrites it.

    :param file_path: CSV or text file path whose lines need double quote removal.
    """
    lines = []
    with open(file_path, 'r') as file:
        for line in file:
            # Remove any double quotes from the line
            line = line.strip().replace('"', '')
            lines.append(line)
    
    with open(file_path, 'w') as file:
        for line in lines:
            file.write(line + '\n')

def create_testing_file_for_pairs(compare_file_path, top_leader_file_path, output_file_path):
    """
    Main driver to:
      1) Read the top leader CSV => top_leader_dict
      2) Read the compare CSV => compare_dict
      3) Combine them by matching (threshold, permutation)
         and write the results to 'output_file_path'.
      4) Finally remove any double quotes from the resulting file.

    :param compare_file_path: e.g. "Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_pairs.txt"
    :param top_leader_file_path: e.g. "Current_Experiment_Top_Leader_Reg_Leader_edges_costs.txt"
    :param output_file_path: e.g. "Current_Experiment_Top_Leader_Reg_Leader_pairs_costs.txt"
    """
    # Step A: Read and parse the top leader CSV
    top_leader_dict = read_top_leader_file(top_leader_file_path)
    # Step B: Read and parse the compare CSV
    compare_dict = read_compare_file(compare_file_path)

    # Step C: Write combined output
    write_output_file(output_file_path, top_leader_dict, compare_dict)

    # Step D: Clean up quotes in the new output
    remove_double_quotes_from_file(output_file_path)



def extract_Infos_from_Experiment_folders(folder):
    """
    Interprets the name of a folder to extract experimental parameters 
    (e.g. num_of_edges, num_of_objs, threshold, avg_length_path, map_id),
    and copies certain files (3_Motions.txt, 4_sensors.txt) from that folder 
    if it contains a valid 'seeds.txt' with a second line specifying a seed.

    Folder naming convention:
       Experiment_<num_of_edges>_<num_of_objs>_<threshold>_<avg_length_path>_<map_id>_<timestamp>

    e.g. Folder: 'Experiment_181_10000_60_15_16_20250126131739' => 
         num_of_edges=181, num_of_objs=10000, threshold=60, avg_length_path=15, map_id=16

    The function also attempts to copy 3_Motions.txt and 4_sensors.txt into the current directory 
    if they exist in the specified folder.

    :param folder: The folder name (string) that presumably follows the 'Experiment_' naming pattern.
    :return: A tuple (num_of_edges, num_of_objs, threshold, avg_length_path, map_id, seed).
             If the seed cannot be found in seeds.txt, it may default to 0 or an undesired value.
    """
    # Current working directory
    current_directory = os.getcwd()
    
    # Regex pattern matching: Experiment_<edges>_<objs>_<threshold>_<length_path>_<map_id>_...
    folder_pattern = re.compile(r'Experiment_(\d+)_(\d+)_(\d+)_(\d+)_(\d+)_.*')
    
    # Full path to the experiment folder
    folder_path = os.path.join(current_directory, folder)

    # Initialize fallback seed (in case it isn't found)
    seed = 0

    # Check if the folder exists
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        # Attempt to parse the folder name with our pattern
        match = folder_pattern.match(folder)
        if match:
            num_of_edges = int(match.group(1))
            num_of_objs = int(match.group(2))
            threshold = int(match.group(3))
            avg_length_path = int(match.group(4))
            map_id = int(match.group(5))
            
            print("Repeating Experiment : ")
            print(f"Folder: {folder}")
            print(f"num_of_edges: {num_of_edges}")
            print(f"num_of_objs: {num_of_objs}")
            print(f"threshold: {threshold}")
            print(f"avg_length_path: {avg_length_path}")
            print(f"map_id: {map_id}")
            
            # seeds.txt path
            seeds_file = os.path.join(folder_path, 'seeds.txt')
            
            if os.path.exists(seeds_file):
                with open(seeds_file, 'r') as file:
                    lines = file.readlines()
                    # The second line might contain our seed in the first position before a semicolon
                    if len(lines) > 1:
                        seed_candidate = lines[1].split(';')[0]
                        try:
                            seed = int(seed_candidate)
                        except ValueError:
                            print(f"Seed in second line is not a valid integer: '{seed_candidate}'")
                        
                        if seed >= 0:
                            # Attempt to copy 3_Motions.txt and 4_sensors.txt from the folder
                            motion_file = os.path.join(folder_path, '3_Motions.txt')
                            sensor_file = os.path.join(folder_path, '4_sensors.txt')
                            
                            if os.path.exists(motion_file):
                                shutil.copy(motion_file, current_directory)
                                print(f"Copied {motion_file} => {current_directory}")
                            else:
                                print(f"{motion_file} does not exist")

                            if os.path.exists(sensor_file):
                                shutil.copy(sensor_file, current_directory)
                                print(f"Copied {sensor_file} => {current_directory}")
                            else:
                                print(f"{sensor_file} does not exist")
                        else:
                            print(f"Seed found is negative: {seed}")
                    else:
                        print(f"{seeds_file} does not have enough lines to read a second line for seed.")
            else:
                print(f"{seeds_file} does not exist in the folder.")
        else:
            print(f"Folder name '{folder}' does not match the expected pattern of 'Experiment_...'.")
            # Provide default placeholders if matching fails
            num_of_edges, num_of_objs, threshold, avg_length_path, map_id = 0, 0, 0, 0, 0
    else:
        print(f"Folder '{folder_path}' does not exist or is not a directory.")
        # Provide default placeholders if folder is invalid
        num_of_edges, num_of_objs, threshold, avg_length_path, map_id = 0, 0, 0, 0, 0

    return num_of_edges, num_of_objs, threshold, avg_length_path, map_id, seed


def copy_files(Experiment_for_Repetition, file1, file2, file3, target_file='Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_all_with_costs.txt'):
    """
    Copies specified files (e.g. '1_combined_nodes_edges.txt', '2_edgeconnections.txt', '3_Motions.txt')
    from a target experiment folder back into the current directory, 
    then optionally reads a 'target_file' in that folder to extract data into a dictionary.

    :param Experiment_for_Repetition: The folder name that contains the experiment files.
    :param file1: File to copy (e.g. '1_combined_nodes_edges.txt').
    :param file2: File to copy (e.g. '2_edgeconnections.txt').
    :param file3: File to copy (e.g. '3_Motions.txt').
    :param target_file: A special file (default: 'Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_all_with_costs.txt')
                       from which we parse columns 6 & 7 to build a dictionary.
    :return: A dictionary extracted from the 'target_file', keyed by column7 => column6, or empty if 
             the file not found or no data was extracted.
    """

    # Store the current directory so we can return to it afterward
    initial_directory = os.getcwd()
    
    # Construct the source folder path inside the current directory
    source_folder = os.path.join(initial_directory, Experiment_for_Repetition)
    extracted_data = {}  # This dictionary will store the extracted info (col7 => col6)

    try:
        # 1) Navigate to the experiment folder
        os.chdir(source_folder)
        
        # 2) Copy the specified files back to the original directory
        shutil.copy(file1, initial_directory)
        shutil.copy(file2, initial_directory)
        shutil.copy(file3, initial_directory)
        # print(f"Copied {file1}, {file2}, {file3} back to {initial_directory}")

        # 3) Check if target_file exists in this folder, then parse it
        if os.path.exists(target_file):
            print(f"Found target file: {target_file} . Extracting information...")

            processing = False    # Will become True once we detect lines beyond the sentinel condition
            line_counter = 0
            prev_col6 = -1
            prev_col7 = -1

            with open(target_file, 'r') as file:
                for line in file:
                    fields = line.strip().split(',')
                    
                    # We assume col6 => fields[5], col7 => fields[6]
                    col6 = int(fields[5])  # Typically the 6th column
                    col7 = int(fields[6])  # Typically the 7th column

                    # If we find a line with both values == -1, it might indicate a sentinel
                    if col6 == -1 and col7 == -1:
                        if line_counter != 0:
                            # Check if the previous line was also sentinel. If so, skip
                            if prev_col6 == -1 and prev_col7 == -1:
                                pass
                            else:
                                # If we're already 'processing', then encountering this again 
                                # might mean we should stop
                                if processing:
                                    break
                                processing = True
                        else:
                            # This is the first line in the file => skip
                            prev_col6 = -1
                            prev_col7 = -1
                            continue
                    else:
                        # If not sentinel, we record col7 => col6
                        extracted_data[col7] = col6
                        processing = True  # We're in the data region

                    prev_col6 = col6
                    prev_col7 = col7
                    line_counter += 1

            print("Extraction complete.")
        else:
            print(f"Error: {target_file} not found in {source_folder}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Always revert to the initial directory
        os.chdir(initial_directory)
    
    return extracted_data

   


#####################################################################################################
#--------------------------------------------- #
#               m a i n 

def main_function():
    """
    The main orchestrating function for running experiments with both RAW and Hashed 
    data. It does the following:

      1. Initializes experiment parameters (compression levels, threshold levels, etc.).
      2. Optionally repeats a previous experiment (if repeat_experiment == 1) by 
         reusing older sensor/network files and changing seeds or thresholds.
      3. For each threshold:
         a) Run the experiment in RAW mode.
         b) Run the experiment in MINHASH mode for multiple compression targets,
            adjusting permutations to stay within ±10% of the desired compression ratio.
      4. Copies or renames resulting sensor files and logs, placing them into 
         a new folder after successful completion of the final threshold.

    NOTE: This function references these helper methods, which must be implemented 
    elsewhere in your codebase:
        - copy_files(...)
        - extract_Infos_from_Experiment_folders(...)
        - keep_specific_files_and_folders(...)
        - run_script(...)
        - hash_data(...)
        - create_testing_file_for_pairs(...)
        - copy_file(...)

    The code is invoked automatically at the end via 'threshold = main_function()'.
    """

    # The hashed sensor file used during minhash runs:
    File_4_sensors_HASHED_FILE = "4_sensors_HASHED.txt"
    # The raw sensor file used initially:
    File_4_sensors = "4_sensors.txt"

    threshold_real = 0  # Will store the last used threshold (as float: e.g. 0.30 for 30%)

    if __name__ == "__main__":
        # 1) Global/High-Level Experiment Parameters
        limitN = 1000000  # Large recursion/object limit for the homopa.py script
        maps = [16]       # List of place IDs
        listof_Seeds = [] # We store seeds used so we don't reuse them accidentally

        depth = 2         # Depth of map partition (0 => single region, 1 => 2, 2 => 4, etc.)

        # Possible compression levels (target ratios) for hashed data
        my_compression_levels = [256, 128, 64, 32, 16, 8, 4, 2]

        # Path length(s) for the motion file or experiment scenario
        my_length_of_pathh_levels = [15]

        # Threshold(s) given in percentages => We'll convert to fraction by dividing by 100
        # my_threshold_levels = [80,75,70,65,60,55,50,45,40,35,30,25,20,15,10]
        my_threshold_levels = [30, 45, 60]

        # Number of objects tested in sensor data
        my_numo_objs_levels = [1000, 2500, 5000, 10000, 25000, 50000]

        # The base random seed for raw or hashed runs
        seed = 12345

        # 2) Logic to handle re-running a previous experiment folder:
        #    We can replicate the same scenario but with a new seed or different thresholds
        folders_for_specific_repetition_for_checking_pairs = [
            'Experiment_181_10000_60_15_16_20250126131739'
        ]
        repeat_experiment = 0

        # If 1, the code includes an offline step analyzing discovered pairs as 
        # part of homopath accuracy (not fully shown).
        testing_pairs = 0

        # help_for_jaccard => if 1, we rely on real raw-data HoMoEdges to test 
        # hashing approach's accuracy. If 0, we let the Cohen-based approach (G-LESE algorithm in paper) 
        # introduce potential errors in HoMoEdgeDetection Phase.
        help_for_jaccard = 0

        # 3) Decide which "places" we are using:
        #    If repeat_experiment=1, we get them from older folders(experiments)
        if repeat_experiment == 1:
            places = folders_for_specific_repetition_for_checking_pairs
        else:
            places = maps

        run_once = 0         # Tells us if we've done the raw run at least once
        max_repetitions = 1  # How many times to repeat the entire experiment

        print("*************************************************************************************************************")
        print("*************************************************************************************************************")
        print("*************************************************************************************************************")
        print("*************************************************************************************************************")

        # 4) Outer loop for repeating the experiment multiple times if needed
        for i in range(0, max_repetitions):
            # If repeating older experiments, we can toggle help_for_jaccard
            # in this setup , in case we repeat an experiment for "max_repetitions", it will run
            # the half of them without "help_for_jaccard", and the other half with it.
            if repeat_experiment == 1:
                if i < int(max_repetitions / 2) or max_repetitions == 1:
                    help_for_jaccard = 0
                else:
                    help_for_jaccard = 1

            # We pick the 0th place from 'places' to replicate
            Experiment_for_Repetition = places[0]
            file1 = '1_combined_nodes_edges.txt'
            file2 = '2_edgeconnections.txt'
            file3 = '3_Motions.txt'

            # If repeating, we copy the older experiment data into our workspace
            if repeat_experiment == 1:
                dictionaryWithComprAndPermut = copy_files(
                    Experiment_for_Repetition, file1, file2, file3
                )
                print("User must put files for Motion and Sensor. If it fails, please check file availability.")

            # 5) Now we loop through each place
            for choice_place_to_run in places:
                # If repeating, parse older experiment metadata (#edges, #objs, threshold, etc.)
                if repeat_experiment == 1:
                    (num_of_edges, num_of_objs, threshold, 
                     avg_length_path, map_id, seed_init) = extract_Infos_from_Experiment_folders(choice_place_to_run)

                    # Example logic: change the seed so each repetition is unique
                    if repeat_experiment == 1:
                        if i < 11:
                            seed = random.randint(2000, 30000)
                            while seed in listof_Seeds:
                                seed = random.randint(2000, 30000)
                        else:
                            seed = random.randint(30001, 60000)
                            while seed in listof_Seeds:
                                seed = random.randint(30001, 60000)

                    # Adjust path length and num objs from that old experiment
                    my_length_of_pathh_levels = [avg_length_path]
                    my_numo_objs_levels = [num_of_objs]
                    choice_place = map_id
                else:
                    choice_place = choice_place_to_run

                if repeat_experiment == 1:
                    my_length_of_pathh_levels = [avg_length_path]

                # 6) For each path length, we try multiple object counts
                for length_of_path in my_length_of_pathh_levels:
                    num_objects_dict = {}
                    if repeat_experiment == 1:
                        my_numo_objs_levels = [num_of_objs]

                    for numo_objs in my_numo_objs_levels:
                        if repeat_experiment == 0:
                            run_once = 0

                        # Possibly handle file management or setup tasks
                        keep_specific_files_and_folders(run_once, repeat_experiment)
                        permutations_calculated = False

                        # We'll store minhash permutations in a dictionary if successful
                        CompressDict = {}

                        # 7) Now loop over each threshold in percentages
                        for threshold in my_threshold_levels:
                            start_time1 = time.time()

                            threshold_real = threshold * 0.01  # Convert to fraction

                            if numo_objs not in num_objects_dict:
                                num_objects_dict[numo_objs] = {}

                            # Hardcode the number of edges for this place
                            
                            if choice_place == 1:
                                numOfEdges = 1306
                            elif choice_place == 2:
                                numOfEdges = 500
                            elif choice_place == 4:
                                numOfEdges = 657
                            elif choice_place == 5:
                                numOfEdges = 3750
                            elif choice_place == 6:
                                numOfEdges = 1750
                            elif choice_place == 7:
                                numOfEdges = 650
                            elif choice_place == 8:
                                numOfEdges = 500
                            elif choice_place == 9:
                                numOfEdges = 120
                            elif choice_place == 10:
                                numOfEdges = 5000
                            elif choice_place == 11:
                                numOfEdges = 6000
                            elif choice_place == 12:
                                numOfEdges = 182
                            elif choice_place == 13:
                                numOfEdges = 806
                            elif choice_place == 14:
                                numOfEdges = 651
                            elif choice_place == 15:
                                numOfEdges = 181
                            elif choice_place == 16:
                                numOfEdges = 181
                            elif choice_place == 17:
                                numOfEdges = 183
                            elif choice_place == 19:
                                numOfEdges = 180
                            else:
                                numOfEdges = 0

                            ###################################################################
                            # 7a) RAW experiment first (raw_or_hashed=0)
                            ###################################################################
                            raw_or_hashed, permutation, current_compress = 0, -1, -1
                            print(f"\n\n\n***********   R u n    W i t h       R  A  W       D a t a     # Threshold: {threshold}% , NumOfObjs:{numo_objs}  ***********\n")
                            result_running = run_script(
                                raw_or_hashed, seed, current_compress, permutation,
                                numo_objs, length_of_path, threshold_real, depth,
                                help_for_jaccard, choice_place, run_once,
                                repeat_experiment, limitN, Experiment_for_Repetition
                            )
                            run_once = 1

                            if result_running == 0:
                                print("No homopaths found at this threshold. Skipping to next threshold.")
                                continue
                            print("Raw data experiment completed.\n")

                            ###################################################################
                            # 7b) MinHash-based experiment for multiple compression targets
                            ###################################################################
                            print(f"*******   M i n H a s h e d    C o m p r e s s e d    D a t a     # Threshold: {threshold}% , NumOfObjs:{numo_objs}  *******\n")

                            # We'll measure file sizes to compute real compression
                            raw_file_size = os.path.getsize(File_4_sensors)

                            listof_Seeds.append(seed)
                            raw_or_hashed = 1
                            retain_numberOfPermutation = False
                            permutation = 0

                            compress_struct = {}

                            # For each desired compression ratio in descending order
                            for current_compress in my_compression_levels:
                                if not retain_numberOfPermutation:
                                    permutation += 1  # Start at 1 for minhash signature length

                                # As outlined in the referenced paper, the data compression process is treated as a "black box" operation, 
                                # where the entire network's data is compressed as a single entity.
                                # 
                                # The primary objectives of this approach are:
                                # 1. Determine the total size of the uncompressed "Raw Data" within the black box.
                                # 2. Begin with a MinHash signature of length 1 and calculate the resulting "Compressed Data" black box.
                                # 3. Compare the size of the "Compressed Data" with the original "Raw Data."
                                # 4. Calculate the compression ratio achieved.
                                # 
                                # Note: This method does not guarantee precise adherence to target compression ratios.
                                # To account for this, a tolerance of ±10% is applied to the target ratio.
                                # For example, if the target compression ratio is 4, an acceptable result would fall within the range of 3.6 to 4.4.

                                max_accepted_real_compress = current_compress + (current_compress * 0.10)
                                min_accepted_real_compress = current_compress - (current_compress * 0.10)

                                File_4_sensors_HASHED_FILE_for_current_compress = f"4_sensors_HASHED_{current_compress}.txt"
                                experiment_run = True

                                # If repeating an older experiment, we might have a known permutation
                                if repeat_experiment == 1:
                                    for compr in dictionaryWithComprAndPermut:
                                        if current_compress in dictionaryWithComprAndPermut:
                                            if current_compress == int(compr):
                                                permutation = dictionaryWithComprAndPermut[compr]
                                                # Hash the data with that known permutation
                                                hash_data(File_4_sensors, permutation, seed, File_4_sensors_HASHED_FILE, threshold)
                                                hashed_file_size = os.path.getsize(File_4_sensors_HASHED_FILE)
                                                real_compress = (raw_file_size / hashed_file_size)
                                                experiment_run = True
                                        else:
                                            experiment_run = False
                                            continue
                                else:
                                    # Not repeating => we find the needed permutations now
                                    hash_data(File_4_sensors, permutation, seed, File_4_sensors_HASHED_FILE, threshold)
                                    hashed_file_size = os.path.getsize(File_4_sensors_HASHED_FILE)
                                    real_compress = (raw_file_size / hashed_file_size)

                                    if not permutations_calculated:
                                        # Check if we are within ±10%
                                        if real_compress > max_accepted_real_compress or real_compress < min_accepted_real_compress:
                                            if real_compress < min_accepted_real_compress:
                                                # Over-compressed => skip
                                                retain_numberOfPermutation = True
                                                experiment_run = False
                                                print(f"Cannot achieve compress {current_compress} with MinHashSig= {permutation}. Next compression goal.")
                                                continue
                                            else:
                                                # If we are above max => increment 'permutation' 
                                                while real_compress > max_accepted_real_compress:
                                                    permutation += 1
                                                    print(f"Attempting compress {current_compress} with MinHashSignature= {permutation}")
                                                    hash_data(File_4_sensors, permutation, seed, File_4_sensors_HASHED_FILE, threshold)
                                                    hashed_file_size = os.path.getsize(File_4_sensors_HASHED_FILE)
                                                    real_compress = (raw_file_size / hashed_file_size)
                                                    if real_compress < min_accepted_real_compress:
                                                        retain_numberOfPermutation = True
                                                        experiment_run = False
                                                        print(f"Overstepped min compress rate for {current_compress} with signature length {permutation}. Adjust or skip.")
                                                        break

                                        # If we succeeded in a valid compress, store in CompressDict
                                        if current_compress not in CompressDict:
                                            CompressDict[current_compress] = permutation
                                    else:
                                        # If the real_compress value exceeds the max_accepted_real_compress, 
                                        # we need to increase the length of the MinHash signature to achieve the desired compression goal.
                                        # 
                                        # Additionally, if the MinHash signatures have already been calculated for specific compression rates, 
                                        # we can avoid redundant calculations when processing different thresholds.
                                        # To optimize the process, we can store the precomputed MinHash signatures for fixed compression goals 
                                        # (e.g., 2, 4, ..., 128, 256), enabling faster execution for subsequent computations.

                                        if current_compress in CompressDict:
                                            permutation = CompressDict[current_compress]
                                        else:
                                            experiment_run = False
                                            continue

                                        # Re-hash with the known permutation
                                        hash_data(File_4_sensors, permutation, seed, File_4_sensors_HASHED_FILE, threshold)
                                        hashed_file_size = os.path.getsize(File_4_sensors_HASHED_FILE)
                                        real_compress = (raw_file_size / hashed_file_size)
                                    # If we get here, experiment_run = True
                                    experiment_run = True

                                # Record the chosen permutation for current_compress
                                if current_compress not in compress_struct:
                                    compress_struct[current_compress] = permutation

                                # If the final check says we can run an experiment:
                                if experiment_run == True:
                                    if current_compress in CompressDict:
                                    # Store the final permutation in our dictionary
                                        CompressDict[current_compress] = permutation

                                    print(f"!!!!!  Achieved Target Compress {current_compress} => Real Compress {real_compress:.2f} (Length of MinHashSig= {permutation})  !!!!!")
                                    
                                    # Copy the hashed sensor file to a named file for that compress
                                    copy_file(File_4_sensors_HASHED_FILE, File_4_sensors_HASHED_FILE_for_current_compress)

                                    # Now run the experiment in hashed mode with the found permutation
                                    run_script(
                                        raw_or_hashed, seed, current_compress, permutation,
                                        numo_objs, length_of_path, threshold_real, depth,
                                        help_for_jaccard, choice_place, run_once,
                                        repeat_experiment, limitN, Experiment_for_Repetition
                                    )

                                    # If last threshold, copy region hashed sensor files as well
                                    if threshold == my_threshold_levels[-1]:
                                        if depth == 2:
                                            copy_file(f"Regional_4_sensors_HASHED112.txt", f"Regional_4_sensors_HASHED112_{current_compress}.txt")
                                            copy_file(f"Regional_4_sensors_HASHED122.txt", f"Regional_4_sensors_HASHED122_{current_compress}.txt")
                                            copy_file(f"Regional_4_sensors_HASHED212.txt", f"Regional_4_sensors_HASHED212_{current_compress}.txt")
                                            copy_file(f"Regional_4_sensors_HASHED222.txt", f"Regional_4_sensors_HASHED222_{current_compress}.txt")
                                        elif depth == 1:
                                            copy_file(f"Regional_4_sensors_HASHED11.txt", f"Regional_4_sensors_HASHED11_{current_compress}.txt")
                                            copy_file(f"Regional_4_sensors_HASHED21.txt", f"Regional_4_sensors_HASHED21_{current_compress}.txt")
                                        elif depth == 0:
                                            copy_file(f"Regional_4_sensors_HASHED10.txt", f"Regional_4_sensors_HASHED10_{current_compress}.txt")
                                        # Please add the corresponding cases for cases with depth >2 

                                    # We track the real final compression ratio
                                    raw_file_size = os.path.getsize(File_4_sensors)
                                    hashed_file_size = os.path.getsize(File_4_sensors_HASHED_FILE)
                                    real_compress = int(round((raw_file_size/hashed_file_size),2))
                                    
                                    # Insert it into our dictionaries
                                    if current_compress not in num_objects_dict[numo_objs]:
                                        num_objects_dict[numo_objs][current_compress] = {}
                                    raw_or_hashed = 1
                                    

                                else:
                                    # If not feasible, skip
                                    continue

                                # Some artificial sleep to simulate time or reduce CPU usage
                                time.sleep(2 + (numo_objs / (current_compress ** threshold) * (1 - run_once) / 1000))
                                num_objects_dict[numo_objs][current_compress] =  current_compress

                                

                            # If we successfully computed permutations for all compress levels
                            if my_compression_levels[-1] in CompressDict:
                                permutations_calculated = True

                            end_time1 = time.time()
                            print(f"Execution time for threshold {threshold}%: {end_time1 - start_time1:.2f} seconds")

                        # 8) If we found permutations for all compress levels, we finalize
                        if permutations_calculated:
                            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                            print(f"Experiment finished for path_len={length_of_path}, threshold={threshold}, #objs={numo_objs}")
                            
                            # File paths
                            compare_file_path = 'Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_pairs.txt'
                            top_leader_file_path = 'Current_Experiment_Top_Leader_Reg_Leader_edges_costs.txt'
                            output_file_path = 'Current_Experiment_Top_Leader_Reg_Leader_pairs_costs.txt'

                            # Possibly produce pair-based analysis for final results
                            create_testing_file_for_pairs(compare_file_path, top_leader_file_path, output_file_path)

                            # Decide on the new folder name for archiving logs
                            if repeat_experiment == 1 and testing_pairs == 1:
                                if help_for_jaccard == 0:
                                    folder_name = f"Experiment_{numOfEdges}_{numo_objs}_{threshold}_{length_of_path}_{choice_place}_{timestamp}RepeatForPairsHelpNO"
                                else:
                                    folder_name = f"Experiment_{numOfEdges}_{numo_objs}_{threshold}_{length_of_path}_{choice_place}_{timestamp}RepeatForPairsHelpYES"
                            elif repeat_experiment == 1 and testing_pairs == 0:
                                if help_for_jaccard == 0:
                                    folder_name = f"Experiment_{numOfEdges}_{numo_objs}_{threshold}_{length_of_path}_{choice_place}_{timestamp}RepeatForEdgesHelpNO"
                                else:
                                    folder_name = f"Experiment_{numOfEdges}_{numo_objs}_{threshold}_{length_of_path}_{choice_place}_{timestamp}RepeatForEdgesHelpYES"
                            else:
                                folder_name = f"Experiment_{numOfEdges}_{numo_objs}_{threshold}_{length_of_path}_{choice_place}_{timestamp}"

                            os.mkdir(folder_name)

                            # Move relevant logs and files into the new folder
                            for file in os.listdir():
                                if (
                                    file == "RESULTS.txt" or
                                    file == "ResultsOfExperiments.txt" or
                                    file == "Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_pairs.txt" or
                                    file == "Current_Experiment_Top_Leader_Reg_Leader_pairs_costs.txt" or
                                    (file.startswith("depth_") and file.endswith(".png")) or
                                    file == "Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_all.txt" or
                                    file == "Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_allwithout_single.txt" or
                                    file == "Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_all_with_costs.txt" or
                                    file == "Current_Experiment_Compare_RAW_HASh_NEW_formatted_paths_single.txt" or
                                    file == "correcthomoedges111.json" or
                                    file == "correcthomoedges112.json" or
                                    file == "correcthomoedges113.json" or
                                    file == "correcthomoedges211.json" or
                                    file == "correcthomoedges212.json" or
                                    file == "correcthomoedges213.json" or
                                    file == "correcthomoedges2.json" or
                                    file == "correcthomoedges3.json" or
                                    file == "Current_Experiment_Info.txt" or
                                    file == "depth_11.png" or
                                    file == "depth_21.png" or
                                    file == "depth_112.png" or
                                    file == "depth_212.png" or
                                    file == "depth_111.png" or
                                    file == "depth_211.png" or
                                    file == "7_ConnectionsBetween_Regions.txt" or
                                    file == "3_Motions.txt" or
                                    file == "Current_Experiment_Top_Leader_flat_visualization_per_Region_brackets.txt" or
                                    file == "Current_Experiment_Top_Leader_flat_visualization_all_together.txt" or
                                    file == "all_with_costs.txt" or
                                    file == "Current_Experiment_Top_Leader_Reg_Leader_edges_costs.txt" or
                                    file == "Current_Experiment_Top_Leader_Reg_Leader_span_HoMoPaths_costs.txt" or
                                    file == "seeds.txt" or
                                    file == "4_sensors_HASHED.txt" or
                                    file == "4_sensors.txt" or
                                    file == "3_Motions.txt" or
                                    file.startswith("4_sensors_HASHED_") or
                                    file.startswith("Regional_4_sensors") or
                                    file.startswith("1_combined_nodes_edges.txt") or
                                    file.startswith("2_edgeconnections.txt")
                                ):
                                    source_path = os.path.join(os.getcwd(), file)
                                    if os.path.isfile(source_path):
                                        destination_path = os.path.join(os.getcwd(), folder_name, file)
                                        shutil.move(source_path, destination_path)
                                        print(f"File: {file} moved to {folder_name}")

    # Return the final threshold used as a courtesy
    return threshold_real


# The function is called here, capturing the final threshold returned.
threshold = main_function()


# Preserve deletion for these files while repeating experiments
experiment_code    = "experiment_creator.py"
homopa_python_code = "homopa.py"










