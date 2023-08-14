# This is an automatic NICER script for fitting and comparing models
import subprocess
import os
from pathlib import Path
from xspec import *

#===================================================================================================================================
# The location of the observation folders
outputDir = "/home/batuhanbahceci/NICER/analysis"

# Set it to True if you have made changes in models, and do not want to use any previous model files in commonDirectory
restartModels = False

# Name of the log file
resultsFile = "script_results.log"

# Critical value for F-test
ftestCrit = 0.005

# The list for models for fitting. The models will be compared using ftest within a loop.
# The structure of the list: 
# [ 1:<model name> 2:<parameter list>  3:<model file name>  4:<Fit results>  
modelList = [
    ["tbabs*diskbb", {"TBabs.nH": 8}, "mod_disk.xcm", {"chi":0, "dof":0}],
    ["tbabs*(diskbb+powerlaw)", {"powerlaw.PhoIndex": 2}, "mod_diskpow.xcm", {"chi":0, "dof":0}],
    ["tbabs*(diskbb+powerlaw+gauss)", {"gaussian.LineE": "6.95,1e-3,6.5,6.5,7.2,7.2", "gaussian.Sigma": "0.03,1e-3,0.001,0.001,0.5,0.5", "gaussian.norm":"-1e-3,1e-4,-1e12,-1e12,-1e-12,-1e-12"}, "mod_diskpowgauss.xcm", {"chi":0, "dof":0}]
]

energyFilter = "1.5 10."    #Do not forget to put . after an integer to spesify energy (in keV) instead of channel
#===================================================================================================================================
# Functions
def shakefit(modelIndex, resultsFile):
    print("\nPerforming shakefit error calculations for the model: " + AllModels(1).expression + ", obsid:" + str(obsid)+ "\n")
    resultsFile.write("========== Proceeding with shakefit error calculations ==========\n")
    paramNum = AllModels(1).nParameters
    updateList = modelList[modelIndex][1]

    for i in range(1, paramNum+1):
        paramDelta = AllModels(1)(i).values[1]
        if paramDelta < 0:  # Check for frozen parameters
            continue

        continueError = True
        delChi = 2.706
        counter = 0
        while continueError and counter < 100:
            counter += 1
            Fit.error("stop 10 0.1 maximum 50 " + str(delChi) + " " + str(i))
            errorResult = AllModels(1)(i).error
            errorString = errorResult[2]
  
            if errorString[3] == "T" or errorString[4] == "T":
                # Hit lower/upper limits, stop the error process for the current model parameter
                continueError = False

            if errorString[0] == "F":
                # Could not find a new minimum
                continueError = False
            elif errorString[1] == "T":
                # Non-monotonicity detected
                delChi += 2

            if continueError == False:
                parName = AllModels(1)(i).name
                errorTuple = "(" + listToStr(errorResult) + ")"
                resultsFile.write("Par " + str(i) + ": " + parName + " " + errorTuple+"\n")

    fitModel()
    updateParameters(modelIndex)
    resultsFile.write("=================================================================\n\n")

def listToStr(array):
    result = ""
    for char in array:
        result += str(char) + " "
    result = result[:-1]
    return result

def enterParameters(currentIndex, prevIndex, fluxPars = {}):
    modelName = modelList[currentIndex][0]
    mainList = modelList[currentIndex][1]
    stemList = modelList[prevIndex][1]

    parNum = AllModels(1).nParameters

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
            if fullName in stemList:
                AllModels(1)(indx).values = stemList[fullName]
            elif fullName in mainList:
                AllModels(1)(indx).values = mainList[fullName]
    
    if fluxPars != {}:
        compObj = AllModels(1).cflux
        for key, val in fluxPars.items():
            parObj = getattr(compObj, key)
            parObj.values = val

def fitModel():
    Fit.nIterations = 100
    Fit.delta = 0.01
    Fit.perform()

def updateParameters(modelIndex):
    modelDict = modelList[modelIndex][1]
    modelStats = modelList[modelIndex][3]

    # Save the parameters loaded in the xspec model to lists
    components = AllModels(1).componentNames
    for comp in components:
        compObj = getattr(AllModels(1), comp)
        parameters = compObj.parameterNames
        for par in parameters:
            parObj = getattr(compObj, par)
            indx = parObj.index
            fullName = comp + "." + par
            modelDict[fullName] = AllModels(1)(indx).values
    
    modelStats["chi"] = Fit.statistic
    modelStats["dof"] = Fit.dof
    modelStats["nullhyp"] = Fit.nullhyp

def saveModel(fileName, location = "default"):
    # This function saves the model file (.xcm) under spesified location. If no location has been given, 
    # the model file will be saved under default (outObsDir) directory

    if location == "default":
        xcmPath = Path(outObsDir + "/" + fileName)
        if xcmPath.exists():
            subprocess.run(["rm", outObsDir + "/" + fileName])

        Xset.save(outObsDir + "/" + fileName, "m")
    else:
        xcmPath = Path(location + "/" + fileName)
        if xcmPath.exists():
            subprocess.run(["rm", location + "/" + fileName])

        Xset.save(location + "/" + fileName, "m")

def saveData(location = "default"):
    # Similar to saveModel function, this function saves the data instead of model in an xcm file
    if location == "default":
        fileName = outObsDir + "/" + "data_" + obsid + ".xcm"
        filePath = Path(fileName)
        if filePath.exists():
            subprocess.run(["rm", fileName])
        Xset.save(fileName, "f")

    else:
        fileName = location + "/" + "data_" + obsid + ".xcm"
        filePath = Path(fileName)
        if filePath.exists():
            subprocess.run(["rm", fileName])
        Xset.save(fileName, "f")

def writeBestFittingModel(modelIndex, resultsFile):
    # This function writes the current model in AllModels container in a log file, assuming that all the models
    # have been compared and the last remaining model is the best fitting model.
    modelDict = modelList[modelIndex][1]
    modelStats = modelList[modelIndex][3]
    resultsFile.write("====================== Best Fitting Model ======================\n")
    resultsFile.write("Model Name: " + AllModels(1).expression + "\n")
    
    resultsFile.write("Fit results:\n")
    fitString = "Null Probability: " + str(modelStats["nullhyp"]) +", Chi-squared: " + str(modelStats["chi"]) + ", Dof: " + str(modelStats["dof"]) + "\n"
    resultsFile.write(fitString)

    parameterString = ""
    for i, j in modelDict.items():
        parameterString += i + ": " + str(j[0]) + ", "

    parameterString = parameterString[:-2]
    parameterString = "[" + parameterString + "]\n"
    resultsFile.write("Parameters: " + parameterString)
    resultsFile.write("=================================================================\n")
#===================================================================================================================
allDir = os.listdir(outputDir)
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
        if file == ("ni" + obsid + "mpu7_sr3c50.pha"):
            spectrumFile = file
            counter += 1
        elif file == ("ni" + obsid + "mpu7_bg3c50.pha"):
            backgroundFile = file
            counter += 1
        elif file == ("ni" + obsid + "mpu73c50.arf"):
            arfFile = file
            counter += 1
        elif file == ("ni" + obsid + "mpu73c50.rmf"):
            rmfFile = file
            counter += 1

        if counter == 4:
            # All necessary files have been found
            break

    if restartModels and iteration == 1:
        os.system("rm " + commonDirectory + "/mod*")

    #-------------------------------------------------------------------------------------    
    # From now on, PyXspec will be utilized for fitting and comparing models
    file = open(resultsFile, "w")
    Xset.openLog("xspecOutput.log")
    Xset.chatter = 1
    Fit.query = "yes"

    # Load the necessary files
    s1 = Spectrum(dataFile=spectrumFile, arfFile=arfFile, respFile=rmfFile, backFile=backgroundFile)
    Plot.xAxis = "keV"
    AllData.ignore("bad")
    AllData(1).ignore("**-"+energyFilter+"-**")
    saveData()
    
    # Initialize the index values of models for comparing them in a loop
    modelNumber = len(modelList)
    mainIdx = 0
    alternativeIdx = 1
    prevIdx = 0
    for i in range(modelNumber-1):
        file.write("Null hypothesis model: ")
        file.write(modelList[mainIdx][0] + " - ")
        mainModelFile = commonDirectory + "/" + modelList[mainIdx][2]

        # Define the current main model
        m = Model(modelList[mainIdx][0])
        modelPath = Path(mainModelFile)
        if modelPath.exists():
            Xset.restore(mainModelFile)
        else:
            enterParameters(mainIdx, prevIdx)

        fitModel()
        updateParameters(mainIdx)
        saveModel(modelList[mainIdx][2])
        saveModel(modelList[mainIdx][2], commonDirectory)

        file.write("Alternative model: " + modelList[alternativeIdx][0] + "\n")
        comparedModelFile = commonDirectory + "/" + modelList[alternativeIdx][2]

        # Define the alternative model
        m = Model(modelList[alternativeIdx][0])
        modelPath = Path(comparedModelFile)
        if modelPath.exists():
            Xset.restore(comparedModelFile)
        else:
            enterParameters(alternativeIdx, prevIdx)

        fitModel()
        updateParameters(alternativeIdx)
        saveModel(modelList[alternativeIdx][2])
        saveModel(modelList[alternativeIdx][2], commonDirectory)

        # Apply the f-test
        newChi = modelList[alternativeIdx][3]["chi"]
        newDof = modelList[alternativeIdx][3]["dof"]
        oldChi = modelList[mainIdx][3]["chi"]
        oldDof = modelList[mainIdx][3]["dof"]
        p_value = Fit.ftest(newChi, newDof, oldChi, oldDof)
        file.write("Ftest: " + str(newChi) +" | "+ str(newDof) +" | "+ str(oldChi) +" | "+ str(oldDof) +"\n\n")

        if abs(p_value) < ftestCrit:    
            # Alternative model has significantly improved the fit, set the alternative model as new main model
            mainModelFile = commonDirectory + "/" + modelList[alternativeIdx][2]
            prevIdx = alternativeIdx
            mainIdx = alternativeIdx
            alternativeIdx += 1
        else:
            mainModelFile = commonDirectory + "/" + modelList[mainIdx][2]
            prevIdx = alternativeIdx
            alternativeIdx += 1
    
    # At the end of the loop, mainIdx will hold the best fitting model. Reload the model
    bestIdx = mainIdx
    Xset.restore(mainModelFile)
    fitModel()
    shakefit(bestIdx, file)
    writeBestFittingModel(bestIdx, file)
    saveModel(modelList[bestIdx][2])
    saveModel(modelList[bestIdx][2], commonDirectory)

    for eachFile in allFiles:
        # Remove any existing "best model" files
        if "best_" in eachFile:
            os.system("rm " + eachFile)
    saveModel("best_" + modelList[bestIdx][2])

    file.close()
    Xset.closeLog()
    AllModels.clear()
    AllData.clear()