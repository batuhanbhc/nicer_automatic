# Change the script switches below to select which files you would like to run

import os
from pathlib import Path

# Find the script's own path
scriptPath = os.path.abspath(__file__)
scriptPathRev = scriptPath[::-1]
scriptPathRev = scriptPathRev[scriptPathRev.find("/") + 1:]
scriptDir = scriptPathRev[::-1] 
os.chdir(scriptDir)

# Script names
create_script = "nicer_create.py"
fit_script = "nicer_fit.py"
flux_script = "nicer_flux.py"

# Script switches
createSwitch = True
fitSwitch = True
fluxSwitch = True

if createSwitch:
    os.system("python3 " + create_script)
if fitSwitch:
    os.system("python3 " + fit_script)
if fluxSwitch:
    os.system("python3 " + flux_script)

if Path("__pycache__").exists():
    os.system("rm -rf __pycache__")

if Path("1").exists():
    # Sometimes, a file named "1" is created for reasons I haven't figured out yet
    os.system("rm 1")