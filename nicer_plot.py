# This is an automatic NICER script for calculating the flux of the best fitting model for each observation
import subprocess
import os
from pathlib import Path
from xspec import *
import matplotlib.pyplot as plt
import math
from astropy.io import fits

#===================================================================================================================================
# The location of the observation folders
outputDir = "/home/batuhanbahceci/NICER/analysis"

# Name of the log file
resultsFile = "script_results.log"

# If set to True, the plot will use the dates of observations in MJD format for x axis values as opposed to using observation IDs.
plotMJD = True

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

def transferToNewList(sourceList):
    newList = [sourceList[0]]
    newParDict = {}
    newStatDict = {}

    sourceParDict = sourceList[1]
    keys = list(sourceParDict.keys())
    values = list(sourceParDict.values())
    for i in range(len(keys)):
        newParDict[keys[i]] = values[i]
    newList.append(newParDict)

    sourceStatDict = sourceList[2]
    keys = list(sourceStatDict.keys())
    values = list(sourceStatDict.values())
    for i in range(len(keys)):
        newStatDict[keys[i]] = values[i]
    newList.append(newStatDict)
    
    return newList

#===================================================================================================================
# Find the script's own path
scriptPath = os.path.abspath(__file__)
scriptPathRev = scriptPath[::-1]
scriptPathRev = scriptPathRev[scriptPathRev.find("/") + 1:]
scriptDir = scriptPathRev[::-1]
os.chdir(scriptDir)

gaussParsDict = {}
otherParsDict = {}
commonDirectory = outputDir + "/commonFiles"   # ~/NICER/analysis/commonFiles

inputFile = open("nicer_obs.txt")
for obs in inputFile.readlines():
    # Extract the obsid from the path name written in nicer_obs.txt
    obs = obs.strip("\n' ")
    parentDir = obs[::-1]
    obsid = parentDir[:parentDir.find("/")]         
    parentDir = parentDir[parentDir.find("/")+1:]   
    
    obsid = obsid[::-1]         # e.g. 6130010120

    outObsDir = outputDir + "/" + obsid
    os.chdir(outObsDir)

    allFiles = os.listdir(outObsDir)
    # Find the data file and the best fitting model file for the current observation
    counter = 0
    for file in allFiles:
        if "parameters_" in file:
            parFile = file
            counter += 1
        elif "best_" in file:
            modFile = file
            counter += 1
        elif file == "ni" + obsid + "mpu7_sr3c50.pha":
            spectrumFile = file
            counter += 1
        
        if counter == 3:
            break
    
    # Extract MJD
    hdu = fits.open(spectrumFile)
    date = str(int(hdu[1].header["MJD-OBS"]))
    hdu.close()

    Xset.restore(modFile)
    abundance = Xset.abund[:Xset.abund.find(":")]
    
    # Initialize the values of keys as lists
    if plotMJD:
        gaussParsDict[date] = []
        otherParsDict[date] = []
    else:
        gaussParsDict[obsid] = []
        otherParsDict[obsid] = []

    file = open(parFile)
    iterator = 0
    for line in file:
        iterator += 1
        if iterator == 1:
            continue

        # Extract the parameter values with uncertainities
        line = line.strip("\n")
        line = line.split(" ")
        line[1] = float(line[1])
        line[2] = line[1] - float(line[2])
        line[3] = float(line[3]) - line[1]
        parTuple = (line[0], line[1], line[2], line[3])

        if plotMJD:
            if "gauss" in parTuple[0]:
                gaussParsDict[date].append(parTuple)
            else:
                otherParsDict[date].append(parTuple)
        else:
            if "gauss" in parTuple[0]:
                gaussParsDict[obsid].append(parTuple)
            else:
                otherParsDict[obsid].append(parTuple)

dictList = [gaussParsDict, otherParsDict]
for eachDict in dictList:
    modelPars = {}
    for key, val in eachDict.items():
        for tuple in val:
            if tuple[0] in modelPars:
                modelPars[tuple[0]][0].append(tuple[1])     # Value
                modelPars[tuple[0]][1].append(tuple[2])     # Error lower
                modelPars[tuple[0]][2].append(tuple[3])     # Error upper
                modelPars[tuple[0]][3].append(key)          # Observation ID / MJD
            else:
                modelPars[tuple[0]] = ([tuple[1]], [tuple[2]], [tuple[3]], [key])

    plotNum = len(modelPars.keys())
    rows = math.ceil(math.sqrt(plotNum))
    cols = math.ceil(plotNum / rows)

    fig, axs = plt.subplots(cols, rows, figsize=(18, 10))

    counter = 0
    for i in range(cols):
        for j in range(rows):
            try:
                xAxis = list(modelPars.values())[counter][3]
                yAxis = list(modelPars.values())[counter][0]
                errorLow = list(modelPars.values())[counter][1]
                errorHigh = list(modelPars.values())[counter][2]
                parName = list(modelPars.keys())[counter]
                ticks = [i for i in range(len(xAxis))]

                axs[i, j].plot(xAxis, yAxis, label= parName, color="black")
                axs[i, j].errorbar(xAxis, yAxis, yerr=[errorLow, errorHigh], fmt='o', ecolor="black", color="black", capsize=10)
                if plotMJD:
                    axs[i, j].set_xlabel('Modified Julian Date (MJD)')
                else:
                    axs[i, j].set_xlabel('Observation IDs')
                axs[i, j].set_ylabel('Xspec model units')
                axs[i, j].legend()
                axs[i, j].set_xticks(ticks, xAxis, rotation=60, ha='right')
                counter += 1
            except:
                break

    general_title = "Best-fitting Model Parameters " + "(Abundance: "+ abundance +")"
    fig.suptitle(general_title, fontsize=16)

    # Adjust layout and save the figure
    plt.tight_layout()

    if eachDict == otherParsDict:
        pngFile = commonDirectory + "/other_parameters.png"
        pngPath = Path(pngFile)
        if pngPath.exists():
            subprocess.run(["rm", pngFile])

        plt.savefig(pngFile)
    else:
        pngFile = commonDirectory + "/gauss_parameters.png"
        pngPath = Path(pngFile)
        if pngPath.exists():
            subprocess.run(["rm", pngFile])

        plt.savefig(pngFile)
