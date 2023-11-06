# This is an automatic NICER script for performing spectral analysis by fitting and comparing different Xspec models
# Authors: Batuhan Bahçeci
# Contact: batuhan.bahceci@sabanciuniv.edu

from nicer_variables import *

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

# Input check for fixNH
if isinstance(fixNH, bool) == False:
    while True:
        print("\nThe 'fixNH' variable is not of type boolean.")
        fixNH = input("Please enter a boolean value for 'fixNH' (True/False): ")

        if fixNH == "True" or fixNH == "False":
            fixNH = bool(fixNH)
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
def shakefit(resultsFile):

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

    # Before proceeding with shakefit, check if powerlaw is in model expression. If so, check whether xspec error for photon index is bigger than 1 or not.
    # If bigger than 1, fix photon index to 1.8 (may change in future) and only then continue with shakefit
    if "powerlaw" in AllModels(1).expression:
        with open("xspec_output.log", "r") as testfile:
            lines = testfile.readlines()[-35:]
        
        print("Checking powerlaw xspec error value...\n")
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
                    errorValue = float(errorValue)
                    if (1 >= errorValue > 0) == False:
                        AllModels(1).powerlaw.PhoIndex.values = "1.7 -1"
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
        fitModel()
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
    modelName = " " + modelList[0] + " "
    if calcChar != "*" and calcChar != "+":
        print("\nIncorrect character for model expression. Terminating the script...\n")
        quit()

    if calcChar == "+":
        targetIdx = modelName.find(targetComp)
        if modelName[targetIdx - 1] != "(" and modelName[targetIdx + len(targetComp)] != ")":
            modelName = modelName.replace(targetComp, "(" + targetComp + ")", 1)

    modelName = modelName[1:-1]
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
                    if listIndex < len(parameterList):
                        parObj = getattr(compObj, par)
                        parObj.values = parameterList[listIndex]
                        listIndex += 1
                    else:
                        break

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

    logFile.write("\nNull hypothesis model: " + mainModelList[0] + "\nAlternative model: " + altModelList[0] +"\n")
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
    threshold = 3

    filtered_dataset = []
    for i in dataset:
        if std_dev == 0 or (abs(i - mean) / std_dev <= threshold):
            filtered_dataset.append(i)
    
    return filtered_dataset

def closeAllFiles():
    logFile.close()
    Xset.closeLog()
    AllModels.clear()
    AllData.clear()

def checkResults():
    for i in range(1, AllModels(1).nParameters+1):
        print(AllModels(1)(i).name, AllModels(1)(i).values[0])
    print("================")
    for key, val in bestModel[1].items():
        print(key,val)
    quit()
#===================================================================================================================
energyLimits = energyFilter.split(" ")
Emin = energyLimits[0]
Emax = energyLimits[1]

allDir = os.listdir(outputDir)
commonDirectory = outputDir + "/commonFiles"   # ~/NICER/analysis/commonFiles

# Open the txt file located within the same directory as the script.
try:
    inputFile = open(scriptDir + "/" + inputTxtFile, "r")
except:
    print("Could not find the input txt file under " + scriptDir + ". Terminating the script...")
    quit()
    
#Extract observation paths from nicer_obs.txt
obsList = []
for line in inputFile.readlines():
    line = line.replace(" ", "")
    line = line.strip("\n")
    if line != "" and Path(line).exists():
        obsList.append(line)
inputFile.close()

if len(obsList) == 0:
    print("ERROR: Could not find any observation directory to process.")
    quit()
    
# Find how many observations will be fitted to find an average value for nH parameters used throughout the script (If fixNH = True)
obsCount = len(obsList)
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

# If both restartOnce and restartAlways are set to True, set restartAlways to False.
if restartOnce:
    restartAlways = False

if chatterOn == False:
    print("Chatter has been disabled.\n") 
    Xset.chatter = 0

for x in range(2):
    iteration = 0
    for obs in obsList:
        iteration += 1

        #Find observation id (e.g. 6130010120)
        pathLocations = obs.split("/")
        if pathLocations[-1] == "":
            obsid = pathLocations[-2]
        else:
            obsid = pathLocations[-1]

        print("=============================================================================================")
        print("Starting the fitting procedure for observation:", obsid)
        if startFixingNH:
            print("Fixing nH parameters: TRUE\n")
        else:
            print("Fixing nH parameters: FALSE\n")

        outObsDir = outputDir + "/" + obsid
        os.chdir(outObsDir)
        allFiles = os.listdir(outObsDir)

        # Find the spectrum, background, arf and response files
        foundSpectrum = False
        foundBackground = False
        foundArf = False
        foundRmf = False
        missingFiles = True
        for file in allFiles:
            if file == ("ni" + obsid + "mpu7_sr3c50.pha"):
                spectrumFile = file
                foundSpectrum = True
            elif file == ("ni" + obsid + "mpu7_bg3c50.pha"):
                backgroundFile = file
                foundBackground = True
            elif file == ("ni" + obsid + "mpu73c50.arf"):
                arfFile = file
                foundArf = True
            elif file == ("ni" + obsid + "mpu73c50.rmf"):
                rmfFile = file
                foundRmf = True

            if foundSpectrum and foundBackground and foundArf and foundRmf:
                # All necessary files have been found
                missingFiles = False
                break
        
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

        # First, check whether the observation has long enough exposure for meaningful data
        hdu = fits.open(outObsDir + "/" + spectrumFile)
        exposure = hdu[0].header["EXPOSURE"]
        if exposure < 100:
            print("Current observation has exposure less than 100, skipping the fitting procedure for current observation. Obsid: " + obsid +", exposure: " + format(exposure, ".2f") + "\n")
            continue
        
        print("All the necessary spectral files are found. Please check if the correct files are in use.")
        print("Spectrum file:", spectrumFile)
        print("Background file:", backgroundFile)
        print("Arf file:", arfFile)
        print("Rmf file:", rmfFile, "\n")

        if restartOnce and iteration == 1:
            print("Removing all model files in '" + commonDirectory + "' for only once.\n")
            os.system("rm " + commonDirectory + "/mod*")
        elif restartAlways:
            print("Removing all model files in '" + commonDirectory + "'\n")
            os.system("rm " + commonDirectory + "/mod*")

        #-------------------------------------------------------------------------------------    
        # From now on, PyXspec will be utilized for fitting and comparing models

        # These are the energies of both emission and absorption gausses that will be tried to fit to the observation along the script.
        # If you add/delete a gauss component along the script, make sure to update this list as well.
        # The list has no significance for the fitting the gausses, this is rather to correctly name gauss components for plotting purposes
        gaussEnergyList = [1.8, 6.98, 6.7]
        
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
        
        # This list will carry the model name, model parameters and fit statistics for the best model throughout the script.
        # First element is the model name, second element is the dictionary for parameter name-value pairs, third element is the dictionary for fit statistics
        # such as chi-squared, degrees of freedom and null hypothesis probability.
        bestModel = ["TBabs*pcfabs(gaussian+diskbb)", {"diskbb.Tin": ",,0.1,0.1,2.5,2.5", "diskbb.norm:":",,0.1,0.1", "pcfabs.CvrFract":0.95}, {}]

        #=================================================================================
        # Load the first model and fit
        print("Loading the first model:", bestModel[0], "\n")
        m = Model(bestModel[0])  

        modelFile = extractModFileName()
        if Path(commonDirectory + "/" + modelFile).exists():
            Xset.restore(commonDirectory + "/" + modelFile)
        else:
            getParsFromList(bestModel)

        gaussPars_1 = ["1.8,,1.6,1.6,1.9,1.9", "0.07,,,,0.2,0.2", "0.1"]
        assignParameters("gaussian", gaussPars_1, 1)

        if startFixingNH:
            print("nH parameters has now been fixed.\n")
            fixAllNH(fixedValuesNH)
            
        fitModel()
        updateParameters(bestModel)

        saveModel(modelFile, obsid)
        saveModel(modelFile, obsid, commonDirectory)

        #===============================================================================================
        # Add an edge around 1.8 keV
        addComp("edge", "TBabs", "after", "*", bestModel)
        print("Adding edge to current model expression.\n")

        edgePars = ["1.8,,1.5,1.5,2,2", "0.2"]
        assignParameters("edge", edgePars, 1)
        
        fitModel()
        updateParameters(bestModel)

        modelFile = extractModFileName()
        saveModel(modelFile, obsid)
        saveModel(modelFile, obsid, commonDirectory)

        nullhypModelList = transferToNewList(bestModel)
        #===============================================================================================
        # Add 6.98 keV absorption gauss and fit
        addComp("gaussian", "diskbb", "before", "+", bestModel)
        print("Adding 6.98 keV absorption gauss to the current model expression.")

        gaussPars_2 = ["6.98,,6.8,6.8,7.5,7.5", "7e-2,,,,0.2,0.2", "-1e-3,,-1e12,-1e12,-1e-12,-1e-12"]
        gaussCount = wordCounter(AllModels(1).expression, "gaussian")
        assignParameters("gaussian", gaussPars_2, gaussCount)

        fitModel()
        updateParameters(bestModel)

        modelFile = extractModFileName()
        saveModel(modelFile, obsid)
        saveModel(modelFile, obsid, commonDirectory)

        altModelList = bestModel
        #===============================================================================================
        # Apply f-test and check whether last gaussian improves the fit significantly or not
        pValue = performFtest(nullhypModelList, altModelList, logFile, "    (Adding 6.98 keV absorption gauss)")
        print("Applying f-test to check the significance of 6.98 keV absorption gauss:")

        if abs(pValue) >= ftestSignificance:
            print("6.98 keV gaussian has been taken out of the model expression by the f-test:")
            print("F-test significance: " + str(ftestSignificance) + ", p-value: " + str(pValue) + "\n")
            removeComp("gaussian", gaussCount, bestModel)
            fitModel()
            updateParameters(bestModel)

            logFile.write("\n====================================================================================\n")
            logFile.write("6.98 keV gauss is taken out from the model due to not improving the fit significantly.")
            logFile.write("\n====================================================================================\n")
        else:
            print("6.98 keV gaussian has been found to be significant by f-test:")
            print("F-test significance: " + str(ftestSignificance) + ", p-value: " + str(pValue) + "\n")

        nullhypModelList = transferToNewList(bestModel)
        #===============================================================================================
        # Add 6.7 keV absorption gauss and fit
        addComp("gaussian", "diskbb", "before", "+", bestModel)
        print("Adding 6.7 keV absorption gauss to the current model expression.")

        gaussPars_3 = ["6.7,,6.4,6.4,6.8,6.8", "0.07,,,,0.2,0.2", "-1e-3, 1e-4, -1e12, -1e12, -1e-12, -1e-12"]
        gaussCount = wordCounter(AllModels(1).expression, "gaussian")
        assignParameters("gaussian", gaussPars_3, gaussCount)

        fitModel()
        updateParameters(bestModel)

        modelFile = extractModFileName()
        saveModel(modelFile, obsid)
        saveModel(modelFile, obsid, commonDirectory)

        altModelList = bestModel
        #===============================================================================================
        # Apply f-test and check whether last gaussian improves the fit significantly or not
        pValue = performFtest(nullhypModelList, altModelList, logFile, "    (adding 6.7 keV absorption gauss)")
        
        if abs(pValue) >= ftestSignificance:
            print("6.7 keV gaussian has been taken out of the model expression by the f-test:")
            print("F-test significance: " + str(ftestSignificance) + ", p-value: " + str(pValue) + "\n")
            removeComp("gaussian", gaussCount, bestModel)
            fitModel()
            updateParameters(bestModel)

            logFile.write("\n====================================================================================\n")
            logFile.write("6.7 keV gauss is taken out from the model due to not improving the fit significantly.")
            logFile.write("\n====================================================================================\n")
        else:
            print("6.7 keV gaussian has been found to be significant by f-test:")
            print("F-test significance: " + str(ftestSignificance) + ", p-value: " + str(pValue) + "\n")

        nullhypModelList = transferToNewList(bestModel)
        #===============================================================================================
        # Add powerlaw
        addComp("powerlaw", "diskbb", "after", "+", bestModel)
        print("Adding powerlaw to the current model expression.")

        powerlawPars = ["1.8,,1.2,1.2,3,3", "0.1"]
        assignParameters("powerlaw", powerlawPars, 1)

        fitModel()
        updateParameters(bestModel)

        modelFile = extractModFileName()
        saveModel(modelFile, obsid)
        saveModel(modelFile, obsid, commonDirectory)

        altModelList = bestModel
        #===============================================================================================
         # Apply f-test
        pValue = performFtest(nullhypModelList, altModelList, logFile, "    (adding powerlaw)")

        if abs(pValue) >= ftestSignificance:
            print("Powerlaw has been taken out of the model expression by the f-test:")
            print("F-test significance: " + str(ftestSignificance) + ", p-value: " + str(pValue) + "\n")
            removeComp("powerlaw", 1, bestModel)
            fitModel()
            updateParameters(bestModel)

            logFile.write("\n====================================================================================\n")
            logFile.write("Powerlaw is taken out from the model due to not improving the fit significantly.")
            logFile.write("\n====================================================================================\n\n")
        else:
            print("Powerlaw has been found to be significant by f-test:")
            print("F-test significance: " + str(ftestSignificance) + ", p-value: " + str(pValue) + "\n")

        nullhypModelList = transferToNewList(bestModel)

        if AllModels(1).edge.MaxTau.values[0] < 1e-4:
            logFile.write("Reset edge.MaxTau parameter to 0.1 for refitting due to having an extremely low value.\n\n")
            AllModels(1).edge.MaxTau.values = 0.1
            fitModel()
            updateParameters(bestModel)
        
        #========================================================================================================================================
        # Start recording nH values if fixNH is set to True.
        if iteration < iterationMax and takeAverages:
            # Save tbabs.nH and pcfabs.nH values after finding the best fitting model (before calculating errors)
            # These values will be used to calculate average nH values, which then will be used to refit all observations by fixing nH parameters  
            # Save TBabs.nH values 
            tbabsNH = AllModels(1).TBabs.nH.values[0]
            finalInput = str(tbabsNH) + "," + str(exposure)
            if "TBabs.nH" not in fixedValuesNH:
                fixedValuesNH["TBabs.nH"] = [finalInput]
            else:
                fixedValuesNH["TBabs.nH"].append(finalInput)

            # Save pcfabs.nH values
            pcfabsNH = AllModels(1).pcfabs.nH.values[0]
            finalInput = str(pcfabsNH) + "," + str(exposure)
            if "pcfabs.nH" not in fixedValuesNH:
                fixedValuesNH["pcfabs.nH"] = [finalInput]
            else:
                fixedValuesNH["pcfabs.nH"].append(finalInput)

            # Close all log files
            writeBestFittingModel(logFile)

            modFileName = extractModFileName()
            # Remove any pre-existing best model files and save a new one
            for eachFile in allFiles:
                if "best_" in eachFile:
                    os.system("rm " + eachFile)

            saveModel("best_" + modFileName, obsid)
            closeAllFiles()

            print("nH values from observation '" + obsid + "' have been saved.")
            continue

        elif iteration >= iterationMax and takeAverages:
            # The maximum sample size for calculating average nH values has been reached.
            # Terminate the first iteration of fitting observations, calculate average nH values and refit all observations again.

            # Save the nH values for calculating average one last time for the last observation
            # Save TBabs.nH values
            tbabsNH = AllModels(1).TBabs.nH.values[0]
            finalInput = str(tbabsNH) + "," + str(exposure)
            if "TBabs.nH" not in fixedValuesNH:
                fixedValuesNH["TBabs.nH"] = [finalInput]
            else:
                fixedValuesNH["TBabs.nH"].append(finalInput)

            # Save pcfabs.nH values
            pcfabsNH = AllModels(1).pcfabs.nH.values[0]
            finalInput = str(pcfabsNH) + "," + str(exposure)
            if "pcfabs.nH" not in fixedValuesNH:
                fixedValuesNH["pcfabs.nH"] = [finalInput]
            else:
                fixedValuesNH["pcfabs.nH"].append(finalInput)
            
            print("nH values from observation '" + obsid + "' have been saved.")
            print("=============================================================================================")
            print("Collecting the sample for determining the values to fix nH parameters is now finished.")
            print("Values from three observations with longest exposures will be used for fixing nH parameters.\n")

            startFixingNH = True
            takeAverages = False
            # Calculate average value for TBabs.nH from top 3 longest exposure observations
            expoNhPairs = {}
            for i in fixedValuesNH["TBabs.nH"]:
                nhValue = float(i.split(",")[0])
                expoValue = float(i.split(",")[1])
                expoNhPairs[expoValue] = nhValue
            
            sortedDict = {key: expoNhPairs[key] for key in sorted(expoNhPairs, reverse=True)}

            countNh = 0
            totalTBabsNH = 0
            try:
                print("Taking the average of nH values for TBabs model:")
                keyList = list(sortedDict.keys())
                valueList = list(sortedDict.values())
                for i in range(3):
                    print("nH value:", valueList[countNh], "from an observation with exposure:", keyList[countNh])
                    totalTBabsNH += valueList[countNh]
                    countNh += 1
            except:
                print("\nWARNING: Average nH values will be calculated using data from less than 3 observations.\n")

            avgTBabs = totalTBabsNH / countNh
            fixedValuesNH["TBabs.nH"] = str(avgTBabs) + " -1"
            print("TBabs.nH has been fixed to the value:", avgTBabs, "\n")

            # Calculate average value for pcfabs.nH from top 3 longest exposure observations
            expoNhPairs = {}
            for i in fixedValuesNH["pcfabs.nH"]:
                nhValue = float(i.split(",")[0])
                expoValue = float(i.split(",")[1])
                expoNhPairs[expoValue] = nhValue
            
            sortedDict = {key: expoNhPairs[key] for key in sorted(expoNhPairs, reverse=True)}

            countNh = 0
            totalPcfabsNH = 0

            try:
                print("Taking the average of nH values for pcfabs model:")
                keyList = list(sortedDict.keys())
                valueList = list(sortedDict.values())
                for i in range(3):
                    print("nH value:", valueList[countNh], "from an observation with exposure:", keyList[countNh])
                    totalPcfabsNH += valueList[countNh]
                    countNh += 1
            except:
                print("\nWARNING: Average nH values will be calculated using data from less than 3 observations.\n")

            avgPcfabs = totalPcfabsNH / countNh
            fixedValuesNH["pcfabs.nH"] = str(avgPcfabs) + " -1"
            print("pcfabs.nH has been fixed to the value:", avgPcfabs)

            # Close all log files5
            writeBestFittingModel(logFile)

            modFileName = extractModFileName()
            # Remove any pre-existing best model files and save a new one
            for eachFile in allFiles:
                if "best_" in eachFile:
                    os.system("rm " + eachFile)

            saveModel("best_" + modFileName, obsid)
            closeAllFiles()

            print("=============================================================================================\n")
            break
        #========================================================================================================================================
        # Calculate uncertainity boundaries
        if errorCalculations:
                shakefit(logFile)

        # Save the last model
        print("Writing the best model parameters to ", resultsFile)
        modFileName = extractModFileName()
        writeBestFittingModel(logFile)

        print("Saving the best model xspec file.\n")
        saveModel(modFileName, obsid)
        saveModel(modFileName, obsid, commonDirectory)
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
            print("Creating", outputParameterFile, "file that will carry the necessary data for creating parameter graphs.\n")

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
        saveModel("best_" + modFileName, obsid)

        if calculateGaussEquivalentWidth:
            # Calculate and write equivalent widths of gausses to log file
            print("Calculating equivalence widths for gaussians in model expression.\n")
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
    else:
        print("Restarting the fitting procedure for all observations by fixing the nH parameters.\n")

os.chdir(scriptDir)

# This file is created after importing variables from another python file
if Path(scriptDir + "/__pycache__").exists():
    os.system("rm -rf "+scriptDir+"/__pycache__")