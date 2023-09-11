# This is an automatic NICER script for fitting and comparing models
import subprocess
import os
from pathlib import Path
from xspec import *

#===================================================================================================================================
# The location of the observation folders
outputDir = "/home/batuhanbahceci/NICER/analysis"

# Set it to True if you have made changes in models, and do not want to use any previous model files in commonDirectory
# restartOnce only deletes model files before the first observation, restartAlways deletes model files before all observations
restartOnce = True
restartAlways = False

# Name of the log file
resultsFile = "script_results.log"

# Critical value for F-test
ftestCrit = 0.05

chatterOn = True

addPcfabs = True            # If powerlaw is taken out due to fitting lower energies, switchPcfabs will add pcfabs component for providing extra absorption
                            # to account for lower energy part. If set to False, the script will add two absorption gausses instead of pcfabs.

makeXspecScript = True      # If set to True, the script will create an .xcm file that loads model and data files to xspec and creates a plot automatically

errorCalculations = True    # If set to True, the script will run "shakefit" function to calculate the error boundaries and possibly converge the
                            # fit to better parameter values.
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
                parName = AllModels(1)(i).name
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

def getParsFromList(currentModList, prevModList, ignoreList = []):
    modelName = currentModList[0]
    mainList = currentModList[1]
    stemList = prevModList[1]

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
                # If the parameter value is stored in previous model's list, take it from there. Otherwise, look whether
                # it is initialized in current model's list
                if fullName in stemList:
                    AllModels(1)(indx).values = stemList[fullName]
                elif fullName in mainList:
                    AllModels(1)(indx).values = mainList[fullName]
 
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
            indx = parObj.index
            fullName = comp + "." + par
            modelDict[fullName] = AllModels(1)(indx).values
    
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
    m = Model(modelName)
    getParsFromList(modelList, modelList)

def addComp(compName, targetComp ,before_after, calcChar, modelList):
    modelName = AllModels(1).expression
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
    getParsFromList(modelList, modelList)
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

def calculateGaussEqw():
    eqwList = []
    counter = 0
    for comp in AllModels(1).componentNames:
        counter += 1
        if "gaussian" in comp:
            compName = comp
            compObj = getattr(AllModels(1), comp)
            energyVal = compObj.LineE.values[0]

            AllModels.eqwidth(counter, err=True, number=1000, level=90)
            eqwList.append("Equivalent width: " + str(listToStr(AllData(1).eqwidth)) + " (" + str(format(energyVal, ".2f")) + " keV gauss)\n")
    
    return eqwList

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
#===================================================================================================================
# Find the script's own path
scriptPath = os.path.abspath(__file__)
scriptPathRev = scriptPath[::-1]
scriptPathRev = scriptPathRev[scriptPathRev.find("/") + 1:]
scriptDir = scriptPathRev[::-1]
os.chdir(scriptDir)

allDir = os.listdir(outputDir)
commonDirectory = outputDir + "/commonFiles"   # ~/NICER/analysis/commonFiles
iteration = 0

inputFile = open("nicer_obs.txt")
for obs in inputFile.readlines():
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

    # The list for models for fitting. The models will be compared using ftest within a loop.
    # The structure of the list: 
    # [ 1:<model name> 2:<parameter list> 3:<Fit results>  
    modelList = [
        ["TBabs*diskbb", {"TBabs.nH": 8}, {}],
        ["TBabs*(diskbb+powerlaw)", {"powerlaw.PhoIndex": 2}, {}],
        ["TBabs*(diskbb+powerlaw+gaussian)", {"gaussian.LineE": "6.984 -1", "gaussian.Sigma": "0.07,,0.05,0.05,0.2,0.2", "gaussian.norm":"-1e-3,1e-4,-1e12,-1e12,-1e-12,-1e-12"}, {}]
    ]
    
    file = open(resultsFile, "w")
    Xset.openLog("xspec_output.log")
    Xset.abund = "wilm"
    if chatterOn == False: 
        Xset.chatter = 0
    Fit.query = "yes"

    file.write("OBSERVATION ID: " + obsid + "\n\n")

    # Load the necessary files
    s1 = Spectrum(dataFile=spectrumFile, arfFile=arfFile, respFile=rmfFile, backFile=backgroundFile)
    Plot.xAxis = "keV"
    AllData.ignore("bad")
    AllData(1).ignore("**-1.5 10.-**")
    saveData()
    
    # Initialize the index values of models for comparing them in a loop
    modelNumber = len(modelList)
    mainIdx = 0
    alternativeIdx = 1
    prevIdx = 0
    for i in range(modelNumber-1):
        # Define the current main model
        m = Model(modelList[mainIdx][0])
        mainModFileName = extractModFileName()
        mainModelFile = commonDirectory + "/" + mainModFileName
        if Path(mainModelFile).exists():
            Xset.restore(mainModelFile)
        else:
            getParsFromList(modelList[mainIdx], modelList[prevIdx])

        fitModel()
        updateParameters(modelList[mainIdx])
        saveModel(mainModFileName, obsid)
        saveModel(mainModFileName, obsid, commonDirectory)
        nullhypModelList = transferToNewList(modelList[mainIdx])

        # Define the alternative model
        m = Model(modelList[alternativeIdx][0])
        altModFileName = extractModFileName()
        alternativeModelFile = commonDirectory + "/" + altModFileName
        if Path(alternativeModelFile).exists():
            Xset.restore(alternativeModelFile)
        else:
            getParsFromList(modelList[alternativeIdx], modelList[prevIdx])

        fitModel()
        updateParameters(modelList[alternativeIdx])
        saveModel(altModFileName, obsid)
        saveModel(altModFileName, obsid, commonDirectory)
        altModelList = transferToNewList(modelList[alternativeIdx])

        # Apply the f-test
        pValue = performFtest(nullhypModelList, altModelList, file)

        if abs(pValue) < ftestCrit:    
            # Alternative model has significantly improved the fit, set the alternative model as new main model
            mainModelFile = alternativeModelFile
            prevIdx = alternativeIdx
            mainIdx = alternativeIdx
        else:
            prevIdx = alternativeIdx
        
        alternativeIdx += 1
    

    # At the end of the loop, mainIdx will hold the best fitting model. Reload the model
    Xset.restore(mainModelFile)
    mainModelName = AllModels(1).expression.replace(" ", "")

    #==============================================================================================
    # Create another entry in modelList, which will carry the best model with further changes to it
    modelList.append([modelList[mainIdx][0]])

    parsDict = {}
    for key,val in modelList[mainIdx][1].items():
        parsDict[key] = val
    modelList[-1].append(parsDict)

    statsDict = {}
    for key,val in modelList[mainIdx][2].items():
        statsDict[key] = val
    modelList[-1].append(statsDict)

    bestModel = modelList[-1]
    #===============================================================================================
    nullhypModelList = transferToNewList(bestModel)

    # Try to add another gauss at 6.7 keV, remove if it does not improve the fit significant enough.
    gaussParList = ["6.7 -1", "0.07,,0.05,0.05,0.2,0.2", "-1e-3, 1e-4, -1e12, -1e12, -1e-12, -1e-12"]
    addComp("gaussian", "diskbb", "after", "+", bestModel)
    assignParameters("gauss", gaussParList, 1)
    fitModel()
    updateParameters(bestModel)

    altModelList = bestModel

    # Apply f-test
    pValue = performFtest(nullhypModelList, altModelList, file, "(adding 6.7 keV absorption gauss)")
    
    if abs(pValue) >= ftestCrit:
        removeComp("gaussian", 1, bestModel)
        fitModel()
        updateParameters(bestModel)

        file.write("\n====================================================================================\n")
        file.write("6.7 keV gauss is taken out from the model due to not improving the fit significantly.")
        file.write("\n====================================================================================\n")
    
    # Check the region where the powerlaw is trying to fit, if the region is located below 2 keV, do not add powerlaw component.
    powOut = False
    if "powerlaw" in AllModels(1).expression:
        removeComp("powerlaw", 1, bestModel)

        Plot("chi")
        residX = Plot.x()
        residY = Plot.y()

        # Group every {binSize} delta chi-sq bins, start rebinning next group with the previous group's last {shiftSize} bins (overlapping groups)
        binSize = len(residX) * 5 // 100    # 5% length of total bin number
        shiftSize = binSize // 2 + 1
        threshold = 50  # Unit: delta chi-squared

        # targetX and targetY will store the groups containing values bigger than the threshold
        newGroupsX = []; newGroupsY = []
        targetX = []; targetY = []
        tempSumX = 0; tempSumY = 0
        pointer = 0
        counter = 0
        while True:
            try:
                counter += 1
                tempSumX += residX[pointer]
                tempSumY += residY[pointer]

                if counter == binSize:
                    counter = 0
                    pointer -= shiftSize
                    newGroupsX.append(tempSumX / binSize);  newGroupsY.append(tempSumY / binSize)
                    if tempSumY / binSize >= threshold:
                        targetX.append(tempSumX / binSize);     targetY.append(tempSumY / binSize)

                    tempSumY = 0;   tempSumX = 0
            except:
                if counter != 1:
                    # There is a left over group at the end that has number of bins lower than binSize
                    newGroupsX.append(tempSumX / counter);  newGroupsY.append(tempSumY / counter)
                    if tempSumY / binSize >= threshold:
                        targetX.append(tempSumX / counter);     targetY.append(tempSumY / counter)

                break
            
            pointer += 1
        
        # Are there any region of data that is below 2 keV, and also has an average delta chi-sq value bigger than the threshold value?
        # If so, remove powerlaw component.
        result = any(value <= 2 for value in targetX)
        if result == True:
            powOut = True

            file.write("\n===============================================================================\n")
            file.write("Powerlaw has been taken out due to trying to fit lower energies (> 2 keV).\n")
            file.write("===============================================================================\n\n")
            
            if addPcfabs:
                pcfabsPars = ["7.296", "0.923"]
                addComp("pcfabs", "TBabs", "after", "*", bestModel)
                assignParameters("pcfabs", pcfabsPars, 1)
                fitModel()
                updateParameters(bestModel)
        
                nullhypModelList = transferToNewList(bestModel)

                # Add an emission line at 1.8 keV (A gold line?)
                gaussPars = ["1.8 -1", "0.07,,0.05,0.05,0.2,0.2", "0.01"]
                addComp("gaussian", "diskbb", "after", "+", bestModel)
                assignParameters("gauss", gaussPars, 1)
                fitModel()
                updateParameters(bestModel)

                altModelList = bestModel

                # Apply f-test
                pValue = performFtest(nullhypModelList, altModelList, file, "(adding 1.8 keV emission gauss)")

                if abs(pValue) >= ftestCrit:
                    removeComp("gaussian", 1, bestModel)
                    fitModel()
                    updateParameters(bestModel)

                    file.write("\n====================================================================================\n")
                    file.write("1.8 keV gauss is taken out from the model due to not improving the fit significantly.")
                    file.write("\n====================================================================================\n\n")
                
                for comp in AllModels(1).componentNames:
                    if comp == "pcfabs":
                        compObj = getattr(AllModels(1), comp)
                        for par in compObj.parameterNames:
                            parObj = getattr(compObj, par)
                            parObj.frozen = True
                            bestModel[1][comp + "." + parObj.name] = parObj.values
                
                fitModel()

                if errorCalculations:
                    shakefit(file)
                    updateParameters(bestModel)
            else:
                addComp("gaussian", "diskbb", "after", "+", bestModel)
                addComp("gaussian", "diskbb", "after", "+", bestModel)
                gaussEnergies = ["1.55 -1", "1.8 -1"]
                gaussCounter = 0
                comps = AllModels(1).componentNames[::-1]
                for comp in comps:
                    if gaussCounter < 2 and "gauss" in comp:
                        compObj = getattr(AllModels(1), comp)
                        pars = compObj.parameterNames
                        for par in pars:
                            if par == "LineE":
                                parObj = getattr(compObj, par)
                                parObj.values = gaussEnergies[gaussCounter]
                                gaussCounter += 1

                fitModel()
                if errorCalculations:
                    shakefit(file)
                    updateParameters(bestModel)

    if powOut == False:
        # Restore the best-fitting model back
        Xset.restore(mainModelFile)

        modFileName = extractModFileName()
        fitModel()
        if errorCalculations:
            shakefit(file)
        writeBestFittingModel(file)
        saveModel(modFileName, obsid)
        saveModel(modFileName, obsid, commonDirectory)
    else:
        # Save the new model without powerlaw
        modFileName = extractModFileName()
        writeBestFittingModel(file)
        saveModel(modFileName, obsid)
        saveModel(modFileName, obsid, commonDirectory)
    #==========================================================================
    if errorCalculations:
        # Rename gauss names in the temp_parameters.txt file for grouping purposes.
        # For instance, this part changes gauss names from "gaussian_5" to "6.7keV_gauss" and so on.
        gaussEnergyList = [1.8, 6.7, 6.984]
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
    #================================================================
    # Remove any existing best model files and save the new one
    for eachFile in allFiles:
        if "best_" in eachFile:
            os.system("rm " + eachFile)
    saveModel("best_" + modFileName, obsid)

    # Write equivalent widths of gausses to log file
    gaussEqwidthList = calculateGaussEqw()
    file.write("Gauss equivalent widths: (90% confidence intervals) \n")
    for each in gaussEqwidthList:
        file.write(each)
    
    file.close()
    Xset.closeLog()
    AllModels.clear()
    AllData.clear()

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