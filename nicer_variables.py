import subprocess
import os
from pathlib import Path
from xspec import *
import numpy as np
from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np
import math
#============================================ Common variables for all scripts =================================================

# The directory where the output files will be created at (Leave it blank [outputDir = ""] if you want output files to be created under the same directory as all scripts)
outputDir = "/home/batuhanbahceci/NICER/analysis"

# The name of the file that contains paths of the observation folders
inputTxtFile = "nicer_obs.txt"

# The log file where the fit results will be saved
resultsFile = "fit_results.log"

# Write it in XSpec format
energyFilter = "0.5 10."

#=============================================== nicer.main spesific variables =================================================
# Script switches
createSwitch = True
fitSwitch = True
fluxSwitch = True
plotSwitch = True

# Script names
createScript = "nicer_create.py"
fitScript = "nicer_fit.py"
plotScript = "nicer_plot.py"
fluxScript = "nicer_flux.py"

#================================================= nicer.create spesific variables =============================================
# Set this variable to True if you want high resolution light curves. If set to False, light curves will have 1 second time resolution.
createHighResLightCurves = True

# Below variables will only be used if createHighResLightCurves is set to True, otherwise pirange=50-1000 and time resolution=1s will be set for all observations
highResLcPiRanges = ["50-200", "200-600", "600-1000"]   # Please do not forget to give each interval in string form, and seperate them by comma
highResLcTimeResInPwrTwo = -8    # Enter a value as a power of two smaller or equal than 0. Lc files will be names as such: 2^0 -> dt0.lc, 2^-8 -> dt8.lc etc.

#================================================= nicer.fit spesific variables ================================================
# Set it to True if you have made changes in models, and do not want to use any previous model files in commonDirectory
# restartOnce only deletes model files before the first observation, restartAlways deletes model files before all observations
restartOnce = True
restartAlways = False

# F-test significance (alpha) value
ftestSignificance = 0.05

chatterOn = False

makeXspecScript = True      # If set to True, the script will create an .xcm file that loads model and data files to xspec and creates a plot automatically

errorCalculations = True    # If set to True, the script will run "shakefit" function to calculate the error boundaries and possibly converge the
                            # fit to better parameter values.

fixNH = True                # If set to True, the script will fit "sampleSize" amount of observations, and take average values for nH parameters, then
                            # refit all observations by freezing nH parameters to the average values.
sampleSize = 15

# Shakefit will only try to calculate errors for below parameters. The keys are xspec modelnames.parameternames, and values are the units.
# If the parameter does not have a spesific unit (like normalizations, photon index etc), put "X" as value
# Also important: You need to write models and parameters exactly like how they are written in Xspec. For instance, you need to write "TBabs" instead of "tbabs".
parametersForShakefit = {
    "diskbb.norm": "Normalization_(diskbb)",
    "diskbb.Tin": "Tin_(keV)",
    "powerlaw.PhoIndex": "index_(Γ)",
    "powerlaw.norm": "Normalization_(powerlaw)"
}

# If set to True, gaussian equivalent widths will be calculated
calculateGaussEquivalentWidth = True

#================================================ nicer.flux spesific variables =================================================
writeParValuesAfterCflux = True