# Change the script switches below to select which files you would like to run

from nicer_variables import *

# Find the script's own path
scriptPath = os.path.abspath(__file__)
scriptPathRev = scriptPath[::-1]
scriptPathRev = scriptPathRev[scriptPathRev.find("/") + 1:]
scriptDir = scriptPathRev[::-1] 
os.chdir(scriptDir)

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