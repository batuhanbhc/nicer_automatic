# This is the main NICER script that provides a full NICER spectral analysis by running all sub-scripts
# Authors: Batuhan Bahçeci
# Contact: batuhan.bahceci@sabanciuniv.edu

from nicer_variables import *

print("==============================================================================")
print("\t\t\tRunning the file: nicer_main.py\n")

# Change the script switches below to select which files you would like to run

# Find the script's own path
scriptPath = os.path.abspath(__file__)
scriptPathRev = scriptPath[::-1]
scriptPathRev = scriptPathRev[scriptPathRev.find("/") + 1:]
scriptDir = scriptPathRev[::-1] 
os.chdir(scriptDir)

# Check if outputDir has been assigned to be a spesific directory or not
# If not, assign outputDir to the directory where the script is located at
if outputDir == "":
    outputDir = scriptDir

# Input check for outputDir
while(Path(outputDir).exists() == False):
    print("Directory defined by outputDir could not be found. Terminating the script...")
    quit()

if createSwitch:
    os.system("python3 " + createScript)
if fitSwitch:
    os.system("python3 " + fitScript)
if fluxSwitch:
    os.system("python3 " + fluxScript)
if plotSwitch:
    os.system("python3 " + plotScript)

if Path("__pycache__").exists():
    os.system("rm -rf __pycache__")

if Path("1").exists():
    # Sometimes, a file named "1" is created for reasons I haven't figured out yet
    os.system("rm 1")