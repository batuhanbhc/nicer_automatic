# This is an automatic NICER script for calculating the flux of the best fitting model for each observation
import subprocess
import os
from pathlib import Path
from xspec import *
import matplotlib.pyplot as plt

#===================================================================================================================================
# The location of obseravtions
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
        compObj = getattr(AllModels(1), comp)
        parameters = compObj.parameterNames
        for par in parameters:
            parObj = getattr(compObj, par)
            indx = parObj.index
            fullName = comp + "." + par
            parList[fullName] = AllModels(1)(indx).values

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
                AllModels(1)(indx).frozen = True
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

def calculateFlux(component):
    if component == "unabsorbed":
        absIndex = modelName.find("abs")
        newName = modelName[:absIndex + 3] + "*cflux" + modelName[absIndex + 3:]
    else:
        compIndex = modelName.find(component)
        newName = modelName[:compIndex] + "cflux*" + modelName[compIndex:]

    m = Model(newName)
    
    enterParameters(parameters, {"Emin":Emin, "Emax":Emax, "lg10Flux" : -8})
    freezeNorm()
    fitModel()
    fluxVals = findFlux()
    
    return fluxVals

#===================================================================================================================
allDir = os.listdir(outputDir)
allDir.sort()
observationFluxes = {}
commonDirectory = outputDir + "/commonFiles"   # ~/NICER/analysis/commonFiles
iteration = 0

for obsid in allDir:
    if obsid.isnumeric():
        outObsDir = outputDir + "/" + obsid      # e.g. ~/NICER/analysis/6130010120   
        os.chdir(outObsDir)
    else:
        continue 
    
    iteration += 1
    allFiles = os.listdir(outObsDir)

    # Find the spectrum, background, arf and response files
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
    Xset.chatter = 1
    Fit.query = "yes"
    modelName = AllModels(1).expression.replace(" ", "")

    parameters = {}
    updateParameters(parameters)

    observationFluxes[obsid] = [("diskbb.Tin", parameters["diskbb.Tin"])]
    if "powerlaw" in modelName:
        observationFluxes[obsid].append(("powerlaw.PhoIndex", parameters["powerlaw.PhoIndex"]))
    else:
        observationFluxes[obsid].append(("powerlaw.PhoIndex", 0))
    
    file.write("===========================================================\n")
    file.write("Fluxes of model components (in ergs/cm^2/s)\n")

    # Absorbed flux
    absFlux = calculateFlux("TBabs")
    file.write(energyFilter +" keV "+AllModels(1).expression+" flux: " + listToStr(absFlux) + "\n")

    # Unabsorbed flux
    unabsFlux = calculateFlux("unabsorbed")
    file.write(energyFilter +" keV "+AllModels(1).expression+" flux: " + listToStr(unabsFlux) + "\n")

    if "gaussian" in modelName:
        # Write gabs equivalent width
        m = Model(modelName)
        enterParameters(parameters)
        comps = AllModels(1).componentNames
        gaussIdx = comps.index("gaussian") + 1
        AllModels.eqwidth(gaussIdx)
        eqw = AllData(1).eqwidth[0]
        file.write("Gabs equivalent width: " + str(eqw) + "\n")

    if "powerlaw" in AllModels(1).expression:
        fluxModPow = modelName[: modelName.find("pow")] + "cflux*" + modelName[modelName.find("pow"):]

        # Powerlaw flux
        fluxPow = calculateFlux("powerlaw")

        file.write(energyFilter +" keV "+AllModels(1).expression+" flux: " + listToStr(fluxPow) + "\n")
    else:
        fluxPow = "0"
        file.write(energyFilter +" keV powerlaw flux: " + fluxPow +"\n")
    
    # Diskbb flux
    fluxDisk = calculateFlux("diskbb")
    file.write(energyFilter +" keV "+AllModels(1).expression+" flux: " + listToStr(fluxDisk) + "\n")
    
    observationFluxes[obsid].append(("Diskbb flux", fluxDisk[0]))
    observationFluxes[obsid].append(("Powerlaw flux", fluxPow[0]))

    file.close()
    AllModels.clear()
    AllData.clear()
    
# Now create the graph of changes in fluxes and parameter values in between observations.
fluxKeys = list(observationFluxes.keys())
fluxKeys.sort()
sorted_fluxes = {i: observationFluxes[i] for i in fluxKeys}

tbabsnH = []
powIndex = []
diskFlux = []
powFlux = []
observations = []
for key, values in sorted_fluxes.items():
    observations.append(key)
    tbabsnH.append(values[0][1][0])
    powIndex.append(values[1][1][0])
    diskFlux.append(values[2][1])
    powFlux.append(values[3][1])

fig, axs = plt.subplots(2, 2, figsize=(12,8))

# Plot the first graph (diskbb.Tin)
axs[0, 0].plot(observations, tbabsnH, label="diskbb.Tin values")
axs[0, 0].scatter(observations, tbabsnH, marker="o")
axs[0, 0].set_xlabel('Observation IDs')
axs[0, 0].set_ylabel('keV')
axs[0, 0].legend()

# Plot the second graph (powerlaw.PhoIndex)
axs[0, 1].plot(observations, powIndex, label="powerlaw.PhoIndex values")
axs[0, 1].scatter(observations, powIndex, marker="o")
axs[0, 1].set_xlabel('Observation IDs')
axs[0, 1].set_ylabel('Photon Index')
axs[0, 1].legend()

# Plot the third graph (Diskbb flux)
axs[1, 0].plot(observations, diskFlux, label="Diskbb fluxes")
axs[1, 0].scatter(observations, diskFlux, marker="o")
axs[1, 0].set_xlabel('Observation IDs')
axs[1, 0].set_ylabel('Flux (ergs/cm^2/s)')
axs[1, 0].legend()

# Plot the fourth graph (Powerlaw flux)
axs[1, 1].plot(observations, powFlux, label="Powerlaw fluxes")
axs[1, 1].scatter(observations, powFlux, marker="o")
axs[1, 1].set_xlabel('Observation IDs')
axs[1, 1].set_ylabel('Flux (ergs/cm^2/s)')
axs[1, 1].legend()

# Adjust layout and save the figure
plt.tight_layout()

pngFile = commonDirectory + "/" + observations[0] + "_" + observations[-1] + ".png"
pngPath = Path(pngFile)
if pngPath.exists():
    subprocess.run(["rm", pngFile])

plt.savefig(commonDirectory + "/" + observations[0] + "_" + observations[-1] + ".png")
