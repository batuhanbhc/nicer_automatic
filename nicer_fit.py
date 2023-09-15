# This is an automatic NICER script for fitting and comparing models
import subprocess
import os
from pathlib import Path
from xspec import *
import numpy as np
from nicer_variables import outputDir, resultsFile, energyFilter

#===================================================================================================================================
# Set it to True if you have made changes in models, and do not want to use any previous model files in commonDirectory
# restartOnce only deletes model files before the first observation, restartAlways deletes model files before all observations
restartOnce = True
restartAlways = False

# Critical value for F-test
ftestCrit = 0.05

chatterOn = True

makeXspecScript = True      # If set to True, the script will create an .xcm file that loads model and data files to xspec and creates a plot automatically

errorCalculations = True    # If set to True, the script will run "shakefit" function to calculate the error boundaries and possibly converge the
                            # fit to better parameter values.

fixNH = True                # If set to True, the script will fit "sampleSize" amount of observations, and take average values for nH parameters, then
                            # refit all observations by freezing nH parameters to the average values.
sampleSize = 10

energyLimits = energyFilter.split(" ")
Emin = energyLimits[0]
Emax = energyLimits[1]
#===================================================================================================================================
# Functions
def shakefit(resultsFile):
    # Create a temporary parameter file that will carry parameter values along with error boundaries
    parameterFile = outObsDir + "/" + "temp_parameters.txt"
    if Path(parameterFile).exists():
        os.system("rm " + parameterFile)
    os.system("touch " + parameterFile)

    parLines = []
    parLines.append("Parameter name | Parameter Value | Parameter Uncertainity Lower Boundary | Parameter Uncertainity Upper Boundary | Extra Information\n")
    counter = 0
    for comp in AllModels(1).componentNames:
        compObj = getattr(AllModels(1), comp)
        for par in compObj.parameterNames:
            counter += 1
            parObj = getattr(compObj, par)
            fullName = comp + "." + par
            parLines.append(fullName + " ")

    Fit.query = "no"
    print("Performing shakefit error calculations for the model: " + AllModels(1).expression + ", obsid:" + str(obsid)+ "\n")
    resultsFile.write("========== Proceeding with shakefit error calculations ==========\n")
    paramNum = AllModels(1).nParameters

    for i in range(1, paramNum+1):
        parDelta = AllModels(1)(i).values[1]

        if parDelta < 0:  # Check for frozen parameters
            continue

        continueError = True
        delChi = 2.706
        counter = 0
        while continueError and counter < 100:
            counter += 1
            Fit.error("stopat 10 0.1 maximum 50 " + str(delChi) + " " + str(i))
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
                # Save error calculation results to the log file
                # Save error calculation results to the log file
                parName = AllModels(1)(i).name
                parValue = AllModels(1)(i).values[0]
                parValue = AllModels(1)(i).values[0]
                errorTuple = "(" + listToStr(errorResult) + ")"
                resultsFile.write("Par " + str(i) + ": " + parName + " " + errorTuple+"\n")

    resultsFile.write("=================================================================\n\n")
    
    # Save parameter information to a list
    for i in range(1, AllModels(1).nParameters+1):
        errorResult = AllModels(1)(i).error
        errorString = errorResult[2]
        parValue = AllModels(1)(i).values[0]

        if AllModels(1)(i).values[1] < 0:
             # Fixed parameter, handle seperately
             parLines[i] = parLines[i] + (str(AllModels(1)(i).values[0]) + " ")*3 +" FIXED\n"
        else:
            lowerBound = str(errorResult[0])
            upperBound = str(errorResult[1])
            info = ""
            if errorString[6] == "T" and errorString[7] == "T":
                # Search failed in both directions
                upperBound = str(parValue)
                lowerBound = str(parValue)
                info = "FAILED_BOTH_DIRECTIONS"
            elif errorString[6] == "T":
                # Search failed in negative direction
                lowerBound = str(parValue)
                info = "FAILED_NEGATIVE_DIRECTION"
            elif errorString[7] == "T":
                # Search failed in positive direction
                upperBound = str(parValue)
                info = "FAILED_POSITIVE_DIRECTION"
            parLines[i] = parLines[i] + str(parValue) + " " + lowerBound + " " + upperBound + " " + info + "\n"

    updateParameters(bestModel)

    # Write the parameter information from list to the temporary parameter file
    parFile = open(parameterFile, "w")
    for line in parLines:
        parFile.write(line)
    parFile.close()

def listToStr(array):
    result = ""
    for char in array:
        result += str(char) + " "
    result = result[:-1]
    return result

def getParsFromList(modList, ignoreList = []):
    modelName = modList[0]
    parameterList = modList[1]

    parNum = AllModels(1).nParameters

    # Take the available parameters from the stemList
    components = AllModels(1).componentNames
    for comp in components:
        if comp in ignoreList:
            pass
        else:
            compObj = getattr(AllModels(1), comp)
            parameters = compObj.parameterNames
            for par in parameters:
                parObj = getattr(compObj, par)
                indx = parObj.index
                fullName = comp + "." + par

                if fullName in parameterList:
                    AllModels(1)(indx).values = parameterList[fullName]
 
def fitModel():
    Fit.query = "yes"
    Fit.nIterations = 100
    Fit.delta = 0.01
    Fit.renorm()
    Fit.perform()

def updateParameters(modList):
    modelDict = modList[1]
    modelStats = modList[2]

    # Save the parameters loaded in the xspec model to lists
    components = AllModels(1).componentNames
    for comp in components:
        compObj = getattr(AllModels(1), comp)
        parameters = compObj.parameterNames
        for par in parameters:
            parObj = getattr(compObj, par)
            fullName = comp + "." + par
            modelDict[fullName] = parObj.values
    
    modelStats["chi"] = Fit.statistic
    modelStats["dof"] = Fit.dof
    modelStats["nullhyp"] = Fit.nullhyp

def saveModel(fileName, obs, location = "default"):
    # This function saves the model file (.xcm) under spesified location. If no location has been given, 
    # the model file will be saved under default (outObsDir) directory
    
    if location == "default":
        xcmPath = Path(outputDir + "/" + obs + "/" + fileName)
        if xcmPath.exists():
            subprocess.run(["rm", outputDir + "/" + obs + "/" + fileName])

        Xset.save(outputDir + "/" + obs + "/" + fileName, "m")
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

def writeBestFittingModel(resultsFile):
    # This function writes the current model in AllModels container in a log file, assuming that all the models
    # have been compared and the last remaining model is the best fitting model.
    resultsFile.write("====================== Best Fitting Model ======================\n")
    resultsFile.write("Model Name: " + AllModels(1).expression + "\n")
    
    resultsFile.write("Fit results:\n")
    fitString = "Null Probability: " + str(Fit.nullhyp) +", Chi-squared: " + str(Fit.statistic) + ", Dof: " + str(Fit.dof) + "\n"
    resultsFile.write(fitString)

    parameterString = ""
    for comp in AllModels(1).componentNames:
        compObj = getattr(AllModels(1), comp)
        for par in compObj.parameterNames:
            parVal = getattr(compObj, par).values
            fullName = comp + "." + par
            parameterString += fullName + ": " + str(parVal) + "\n"

    resultsFile.write("Parameters: \n" + parameterString)
    resultsFile.write("=================================================================\n")

def extractModFileName():
    fileName = "model_"
    comps = sorted(AllModels(1).componentNames)
    compPart = ""
    for comp in comps:
        compPart += comp[:3]
    fileName += compPart + ".xcm"
    
    return fileName

def removeComp(compName, compNum, modelList):   # compNum is the n'th occurence of a spesific model, it is not the component number in general
    iteration = 1
    targetModelCounter = 1
    deletedCompIndex = 999
    modelFirstEncounter = True
    tempDict = {}
    modelName = AllModels(1).expression.replace(" ", "")

    # This loop iterates over each component, and assigns the model parameters with their values only if they do not belong to the targeted model
    for comp in AllModels(1).componentNames:
        if  targetModelCounter != compNum or (compName not in comp):
            compObj = getattr(AllModels(1), comp)
            if compName in comp:
                if modelFirstEncounter == True and "_" in comp:
                    for par in compObj.parameterNames:
                        parObj = getattr(compObj, par)
                        newComp = comp[:comp.find("_")]
                        fullName = newComp + "." + par
                        tempDict[fullName] = parObj.values
                elif "_" in comp and deletedCompIndex <= int(comp[comp.find("_") + 1:]):
                    for par in compObj.parameterNames:
                        parObj = getattr(compObj, par)
                        newComp = comp[:comp.find("_") + 1] + str(int(comp[comp.find("_") + 1:]) - 1)
                        fullName = newComp + "." + par
                        tempDict[fullName] = parObj.values
                else:
                    for par in compObj.parameterNames:
                        parObj = getattr(compObj, par)
                        fullName = comp + "." + par
                        tempDict[fullName] = parObj.values

                modelFirstEncounter = False
                targetModelCounter += 1
            else:
                for par in compObj.parameterNames:
                    parObj = getattr(compObj, par)
                    if "_" in comp and deletedCompIndex <= int(comp[comp.find("_") + 1:]):
                        newComp = comp[:comp.find("_") + 1] + str(int(comp[comp.find("_") + 1:]) - 1)
                        fullName = newComp + "." + par
                        tempDict[fullName] = parObj.values
                    else:
                        fullName = comp + "." + par
                        tempDict[fullName] = parObj.values
        else:
            targetModelCounter += 1
            deletedCompIndex = iteration
        
        iteration += 1

    # Look for the position of the targeted model component, then remove it from the model expression
    try: 
        test = modelName.index("+" + compName + "+")
        modelName = modelName.replace("+" + compName + "+", "+", 1) 
    except:
        try: 
            test = modelName.index("+" + compName)
            modelName = modelName.replace("+" + compName, "", 1) 
        except: 
            try: 
                test = modelName.index(compName + "+")
                modelName = modelName.replace(compName + "+", "", 1)
            except: 
                try: 
                    test = modelName.index(compName + "*")
                    modelName = modelName.replace(compName + "*", "", 1)
                except:
                    try:
                        test = modelName.index("*" + compName)
                        modelName = modelName.replace("*" + compName, "", 1)
                    except:
                        try:
                            test = modelName.index("(" + compName + ")")
                            modelName = modelName.replace("(" + compName +")", "", 1)
                        except:
                            modelName = modelName.replace(compName, "", 1)

    modelList[1] = tempDict
    modelList[0] = modelName
    m = Model(modelName)
    getParsFromList(modelList)

def addComp(compName, targetComp ,before_after, calcChar, modelList):
    modelName = modelList[0]
    if calcChar != "*" and calcChar != "+":
        print("\nIncorrect character for model expression. Terminating the script...\n")
        quit()

    if before_after == "before":
        targetIdx = modelName.find(targetComp)
        insertionText = compName + calcChar
        addedCompIndex = AllModels(1).componentNames.index(targetComp) + 1
    elif before_after == "after":
        targetIdx = modelName.find(targetComp) + len(targetComp)
        insertionText = calcChar + compName
        addedCompIndex = AllModels(1).componentNames.index(targetComp) + 2
    else:
        print("\nIncorrect entry for the placement of new component around the target component. Terminating the script...\n")
        quit()
    
    newModelName = modelName[:targetIdx] + insertionText + modelName[targetIdx:]

    alter_list_add(compName, addedCompIndex, modelList)
    m = Model(newModelName)
    modelList[0] = AllModels(1).expression.replace(" ", "")
    getParsFromList(modelList)
    modelList[1] = {}
    updateParameters(modelList)

def alter_list_add(compName, addedIdx, bestModelList):
    modelKeys = list(bestModelList[1].keys())[::-1]
    modelValues = list(bestModelList[1].values())[::-1]
    
    for i in range(len(modelKeys)):
        if "_" in modelKeys[i]:
            compNum = modelKeys[i][modelKeys[i].find("_") + 1: modelKeys[i].find(".")]
            if int(compNum) > addedIdx:
                newKey = modelKeys[i].replace(compNum, str(int(compNum)+1))
                bestModelList[1].pop(modelKeys[i])
                bestModelList[1][newKey] = modelValues[i]
        elif compName in modelKeys[i]:
            compIdx = AllModels(1).componentNames.index(compName) + 1
            if compIdx >= addedIdx:
                newKey = modelKeys[i][: modelKeys[i].find(".")] + "_" + str(compIdx + 1) + modelKeys[i][modelKeys[i].find(".") :]
                bestModelList[1].pop(modelKeys[i])
                bestModelList[1][newKey] = modelValues[i]

def wordCounter(source, word):
    start = 0
    count = 0
    while True:
        idx = source.find(word, start)

        if idx == -1:
            break
        else:
            start = idx + 1
            count += 1
    
    return count

def assignParameters(compName, parameterList, nthOccurence):
    startAssign = False
    occurence = 0
    for comp in AllModels(1).componentNames:
        compObj = getattr(AllModels(1), comp)
        if compName in comp:
            occurence += 1
            if occurence == nthOccurence:
                listIndex = 0
                for par in compObj.parameterNames:
                    parObj = getattr(compObj, par)
                    parObj.values = parameterList[listIndex]
                    listIndex += 1

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

def performFtest(mainModelList, altModelList, logFile, infoTxt = ""):
    newChi = altModelList[2]["chi"]
    newDof = altModelList[2]["dof"]
    oldChi = mainModelList[2]["chi"]
    oldDof = mainModelList[2]["dof"]

    pValue = Fit.ftest(newChi, newDof, oldChi, oldDof)
    
    logFile.write("Performing f-test: ")

    if infoTxt != "":
        logFile.write(infoTxt)

    logFile.write("\nNull hypothesis model: " + mainModelList[0] + "\nAlternative model: " + altModelList[0] +"\np-value: " + str(pValue)+"\n\n")

    return pValue

def calculateGaussEqw(logFile):
    eqwList = []
    counter = 0
    for comp in AllModels(1).componentNames:
        counter += 1
        if "gaussian" in comp:
            compName = comp
            compObj = getattr(AllModels(1), comp)
            energyVal = compObj.LineE.values[0]

            try:
                AllModels.eqwidth(counter, err=True, number=1000, level=90)
                eqwList.append("Equivalent width: " + str(listToStr(AllData(1).eqwidth)) + " (" + str(format(energyVal, ".2f")) + " keV gauss)\n")
            except:
                eqwList.append("Calculating eqw failed for component: " + comp + "\n")
    
    if eqwList != []:
        logFile.write("Gauss equivalent widths: (90% confidence intervals) \n")
        for each in eqwList:
            logFile.write(each)

def findTheClosestValue(targetNum, valueList):
    minDiff = 9999
    closestValue = 0
    for val in valueList:
        tempDiff = abs(targetNum - val)
        if tempDiff < minDiff:
            minDiff = tempDiff
            closestValue = val
    
    return closestValue

def matchGaussWithEnergy(gaussGroups):
    # Match gaussian component with their corresponding emission/absorption line in keV
    # e.g. matchDict = {gaussian: 1.8keV_gauss, gaussian_5: 6.7keV_gauss, ...}
    matchDict = {}

    for comp in AllModels(1).componentNames:
        if "gauss" in comp:
            compObj = getattr(AllModels(1), comp)
            for par in compObj.parameterNames:
                if par == "LineE":
                    parObj = getattr(compObj, par)
                    value = parObj.values[0]
                    energyGroup = findTheClosestValue(value, gaussGroups)
                    matchDict[comp] = str(energyGroup) + "keV_gauss"
    
    return matchDict

def findTheClosestValue(targetNum, valueList):
    minDiff = 9999
    closestValue = 0
    for val in valueList:
        tempDiff = abs(targetNum - val)
        if tempDiff < minDiff:
            minDiff = tempDiff
            closestValue = val
    
    return closestValue

def matchGaussWithEnergy(gaussGroups):
    # Match gaussian component with their corresponding emission/absorption line in keV
    # e.g. matchDict = {gaussian: 1.8keV_gauss, gaussian_5: 6.7keV_gauss, ...}
    matchDict = {}

    for comp in AllModels(1).componentNames:
        if "gauss" in comp:
            compObj = getattr(AllModels(1), comp)
            for par in compObj.parameterNames:
                if par == "LineE":
                    parObj = getattr(compObj, par)
                    value = parObj.values[0]
                    energyGroup = findTheClosestValue(value, gaussGroups)
                    matchDict[comp] = str(energyGroup) + "keV_gauss"
    
    return matchDict

def fixAllNH(nhDict):
    if "TBabs" in AllModels(1).expression:
        AllModels(1).TBabs.nH.values = nhDict["TBabs.nH"]
    
    if "pcfabs" in AllModels(1).expression:
        AllModels(1).pcfabs.nH.values = nhDict["pcfabs.nH"]

def filterOutliers(dataset):
    # Here I use Z-Score algorithm to filter out the outliers of the dataset
    # I saw that 3 sigma was commonly used for filtering outliers in this method, but since I will be filtering out nH values and we do not expect nH values to change
    # that drastically, I narrowed down the interval and set the z-score as 2 sigma.
    mean = np.mean(dataset)
    std_dev = np.std(dataset)
    threshold = 2 

    filtered_dataset = [x for x in dataset if abs(x - mean) / std_dev <= threshold]
    
    return filtered_dataset

def closeAllFiles():
    logFile.close()
    Xset.closeLog()
    AllModels.clear()
    AllData.clear()
#===================================================================================================================
# Find the script's own path
scriptPath = os.path.abspath(__file__)
scriptPathRev = scriptPath[::-1]
scriptPathRev = scriptPathRev[scriptPathRev.find("/") + 1:]
scriptDir = scriptPathRev[::-1]
os.chdir(scriptDir)

# Check if outputDir has been assigned to be a spesific directory or not
if outputDir == "":
    outputDir = scriptDir

allDir = os.listdir(outputDir)
commonDirectory = outputDir + "/commonFiles"   # ~/NICER/analysis/commonFiles

# Open the input txt file
with open("nicer_obs.txt", "r") as inputFile:
    obsPaths = inputFile.readlines()
    
# Find how many observations will be fitted to find an average value for nH parameters used throughout the script (If fixNH = True)
obsCount = len(obsPaths)
if obsCount < sampleSize:
    iterationMax = obsCount
else:
    iterationMax = sampleSize   

# Initializing required variables/dictionaries in case fixNH is set to True.
fixedValuesNH = {}
takeAverages = False
startFixingNH = False
if fixNH:
    takeAverages = True

for x in range(2):
    iteration = 0
    for obs in obsPaths:
        iteration += 1
    
        # Extract the obsid from the path name written in nicer_obs.txt
        obs = obs.strip("\n' ")
        parentDir = obs[::-1]
        obsid = parentDir[:parentDir.find("/")]         
        parentDir = parentDir[parentDir.find("/")+1:]   
        
        obsid = obsid[::-1]         # e.g. 6130010120

        outObsDir = outputDir + "/" + obsid
        os.chdir(outObsDir)
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

        if restartOnce and iteration == 1:
            os.system("rm " + commonDirectory + "/mod*")
        elif restartAlways:
            os.system("rm " + commonDirectory + "/mod*")

        #-------------------------------------------------------------------------------------    
        # From now on, PyXspec will be utilized for fitting and comparing models

        # These are the energies of both emission and absorption gausses that will be tried to fit to the observation along the script.
        # If you add/delete a gauss component along the script, make sure to update this list as well.
        gaussEnergyList = [6.98, 6.7, 1.8]
        
        # Set some Xspec settings
        logFile = open(resultsFile, "w")
        Xset.openLog("xspec_output.log")
        Xset.abund = "wilm"
        if chatterOn == False: 
            Xset.chatter = 0
        Fit.query = "yes"

        logFile.write("OBSERVATION ID: " + obsid + "\n\n")

        # Load the necessary files
        s1 = Spectrum(dataFile=spectrumFile, arfFile=arfFile, respFile=rmfFile, backFile=backgroundFile)
        Plot.xAxis = "keV"
        AllData.ignore("bad")
        AllData(1).ignore("**-" + Emin + " " + Emax +"-**")
        saveData()
        
        # This list will carry the model name, model parameters and fit statistics for the best model throughout the script.
        # First element is the model name, second element is the dictionary for parameter name-value pairs, third element is the dictionary for fit statistics
        # such as chi-squared, degrees of freedom and null hypothesis probability.
        bestModel = ["TBabs*(diskbb)", {}, {}]

        #=================================================================================
        # Load the first model (TBabs*diskbb) and fit
        m = Model(bestModel[0])  

        modelFile = extractModFileName()
        if Path(commonDirectory + "/" + modelFile).exists():
            # Load the model file to PyXspec
            Xset.restore(commonDirectory + "/" + modelFile)
        else:
            getParsFromList(bestModel)

        fitModel()
        updateParameters(bestModel)
        saveModel(modelFile, obsid)
        saveModel(modelFile, obsid, commonDirectory)
        nullhypModelList = transferToNewList(bestModel)
        #=================================================================================
        # Add powerlaw to the previous model and fit
        addComp("powerlaw", "diskbb", "after", "+", bestModel)

        modelFile = extractModFileName()
        if Path(commonDirectory + "/" + modelFile).exists():
            Xset.restore(commonDirectory + "/" + modelFile)
        else:
            getParsFromList(bestModel)
            powerlawPars = ["3", "1e-3"]
            assignParameters("powerlaw", powerlawPars, 1)
        
        fitModel()
        updateParameters(bestModel)
        saveModel(modelFile, obsid)
        saveModel(modelFile, obsid, commonDirectory)
        altModelList = bestModel
        
        #=================================================================================
        # Apply f-test and check whether powerlaw improves the fit significantly or not
        pValue = performFtest(nullhypModelList, altModelList, logFile, "Adding powerlaw")

        if abs(pValue) >= ftestCrit:
            removeComp("powerlaw", 1, bestModel)
            fitModel()
            updateParameters(bestModel)

        nullhypModelList = transferToNewList(bestModel)
        #=================================================================================
        # Add 6.98 keV absorption gauss and fit
        gaussPars_1 = ["6.98 -1", "7e-2,,0.05,0.05,0.2,0.2", "-1e-3,,-1e12,-1e12,-1e-12,-1e-12"]
        addComp("gaussian", "diskbb", "before", "+", bestModel)
        getParsFromList(bestModel)
        assignParameters("gaussian", gaussPars_1, 1)

        fitModel()
        updateParameters(bestModel)
        saveModel(modelFile, obsid)
        altModelList = bestModel

        #=================================================================================
        # Apply f-test and check whether last gaussian improves the fit significantly or not
        pValue = performFtest(nullhypModelList, altModelList, logFile, "Adding 6.98 keV absorption gauss")

        if abs(pValue) >= ftestCrit:
            removeComp("gaussian", 1, bestModel)
            fitModel()
            updateParameters(bestModel)

        nullhypModelList = transferToNewList(bestModel)
        #===============================================================================================
        # Add 6.7 keV absorption gauss and fit
        gaussPars_2 = ["6.7 -1", "0.07,,0.05,0.05,0.2,0.2", "-1e-3, 1e-4, -1e12, -1e12, -1e-12, -1e-12"]
        addComp("gaussian", "diskbb", "before", "+", bestModel)
        gaussCount = wordCounter(AllModels(1).expression, "gaussian")
        assignParameters("gauss", gaussPars_2, gaussCount)

        fitModel()
        updateParameters(bestModel)

        altModelList = bestModel

        #===============================================================================================
        # Apply f-test and check whether last gaussian improves the fit significantly or not
        pValue = performFtest(nullhypModelList, altModelList, logFile, "(adding 6.7 keV absorption gauss)")
        
        if abs(pValue) >= ftestCrit:
            removeComp("gaussian", 1, bestModel)
            fitModel()
            updateParameters(bestModel)

            logFile.write("\n====================================================================================\n")
            logFile.write("6.7 keV gauss is taken out from the model due to not improving the fit significantly.")
            logFile.write("\n====================================================================================\n")
        
        # Check whether powerlaw has positive index and steep slope (> 6, pretty much fits the lower energies only), take it out if that is the case
        modelBeforePowerlaw = extractModFileName()
        saveModel(modelBeforePowerlaw, obsid)

        powOut = False
        if "powerlaw" in AllModels(1).expression:
            if AllModels(1).powerlaw.PhoIndex.values[0] > 6:
                removeComp("powerlaw", 1, bestModel)

                powOut = True
                logFile.write("\n===============================================================================\n")
                logFile.write("Powerlaw has been taken out due to trying to fit lower energies (> 2 keV).\n")
                logFile.write("===============================================================================\n\n")
                
                pcfabsPars = ["7.296", "0.923"]
                addComp("pcfabs", "TBabs", "after", "*", bestModel)
                assignParameters("pcfabs", pcfabsPars, 1)
                if startFixingNH:
                    fixAllNH(fixedValuesNH)
                fitModel()
                updateParameters(bestModel)
        
                nullhypModelList = transferToNewList(bestModel)

                # Add an emission line at 1.8 keV (A gold line?)
                gaussPars_3 = ["1.8 -1", "0.07,,0.05,0.05,0.2,0.2", "0.01"]
                addComp("gaussian", "diskbb", "after", "+", bestModel)
                gaussCount = wordCounter(AllModels(1).expression, "gaussian")
                assignParameters("gauss", gaussPars_3, gaussCount)

                fitModel()
                updateParameters(bestModel)

                altModelList = bestModel

                # Apply f-test
                pValue = performFtest(nullhypModelList, altModelList, logFile, "(adding 1.8 keV emission gauss)")

                if abs(pValue) >= ftestCrit:
                    removeComp("gaussian", 1, bestModel)
                    fitModel()
                    updateParameters(bestModel)

                    logFile.write("\n====================================================================================\n")
                    logFile.write("1.8 keV gauss is taken out from the model due to not improving the fit significantly.")
                    logFile.write("\n====================================================================================\n\n")

        #========================================================================================================================================
        # Start recording nH values if fixNH is set to True.
        if iteration < iterationMax and takeAverages:
            # Save tbabs.nH and pcfabs.nH values after finding the best fitting model (before calculating errors)
            # These values will be used to calculate average nH values, which then will be used to refit all observations by fixing nH parameters    
            if "TBabs" in AllModels(1).expression:
                tbabsNH = AllModels(1).TBabs.nH.values[0]
                if "TBabs.nH" not in fixedValuesNH:
                    fixedValuesNH["TBabs.nH"] = [tbabsNH]
                else:
                    fixedValuesNH["TBabs.nH"].append(tbabsNH)

            if "pcfabs" in AllModels(1).expression:
                pcfabsNH = AllModels(1).pcfabs.nH.values[0]
                if "pcfabs.nH" not in fixedValuesNH:
                    fixedValuesNH["pcfabs.nH"] = [pcfabsNH]
                else:
                    fixedValuesNH["pcfabs.nH"].append(pcfabsNH)

            # Close all log files
            closeAllFiles()

            continue

        elif iteration == iterationMax and takeAverages:
            # The maximum sample size for calculating average nH values has been reached.
            # Terminate the first iteration of fitting observations, calculate average nH values and refit all observations again.

            # Save the nH values for calculating average one last time for the last observation
            if "TBabs" in AllModels(1).expression:
                tbabsNH = AllModels(1).TBabs.nH.values[0]
                if "TBabs.nH" not in fixedValuesNH:
                    fixedValuesNH["TBabs.nH"] = [tbabsNH]
                else:
                    fixedValuesNH["TBabs.nH"].append(tbabsNH)

            if "pcfabs" in AllModels(1).expression:
                pcfabsNH = AllModels(1).pcfabs.nH.values[0]
                if "pcfabs.nH" not in fixedValuesNH:
                    fixedValuesNH["pcfabs.nH"] = [pcfabsNH]
                else:
                    fixedValuesNH["pcfabs.nH"].append(pcfabsNH)

            startFixingNH = True
            takeAverages = False

            if "TBabs" in AllModels(1).expression:
                totalTBabsNH = 0
                fixedValuesNH["TBabs.nH"] = filterOutliers(fixedValuesNH["TBabs.nH"])
                tbabsNum = len(fixedValuesNH["TBabs.nH"])
                for val in fixedValuesNH["TBabs.nH"]:
                    totalTBabsNH += val

                avgTBabs = totalTBabsNH / tbabsNum
                fixedValuesNH["TBabs.nH"] = str(avgTBabs) + " -1"
            
            if "pcfabs" in AllModels(1).expression:
                totalPcfabsNH = 0
                fixedValuesNH["pcfabs.nH"] = filterOutliers(fixedValuesNH["pcfabs.nH"])
                pcfabsNum = len(fixedValuesNH["pcfabs.nH"])
                for val in fixedValuesNH["pcfabs.nH"]:
                    totalPcfabsNH += val
            
                avgPcfabs = totalPcfabsNH / pcfabsNum
                fixedValuesNH["pcfabs.nH"] = str(avgPcfabs) + " -1"

            # Close all log files
            closeAllFiles()
            
            break
        #========================================================================================================================================
        
        if powOut == False:
            # Restore the best-fitting model back
            Xset.restore(modelBeforePowerlaw)
            modFileName = extractModFileName()

            if fixNH:
                fixAllNH(fixedValuesNH)

            fitModel()
            updateParameters(bestModel)

            if errorCalculations:
                shakefit(logFile)
                
            writeBestFittingModel(logFile)
            saveModel(modFileName, obsid)
            saveModel(modFileName, obsid, commonDirectory)
        else:
            # Save the new model without powerlaw
            if errorCalculations:
                    shakefit(logFile)

            modFileName = extractModFileName()
            writeBestFittingModel(logFile)
            saveModel(modFileName, obsid)
            saveModel(modFileName, obsid, commonDirectory)

        #==========================================================================
        if errorCalculations:
            # Rename gauss names in the temp_parameters.txt file for grouping purposes.
            # For instance, this part changes gauss names from "gaussian_5" to "6.7keV_gauss" and so on.
            gaussEnergyList = [1.8, 6.7, 6.98]
            renameDict = matchGaussWithEnergy(gaussEnergyList)
            inputFile = open("temp_parameters.txt", "r")
            outputFile = "parameters_bestmodel.txt"

            if Path(outputFile).exists():
                os.system("rm " + outputFile)
            os.system("touch " + outputFile)

            outFile = open(outputFile, "w")

            for line in inputFile.readlines():
                line = line.split(" ")
                compName = line[0]
                compName = compName[: compName.find(".")]
                rest = line[0][line[0].find("."):]
                for key, val in renameDict.items():
                    if compName == key:
                        line[0] = val + rest
                        break

                outFile.write(listToStr(line))
            
            inputFile.close()
            outFile.close()
        #===========================================================================
        # Remove any pre-existing best model files and save a new one
        for eachFile in allFiles:
            if "best_" in eachFile:
                os.system("rm " + eachFile)
        saveModel("best_" + modFileName, obsid)

        # Calculate and write equivalent widths of gausses to log file
        calculateGaussEqw(logFile)
        
        # Close all log files
        closeAllFiles()

        # Write an xspec script for analyzing parameter values along with linear-data and residual plots quickly
        if makeXspecScript:
            if Path("xspec_bestmod_script.xcm").exists():
                os.system("rm -rf xspec_bestmod_script.xcm")
            os.system("touch xspec_bestmod_script.xcm")

            file = open("xspec_bestmod_script.xcm", "w")
            file.write("@data_" + obsid + ".xcm\n")
            file.write("@best_" + modFileName + "\n")
            file.write("cpd /xw\n")
            file.write("setpl e\n")
            file.write("fit\n")
            file.write("pl ld chi\n")
            file.write("show par\n")
            file.write("show fit\n")
            file.write("echo OBSID:" + obsid + "\n")
            file.close()

    if fixNH == False:
        # The whole fitting process is looped twice for refitting purposes. If fixing nH option is False, do not try to refit
        break

os.chdir(scriptDir)

# Run the plot script
os.system("python3 nicer_plot.py")

# This file is created after importing variables from another python file
if Path("__pycache__").exists():
    os.system("rm -rf __pycache__")