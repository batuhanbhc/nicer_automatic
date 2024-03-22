import subprocess
import os
from pathlib import Path
from xspec import *
import numpy as np
from astropy.io import fits
import numpy as np
import math
import re
#============================================ Common variables for all scripts =================================================

# The directory where the output files will be created at (Leave it blank [outputDir = ""] if you want output files to be created under the same directory as all scripts)
outputDir = ""

# The name of the file that contains paths of the observation folders
inputTxtFile = "observations.txt"

# The log file where the fit results will be saved
resultsFile = "fit_results.log"

# Write it in XSpec format
energyFilter = "0.8 10."

#=============================================== nicer.main spesific variables =================================================
# Script switches
run_create_script = False
run_fit_script = True
run_flux_script = True
run_plot_script = True

# Script names
create_script_name = "nicer_create.py"
fit_script_name = "nicer_fit.py"
flux_script_name = "nicer_flux.py"
plot_script_name = "nicer_plot.py"

#================================================= nicer.create spesific variables =============================================
# This variable turns on 'clobber' parameter to YES while running nicer headas tasks.
# Turn this FALSE if you are dealing with READ-ONLY observation files. However, this will delete all the previous files under the output directory.
# Turn this TRUE if you are dealing with observation files that you have WRITE permission. This may overwrite some files.
overwrite_files = False

# nicer_create will keep the records of processed file paths in processed_obs.txt and update it when you filter new observations.
# If you ever want to clean the contents of processed_obs.txt (in cases where certain observations may no longer be valid for spectral analysis), set
# clean_obs_history to True.
clean_obs_history = False

# Set this variable to True if you want high resolution light curves. If set to False, light curves will have 1 second time resolution.
createHighResLightCurves = True

# Below variables will only be used if createHighResLightCurves is set to True, otherwise pirange=50-1000 and time resolution=1s will be set for all observations
highResLcPiRanges = ["50-200", "200-600", "600-1000"]   # Please do not forget to give each interval in string form, and seperate them by comma
highResLcTimeResInPwrTwo = -8    # Enter a value as a power of two smaller or equal than 0. Lc files will be names as such: 2^0 -> dt0.lc, 2^-8 -> dt8.lc etc.

#================================================= nicer.fit spesific variables ================================================
# Nicer_fit will save all fit results under $output_dir/results directory with versioning.
# Setting this to True will clear/delete all the previous fit 
clean_result_history = False

# Xspec abundance to be used
xspec_abundance = "wilm"

# Name of the file that contains the definitions of models
model_file = "models.txt"

# Name of the model to be used for fitting, defined in models.txt
# DO NOT ENTER ANY EMPTY SPACE, USE "_" INSTEAD
model_pipeline_name = "model_2"

# If 'fix_parameters_after_sampling' variable is set to True, the script will fit 'fix_sample_size' amount of observations, take average values for parameters and refit all
# observations while fixing these parameters to their averages.
fix_parameters_after_sampling = False
fix_sample_size = 15
parametersToFix = ["TBabs.nH", "pcfabs.nH"] # Enter each element in string format, seperate them by comma. Each element is in the format component_name.parameter_name

# Set it to True if you have made changes in models, and do not want to use any previous model files for parameter initialization in commonDirectory
# restartOnce only deletes model files before the first observation, restartAlways deletes model files before all observations
restartOnce = True
restartAlways = False

# F-test significance (alpha) value
ftestSignificance = 0.05

chatterOn = False

# If set to True, the script will run "shakefit" function to calculate the error boundaries and possibly converge the fit to better parameter values.
errorCalculations = True

# If set to True, shakefit function will check whether powerlaw exists; if so, check whether its xspec error is bigger than 1 or not. If so, freeze its value at 'powerlawIndexToFreezeAt'
checkPowerlawErrorAndFreeze = False
powerlawIndexToFreezeAt = 1.7

# Shakefit will only try to calculate errors for below parameters. The keys are xspec modelnames.parameternames, and values are the units.
# If the parameter does not have a spesific unit (like normalizations, photon index etc), put "X" as value
# Also important: You need to write models and parameters exactly like how they are written in Xspec. For instance, you need to write "TBabs" instead of "tbabs".
# Do not forget to put "_" instead of spaces
parametersForShakefit = {
    "diskbb.norm": "Normalization_(diskbb)",
    "diskbb.Tin": "Tin_(keV)",
    "powerlaw.PhoIndex": "Powerlaw_index",
    "powerlaw.norm": "Normalization_(powerlaw)",
    "TBabs.nH": "TBabs_nH",
    "edge.edgeE": "Edge_Energy_(keV)",
    "simpl.Gamma": "Simpl_Gamma"
}

#================================================ nicer.flux spesific variables =================================================
# nicer_flux will add "cflux" component before the spesified models below to calculate flux.
# 'absorbed' keyword adds cflux at the beginning, 'unabsorbed' keyword adds cflux after the last absorption model.
# Be careful while using 'unabsorbed' keyword, do not use it if the above usage does not give the unabsorbed flux.
fluxes_to_be_calculated = ["absorbed", "unabsorbed", "simpl", "diskbb", "powerlaw"]

# Used for 'unabsorbed' flux.
last_absorption_model = "TBabs"

# If set to true, bottom and top limits of parameters will be set to (value +/- 0.1) before fitting with cflux.
restrict_parameters = True

#================================================ nicer.plot spesific variables =================================================
# If set to True, the script will create new graphs with a count/version number at the end instead of updating only one file.
# e.g. model_parameters_1.png, model_parameters_2.png, ... As you continue to run the script, previous files will not be deleted.
# If set to False, the script will only create one file, and delete the previous one (e.g. model_parameters.png, without a count/version number at the end)
enable_versioning = True

# Setting this variable to True will clear all the previously created files (graphs and tables), and reset the count/version number
# to 1 if enable_versioning is set to True
delete_previous_files = False

# Custom name for naming graphs and tables. If you set 'custom_name' = "", then the model name used for fitting will be used for naming
# e.g: custom_name = "", graph name: model_simpl_edge_1.png OR custom_name = "nH_fixed", graph name = nH_fixed_1.png
custom_name = ""

# Modified z-score algorithm will be used for outlier detection
# Possibility of removing "good" data always exists, turn it on or off accordingly
use_outlier_detection = False

# Lower threshold value for modified z-score algorithm (Change it according to your needs)
outlier_lower_threshold = -10

# Upper threshold value for modified z-score algorithm (Change it according to your needs)
outlier_upper_threshold = 10
