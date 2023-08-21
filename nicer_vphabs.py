# This is an automatic NICER script for calculating the flux of the best fitting model for each observation
import subprocess
import os
from pathlib import Path
from xspec import *
import matplotlib.pyplot as plt
import math
import tkinter as tk

#===================================================================================================================================
# The location of the observation folders
outputDir = "/home/batuhanbahceci/NICER/analysis"

# Name of the log file
resultsFile = "script_results.log"

energyFilter = "1.5 10."
energyLimits = energyFilter.split(" ")
Emin = energyLimits[0]
Emax = energyLimits[1]
#===================================================================================================================================
# Functions
def listToStr(array):
    result = ""
    for char in array:
        result += str(char) + " "
    result = result[:-1]
    return result

def enterParameters(parList, fluxPars = {}):
    # Take the available parameters from the stemList
    components = AllModels(1).componentNames
    for comp in components:
        compObj = getattr(AllModels(1), comp)
        parameters = compObj.parameterNames
        for par in parameters:
            parObj = getattr(compObj, par)
            indx = parObj.index
            fullName = comp + "." + par
            # If the parameter value is stored in previous model's list, take it from there. Otherwise, look whether
            # it is initialized in current model's list
            if fullName in parList:
                AllModels(1)(indx).values = parList[fullName]
    
    if fluxPars != {}:
        compObj = AllModels(1).cflux
        for key, val in fluxPars.items():
            parObj = getattr(compObj, key)
            parObj.values = val

def fitModel():
    Fit.nIterations = 100
    Fit.delta = 0.01
    Fit.perform()

def updateParameters(parList):
    # Save the parameters loaded in the xspec model to lists
    components = AllModels(1).componentNames
    for comp in components:
        if comp == "vphabs":
            compObj = getattr(AllModels(1), comp)
            parameters = compObj.parameterNames
            for par in parameters:
                parObj = getattr(compObj, par)
                if parObj.values[1] > 0:
                    indx = parObj.index
                    fullName = comp + "." + par
                    parList.append((fullName, AllModels(1)(indx).values[0]))

#===================================================================================================================
allDir = os.listdir(outputDir)
allDir.sort()
vphabsPars = {}
commonDirectory = outputDir + "/commonFiles"   # ~/NICER/analysis/commonFiles
iteration = 0

for obsid in allDir:
    if obsid.isnumeric():
        # If the file name is all numerical, assume it is an observation. If not, you may need to change this part
        outObsDir = outputDir + "/" + obsid      # e.g. ~/NICER/analysis/6130010120   
        os.chdir(outObsDir)
    else:
        continue 
    
    iteration += 1
    allFiles = os.listdir(outObsDir)

    # Find the data file and the best fitting model file for the current observation
    counter = 0
    for file in allFiles:
        if "best_" in file:
            modFile = file
            counter += 1
        elif "data_" in file:
            dataFile = file
            counter += 1

        if counter == 2:
            # All necessary files have been found
            break
    
    file = open(resultsFile, "a")
    Xset.restore(dataFile)
    Xset.restore(modFile)

    vphabsPars[obsid] = []
    updateParameters(vphabsPars[obsid])
    abundance = Xset.abund[:Xset.abund.find(":")]

parDict = {}
xAxis = []
for key, val in vphabsPars.items():
    xAxis.append(key[-4:])
    for parTuple in val:
        if parTuple[0] in parDict:
            parDict[parTuple[0]].append(parTuple[1])
        else:
            parDict[parTuple[0]] = [parTuple[1]]

plotNum = len(parDict.keys())
rows = math.ceil(math.sqrt(plotNum))
cols = math.ceil(plotNum / rows)

fig, axs = plt.subplots(cols, rows, figsize=(16, 10))

counter = 0
for i in range(cols):
    for j in range(rows):
        try:
            yAxis = list(parDict.values())[counter]
            parName = list(parDict.keys())[counter]
            axs[i, j].plot(xAxis, yAxis, label= parName)
            axs[i, j].scatter(xAxis, yAxis, marker="o")
            axs[i, j].set_xlabel('Observation IDs')
            axs[i, j].set_ylabel('Vphabs parameter units')
            axs[i, j].legend()
            counter += 1
        except:
            break

general_title = "Vphabs model parameters" + "(Abundance: "+ abundance +")"
fig.suptitle(general_title, fontsize=16)

# Adjust layout and save the figure
plt.tight_layout()

pngFile = commonDirectory + "/vphabs_comparison.png"
pngPath = Path(pngFile)
if pngPath.exists():
    subprocess.run(["rm", pngFile])

plt.savefig(pngFile)
