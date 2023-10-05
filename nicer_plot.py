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

    if plotMJD:
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

        # If the parameter is a float number with fractional part having more than 5 digits, round the fractional part to 5 digits.
        tempList = [line[1], line[2], line[3]]
        tempCounter = 0
        for i in tempList:
            tempCounter += 1
            if i > 10**-5 and len(str(i)[str(i).find(".") +1:]) > 5:
                line[tempCounter] = float(format(i, ".5f"))

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

counter = 0
dictList = [gaussParsDict, otherParsDict]
print("=============================================================================================================")
for eachDict in dictList:
    counter += 1

    if counter == 1:
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
                modelPars[tuple[0]][3].append(key)          # Observation ID / MJD
            else:
                modelPars[tuple[0]] = ([tuple[1]], [tuple[2]], [tuple[3]], [key])

    plotNum = len(modelPars.keys())
    
    if plotNum == 0:
        if counter == 1:
            problematicGraph = "gauss parameters"
        else:
            problematicGraph = "non-gauss parameters"

        print("WARNING: The script is trying to create graphs without any parameters. Skipping the following graph: " + problematicGraph + "\n")

        continue
    
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

                if plotMJD:
                    xMin = int(min(xAxis)) - 1
                    xMax = int(max(xAxis)) + 1
                    
                    if (xMax - xMin) < 20:
                        tickInterval = 1
                    elif 20 <= (xMax - xMin) < 100:
                        tickInterval = 5
                    elif 100 <= (xMax - xMin) < 200:
                        tickInterval = 10
                    else:
                        tickInterval = 20
                        
                    ticks = []
                    for k in range(xMin, xMax + tickInterval, tickInterval):
                        ticks.append(k)
                else:
                    ticks = xAxis

                #axs[i, j].plot(xAxis, yAxis, label= parName, color="black")
                axs[i, j].errorbar(xAxis, yAxis, yerr=[errorLow, errorHigh], fmt='*', ecolor="black", color="black", capsize=0, label=parName)
                if plotMJD:
                    axs[i, j].set_xlabel("Date (MJD "+str(startDateMJD)+ ")")
                else:
                    axs[i, j].set_xlabel('Observation IDs')
                axs[i, j].set_ylabel('Xspec model units')

                axs[i, j].set_xticks(ticks)
                axs[i, j].set_xticklabels(ticks, rotation=60, ha='right')

                axs[i, j].legend()

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

    print("Plotting the graph was successful.\n")

# This file is created after importing variables from another python file
if Path(scriptDir + "/__pycache__").exists():
    os.system("rm -rf " +scriptDir+"/__pycache__")