# This is an automatic NICER script for performing spectral analysis by fitting and comparing different Xspec models
# Authors: Batuhan Bahçeci
# Contact: batuhan.bahceci@sabanciuniv.edu

from parameter import *
import operator

operator_mapping = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne
}

print("==============================================================================")
print("\t\t\tRunning the file: " + fitScript + "\n")

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

#========================================================== Input Checks ===========================================================
# Input check for outputDir
if Path(outputDir).exists() == False:
    print("Directory defined by outputDir could not be found. Terminating the script...")
    quit()

# Input check for restartAlways
if isinstance(restartAlways, bool) == False:
    while True:
        print("\nThe 'restartAlways' variable is not of type boolean.")
        restartAlways = input("Please enter a boolean value for 'restartAlways' (True/False): ")

        if restartAlways == "True" or restartAlways == "False":
            restartAlways = bool(restartAlways)
            break

# Input check for restartOnce
if isinstance(restartOnce, bool) == False:
    while True:
        print("\nThe 'restartOnce' variable is not of type boolean.")
        restartOnce = input("Please enter a boolean value for 'restartOnce' (True/False): ")

        if restartOnce == "True" or restartOnce == "False":
            restartOnce = bool(restartOnce)
            break

# Input check for ftestSignificance
if isinstance(ftestSignificance, float) == False or not (0 < ftestSignificance < 1):
    while True:
        try:
            ftestSignificance = float(ftestSignificance)
            if ftestSignificance <= 0 or ftestSignificance >= 1:
                # Make an error on purpose and trigger except block, since fTestSignificance is not on the correct interval
                errorVariable = int("99.99")
            else:
                break
        except:
            print("\nThe 'fTestSignificance' variable must be a float number between 0 and 1.")
            ftestSignificance = input("Please enter a float number between 0 and 1 for 'ftestSignificance' (0 < x < 1): ")

# Input check for sampleSize
if str(sampleSize).isnumeric() == False or int(sampleSize) <= 0:
    while True:
        print("\nEither the 'sampleSize' variable is not of type integer, or it is smaller or equal to 0.")
        sampleSize = input("Please enter a positive integer value for 'sampleSize' (x > 0): ")

        if sampleSize.isnumeric() and int(sampleSize) > 0:
            sampleSize = int(sampleSize)
            break

# Input check for fixParameters
if isinstance(fixParameters, bool) == False:
    while True:
        print("\nThe 'fixParameters' variable is not of type boolean.")
        fixParameters = input("Please enter a boolean value for 'fixParameters' (True/False): ")

        if fixParameters == "True" or fixParameters == "False":
            fixParameters = bool(fixParameters)
            break

# Input check for errorCalculations
if isinstance(errorCalculations, bool) == False:
    while True:
        print("\nThe 'errorCalculations' variable is not of type boolean.")
        errorCalculations = input("Please enter a boolean value for 'errorCalculations' (True/False): ")

        if errorCalculations == "True" or errorCalculations == "False":
            errorCalculations = bool(errorCalculations)
            break

# Input check for makeXspecScript
if isinstance(makeXspecScript, bool) == False:
    while True:
        print("\nThe 'makeXspecScript' variable is not of type boolean.")
        makeXspecScript = input("Please enter a boolean value for 'makeXspecScript' (True/False): ")

        if makeXspecScript == "True" or makeXspecScript == "False":
            makeXspecScript = bool(makeXspecScript)
            break

# Input check for calculateGaussEqw
if isinstance(calculateGaussEquivalentWidth, bool) == False:
    while True:
        print("\nThe 'calculateGaussEquivalentWidth' variable is not of type boolean.")
        calculateGaussEquivalentWidth = input("Please enter a boolean value for 'calculateGaussEquivalentWidth' (True/False): ")

        if calculateGaussEquivalentWidth == "True" or calculateGaussEquivalentWidth == "False":
            calculateGaussEquivalentWidth = bool(calculateGaussEquivalentWidth)
            break
#===================================================================================================================================

#===================================================================================================================================
# Functions
def shakefit(bestModelList, resultsFile):

    # Shakefit will only be run for these parameters
    parametersToCalculateError = []

    for key in parametersForShakefit.keys():
        model = key[:key.find(".")]
        parameter = key[key.find(".") + 1:]
        if model in AllModels(1).expression:
            compObj = getattr(AllModels(1), model)
            parObj = getattr(compObj, parameter)
            index = parObj.index

            parametersToCalculateError.append(index)
        else:
            pass

    if checkPowerlawErrorAndFreeze:
        # Before proceeding with shakefit, check if powerlaw is in model expression. If so, check whether xspec error for photon index is bigger than 1 or not.
        # If bigger than 1, fix photon index to 1.7 (may change in future) and only then continue with shakefit
        if "powerlaw" in AllModels(1).expression:
            with open("xspec_output.log", "r") as testfile:
                lines = testfile.readlines()[-35:]
            
            print("\nChecking powerlaw xspec error value...\n")
            retrievePhotonIndex = False
            for line in lines:
                line = line.strip("\n")
                if " par  comp" in line:
                    retrievePhotonIndex = True
                
                if retrievePhotonIndex:
                    if "powerlaw" not in line:
                        pass
                    else:
                        words = line.split(" ")

                        # Remove all empty elements from the list
                        while True:
                            try:
                                emptyIndex = words.index("")
                                words.pop(emptyIndex)
                            except:
                                break

                        errorValue = words[-1]  # Xspec error value
                        errorValue = errorValue.strip("\n")
                        
                        if errorValue == "frozen":
                            break

                        errorValue = float(errorValue)
                        if (1 >= errorValue > 0) == False:
                            AllModels(1).powerlaw.PhoIndex.values = str(powerlawIndexToFreezeAt) + " -1"
                            resultsFile.write("\nWARNING: Powerlaw photon index is frozen at " + str(AllModels(1).powerlaw.PhoIndex.values[0]) + " for having large xspec error: " + str(errorValue)+ "\n")
                            print("Powerlaw xspec error value is: " + str(errorValue))
                            print("\nWARNING: Powerlaw photon index is frozen at " + str(AllModels(1).powerlaw.PhoIndex.values[0]) + " for having xspec error bigger than 1: "+str(errorValue)+"\n")
                        
                        break

    Fit.query = "no"
    resultsFile.write("========== Proceeding with shakefit error calculations ==========\n")
    paramNum = AllModels(1).nParameters
    rerunShakefit = False
    for k in range(2):
        if k == 1 and rerunShakefit == False:
            break

        print("Performing shakefit error calculations for the model: " + AllModels(1).expression + ", obsid:" + str(obsid)+ ", shakefit number: " + str(k+1)+"\n")
        fitModel(bestModelList)
        updateParameters(bestModel)

        for i in range(1, paramNum+1):
            parDelta = AllModels(1)(i).values[1]

            if parDelta < 0:  # Check for frozen parameters
                continue
            
            if i not in parametersToCalculateError:
                continue

            continueError = True
            delChi = 2.706
            counter = 0
            while continueError and counter < 100:
                counter += 1
                Fit.error("stopat 10 0.1 maximum 100 " + str(delChi) + " " + str(i))
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
            
        # Check if any parameter value has gotten outside their initially calculated confidence interval
        rerunShakefit = False
        for m in range(1, AllModels(1).nParameters+1):
            parValue = AllModels(1)(m).values[0]
            errorString = AllModels(1)(m).error
            if errorString[0] != 0 and parValue < errorString[0]:
                rerunShakefit = True
                print("Some parameters are out of their previously calculated error boundaries. Rerunning shakefit...\n")
                break
            elif errorString[1] != 0 and parValue > errorString[1]:
                print("Some parameters are out of their previously calculated error boundaries. Rerunning shakefit...\n")
                rerunShakefit = True
                break

    resultsFile.write("=================================================================\n\n")
    updateParameters(bestModel)

def listToStr(array):
    result = ""
    for char in array:
        result += str(char) + " "
    result = result[:-1]
    return result

def getParsFromList(modList, ignoreList = []):
    parameterList = modList[0]

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
 
def fitModel(bestModelList): 
    print("\nFitting the model: " + AllModels(1).expression + "\n")

    Fit.nIterations = 100
    Fit.delta = 0.01
    Fit.renorm()
    Fit.perform()
    updateParameters(bestModelList)

def updateParameters(modList):
    modelDict = modList[0]
    modelStats = modList[1]

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
            parameterString += fullName + ":\t" + str(parVal) + "\n"

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

    compCount = wordCounter(modelName, compName)
    if compCount < compNum or compNum <= 0:
        print("\nERROR: There are (" + str(compCount) + ") " + compName + " in the current model expression.")
        print("Given component number should be in between 1 <= x <= " + str(compCount) + " (Given input: " + str(compNum) + ")\n")
        quit()

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

    modelList[0] = tempDict
    m = Model(modelName)
    getParsFromList(modelList)

def addComp(compName, targetComp ,before_after, calcChar, modelList, encapsulate=False):
    modelName = " " + AllModels(1).expression + " "
    if calcChar != "*" and calcChar != "+":
        print("\nIncorrect character for model expression. Terminating the script...\n")
        quit()

    modelName = modelName[1:-1]
    if before_after == "before":
        if encapsulate:
            targetIdx = modelName.find(targetComp)
            insertionText =  "(" + compName + calcChar + targetComp + ")"
            addedCompIndex = AllModels(1).componentNames.index(targetComp) + 1

            newModelName = modelName[:targetIdx] + insertionText + modelName[targetIdx + len(targetComp):]
        else:
            targetIdx = modelName.find(targetComp)
            insertionText = compName + calcChar
            addedCompIndex = AllModels(1).componentNames.index(targetComp) + 1

            newModelName = modelName[:targetIdx] + insertionText + modelName[targetIdx:]
    elif before_after == "after":
        if encapsulate:
            targetIdx = modelName.find(targetComp)
            insertionText = "(" + targetComp + calcChar + compName + ")"
            addedCompIndex = AllModels(1).componentNames.index(targetComp) + 2

            newModelName = modelName[:targetIdx] + insertionText + modelName[targetIdx + len(targetComp):]
        else:
            targetIdx = modelName.find(targetComp)
            insertionText = calcChar + compName
            addedCompIndex = AllModels(1).componentNames.index(targetComp) + 2

            newModelName = modelName[:targetIdx + len(targetComp)] + insertionText + modelName[targetIdx + len(targetComp):]
    else:
        print("\nIncorrect entry for the placement of new component around the target component. Terminating the script...\n")
        quit()
    
    alter_list_add(compName, addedCompIndex, modelList)
    m = Model(newModelName)
    getParsFromList(modelList)
    modelList[0] = {}
    updateParameters(modelList)

def alter_list_add(compName, addedIdx, bestModelList):
    modelKeys = list(bestModelList[0].keys())[::-1]
    modelValues = list(bestModelList[0].values())[::-1]
    
    for i in range(len(modelKeys)):
        compPart = modelKeys[i][:modelKeys[i].find(".")]
        rest = modelKeys[i][modelKeys[i].find("."):]
        if "_" in compPart:
            compNum = compPart[compPart.find("_") + 1 :]
            if int(compNum) > addedIdx:
                newKey = compPart.replace(compNum, str(int(compNum)+1)) + rest
                bestModelList[0].pop(modelKeys[i])
                bestModelList[0][newKey] = modelValues[i]
        elif compName in modelKeys[i]:
            compIdx = AllModels(1).componentNames.index(compName) + 1
            if compIdx >= addedIdx:
                newKey = modelKeys[i][: modelKeys[i].find(".")] + "_" + str(compIdx + 1) + modelKeys[i][modelKeys[i].find(".") :]
                bestModelList[0].pop(modelKeys[i])
                bestModelList[0][newKey] = modelValues[i]

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

def assignParameters(compName, nthOccurence, parameterTuple):
    startAssign = False
    occurence = 0
    for comp in AllModels(1).componentNames:
        compObj = getattr(AllModels(1), comp)
        if compName in comp:
            occurence += 1
            if occurence == nthOccurence:
                parameterName = parameterTuple[0]
                value = parameterTuple[1]
                parObject = getattr(compObj, parameterName)
                parObject.values = value

def transferToNewList(sourceList):
    newList = []
    newParDict = {}
    newStatDict = {}

    sourceParDict = sourceList[0]
    keys = list(sourceParDict.keys())
    values = list(sourceParDict.values())
    for i in range(len(keys)):
        newParDict[keys[i]] = values[i]
    newList.append(newParDict)

    sourceStatDict = sourceList[1]
    keys = list(sourceStatDict.keys())
    values = list(sourceStatDict.values())
    for i in range(len(keys)):
        newStatDict[keys[i]] = values[i]
    newList.append(newStatDict)
    
    return newList

def performFtest(nullModelList, altModelList, logFile, infoTxt = ""):
    newChi = altModelList[1]["chi"]
    newDof = altModelList[1]["dof"]
    oldChi = nullModelList[1]["chi"]
    oldDof = nullModelList[1]["dof"]

    pValue = Fit.ftest(newChi, newDof, oldChi, oldDof)
    
    logFile.write("Performing f-test: ")

    if infoTxt != "":
        logFile.write(infoTxt)

    logFile.write("F-test significance: "+ str(ftestSignificance)+", p-value: " + str(pValue)+"\n\n")
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

def fixAllParameters(fixedValues):
    for key, val in fixedValues.items():
        temp = key.split(".")
        compName = temp[0]
        parName = temp[1]
        compObj = getattr(AllModels(1), compName)
        parObj = getattr(compObj, parName)

        parObj.values = fixedValues[key]

def filterOutliers(dataset):
    # Here I use Z-Score algorithm to filter out the outliers of the dataset
    # I saw that 3 sigma was commonly used for filtering outliers in this method, but since I will be filtering out nH values and we do not expect nH values to change
    # that drastically, I narrowed down the interval and set the z-score as 2 sigma.
    mean = np.mean(dataset)
    std_dev = np.std(dataset)
    threshold = 3

    filtered_dataset = []
    for i in dataset:
        if std_dev == 0 or (abs(i - mean) / std_dev <= threshold):
            filtered_dataset.append(i)
    
    return filtered_dataset

def closeAllFiles():
    print("\nClosing all files..")
    logFile.close()
    Xset.closeLog()
    AllModels.clear()
    AllData.clear()

def checkResults(bestModelList):
    for i in range(1, AllModels(1).nParameters+1):
        print(AllModels(1)(i).name, AllModels(1)(i).values[0])
    print("================")
    for key, val in bestModelList[0].items():
        print(key,val)

def clearList(listInput):
    for i in range(len(listInput)):
        listInput.pop()

def constructList(listToConstruct, sourceList):
    clearList(listToConstruct)
    listToConstruct.append({})
    listToConstruct.append({})
    for i in range(len(sourceList)):
        for key, val in sourceList[i].items():
            listToConstruct[i][key] = val

def loadModel(modelName):
    print("Loading model: " + modelName)
    m = Model(modelName)

def assignTxtParameters(parameterList):
    print()
    for tuple in parameterList:
        compName = tuple[0]
        compNum = tuple[1]
        parTuple = tuple[2]

        print("Assigning new values for parameter: " + compName + "." + parTuple[0])
        assignParameters(compName, compNum, parTuple)

def searchPremodel(bestModelList, path = ""):
    modelfile = extractModFileName()
    foundFile = False
    if path == "":
        path = outputDir + "/commonFiles"
        print("\nLooking for a model file '" + modelfile + "' under '" + path + "'")
        if Path(path + "/" + modelfile).exists():
            foundFile = True
            print("Found the spesified model file.")
            print("Extracting all the model parameters..")
            updateParameters(bestModelList)

            Xset.restore(path + "/" + modelfile)
    else:
        print("\nLooking for a model file '" + modelfile + "' under '" + path + "'")
        if Path(path + "/" + modelfile).exists():
            foundFile = True
            print("Found the spesified model file.")
            print("Extracting all the model parameters..")
            updateParameters(bestModelList)

            Xset.restore(path + "/" + modelfile)
    
    if foundFile == False:
        print("Could not find the target model file under '" + path + "'")

def saveCommand(saveType):
    print("Saving requested xcm file as type: " + saveType)
    modelName = extractModFileName()
    if saveType == "model":
        saveModel(modelName)
        saveModel(modelName, commonDirectory)
    elif saveType == "data":
        saveData()
    else:
        saveModel(modelName)
        saveModel(modelName, commonDirectory)
        saveData()

def ftestOptions(option, bestModelList, nullhypList, logfile, lastAddedModel, lastAddedModelNumber, orderSuffix, infoTxt = ""):
    if option == "nullhyp":
        print("\nSaved null hypothesis statistics\n")
        constructList(nullhypList, bestModelList)
    else:
        print("\nPerforming ftest: " + infoTxt + "\n")
        pvalue = performFtest(nullhypList, bestModelList, logFile, infoTxt)

        if abs(pvalue) >= ftestSignificance:
            print("\nFTEST: Choosing null hypothesis model")
            print("F-test significance: " + str(ftestSignificance) + ", p-value: " + str(pvalue) + "\n")

            print("Removing the model: " + str(lastAddedModelNumber) + orderSuffix + " " + lastAddedModel)
            removeComp(lastAddedModel, lastAddedModelNumber, bestModelList)
            fitModel(bestModelList)
            updateParameters(bestModelList)
        else:
            print("\nFTEST: Keeping the alternative model")
            print("F-test significance: " + str(ftestSignificance) + ", p-value: " + str(pvalue) + "\n")

def calculateComponentOrder(compName, targetName):
    modelExpression = AllModels(1).expression.replace(" ", "")
    targetIdx = modelExpression.find(targetName)
    newExpression = modelExpression[:targetIdx]
    compCount = wordCounter(newExpression, compName)

    return compCount + 1

def parseTxt(source, bestModelList, nullhypList, logFile, enableFixing):
    sourcefile = open(source, "r")
    lines = sourcefile.readlines()
    currentModel = ""
    inside_if = False
    if_evaluation = False
    lastAddedModel = ""
    lastAddedModelNumber = 0
    orderSuffix = ""

    lineCount = 0
    for line in lines:
        lineCount += 1
        line = line.strip()

        if len(line) == 0:
            continue
        
        if line[0] == "#":
            continue
        
        line = line.split(" ")
        try:
            if line[0].lower() == "model":
                if line[1] == processPipeline:
                    if currentModel == "":
                        currentModel = processPipeline
                        continue
                    else:
                        # A model pipeline has been defined before, but the current line tries to define another pipeline
                        print("ERROR: Trying to process another model pipeline, probably due to not using ENDMODEL keyword.")
                        quit()
        except:
            print("\nERROR: Invalid implementation for a pipeline name in models.txt -> Line: " + str(lineCount))
            quit()

        if currentModel != processPipeline:
            # If the current pipeline does not match
            continue
            
        if line[0].lower() == "endmodel":
            # End of model pipeline
            return True
        
        if inside_if:
            if line[0] == "endif":
                inside_if = False
                continue
            else:
                if if_evaluation == False:
                    continue

        try:
            if line[0] == "load":
                modelName = ""
                for par in line[1:]:
                    modelName += par

                loadModel(modelName)
                continue
        except:
            print("\nERROR: Invalid implementation of 'load' command in models.txt -> Line: " + str(lineCount))
            quit()
          
        try:
            if line[0] == "assign":
                if line[1] == "-last":
                    parameterList = []
                    for eachPar in line[2:]:
                        temp = eachPar.split(":")
                        compName = temp[0].split(".")[0]
                        parName = temp[0].split(".")[1]
                        parValue = temp[1]

                        parameterList.append((compName, lastAddedModelNumber, (parName, parValue)))
                        
                    assignTxtParameters(parameterList)

                    continue
                else:
                    parameterList = []
                    for eachPar in line[1:]:
                        if eachPar[0] == "(":
                            bracketIdx = eachPar.find(")")
                            compNum = int(eachPar[1:bracketIdx])

                            temp = eachPar.split(":")
                            fullName = temp[0][bracketIdx+1:]
                            compName = fullName.split(".")[0]
                            parName = fullName.split(".")[1]
                            parValue = temp[1]

                            parameterList.append((compName, compNum, (parName, parValue)))
                        else:
                            compNum = 1
                            temp = eachPar.split(":")
                            compName = temp[0].split(".")[0]
                            parName = temp[0].split(".")[1]
                            parValue = temp[1]

                            parameterList.append((compName, compNum, (parName, parValue)))
                        
                    assignTxtParameters(parameterList)

                    continue

        except:
            print("\nERROR: Invalid implementation of 'assign' command in models.txt -> Line: " + str(lineCount))
            quit()
        
        try:
            if line[0] == "search" and line[1] == "premodel":
                if len(line) > 2:
                    modelString = ""
                    for i in line[2:]:
                        modelString += i
                    if modelString[-1] == "/":
                        modelString = modelString[:-1]
                
                    searchPremodel(bestModelList, modelString)
                else:
                    searchPremodel(bestModelList)

                continue
        except:
            print("\nERROR: Invalid implementation of 'search' command in models.txt -> Line: " + str(lineCount))
            quit()               
        
        try:
            if line[0] == "fit":
                fitModel(bestModelList)
                continue
        except:
            print("\nERROR: Invalid implementation of 'fit' command in models.txt -> Line: " + str(lineCount))
            quit()
        
        try:
            if line[0] == "save":
                if line[1] == "model":
                    saveCommand("model")
                elif line[1] == "data":
                    saveCommand("data")
                else:
                    print("ERROR: Invalid parameter for the 'save' command")
                    quit()

                continue
        except:
            print("\nERROR: Invalid implementation of 'save' command in models.txt -> Line: " + str(lineCount))
            quit()
        
        try:
            if line[0] == "ftest":
                if line[1] == "nullhyp" or line[1] == "null" or line[0] == "nullhypothesis":
                    ftestOptions("nullhyp", bestModelList, nullhypList, logFile, lastAddedModel, lastAddedModelNumber, orderSuffix)
                    continue

                elif line[1] == "perform":
                    if lastAddedModel == "":
                        print("ERROR: You must use addcomp to add models before using f-test")
                        quit()
                        
                    if len(line) > 2:
                        newStr = " ".join(line[2:])
                        if (newStr[0] != "\"" and newStr[0] != "'") or (newStr[-1] != "\"" and newStr[-1] != "'") or (newStr[0] != newStr[-1]):
                            print("ERROR: Invalid parameter entry for 'ftest' command")
                            quit()
                        else:
                            newStr = newStr[1:-1]
                            ftestOptions("perform", bestModelList, nullhypList, logFile, lastAddedModel, lastAddedModelNumber, orderSuffix, newStr)

                            lastAddedModelNumber = 0
                            lastAddedModel = ""
                            continue

                    ftestOptions("perform", bestModelList, nullhypList, logFile, lastAddedModel, lastAddedModelNumber, orderSuffix)

                    lastAddedModelNumber = 0
                    lastAddedModel = ""
                    continue
                else:
                    print("\nERROR: Cannot process anything related to ftest unless a model is defined first.")
                    quit()

        except:
            print("\nERROR: Invalid implementation of 'ftest' command in models.txt -> Line: " + str(lineCount))
            quit()
        
        try:
            if line[0] == "addcomp" or line[0] == "addc":
                if len(line) == 6:
                    if line[5] == "-wrap":
                        # addcomp edge after TBabs *
                        lastAddedModel = line[1]
                        lastAddedModelNumber = calculateComponentOrder(line[1], line[3])
                        addComp(line[1], line[3], line[2], line[4], bestModelList, True)
                        
                        if lastAddedModelNumber == 1:
                            orderSuffix = "st"
                        elif lastAddedModelNumber == 2:
                            orderSuffix = "nd"
                        elif lastAddedModelNumber == 3:
                            orderSuffix = "rd"
                        else:
                            orderSuffix = "th"
                        continue
                    else:
                        print("ERROR: Invalid input for the the optional 'wrap' parameter.")
                        quit()

                elif len(line) > 6:
                    print("ERROR: addcomp function takes 6 parameters at maximum, more than 6 inputs were given.")
                    quit()
                
                lastAddedModel = line[1]
                lastAddedModelNumber = calculateComponentOrder(line[1], line[3])
                addComp(line[1], line[3], line[2], line[4], bestModelList)

                if lastAddedModelNumber == 1:
                    orderSuffix = "st"
                elif lastAddedModelNumber == 2:
                    orderSuffix = "nd"
                elif lastAddedModelNumber == 3:
                    orderSuffix = "rd"
                else:
                    orderSuffix = "th"
                continue
        except:
            print("\nERROR: Invalid implementation of 'addcomp' command in models.txt -> Line: " + str(lineCount))
            quit()
        
        try:
            if line[0] == "if":
                inside_if = True

                fullName = line[1].split(".")
                compObj = getattr(AllModels(1), fullName[0])
                parName = fullName[1]
                parObj = getattr(compObj, parName)
                parValue = parObj.values[0]

                lhs = float(parValue)
                rhs = float(line[3])
                actualOperator = operator_mapping.get(line[2])

                result = actualOperator(lhs, rhs)
                if result:
                    if_evaluation = True
                else:
                    if_evaluation = False
                continue
        except:
            print("\nERROR: Invalid implementation of 'if' command in models.txt -> Line: " + str(lineCount))
            quit()
        
        try:
            if line[0] == "delc" or line[0] == "delcomp":
                if line[1][0] == "(":
                    closingIdx = int(line[1].find(")"))
                    compNum = line[1][1:closingIdx]

                    removeComp(line[1][closingIdx +1:], int(compNum), bestModelList)
                    continue

                removeComp(line[1], 1, bestModelList)
                continue
        except:
            print("\nERROR: Invalid implementation of 'delcomp' command in models.txt -> Line: " + str(lineCount))
            quit()
        
        try:
            if line[0] == "setpoint":
                if line[1] == "fix":
                    if enableFixing[0]:
                        print("\nAll parameters spesified by 'fixParameters' have now been fixed.")
                        fixAllParameters(fixedValues)
                        continue
                    else:
                        continue
        except:
            print("\nERROR: Invalid implementation of 'setpoint' command in models.txt -> Line: " + str(lineCount))
            quit()
        
        try:
            if line[0] == "shakefit":
                shakefit(bestModelList, logFile)
        except:
            print("\nERROR: Invalid implementation of 'shakefit' command in models.txt -> Line: " + str(lineCount))
            quit()

        
        while (True):
            print("\nUndefined command in current line: '" + " ".join(line) + "' (Line "+ str(lineCount) +")")
            userInput = input("The line will not be executed. Would you like to continue executing the script ? (y/n): ")
            print()
            if userInput.lower() == "n":
                print("Terminating the script..")
                quit()
            elif userInput.lower() == "y":
                print("Continuing to the script..")
                break
    
    return False

#===================================================================================================================
energyLimits = energyFilter.split(" ")
Emin = energyLimits[0]
Emax = energyLimits[1]

allDir = os.listdir(outputDir)
commonDirectory = outputDir + "/commonFiles"   # ~/NICER/analysis/commonFiles

# Initializing required variables/dictionaries in case fixParameters is set to True.
fixedValues = {}
takeAverages = False
startFixingParameters = [False]
if fixParameters:
    takeAverages = True

# If both restartOnce and restartAlways are set to True, set restartAlways to False.
if restartOnce:
    restartAlways = False

# Switch on/off chatter
if chatterOn == False:
    print("Chatter has been disabled.\n") 
    Xset.chatter = 0

# Set the correct path for the pipelineFile
pipelineFile = scriptDir + "/" + pipelineFile

searchedObsid = []
with open(scriptDir + "/" + inputTxtFile, "r") as file:
    allLines = file.readlines()
    for line in allLines:
        line = line.replace(" ", "")
        line = line.strip("\n")
        if line != "" and Path(line).exists():
            if line[-1] != "/":
                slashIdx = line.rfind("/")
                obsid = line[slashIdx+1 :]
            else:
                slashIdx = line[:-1].rfind("/")
                obsid = line[slashIdx+1:-1]
            
            searchedObsid.append(obsid)

if len(searchedObsid) == 0:
    print("\nCould not find any valid observation path, as given in the obs.txt file.")
    quit()

iterationMax = 0
searchedObservations = []
if Path(commonDirectory + "/filtered_directories.txt").exists() == False:
    print("\nERROR: Could not find 'filtered_directories.txt' file under the 'commonFiles' directory.")
    print("Please make sure both the 'commonFiles' directory and the 'filtered_directories.txt' files exist and are constructed as intended by nicer_create.py.\n")
    quit()
else:
    with open(commonDirectory + "/filtered_directories.txt", "r") as filteredFile:
        allLines = filteredFile.readlines()
        for eachObsid in searchedObsid:
            for line in allLines:
                line = line.strip("\n")
                lineElements = line.split(" ")

                if lineElements[1] == eachObsid:
                    iterationMax += 1
                    searchedObservations.append((lineElements[0], lineElements[1], lineElements[2]))

if len(searchedObservations) == 0:
    print("\nCould not find the searched observation paths in 'filtered_directories.txt', most likely due to having low exposure.")
    quit()

if iterationMax > sampleSize:
    iterationMax = sampleSize

for x in range(2):
    iteration = 0
    for path, obsid, exposure in searchedObservations:
        iteration += 1

        print("=============================================================================================")
        print("Starting the fitting procedure for observation:", obsid)
        if startFixingParameters[0]:
            print("Fixing nH parameters: TRUE\n")
        else:
            print("Fixing nH parameters: FALSE\n")

        outObsDir = path
        os.chdir(outObsDir)
        allFiles = os.listdir(outObsDir)

        # Find the spectrum, background, arf and response files
        foundSpectrum = False
        foundBackground = False
        foundArf = False
        foundRmf = False
        missingFiles = True

        if Path("ni"+obsid+"mpu7_sr3c50.pha").exists():
            spectrumFile = "ni"+obsid+"mpu7_sr3c50.pha"
            foundSpectrum = True

        if Path("ni" + obsid + "mpu7_bg3c50.pha").exists():
            backgroundFile = "ni" + obsid + "mpu7_bg3c50.pha"
            foundBackground = True

        if Path("ni" + obsid + "mpu73c50.arf").exists():
            arfFile = "ni" + obsid + "mpu73c50.arf"
            foundArf = True

        if Path("ni" + obsid + "mpu73c50.rmf").exists():
            rmfFile = "ni" + obsid + "mpu73c50.rmf"
            foundRmf= True

        if foundSpectrum and foundBackground and foundArf and foundRmf:
            # All necessary files have been found
            missingFiles = False
        
        # Check if there are any missing files
        if missingFiles:
            f = open(resultsFile, "w")
            print("ERROR: Necessary files for spectral fitting are missing for the observation: " + obsid)
            f.write("ERROR: Necessary files for spectral fitting are missing for the observation: " + obsid + "\n")
            if foundSpectrum == False:
                print("Missing spectrum file")
                f.write("Missing spectrum file\n")
            if foundBackground == False:
                print("Missing background file")
                f.write("Missing background file\n")
            if foundArf == False:
                print("Missing arf file")
                f.write("Missing arf file\n")
            if foundRmf == False:
                print("Missing rmf file")
                f.write("Missing spectrum file\n")
            f.close()
            continue
        
        print("All the necessary spectral files are found. Please check if the correct files are in use.")
        print("Spectrum file:", spectrumFile)
        print("Background file:", backgroundFile)
        print("Arf file:", arfFile)
        print("Rmf file:", rmfFile, "\n")

        if restartOnce and iteration == 1:
            print("Removing all model files under '" + commonDirectory + "'\n")
            os.system("rm " + commonDirectory + "/mod*")
        elif restartAlways:
            print("Removing all model files under '" + commonDirectory + "'\n")
            os.system("rm " + commonDirectory + "/mod*")

        #-------------------------------------------------------------------------------------    
        # From now on, PyXspec will be utilized for fitting and comparing models
        
        # Set some Xspec settings
        logFile = open(resultsFile, "w")
        Xset.openLog("xspec_output.log")
        Xset.abund = "wilm"
        Fit.query = "no"

        logFile.write("OBSERVATION ID: " + obsid + "\n\n")

        # Load the necessary files
        s1 = Spectrum(dataFile=spectrumFile, arfFile=arfFile, respFile=rmfFile, backFile=backgroundFile)
        Plot.xAxis = "keV"
        AllData.ignore("bad")
        AllData(1).ignore("**-" + Emin + " " + Emax +"-**")
        saveData()
        
        # Lists that will store parameter values throughout the script
        bestModel = [{}, {}]
        nullhypList = [{}, {}]
        
        # Parse the txt file and start processing the commands within
        foundTargetModel = parseTxt(pipelineFile, bestModel, nullhypList, logFile, startFixingParameters)

        if foundTargetModel == False:
            print("\nModel pipeline identifier '" + processPipeline + "' could not be found.")
            quit()
        
        #========================================================================================================================================
        # Start recording nH values if fixParameters is set to True.
        if iteration < iterationMax and takeAverages:
            for eachPar in parametersToFix:
                fullName = eachPar
                eachPar = eachPar.split(".")
                compName = eachPar[0]
                parName = eachPar[1]
                if compName in AllModels(1).expression:
                    compObj = getattr(AllModels(1), compName)
                    parObj = getattr(compObj, parName)
                    parVal = parObj.values[0]

                    valueExposurePair = str(parVal) + "," + str(exposure)
                    if fullName not in fixedValues:
                        fixedValues[fullName] = [valueExposurePair]
                    else:
                        fixedValues[fullName].append(valueExposurePair)
                else:
                    print("\n" + compName + " is not included in the model expression for observation " + obsid)
                    print("There will not be any value added to the sample for calculating parameter average for " + fullName)
                    continue
                    
            writeBestFittingModel(logFile)

            modFileName = extractModFileName()
            # Remove any pre-existing best model files and save a new one
            for eachFile in allFiles:
                if "best_" in eachFile:
                    os.system("rm " + eachFile)

            saveModel("best_" + modFileName)
            closeAllFiles()

            print("Parameters from observation '" + obsid + "' have been saved.")
            continue

        elif iteration >= iterationMax and takeAverages:
            for eachPar in parametersToFix:
                fullName = eachPar
                eachPar = eachPar.split(".")
                compName = eachPar[0]
                parName = eachPar[1]
                if compName in AllModels(1).expression:
                    compObj = getattr(AllModels(1), compName)
                    parObj = getattr(compObj, parName)
                    parVal = parObj.values[0]

                    valueExposurePair = str(parVal) + "," + str(exposure)
                    if fullName not in fixedValues:
                        fixedValues[fullName] = [valueExposurePair]
                    else:
                        fixedValues[fullName].append(valueExposurePair)
                else:
                    print("\n" + compName + " is not included in the model expression for observation " + obsid)
                    print("There will not be any value added to the sample for calculating parameter average for " + fullName)
                    continue
            
            print("Parameters from observation '" + obsid + "' have been saved.")
            print("=============================================================================================")
            print("Collecting the sample for calculating parameter averages is now finished.")
            print("Values from three observations with longest exposures will be used for fixing the target parameters.\n")
            print()

            startFixingParameters.pop()
            startFixingParameters.append(True)
            takeAverages = False

            for eachPar in parametersToFix:
                fullName = eachPar
                eachPar = eachPar.split(".")
                compName = eachPar[0]
                parName = eachPar[1]
                if compName in AllModels(1).expression:
                    compObj = getattr(AllModels(1), compName)
                    parObj = getattr(compObj, parName)
                    parVal = parObj.values[0]
                    
                    parPairs = {}
                    for pair in fixedValues[fullName]:
                        parValue = float(pair.split(",")[0])
                        expoValue = float(pair.split(",")[1])
                        if expoValue in parPairs:
                            parPairs[expoValue].append(parValue)
                        else:
                            parPairs[expoValue] = [parValue]
                    
                    sortedPairs = {key: parPairs[key] for key in sorted(parPairs, reverse=True)}

                    countPar = 0
                    totalParValue = 0

                    try:
                        print("Taking the average of " + fullName + " values:")
                        keyList = list(sortedPairs.keys())
                        valueList = list(sortedPairs.values())
                        for i in range(3):
                            for j in range(len(valueList[i])):
                                print(fullName + " value:", valueList[i][j], "from an observation with exposure:", keyList[i])
                                totalParValue += valueList[i][j]
                                countPar += 1
                    except:
                        print("\nWARNING: Average " + fullName + " values will be calculated using data from less than 3 observations.\n")
                    
                    avgPar = totalParValue / countPar
                    fixedValues[fullName] = str(avgPar) + " -1"
                    print(fullName + " has been fixed to the value:", avgPar, "\n")
                else:
                    print("\n" + compName + " is not in the current model expression.")
                    print("There will not be any parameter fixing applied for this model.")

            # Close all log files
            writeBestFittingModel(logFile)

            modFileName = extractModFileName()
            # Remove any pre-existing best model files and save a new one
            for eachFile in allFiles:
                if "best_" in eachFile:
                    os.system("rm " + eachFile)

            saveModel("best_" + modFileName)
            closeAllFiles()

            print("=============================================================================================\n")
            break

        #========================================================================================================================================
        # Calculate uncertainity boundaries
        if errorCalculations:
            shakefit(bestModel, logFile)

        # Save the last model
        print("Writing the best model parameters to " + resultsFile + "...")
        modFileName = extractModFileName()
        writeBestFittingModel(logFile)

        print("Saving the best model xspec file...\n")
        saveModel(modFileName)
        saveModel(modFileName, commonDirectory)
        #==========================================================================
        if errorCalculations:
            # Initialize the strings that will be used as seperate lines for parameter file
            parLines = []
            parLines.append("Parameter name | Parameter Value | Parameter Uncertainity Lower Boundary | Parameter Uncertainity Upper Boundary\n")
            
            # Save parameter information to parLines
            for comp in AllModels(1).componentNames:
                compObj = getattr(AllModels(1), comp)
                for par in compObj.parameterNames:
                    parObj = getattr(compObj, par)
                    parName = parObj.name
                    parValue = parObj.values[0]
                    index = parObj.index
                    fullName = comp + "." + parName

                    if fullName in parametersForShakefit:
                        errorResult = AllModels(1)(index).error
                        errorString = errorResult[2]
                        
                        lowerBound = errorResult[0]
                        upperBound = errorResult[1]
                        if lowerBound == 0:
                            lowerBound = parValue
                        
                        if upperBound == 0:
                            upperBound = parValue

                        if parametersForShakefit[fullName] == "X":
                            parUnit = fullName
                        else:
                            unit = ""
                            for char in parametersForShakefit[fullName]:
                                if char == " ":
                                    unit += "_"
                                else:
                                    unit += char

                            parUnit = unit
                        parLines.append(parUnit + " " + str(parValue) + " " + str(lowerBound) + " " + str(upperBound) +"\n")
            
            # Create parameter files that will be used by nicer_plot for creating parameter graphs
            outputParameterFile = outObsDir + "/parameters_bestmodel.txt"
            print("Creating", outputParameterFile, "file that will carry the necessary data for creating parameter graphs...\n")

            # Create a temporary parameter file that will carry parameter values along with error boundaries
            if Path(outputParameterFile).exists():
                os.system("rm " + outputParameterFile)
            os.system("touch " + outputParameterFile)

            # Write the parameter information from list to the parameter file
            parFile = open(outputParameterFile, "w")
            for line in parLines:
                parFile.write(line)
            parFile.close()
        #===========================================================================
        # Remove any pre-existing best model files and save a new one
        for eachFile in allFiles:
            if "best_" in eachFile:
                os.system("rm " + eachFile)
        saveModel("best_" + modFileName)

        if calculateGaussEquivalentWidth:
            # Calculate and write equivalent widths of gausses to log file
            print("Calculating equivalence widths for gaussians in model expression...\n")
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

    if fixParameters == False:
        # The whole fitting process is looped twice for refitting purposes. If fixing nH option is False, do not try to refit
        break
    else:
        if x == 0:
            print("Restarting the fitting procedure for all observations by fixing the nH parameters...\n")

os.chdir(scriptDir)

# This file is created after importing variables from another python file
if Path(scriptDir + "/__pycache__").exists():
    os.system("rm -rf "+scriptDir+"/__pycache__")