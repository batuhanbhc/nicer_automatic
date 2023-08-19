import os

scriptsLoc = "/home/batuhanbahceci/scripts/nicer"
os.chdir(scriptsLoc)

# Script names
create_script = "nicer_create.py"
fit_script = "nicer_fit.py"
flux_script = "nicer_flux.py"

# Script switches
createSwitch = True
fitSwitch = True
fluxSwitch = False

if createSwitch:
    os.system("python3 " + create_script)
if fitSwitch:
    os.system("python3 " + fit_script)
if fluxSwitch:
    os.system("python3 " + flux_script)