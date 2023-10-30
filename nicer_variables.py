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
#================================================ nicer.flux spesific variables =================================================
writeParValuesAfterCflux = True

#================================================ nicer.plot spesific variables =================================================
startDateMJD = 60000

"""#================================================================================================================================
#Input checks

if str(startDateMJD).isnumeric() == False:
    while True:
        print("\nstartDateMJD variable is not type integer.")
        startDateMJD = input("Please enter an integer value for startDateMJD: ")

        if startDateMJD.isnumeric():
            startDateMJD = int(startDateMJD)
            break
        
if isinstance(writeParValuesAfterCflux, bool) == False:
    while True:
        print("\nwriteParValuesAfterCflux variable is not type boolean.")
        writeParValuesAfterCflux = input("Please enter a boolean value for writeParValuesAfterCflux (True/False): ")

        if writeParValuesAfterCflux == "True" or writeParValuesAfterCflux == "False":
            writeParValuesAfterCflux = bool(writeParValuesAfterCflux)
            break

if str(sampleSize).isnumeric() == False or int(sampleSize) <= 0:
    while True:
        print("\nEither sampleSize variable is not type integer, or it is smaller than 0.")
        sampleSize = input("Please enter a positive integer value for sampleSize: ")

        if sampleSize.isnumeric() and int(sampleSize) > 0:
            sampleSize = int(sampleSize)
            break

if isinstance(fixNH, bool) == False:
    while True:
        print("\nfixNH variable is not type boolean.")
        fixNH = input("Please enter a boolean value for fixNH (True/False): ")

        if fixNH == "True" or fixNH == "False":
            fixNH = bool(fixNH)
            break

if isinstance(errorCalculations, bool) == False:
    while True:
        print("\nerrorCalculations variable is not type boolean.")
        errorCalculations = input("Please enter a boolean value for errorCalculations (True/False): ")

        if errorCalculations == "True" or errorCalculations == "False":
            errorCalculations = bool(errorCalculations)
            break

if isinstance(makeXspecScript, bool) == False:
    while True:
        print("\nmakeXspecScript variable is not type boolean.")
        makeXspecScript = input("Please enter a boolean value for makeXspecScript (True/False): ")

        if makeXspecScript == "True" or makeXspecScript == "False":
            makeXspecScript = bool(makeXspecScript)
            break

if isinstance(chatterOn, bool) == False:
    while True:
        print("\nchatterOn variable is not type boolean.")
        chatterOn = input("Please enter a boolean value for chatterOn (True/False): ")

        if chatterOn == "True" or chatterOn == "False":
            chatterOn = bool(chatterOn)
            break

if isinstance(ftestSignificance, float) == False or not (0 < ftestSignificance < 1):
    while True:
        try:
            ftestSignificance = float(ftestSignificance)
            if ftestSignificance <= 0 or ftestSignificance >= 1:
                # Make an error on purpose and trigger except block, since fTestSignificance is not on the correct interval
                errorVariable = int("99.99")
            else:
                break
        except:
            print("\nfTestSignificance variable must be a float number between 0 and 1.")
            ftestSignificance = input("Please enter a float number between 0 and 1 for ftestSignificance (0 < x < 1): ")

if isinstance(restartAlways, bool) == False:
    while True:
        print("\nrestartAlways variable is not type boolean.")
        restartAlways = input("Please enter a boolean value for restartAlways (True/False): ")

        if restartAlways == "True" or restartAlways == "False":
            restartAlways = bool(restartAlways)
            break

if isinstance(restartOnce, bool) == False:
    while True:
        print("\nrestartOnce variable is not type boolean.")
        restartOnce = input("Please enter a boolean value for restarOnce (True/False): ")

        if restartOnce == "True" or restartOnce == "False":
            restartOnce = bool(restartOnce)
            break

if isinstance(lightCurveTimeResolution, float) == False or isinstance(lightCurveTimeResolution, int) == False or lightCurveTimeResolution < (300 * 10 ** -9):
    while True:
        try:
            lightCurveTimeResolution = float(lightCurveTimeResolution)
            if lightCurveTimeResolution < (300* 10**-9):
                # Make an error on purpose and trigger except block, since fTestSignificance is not on the correct interval
                errorVariable = int("99.99")
            else:
                if lightCurveTimeResolution == int(lightCurveTimeResolution):
                    lightCurveTimeResolution = int(lightCurveTimeResolution)
                
                break
        except:
            print("\nlightCurveTimeResolution must be a number bigger or equal than 300 ns.")
            lightCurveTimeResolution = input("Please enter a number bigger or equal than 300 ns for lightCurveTimeResolution (>= 3e-7 s): ")"""