# This is an automatic NICER script for calculating the flux of the best fitting model for each observation
import subprocess
import os
from pathlib import Path
from xspec import *
import matplotlib.pyplot as plt
import math
from astropy.io import fits
from nicer_variables import *
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
energyLimits = energyFilter.split(" ")
Emin = energyLimits[0]
Emax = energyLimits[1]

# Find the script's own path
scriptPath = os.path.abspath(__file__)
scriptPathRev = scriptPath[::-1]
scriptPathRev = scriptPathRev[scriptPathRev.find("/") + 1:]
scriptDir = scriptPathRev[::-1]
os.chdir(scriptDir)

# Check if outputDir has been assigned to be a spesific directory or not
# If not, assign outputDir to the directory where the script is located at
if outputDir == "":
    outputDir = scriptDir

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
    
    if counter != 3:
        print("WARNING: Necessary files for retrieving parameters and plotting are missing for observation: " + obsid + "\n")
        continue

    # Extract MJD
    hdu = fits.open(spectrumFile)
    date = float(format(hdu[1].header["MJD-OBS"], ".3f"))

    if date < startDateMJD:
        print("MJD smaller than " + str(startDateMJD)+" has been detected. The graphs are plotted starting from MJD "+str(startDateMJD)+". Please change 'startDateMJD' variable to account for older MJD.")
        quit()
    else:
        date = date - startDateMJD
    hdu.close()

    Xset.chatter = 0
    Xset.restore(modFile)
    abundance = Xset.abund[:Xset.abund.find(":")]
    
    # Initialize the values of keys as lists
    gaussParsDict[date] = []
    otherParsDict[date] = []

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

        # If the parameter is a float number with fractional part having more than 5 digits, round the fractional part to 5 digits.
        tempList = [line[1], line[2], line[3]]
        tempCounter = 0
        for i in tempList:
            tempCounter += 1
            if i > 10**-5 and len(str(i)[str(i).find(".") +1:]) > 5:
                line[tempCounter] = float(format(i, ".5f"))

        parTuple = (line[0], line[1], line[2], line[3])

        if "gauss" in parTuple[0]:
            gaussParsDict[date].append(parTuple)
        else:
            otherParsDict[date].append(parTuple)

# Set static x-axis ticks for all graphs
mjdList = list(gaussParsDict.keys()) + list(otherParsDict.keys())
minMjd = min(mjdList)
maxMjd = max(mjdList)
if (maxMjd - minMjd) < 20:
    tickInterval = 5
elif 20 <= (maxMjd - minMjd) < 100:
    tickInterval = 25
else:
    tickInterval = 50

xAxisStart = round((minMjd - tickInterval*2) / tickInterval) * tickInterval
xAxisEnd = round((maxMjd + tickInterval*2) / tickInterval) * tickInterval + 1
xAxisTicksMajor = []
xAxisTicksMinor = []

for i in range(xAxisStart, xAxisEnd):
    if i % tickInterval == 0:
        xAxisTicksMajor.append(i)
    else:
        xAxisTicksMinor.append(i)

dictionaryCounter = 0
dictList = [gaussParsDict, otherParsDict]
print("=============================================================================================================")
for eachDict in dictList:
    dictionaryCounter += 1

    if dictionaryCounter == 1:
        print("Plotting the graph: gauss parameters")
    else:
        print("Plotting the graph: non-gauss parameters")

    modelPars = {}
    for key, val in eachDict.items():
        for tuple in val:
            if tuple[0] in modelPars:
                modelPars[tuple[0]][0].append(tuple[1])     # Value
                modelPars[tuple[0]][1].append(tuple[2])     # Error lower
                modelPars[tuple[0]][2].append(tuple[3])     # Error upper
                modelPars[tuple[0]][3].append(key)          # MJD
            else:
                modelPars[tuple[0]] = ([tuple[1]], [tuple[2]], [tuple[3]], [key])

    plotNum = len(modelPars.keys())
    
    if plotNum == 0:
        if dictionaryCounter == 1:
            problematicGraph = "gauss parameters"
        else:
            problematicGraph = "non-gauss parameters"

        print("WARNING: The script is trying to create graphs without any parameters. Skipping the following graph: " + problematicGraph + "\n")

        continue
    
    rows = plotNum
    cols = 1

    fig, axs = plt.subplots(rows, cols, figsize=(6, plotNum*2))
    plt.subplots_adjust(wspace=0, hspace=0)
    counter = 0

    for i in range(rows):
        if i < rows - 1:
            axs[i].xaxis.set_visible(False)

        xAxis = list(modelPars.values())[counter][3]
        yAxis = list(modelPars.values())[counter][0]
        errorLow = list(modelPars.values())[counter][1]
        errorHigh = list(modelPars.values())[counter][2]
        parName = list(modelPars.keys())[counter]

        axs[i].errorbar(xAxis, yAxis, yerr=[errorLow, errorHigh], fmt='*', ecolor="black", color="black", capsize=0, label=parName)
        axs[i].legend()

        axs[i].set_xlabel("Time (MJD-"+str(startDateMJD)+ " days)")
        axs[i].set_ylabel('Xspec model units')

        axs[i].set_xticks(xAxisTicksMajor)
        axs[i].set_xticks(xAxisTicksMinor, minor = True)

        counter += 1

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

    print("Plotting the graph was successful.\n")

# This file is created after importing variables from another python file
if Path(scriptDir + "/__pycache__").exists():
    os.system("rm -rf " +scriptDir+"/__pycache__")