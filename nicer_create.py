# This is an automatic NICER script for creating output files (Event files, spectrum, background, responses, light curves...)
# Authors: Batuhan Bahçeci
# Contact: batuhan.bahceci@sabanciuniv.edu

from parameter import *
from datetime import datetime, timezone, timedelta

print("==============================================================================")
print("\t\t\tRunning " + create_script_name + "\n")

# Find the script's own path
scriptPath = os.path.abspath(__file__)
scriptPathRev = scriptPath[::-1]
scriptPathRev = scriptPathRev[scriptPathRev.find("/") + 1:]
scriptDir = scriptPathRev[::-1]

# Check if outputDir has been assigned to be a spesific directory or not
# If not, assign outputDir to the directory where the script is located at
if outputDir == "":
    outputDir = scriptDir

#=============================================== Input Checks ===========================================================
# Input check for outputDir
while(Path(outputDir).exists() == False):
    print("Directory defined by outputDir could not be found. Terminating the script...")
    quit()

# Input check for overwrite_files
if isinstance(overwrite_files, bool) == False:
    while True:
        print("\nThe 'overwrite_files' variable is not of type boolean.")
        overwrite_files = input("Please enter a boolean value for 'overwrite_files' (True/False): ")

        if overwrite_files == "True" or overwrite_files == "False":
            overwrite_files = bool(overwrite_files)
            break

# Input check for createHighResLightCurves
if isinstance(createHighResLightCurves, bool) == False:
    while True:
        print("\nThe 'createHighResLightCurves' variable is not of type boolean.")
        createHighResLightCurves = input("Please enter a boolean value for 'createHighResLightCurves' (True/False): ")

        if createHighResLightCurves == "True" or createHighResLightCurves == "False":
            createHighResLightCurves = bool(createHighResLightCurves)
            break

# Input check for highResLcTimeResInPwrTwo
if createHighResLightCurves:
    while (str(highResLcTimeResInPwrTwo).lstrip("-").isnumeric() == False) or (int(highResLcTimeResInPwrTwo) > 0):
        print("Please enter an integer value x <= 0 for the time resolution of high resolution light curves, or enter 'exit' to terminate the script.")
        highResLcTimeResInPwrTwo = input("Enter your input x (x<=0 / exit): ")
        if highResLcTimeResInPwrTwo == "exit":
            print("Terminating " + create_script_name + ": Next scripts to be executed may crash.")
            quit()
        if highResLcTimeResInPwrTwo.lstrip("-").isnumeric() == True and int(highResLcTimeResInPwrTwo) <= 0:
            highResLcTimeResInPwrTwo = int(highResLcTimeResInPwrTwo)
            break

# Input check for createHighResLightCurves
while (str(createHighResLightCurves) != "True" and str(createHighResLightCurves) != "False"):
    createHighResLightCurves = input("Enter True or False to create light curves with high resolution (True/False): ")
    if createHighResLightCurves == "True" or createHighResLightCurves == "False":
        createHighResLightCurves = bool(createHighResLightCurves)
        break

# Open the txt file located within the same directory as the script.
try:
    inputFile = open(scriptDir + "/" + inputTxtFile, "r")
except Exception as e:
    print(f"Exception occured while opening {inputTxtFile}: {e}")
    quit()
#========================================================================================================================
if overwrite_files == True:
    print("'overwrite_files' variable is set to True: Clobber parameter for Nicer tasks will be set to YES.\n")
else:
    print("'overwrite_files' variable is set to False: Clobber parameter for Nicer tasks will be set to NO.")
    print("Already existing files under output directories will be deleted before running Nicer tasks.\n")
    
# Create "commonFiles" directory for storing model files and flux graphs
commonDirectory = outputDir + "/commonFiles"   # ~/NICER/analysis/commonFiles
if Path(commonDirectory).exists() == False:
    os.system("mkdir " + commonDirectory)

# Create 22/05/2023 Nicer light leak date object
lightLeak_date = "2023/05/22" 
date_format = "%Y/%m/%d"
lightleak_object = datetime.strptime(lightLeak_date, date_format)

#Extract observation paths from observations.txt
validPaths = []
for line in inputFile.readlines():
    line = line.replace(" ", "")
    line = line.strip("\n")
    if line != "" and Path(line).exists():
        validPaths.append(line)

inputFile.close()

# If there is no valid observation path, do not proceed any further
if len(validPaths) == 0:
    print("Could not find any observation directory to process.")
    quit()

cwd = os.getcwd()

# Test whether $GEOMAG_PATH is defined or not, change directory to $GEOMAG_PATH if it exists.
geomag_path = os.environ.get("GEOMAG_PATH")
try:
    os.chdir(geomag_path)
except TypeError:
    print("Environment variable $GEOMAG_PATH is not defined.")
    quit()
except:
    print("Could not find the directory spesified by $GEOMAG_PATH. Please check whether it points to an existing directory.")
    quit()

nigeodownFlag = True

if Path("kp_potsdam.fits").exists() == False:
    print("Running nigeodown...")
    os.system("nigeodown chatter=5")
    print("Finished nigeodown.")
    nigeodownFlag = False

# Extract file creation date
hdu = fits.open("kp_potsdam.fits")
date = hdu[0].header["DATE"]
hdu.close()

date = date.replace("T", " ")
geomag_time_object = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
geomag_time_object = geomag_time_object + timedelta(days=1)

# Change directory back to the previous location
os.chdir(cwd)
import glob
# This dictionary will carry obsid-(output directory, orbit time) key-value pairs for the observation made after the light leak
lightleak_observations = {}

processed_paths = []

valid_paths_v2 = []

# Iterate through the filter files of observations, extract date of each observation
for obs in validPaths:
    #Find observation id (e.g. 6130010120)
    pathLocations = obs.split("/")
    if pathLocations[-1] == "":
        obsid = pathLocations[-2]
    else:
        obsid = pathLocations[-1]
    
    matching_mkf_files = glob.glob(obs + "/auxil/ni*.mkf*")

    if not any(matching_mkf_files):
        print(f"Could not find mkf file under {obs}/auxil")
        print(f"Observation {obsid} will not be processed.")
        continue

    hdu = fits.open(matching_mkf_files[0])
    date = hdu[1].header["DATE-OBS"]
    date = date.replace("T", " ")
    time_object = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')

    if nigeodownFlag and geomag_time_object < time_object:
        # Geomagnetic data is not updated for the current observation
        nigeodownFlag = False
        print("Running nigeodown...")
        os.system("nigeodown chatter=5")
        print("Finished nigeodown.")
    
    if time_object > lightleak_object:
        try:
            sunshine = hdu[1].data["SUNSHINE"]
        except Exception as e:
            print(f"Exception occured while accessing 'SUNSHINE' column in mkf file: {e}")
            continue

        dayFlag = False
        nightFlag = False
        mixFlag = False
        for val in sunshine:
            if val == 1:
                dayFlag = True
            else:
                nightFlag = True
            
            if dayFlag and nightFlag:
                mixFlag = True
                break
        
        if dayFlag and (not nightFlag):
            # Day observation after light leak
            lightleak_observations[obsid] = [(outputDir + "/" + obsid + "/day", "day")]

            # Create the output directories if they are not created already
            if Path(outputDir + "/" + obsid).exists() == False:
                os.system("mkdir " + outputDir + "/" + obsid)
            if Path(outputDir + "/" + obsid + "/day").exists() == False:
                os.system("mkdir " + outputDir + "/" + obsid + "/day")

            processed_paths.append([outputDir + "/" + obsid + "/day", obsid])

        elif nightFlag and (not dayFlag):
            # Night observation after light leak
            lightleak_observations[obsid] = [(outputDir + "/" + obsid + "/night", "night")]

            # Create the output directories if they are not created already
            if Path(outputDir + "/" + obsid).exists() == False:
                os.system("mkdir " + outputDir + "/" + obsid)
            if Path(outputDir + "/" + obsid + "/night").exists() == False:
                os.system("mkdir " + outputDir + "/" + obsid + "/night")

            processed_paths.append([outputDir + "/" + obsid + "/night", obsid])

        else:
            # Mixed observation (both day and night) after light leak
            lightleak_observations[obsid] = [(outputDir + "/" + obsid + "/day", "day"), (outputDir + "/" + obsid + "/night", "night")]

            # Create the output directories if they are not created already
            if Path(outputDir + "/" + obsid).exists() == False:
                os.system("mkdir " + outputDir + "/" + obsid)
            if Path(outputDir + "/" + obsid + "/night").exists() == False:
                os.system("mkdir " + outputDir + "/" + obsid + "/night")
            if Path(outputDir + "/" + obsid + "/day").exists() == False:
                os.system("mkdir " + outputDir + "/" + obsid + "/day")

            processed_paths.append([outputDir + "/" + obsid + "/day", obsid])
            processed_paths.append([outputDir + "/" + obsid + "/night", obsid])

    else:
        # Observation before the light leak
        if Path(outputDir + "/" + obsid).exists() == False:
            os.system("mkdir " + outputDir + "/" + obsid)

        processed_paths.append([outputDir + "/" + obsid, obsid])
    
    valid_paths_v2.append(obs)

for obs in valid_paths_v2:
    #Find observation id (e.g. 6130010120)
    pathLocations = obs.split("/")
    if pathLocations[-1] == "":
        obsid = pathLocations[-2]
    else:
        obsid = pathLocations[-1]
    
    if obsid not in lightleak_observations:
        # Observation made before the light leak
        outObsDir = outputDir + "/" + obsid

        # Create a log file to record the outputs of pipeline commands
        pipelineLog = outObsDir + "/pipeline_output.log"
        if Path(pipelineLog).exists() == False:
            os.system("touch " + pipelineLog)

        
        clobber_parameter = "no"

        if (overwrite_files == False):
            os.system(f"rm -r {outObsDir}/*")
        else:
            clobber_parameter = "yes"

        matching_mkf_files = glob.glob(obs + "/auxil/ni*.mkf*")
        for each_file in matching_mkf_files:
            os.system(f"cp {each_file} {outObsDir}")

        # Run nicer pipeline commands
        print("==============================================================================")
        print("Starting to run pipeline commands for observation: " + obsid + "\n")

        # Run nicerl2
        print("Running nicerl2...")
        nicerl2 = "nicerl2 indir=" + obs + " mkfile='$CLDIR/ni$OBSID.mkf' clobber=" + clobber_parameter + " chatter=3 history=yes detlist=launch,-14,-34 filtcolumns=NICERV5 cldir=" + outObsDir + " > " + pipelineLog
        try:
            os.system(nicerl2)
            print("Finished nicerl2.\n")
        except Exception as e:
            print(f"Exception occured while running nicerl2: {e}")
            continue

        # Run nicerl3-spect
        print("Running nicerl3-spect...")
        nicerl3spect = "nicerl3-spect " + outObsDir + " mkfile='$CLDIR/ni$OBSID.mkf' clobber=" + clobber_parameter + " grouptype=optmin chatter=3 groupscale=10 bkgmodeltype=3c50 suffix=3c50 >> " + pipelineLog     
        try:
            os.system(nicerl3spect)
            print("Finished nicerl3-spect.\n")
        except Exception as e:
            print(f"Exception occured while running nicerl3-spect: {e}")
            continue
        
        # Run nicerl3-lc and create default resolution (1s) light curve
        print("Running nicerl3-lc...")
        nicerl3lc = "nicerl3-lc " + outObsDir + " mkfile='$CLDIR/ni$OBSID.mkf' clobber=" + clobber_parameter + " pirange=50-1000 chatter=4 timebin=1 suffix=_50_1000_dt0 >> " + pipelineLog 
        try:
            os.system(nicerl3lc)
            print("Finished nicerl3-lc.")
        except Exception as e:
            print(f"Exception occured while running nicerl3-lc: {e}")
            continue

        # Check whether the user wants to create high resolution light curves
        if createHighResLightCurves:
            for each in highResLcPiRanges:
                each = each.replace(" ", "")
                nicerl3lc = "nicerl3-lc " + outObsDir + " mkfile='$CLDIR/ni$OBSID.mkf' clobber=" + clobber_parameter + " pirange=" + str(each) + " timebin=" + str(2**highResLcTimeResInPwrTwo) +" suffix=_"+ str(each).replace("-", "_") + "_dt" + str(abs(highResLcTimeResInPwrTwo)).replace(".", "") + " >> " + pipelineLog
                try:
                    os.system(nicerl3lc)
                except:
                    print(f"Exception occured while running high resolution nicerl3-lc: {e}")
                    break

            print("Finished nicerl3-lc.\n")

        print("Please do not forget to check pipeline log file to detect potential issues that might have occured while creating output files.")
        print("==============================================================================")

        # Create log file for saving fit results that will be used by nicer_fit.py
        fitLog = outObsDir +"/" + resultsFile
        if Path(fitLog).exists() == False:
            os.system("touch " + fitLog)
    
    else:
        for obsTuple in lightleak_observations[obsid]:
            outObsDir = obsTuple[0]
            obsMode = obsTuple[1]

            # Create a log file to record the outputs of pipeline commands
            pipelineLog = outObsDir + "/pipeline_output.log"
            if Path(pipelineLog).exists() == False:
                os.system("touch " + pipelineLog)
            
            clobber_parameter = "no"

            if (overwrite_files == False):
                os.system(f"rm -r {outObsDir}/*")
            else:
                clobber_parameter = "yes"
            
            matching_mkf_files = glob.glob(obs + "/auxil/ni*.mkf*")
            for each_file in matching_mkf_files:
                os.system(f"cp {each_file} {outObsDir}")

            if obsMode == "night":
                threshRange = "'-3.0-3.0'"
            else:
                threshRange = "'32-38'"

            # Run nicer pipeline commands
            print("==============================================================================")
            print("Starting to run pipeline commands for observation: " + obsid + "\n")

            print("NOTICE: Observation " + obsid + " is made after the 22/05/2023 NICER optical light leak.")
            print("Spectral files will be located under 'day' and 'night' sub-directories depending on the observation orbit time.")
            print("Getting exposure=0 error especially for day-time observations is an expected result.")
            print("Currently processing: " + obsMode + " time\n")

            # Run nicerl2
            print("Running nicerl2...")
            nicerl2 = "nicerl2 indir=" + obs + " mkfile='$CLDIR/ni$OBSID.mkf' clobber=" + clobber_parameter + " chatter=3 history=yes detlist=launch,-14,-34 thresh_range=" + threshRange + " filtcolumns=NICERV5 cldir=" + outObsDir + " > " + pipelineLog
            try:
                os.system(nicerl2)
                print("Finished nicerl2.\n")
            except Exception as e:
                print(f"Exception occured while running nicerl2: {e}")
                continue

            # Run nicerl3-spect
            print("Running nicerl3-spect...")
            nicerl3spect = "nicerl3-spect " + outObsDir + " mkfile='$CLDIR/ni$OBSID.mkf' clobber=" + clobber_parameter + " grouptype=optmin groupscale=10 bkgmodeltype=3c50 suffix=3c50 >> " + pipelineLog
            try:
                os.system(nicerl3spect)
                print("Finished nicerl3-spect.\n")
            except Exception as e:
                print(f"Exception occured while running nicerl3-spect: {e}")
                continue
            
            # Run nicerl3-lc and create default resolution (1s) light curve
            print("Running nicerl3-lc...")
            nicerl3lc = "nicerl3-lc " + outObsDir + " mkfile='$CLDIR/ni$OBSID.mkf' clobber=" + clobber_parameter + " pirange=50-1000 timebin=1 suffix=_50_1000_dt0 >> " + pipelineLog
            try:
                os.system(nicerl3lc)
                print("Finished nicerl3-lc.\n")
            except Exception as e:
                print(f"Exception occured while running nicerl3-lc: {e}")
                continue

            # Check whether the user wants to create high resolution light curves
            if createHighResLightCurves:
                for each in highResLcPiRanges:
                    each = each.replace(" ", "")
                    nicerl3lc = "nicerl3-lc " + outObsDir + " mkfile='$CLDIR/ni$OBSID.mkf' clobber=" + clobber_parameter + " pirange=" + str(each) + " timebin=" + str(2**highResLcTimeResInPwrTwo) +" suffix=_"+ str(each).replace("-", "_") + "_dt" + str(abs(highResLcTimeResInPwrTwo)).replace(".", "") + " >> " + pipelineLog
                    try:
                        os.system(nicerl3lc)
                    except Exception as e:
                        print(f"Exception occured while running high resolution nicerl3-lc: {e}")
                        break


            print("Please do not forget to check pipeline log file to detect potential issues that might have occured while creating output files.")
            print("==============================================================================")

            # Create log file for saving fit results that will be used by nicer_fit.py
            fitLog = outObsDir +"/" + resultsFile
            if Path(fitLog).exists() == False:
                os.system("touch " + fitLog)

# Extract the paths, obsid and exposure of observations with exposure > 100 only.
expo_processed_paths = []
for each_path in processed_paths:
    folder_path = each_path[0]
    obsid = each_path[1]

    try:
        hdu = fits.open(folder_path + "/ni" + obsid + "mpu7_sr3c50.pha")
    except Exception as e:
        print(f"Exception occured while opening ni{obsid}mpu7_sr3c50.pha: {e}")
        continue
    try:
        expo = hdu[1].header["EXPOSURE"]
    except Exception as e:
        print(f"Missing column 'EXPOSURE' in ni{obsid}mpu7_sr3c50.pha: {e}")
        continue

    if expo >= 100:
        # Filter out observations with exposure less than 100 seconds
        expo_processed_paths.append([folder_path, obsid, expo])
    else:
        print(f"Observation {obsid} has exposure below 100 seconds, spectral fitting will not be applied.")


# Create processed_obs.txt that will serve as a log of the previously processed observations
if Path(commonDirectory + "/processed_obs.txt").exists() == False:
    os.system("touch " + commonDirectory + "/processed_obs.txt")


if clean_obs_history == False:
    all_file_lines = {}

    file = open(commonDirectory + "/processed_obs.txt", "r")
    all_lines = file.readlines()
    file.close()

    # Extract previously recorded paths
    for line in all_lines:
        line = line.strip("\n")
        all_file_lines[line] = 1

    # Add the exposure filtered paths into a single dictionary with the previous paths from processed_obs.txt
    for each in expo_processed_paths:
        path = each[0]
        obsid = each[1]
        expo = each[2]
        line = path + " " + str(obsid) + " " + str(expo)

        if line not in all_file_lines:
            all_file_lines[line] = 1

    # Convert the obsid value from int to string, and save all lines in a list of tuples
    lines_to_be_sorted = []
    for each_line in all_file_lines.keys():
        each_line = each_line.split(" ")
        each_line[1] = int(each_line[1])
        each_line = tuple(each_line)

        lines_to_be_sorted.append(each_line)

    # Sort the tuples according to obsid values
    sorted_lines = sorted(lines_to_be_sorted, key=lambda x: x[1])

    # Convert the sorted tuples to a line format in string
    lines_to_be_written = []
    for line in sorted_lines:
        line_str = ""

        for elem in line:
            line_str += (str(elem) + " ")
        
        line_str = line_str[:-1]
        line_str += "\n"

        lines_to_be_written.append(line_str)

    # Rewrite the contents of the processed_obs.txt
    file = open(commonDirectory + "/processed_obs.txt", "w")
    for line in lines_to_be_written:
        file.write(line)

    file.close()

else:
    # The previous records of paths will not be kept

    # Write the contents of the processed_obs.txt with only the currently filtered observations
    file = open(commonDirectory + "/processed_obs.txt", "w")
    for each in expo_processed_paths:
        line = ""

        for elem in each:
            line += (str(elem) + " ")
        
        line = line[:-1]
        line += "\n"

        file.write(line)
        
    file.close()

# This file is created after importing variables from another python file
if Path(scriptDir + "/__pycache__").exists():
    os.system("rm -rf "+scriptDir+"/__pycache__")