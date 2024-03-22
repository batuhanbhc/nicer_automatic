# This is the main NICER script that provides a full NICER spectral analysis by running all sub-scripts
# Authors: Batuhan Bahçeci
# Contact: batuhan.bahceci@sabanciuniv.edu

from parameter import *

print("==============================================================================")
print("\t\t\tRunning nicer_main.py\n")

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
if Path(scriptDir + "/" + create_script_name).exists() == False:
    print(create_script_name + " file necessary for the proper execution of the script could not be found under " + scriptDir)
    stopExecution = True

if Path(scriptDir + "/" + fit_script_name).exists() == False:
    print(fit_script_name + " file necessary for the proper execution of the script could not be found under " + scriptDir)
    stopExecution = True

if Path(scriptDir + "/" + flux_script_name).exists() == False:
    print(flux_script_name + " file necessary for the proper execution of the script could not be found under " + scriptDir)
    stopExecution = True

if Path(scriptDir + "/" + plot_script_name).exists() == False:
    print(plot_script_name + " file necessary for the proper execution of the script could not be found under " + scriptDir)
    stopExecution = True

if stopExecution:
    print("Terminating the script...")
    quit()
# ====================================================================================================================

if run_create_script:
    os.system("python3 " + create_script_name)
if run_fit_script:
    os.system("python3 " + fit_script_name)
if run_flux_script:
    os.system("python3 " + flux_script_name)
if run_plot_script:
    os.system("python3 " + plot_script_name)

if Path("__pycache__").exists():
    os.system("rm -rf __pycache__")

if Path("1").exists():
    # Sometimes, a file named "1" is created, I haven't figured out why yet
    os.system("rm 1")