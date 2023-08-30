# This is an automatic NICER script for calculating the flux of the best fitting model for each observation
import subprocess
import os
from pathlib import Path
from xspec import *
import matplotlib.pyplot as plt
import math

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
parsDict = {}
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
        if "parameters" in file:
            parFile = file
            counter += 1
        elif "best_" in file:
            modFile = file
            counter += 1
        
        if counter == 2:
            break
    
    Xset.restore(modFile)
    abundance = Xset.abund[:Xset.abund.find(":")]

    parsDict[obsid] = []

    file = open(parFile)
    iterator = 0
    for line in file:
        iterator += 1
        if iterator == 1:
            continue
        line = line.strip("\n")
        line = line.split(" ")
        line[1] = float(line[1])
        line[2] = line[1] - float(line[2])
        line[3] = float(line[3]) - line[1]
        parTuple = (line[0], line[1], line[2], line[3])
        if "gauss" in parTuple[0]:
            pass
        else:
            parsDict[obsid].append(parTuple)

modelPars = {}
xAxis = []
for key, val in parsDict.items():
    xAxis.append(key[-4:])
    for tuple in val:
        if tuple[0] in modelPars:
            modelPars[tuple[0]][0].append(tuple[1])     # Value
            modelPars[tuple[0]][1].append(tuple[2])     # Error lower
            modelPars[tuple[0]][2].append(tuple[3])     # Error upper
        else:
            modelPars[tuple[0]] = ([tuple[1]], [tuple[2]], [tuple[3]])

plotNum = len(modelPars.keys())
rows = math.ceil(math.sqrt(plotNum))
cols = math.ceil(plotNum / rows)

fig, axs = plt.subplots(cols, rows, figsize=(16, 10))

counter = 0
for i in range(cols):
    for j in range(rows):
        try:
            yAxis = list(modelPars.values())[counter][0]
            errorLow = list(modelPars.values())[counter][1]
            errorHigh = list(modelPars.values())[counter][2]
            parName = list(modelPars.keys())[counter]

            axs[i, j].plot(xAxis, yAxis, label= parName, color="black")
            axs[i, j].errorbar(xAxis, yAxis, yerr=[errorLow, errorHigh], fmt='o', ecolor="black", color="black", capsize=10, label='Error Bars')
            axs[i, j].set_xlabel('Observation IDs')
            axs[i, j].set_ylabel('Parameter units with errors')
            axs[i, j].legend()
            counter += 1
        except:
            break

general_title = "Best-fitting Model Parameters" + "(Abundance: "+ abundance +")"
fig.suptitle(general_title, fontsize=16)

# Adjust layout and save the figure
plt.tight_layout()

pngFile = commonDirectory + "/par_comparison.png"
pngPath = Path(pngFile)
if pngPath.exists():
    subprocess.run(["rm", pngFile])

plt.savefig(pngFile)
