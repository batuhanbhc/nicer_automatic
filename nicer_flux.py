# This is an automatic NICER script for calculating the flux of the best fitting model for each observation
import subprocess
import os
from pathlib import Path
from xspec import *
import matplotlib.pyplot as plt
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
    checkFullName = False
    components = AllModels(1).componentNames
    for comp in components:
        if comp == "cflux":
            checkFullName = True

        compObj = getattr(AllModels(1), comp)
        parameters = compObj.parameterNames
        for par in parameters:
            parObj = getattr(compObj, par)
            fullName = comp + "." + par

            if checkFullName and "_" in comp:
                compNum = comp[comp.find("_") + 1:]
                newComp = comp[:comp.find("_") + 1] + str(int(compNum) - 1)
                fullName = newComp + "." + par

            if fullName in parList:
                parObj.values = parList[fullName]
    
    if fluxPars != {}:
        compObj = AllModels(1).cflux
        for key, val in fluxPars.items():
            parObj = getattr(compObj, key)
            parObj.values = val

def fitModel():
    Fit.nIterations = 100
    Fit.delta = 0.01
    Fit.renorm()
    Fit.perform()

def updateParameters(parList):
    # Save the parameters loaded in the xspec model to lists
    for comp in AllModels(1).componentNames:
        compObj = getattr(AllModels(1), comp)
        parameters = compObj.parameterNames
        for par in parameters:
            parObj = getattr(compObj, par)
            fullName = comp + "." + par
            parList[fullName] = parObj.values

def freezeNorm():
    # Freezes all current normalization parameters in a model, also sets new limits for parameters to vary
    comps = AllModels(1).componentNames
    for comp in comps:
        compObj = getattr(AllModels(1), comp)
        parNames = compObj.parameterNames
        for par in parNames:
            parObj = getattr(compObj, par)
            indx = parObj.index
            if par == "norm":
                parObj.frozen = True
                    
            elif comp != "cflux":
                # Noticed that for some observations, fitting the model after adding cflux componant may change parameter values drastically,
                # (e.g. nH 8 -> 1.7, Tin 1.4 -> 0.07) which messes up the chi-sq value and a significant change in the model. Here, I force the
                # already fitted model to not vary at all by limiting parameter values with 0.1 wide intervals from both ends
                valString = str(parObj.values[0])+","+str(parObj.values[1])+","+str(parObj.values[0]-0.1)+","+str(parObj.values[0]-0.1)+","+str(parObj.values[0]+0.1)+","+str(parObj.values[0]+0.1)
                AllModels(1)(indx).values = valString

def findFlux():
    parNums = AllModels(1).nParameters
    for i in range(1, parNums +1):
        name = AllModels(1)(i).name
        if name == "lg10Flux":
            # Convert log10(x) flux to x
            flux = 10 ** AllModels(1)(i).values[0]
            Fit.error("maximum 50 "+ str(i))
            lowerFlux = "errLow:" + str(10**AllModels(1)(i).error[0])
            upperFlux = "errHigh:" + str(10**AllModels(1)(i).error[1])
            return [flux, lowerFlux, upperFlux]

def calculateFlux(component, modelName, initialFlux = ""):
    if component == "unabsorbed":
        if "pcfabs" in modelName:
            # Assuming TBabs also exists, and pcfabs comes after TBabs. If not, please change this part.
            absIndex = modelName.find("pcfabs")
            newName = modelName[:absIndex + 6] + "*cflux" + modelName[absIndex + 6:]
        else:
            absIndex = modelName.find("TBabs")
            newName = modelName[:absIndex + 5] + "*cflux" + modelName[absIndex + 5:]
        
    else:
        compIndex = modelName.find(component)
        newName = modelName[:compIndex] + "cflux*" + modelName[compIndex:]

    m = Model(newName)
    if initialFlux != "":
        enterParameters(parameters, {"Emin":Emin, "Emax":Emax, "lg10Flux": initialFlux})
    else:
        enterParameters(parameters, {"Emin":Emin, "Emax":Emax})
    freezeNorm()
    fitModel()
    fluxVals = findFlux()
    
    return fluxVals

def writeParsAfterFlux():
    for comp in AllModels(1).componentNames:
        compObj = getattr(AllModels(1), comp)
        for par in compObj.parameterNames:
            parObj = getattr(compObj, par)
            fullName = comp + "." + par
            file.write(fullName + "     " + str(parObj.values[0]) + "\n")
    
    file.write("\n")
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
    Fit.query = "yes"

    parameters = {}
    updateParameters(parameters)

    file.write("\n===========================================================\n")
    file.write("Fluxes of model components (in ergs/cm^2/s) (90% confidence intervals)\n\n")
    modelName = AllModels(1).expression.replace(" ", "")

    # Absorbed flux
    absFlux = calculateFlux("TBabs", modelName, -8.4)
    file.write(energyFilter +" keV "+AllModels(1).expression+"\nFlux: " + listToStr(absFlux) + "\n")
    if writeParValuesAfterCflux:
        writeParsAfterFlux()

    if "pcfabs" in modelName:
        # TBabs excluded flux
        halfAbsFlux = calculateFlux("pcfabs", modelName, -8.1)
        file.write(energyFilter +" keV "+AllModels(1).expression+"\nFlux: " + listToStr(halfAbsFlux) + "\n")
        if writeParValuesAfterCflux:
            writeParsAfterFlux()
        
    # Unabsorbed flux
    unabsFlux = calculateFlux("unabsorbed", modelName, -7.85)
    file.write(energyFilter +" keV "+AllModels(1).expression+"\nFlux: " + listToStr(unabsFlux) + "\n")
    if writeParValuesAfterCflux:
        writeParsAfterFlux()

    # Diskbb flux
    fluxDisk = calculateFlux("diskbb", modelName, -7.85)
    file.write(energyFilter +" keV "+AllModels(1).expression+"\nFlux: " + listToStr(fluxDisk) + "\n")
    if writeParValuesAfterCflux:
        writeParsAfterFlux()

    if "powerlaw" in modelName:
        # Powerlaw flux
        fluxPow = calculateFlux("powerlaw", modelName, -9)
        file.write(energyFilter +" keV "+AllModels(1).expression+"\nFlux: " + listToStr(fluxPow) + "\n")
        if writeParValuesAfterCflux:
            writeParsAfterFlux()
    else:
        file.write("Powerlaw flux is 0. There is no powerlaw component in the model expression.\n")

    file.close()
    AllModels.clear()
    AllData.clear()

# This file is created after importing variables from another python file
if Path(scriptDir + "/__pycache__").exists():
    os.system("rm -rf "+scriptDir+"/__pycache__")