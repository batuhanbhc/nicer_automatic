# This is the main NICER script that provides a full NICER spectral analysis by running all sub-scripts
# Authors: Batuhan Bahçeci
# Contact: batuhan.bahceci@sabanciuniv.edu

from parameter import *

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

# ========================================= Input checks =============================================================
# Input check for outputDir
if Path(outputDir).exists() == False:
    print("Directory defined by outputDir could not be found. Terminating the script...")
    quit()

stopExecution = False
# Input checks for sub-scripts
if Path(scriptDir + "/" + createScript).exists() == False:
    print(createScript + " file necessary for the proper execution of the script could not be found under " + scriptDir)
    stopExecution = True

if Path(scriptDir + "/" + fitScript).exists() == False:
    print(fitScript + " file necessary for the proper execution of the script could not be found under " + scriptDir)
    stopExecution = True

if Path(scriptDir + "/" + fluxScript).exists() == False:
    print(fluxScript + " file necessary for the proper execution of the script could not be found under " + scriptDir)
    stopExecution = True

if Path(scriptDir + "/" + plotScript).exists() == False:
    print(plotScript + " file necessary for the proper execution of the script could not be found under " + scriptDir)
    stopExecution = True

if stopExecution:
    print("Terminating the script...")
    quit()
# ====================================================================================================================

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