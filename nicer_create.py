# This is an automatic NICER script for creating output files (Event files, spectrum, background, responses, light curves...)
# Authors: Batuhan Bahçeci
# Contact: batuhan.bahceci@sabanciuniv.edu

from nicer_variables import *
from datetime import datetime, timezone

print("==============================================================================")
print("\t\t\tRunning the file: " + createScript + "\n")

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
            print("Terminating the " + createScript + ": Next scripts to be executed may crash.")
            quit()
        if highResLcTimeResInPwrTwo.lstrip("-").isnumeric() == True and int(highResLcTimeResInPwrTwo) <= 0:
            highResLcTimeResInPwrTwo = int(highResLcTimeResInPwrTwo)
            break
#========================================================================================================================
# Open the txt file located within the same directory as the script.
try:
    inputFile = open(scriptDir + "/" + inputTxtFile, "r")
except:
    print("Could not find the input txt file under " + scriptDir + ". Terminating the script...")
    quit()

print("Observation directories to be processed:")
#Extract observation paths from nicer_obs.txt
obsList = []
for line in inputFile.readlines():
    line = line.replace(" ", "")
    line = line.strip("\n")
    if line != "" and Path(line).exists():
        print(line)
        obsList.append(line)
print()
inputFile.close()

if len(obsList) == 0:
    print("ERROR: Could not find any observation directory to process.")
    quit()

cwd = os.getcwd()

geomag_path = os.environ.get("GEOMAG_PATH")

try:
    os.chdir(geomag_path)
except TypeError:
    print("Environment variable $GEOMAG_PATH is not defined.")
    quit()
except:
    print("Could not find the directory spesified by $GEOMAG_PATH. Please check whether it points to an existing directory.")
    quit()

# Extract file creation date
hdu = fits.open("kp_potsdam.fits")
date = hdu[0].header["DATE"]
hdu.close()

date = date.replace("T", " ")
date_time_object = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')

current_utc_time = datetime.now(timezone.utc)
current_utc_time_str = current_utc_time.strftime('%Y-%m-%d %H:%M:%S')
current_utc_time_object = datetime.strptime(current_utc_time_str, '%Y-%m-%d %H:%M:%S')

difference = current_utc_time_object - date_time_object
total_difference = difference.total_seconds()

print("Time since Nicer geomagnetic files were last created (in seconds): " + str(total_difference))

# Check if the difference between UTC time and last file creation time is bigger than ~ 1 day; run nigeodown if so.
if (total_difference >= 87000):
    print("Running nigeodown...")
    os.system("nigeodown chatter=5")
    print("Finished nigeodown.")
else:
    print("Nicer geomagnetic data was updated recently, skipping nigeodown...")

os.chdir(cwd)

counter = 0
for obs in obsList:
    counter += 1

    #Find observation id (e.g. 6130010120)
    pathLocations = obs.split("/")
    if pathLocations[-1] == "":
        obsid = pathLocations[-2]
    else:
        obsid = pathLocations[-1]

    # Create observation directory for storing event files and etc.
    outObsDir = outputDir +"/"+ obsid      # e.g. ~/NICER/analysis/6130010120
    if Path(outObsDir).exists() == False:
        os.system("mkdir " + outObsDir)

    # Create "commonFiles" directory for storing model files and flux graphs
    commonDirectory = outputDir + "/commonFiles"   # ~/NICER/analysis/commonFiles
    if Path(commonDirectory).exists() == False:
        os.system("mkdir " + commonDirectory)

    # Create a log file to record the outputs of pipeline commands
    pipelineLog = outObsDir + "/pipeline_output.log"
    if Path(pipelineLog).exists() == False:
        os.system("touch " + pipelineLog)

    gunzipMkf = True
    fileList = os.listdir(obs+"/auxil")
    for each in fileList:
        each = each.strip("\n")
        if each == "ni" + obsid + ".mkf":
            gunzipMkf = False
            break

    if gunzipMkf:
        print("Gunzipping the mkf file prior to nicerl2.\n")
        os.system("gunzip "+obs+"/auxil/ni" + obsid + ".mkf.gz")

    # Run nicer pipeline commands
    print("==============================================================================")
    print("Starting to run pipeline commands for observation: " + obsid + "\n")

    # Run nicerl2
    print("Running nicerl2...")
    nicerl2 = "nicerl2 indir=" + obs + " clobber=yes history=yes detlist=launch,-14,-34 filtcolumns=NICERV5 niprefilter2_coltypes=base,3c50 cldir=" + outObsDir + " > " + pipelineLog
    os.system(nicerl2)
    print("Finished nicerl2.\n")

    # Run nicerl3-spect
    print("Running nicerl3-spect...")
    nicerl3spect = "nicerl3-spect " + outObsDir + " grouptype=optmin groupscale=10 bkgmodeltype=3c50 suffix=3c50 clobber=YES mkfile=" + obs + "/auxil/*.mkf >> " + pipelineLog
    os.system(nicerl3spect)
    print("Finished nicerl3-spect.\n")
    
    # Run nicerl3-lc and create default resolution (1s) light curve
    print("Running nicerl3-lc...")
    nicerl3lc = "nicerl3-lc " + outObsDir + " pirange=50-1000 timebin=1 suffix=_50_1000_1s clobber=YES mkfile=" + obs + "/auxil/*.mkf >> " + pipelineLog
    os.system(nicerl3lc)

    # Input check for createHighResLightCurves
    while (str(createHighResLightCurves) != "True" and str(createHighResLightCurves) != "False"):
        createHighResLightCurves = input("Enter True or False to create light curves with high resolution (True/False): ")
        if createHighResLightCurves == "True" or createHighResLightCurves == "False":
            createHighResLightCurves = bool(createHighResLightCurves)
            break

    # Check whether the user wants to create high resolution light curves
    if createHighResLightCurves:
        for each in highResLcPiRanges:
            each = each.replace(" ", "")
            nicerl3lc = "nicerl3-lc " + outObsDir + " pirange=" + str(each) + " timebin=" + str(2**highResLcTimeResInPwrTwo) +" suffix=_"+ str(each).replace("-", "_") + "_dt" + str(abs(highResLcTimeResInPwrTwo)).replace(".", "") + " clobber=YES mkfile=" + obs + "/auxil/*.mkf >> " + pipelineLog
            os.system(nicerl3lc)

    print("Finished nicerl3-lc.\n")

    print("Please do not forget to check pipeline log file to detect potential issues that might have occured while creating output files.")
    print("==============================================================================")

    # Create log file for saving fit results that will be used by nicer_fit.py
    fitLog = outObsDir +"/" + resultsFile
    if Path(fitLog).exists() == False:
        os.system("touch " + fitLog)

# This file is created after importing variables from another python file
if Path(scriptDir + "/__pycache__").exists():
    os.system("rm -rf "+scriptDir+"/__pycache__")