# This is an automatic NICER script for creating event files
# Make sure the script is located at the same directory as the input text file containing the locations of observation folders

import subprocess
import os
from pathlib import Path
from nicer_variables import *

# Find the script's own path
scriptPath = os.path.abspath(__file__)
scriptPathRev = scriptPath[::-1]
scriptPathRev = scriptPathRev[scriptPathRev.find("/") + 1:]
scriptDir = scriptPathRev[::-1]

# Check if outputDir has been assigned to be a spesific directory or not
# If not, assign outputDir to the directory where the script is located at
if outputDir == "":
    outputDir = scriptDir

# Open the txt file located within the same directory as the script.
try:
    inputFile = open(scriptDir + "/" + inputTxtFile, "r")
except:
    print("Could not find the input txt file under " + scriptDir + ". Terminating the script...")
    quit()

obsList = []
for line in inputFile.readlines():
    line = line.strip("\n' ")
    obsList.append(line)
inputFile.close()

# Update Nicer geomagnetic data
os.system("nigeodown chatter=3")

counter = 0
for obs in obsList:
    counter += 1
    if obs == "":
        print("Empty line detected in " + inputTxtFile + ": Line " + str(counter) + ".\n")
        continue

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
    nicerl2 = "nicerl2 indir=" + obs + " clobber=yes chatter=1 history=yes detlist=launch,-14,-34 filtcolumns=NICERV4 cldir=" + outObsDir
    os.system(nicerl2)

    nicerl3spect = "nicerl3-spect " + outObsDir + " grouptype=optmin groupscale=10 bkgmodeltype=3c50 suffix=3c50 clobber=YES mkfile=" + obs + "/auxil/*.mkf"
    os.system(nicerl3spect)

    nicerl3lc = "nicerl3-lc " + outObsDir + " pirange=50-1000 timebin=1 clobber=YES mkfile=" + obs + "/auxil/*.mkf"
    os.system(nicerl3lc)

    # Create log file
    logPath = Path(outObsDir +"/" + resultsFile)
    if not logPath.exists():
        subprocess.run(["touch", outObsDir + "/" + resultsFile])

# This file is created after importing variables from another python file
if Path(scriptDir + "/__pycache__").exists():
    os.system("rm -rf "+scriptDir+"/__pycache__")