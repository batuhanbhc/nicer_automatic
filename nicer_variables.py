import os

#============================================ Common variables for all scripts =================================================

# The directory where the output files will be created at (Leave it blank [outputDir = ""] if you want output files to be created under the same directory as all scripts)
outputDir = "/home/batuhanbahceci/NICER/analysis"

# The name of the file that contains paths of the observation folders
inputTxtFile = "nicer_obs.txt"

# The log file where the fit results will be saved
resultsFile = "script_results.log"

# Write it in XSpec format
energyFilter = "0.5 10."

#=============================================== nicer.main spesific variables =================================================
# Script switches
createSwitch = False
fitSwitch = True
plotSwitch = True
fluxSwitch = False

# Script names
createScript = "nicer_create.py"
fitScript = "nicer_fit.py"
plotScript = "nicer_plot.py"
fluxScript = "nicer_flux.py"

#================================================= nicer.fit spesific variables ================================================
# Set it to True if you have made changes in models, and do not want to use any previous model files in commonDirectory
# restartOnce only deletes model files before the first observation, restartAlways deletes model files before all observations
restartOnce = True
restartAlways = False

# Critical value for F-test
ftestCrit = 0.05

chatterOn = True

makeXspecScript = True      # If set to True, the script will create an .xcm file that loads model and data files to xspec and creates a plot automatically

errorCalculations = True    # If set to True, the script will run "shakefit" function to calculate the error boundaries and possibly converge the
                            # fit to better parameter values.

fixNH = True                # If set to True, the script will fit "sampleSize" amount of observations, and take average values for nH parameters, then
                            # refit all observations by freezing nH parameters to the average values.
sampleSize = 10

#================================================ nicer.flux spesific variables ================================================
writeParValuesAfterCflux = True

#================================================ nicer.plot spesific variables =================================================
# If set to True, the plot will use the dates of observations in MJD format for x axis values as opposed to using observation IDs.
plotMJD = True
startDateMJD = 60000