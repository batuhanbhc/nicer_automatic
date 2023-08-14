# This is an automatic NICER script for creating event files
# Make sure the script is located at the same directory as the input text file containing the locations of observation folders

import subprocess
import os
from pathlib import Path

#===================================================================================================================================
# Where do you want the event files to be created at (make sure you have this folder exists before running the script)
outputDir = "/home/batuhanbahceci/NICER/analysis"

# The name of the file that contains paths of the observation folders
inputTxtFile = "nicer_obs.txt"

# Where do you want the fit results to be recorded
resultsFile = "script_results.log"
#====================================================================================================================================

cwd = os.getcwd()

# Find the script's own path
scriptPath = os.path.abspath(__file__)
scriptPathRev = scriptPath[::-1]
scriptPathRev = scriptPathRev[scriptPathRev.find("/") + 1:]
scriptPath = scriptPathRev[::-1]

# Open the txt file located within the same directory as the script.
try:
    inputFile = open(scriptPath + "/" + inputTxtFile, "r")
except:
    print("Could not find the input txt file under " + scriptPath + ". Terminating the script...")
    quit()

obsList = []
for line in inputFile.readlines():
    line = line.strip("\n' ")
    obsList.append(line)
inputFile.close()

# Update Nicer geomagnetic data
os.system("nigeodown chatter=3")

for obs in obsList:
    parentDir = obs[::-1]
    obsid = parentDir[:parentDir.find("/")]         
    parentDir = parentDir[parentDir.find("/")+1:]   
    
    obsid = obsid[::-1]         # e.g. 6130010120

    outObsDir = outputDir +"/"+ obsid      # e.g. ~/NICER/analysis/6130010120   
    commonDirectory = outputDir + "/" + "commonFiles"   # ~/NICER/analysis/commonFiles

    # Create "commonFiles" directory for storing model files and flux graphs
    commonPath = Path(commonDirectory)
    if not commonPath.exists():
        subprocess.run(["mkdir", commonDirectory])

    # Run nicer pipeline commands
    nicerl2 = "nicerl2 indir=" + obs + " clobber=yes chatter=1 history=yes filtcolumns=NICERV4 cldir=" + outObsDir
    os.system(nicerl2)

    nicerl3spect = "nicerl3-spect " + outObsDir + " grouptype=optmin groupscale=10 bkgmodeltype=3c50 suffix=3c50 clobber=YES mkfile=" + obs + "/auxil/*.mkf"
    os.system(nicerl3spect)

    nicerl3lc = "nicerl3-lc " + outObsDir + " pirange=50-1000 timebin=1 clobber=YES mkfile=" + obs + "/auxil/*.mkf"
    os.system(nicerl3lc)

    # Create log file
    logPath = Path(outObsDir +"/" + resultsFile)
    if not logPath.exists():
        subprocess.run(["touch", outObsDir + "/" + resultsFile])
