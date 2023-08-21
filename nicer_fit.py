# This is an automatic NICER script for fitting and comparing models
import subprocess
import os
from pathlib import Path
from xspec import *
import matplotlib.pyplot as plt

#===================================================================================================================================
# The location of the observation folders
outputDir = "/home/batuhanbahceci/NICER/analysis"

# Set it to True if you have made changes in models, and do not want to use any previous model files in commonDirectory
restartModels = True

# Name of the log file
resultsFile = "script_results.log"

# Critical value for F-test
ftestCrit = 0.005

# The list for models for fitting. The models will be compared using ftest within a loop.
# The structure of the list: 
# [ 1:<model name> 2:<parameter list> 3:<Fit results>  
modelList = [
    ["tbabs*diskbb", {"TBabs.nH": 8}, {}],
    ["tbabs*(diskbb+powerlaw)", {"powerlaw.PhoIndex": 2}, {}],
    ["tbabs*(diskbb+powerlaw+gauss)", {"gaussian.LineE": "6.98,1e-3,6.95,6.95,7.1,7.1", "gaussian.Sigma": "0.03,1e-3,0.001,0.001,0.1,0.1", "gaussian.norm":"-1e-3,1e-4,-1e12,-1e12,-1e-12,-1e-12"}, {}]
]

chatterOn = True

switchVphabs = True       # If powerlaw is taken out due to fitting lower energies, switchVphabs = True will replace TBabs with vphabs to look
                            # for elemental abundances. If set to False, the script will add absorption gausses to account for the low energy region phenomenologically.

refitVphabs = True         # If set to True, the script will go through all observations that have vphabs model instead of after taking out powerlaw,
                            # take vphabs parameters and calculate the weighted average value for each parameter, then refit those observations with
                            # new parameters (Only works if switchVphabs = True)

makeXspecScript = True      # If set to True, the script creates an .xcm file that loads model and data files to xspec and creates a plot automatically
#===================================================================================================================================
# Functions
def shakefit(resultsFile):
    print("\nPerforming shakefit error calculations for the model: " + AllModels(1).expression + ", obsid:" + str(obsid)+ "\n")
    resultsFile.write("========== Proceeding with shakefit error calculations ==========\n")
    paramNum = AllModels(1).nParameters

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
    resultsFile.write("=================================================================\n\n")

def listToStr(array):
    result = ""
    for char in array:
        result += str(char) + " "
    result = result[:-1]
    return result

def getParsFromList(currentIndex, prevIndex):
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
 
def fitModel():
    Fit.nIterations = 100
    Fit.delta = 0.01
    Fit.perform()

def updateParameters(modelIndex):
    modelDict = modelList[modelIndex][1]
    modelStats = modelList[modelIndex][2]

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
#===================================================================================================================
# Find the script's own path
scriptPath = os.path.abspath(__file__)
scriptPathRev = scriptPath[::-1]
scriptPathRev = scriptPathRev[scriptPathRev.find("/") + 1:]
scriptDir = scriptPathRev[::-1]

allDir = os.listdir(outputDir)
commonDirectory = outputDir + "/commonFiles"   # ~/NICER/analysis/commonFiles
iteration = 0
vphabsPars = {}
vphabsObs = []
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
    Xset.openLog("xspec_output.log")
    if chatterOn == False: 
        Xset.chatter = 0
    Xset.abund = "wilm"
    Xset.seed = 2
    Fit.query = "yes"

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
        file.write("Null hypothesis model: ")
        file.write(modelList[mainIdx][0] + " - ")

        # Define the current main model
        m = Model(modelList[mainIdx][0])
        modFileName = extractModFileName()
        mainModelFile = commonDirectory + "/" + modFileName
        if Path(mainModelFile).exists():
            Xset.restore(mainModelFile)
        else:
            getParsFromList(mainIdx, prevIdx)

        fitModel()
        updateParameters(mainIdx)
        saveModel(modFileName, obsid)
        saveModel(modFileName, obsid, commonDirectory)

        file.write("Alternative model: " + modelList[alternativeIdx][0] + "\n")

        # Define the alternative model
        m = Model(modelList[alternativeIdx][0])
        modFileName = extractModFileName()
        alternativeModelFile = commonDirectory + "/" + modFileName
        if Path(alternativeModelFile).exists():
            Xset.restore(alternativeModelFile)
        else:
            getParsFromList(alternativeIdx, prevIdx)

        fitModel()
        updateParameters(alternativeIdx)
        saveModel(modFileName, obsid)
        saveModel(modFileName, obsid, commonDirectory)

        # Apply the f-test
        newChi = modelList[alternativeIdx][2]["chi"]
        newDof = modelList[alternativeIdx][2]["dof"]
        oldChi = modelList[mainIdx][2]["chi"]
        oldDof = modelList[mainIdx][2]["dof"]
        p_value = Fit.ftest(newChi, newDof, oldChi, oldDof)
        file.write("Ftest: " + str(newChi) +" | "+ str(newDof) +" | "+ str(oldChi) +" | "+ str(oldDof) +"\n\n")

        if abs(p_value) < ftestCrit:    
            # Alternative model has significantly improved the fit, set the alternative model as new main model
            mainModelFile = alternativeModelFile
            prevIdx = alternativeIdx
            mainIdx = alternativeIdx
        else:
            prevIdx = alternativeIdx
        
        alternativeIdx += 1
    
    # At the end of the loop, mainIdx will hold the best fitting model. Reload the model
    bestIdx = mainIdx
    Xset.restore(mainModelFile)
    Plot("model")
    addCompNum = Plot.nAddComps()
    
    # Check the region where the powerlaw is trying to fit, if the region is located below 2 keV, do not add powerlaw component.
    powOut = False
    if "powerlaw" in AllModels(1).expression:
        if addCompNum == 1:
            print("There must be at least one additive component in the model.")
            print("Powerlaw cannot be taken out of model expression.")
        else:
            modelName = AllModels(1).expression.replace(" ", "")
            # This part tries to find the location of the powerlaw component in the model expression by manually checking its surrounding characters
            # When it finds the powerlaw's location, it deletes it from the expression.
            try: 
                test = modelName.index("+powerlaw+")
                modelName = modelName.replace("+powerlaw+", "+", 1) 
            except:
                try: 
                    test = modelName.index("+powerlaw")
                    modelName = modelName.replace("+powerlaw", "", 1) 
                except: 
                    try: 
                        test = modelName.index("powerlaw+")
                        modelName = modelName.replace("powerlaw+", "", 1)
                    except: 
                        try: 
                            test = modelName.index("powerlaw*")
                            modelName = modelName.replace("powerlaw*", "", 1)
                        except:
                            try:
                                test = modelName.index("*powerlaw")
                                modelName = modelName.replace("*powerlaw", "", 1)
                            except:
                                print("Unknown powerlaw placement in model expression. Please revise and change the script accordingly.")
                                quit()

            m = Model(modelName)
            getParsFromList(bestIdx, bestIdx)

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
                file.write("===============================================================================\n")

                if switchVphabs:
                    modelName = AllModels(1).expression.replace("TBabs", "vphabs", 1)
                    m = Model(modelName)
                    getParsFromList(bestIdx, bestIdx)

                    AllModels(1)(8).frozen = False  # Mg
                    fitModel()
                    AllModels(1)(10).frozen = False # Si
                    fitModel()
                    AllModels(1)(11).frozen = False # S
                    fitModel()
                    AllModels(1)(5).frozen = False  # O
                    fitModel()
                    AllModels(1)(6).frozen = False  # Ne
                    fitModel()
                    AllModels(1)(16).frozen = False # Fe
                    fitModel()

                    # Saving vphabs parameter values with their weights (currently, arithmetic mean calculation)
                    comps = AllModels(1).componentNames
                    for comp in comps:
                        if comp == "vphabs":
                            compObj = getattr(AllModels(1), comp)
                            pars = compObj.parameterNames
                            for par in pars:
                                parObj = getattr(compObj, par)
                                fullName = comp + "." + par
                                if parObj.values[1] > 0:   # Non-frozen parameter
                                    val = parObj.values[0]
                                    weight = 1  # Change the weight according to your needs
                                    if fullName in vphabsPars:
                                        vphabsPars[fullName].append((val, weight))
                                    else:
                                        vphabsPars[fullName] = [(val, weight)]
                    
                    vphabsObs.append(obsid)
                else:
                    modelNamev1 =AllModels(1).expression + "+gauss+gauss"
                    modelNamev2 = AllModels(1).expression[:AllModels(1).expression.find("diskbb") + 6] + "+gauss+gauss" + AllModels(1).expression[AllModels(1).expression.find("diskbb") + 6:]
                    m = Model(modelNamev2)
                    getParsFromList(bestIdx, bestIdx)
                    gabsEnergies = ["1.55 -1", "1.8 -1"]
                    gabsCounter = 0
                    comps = AllModels(1).componentNames[::-1]
                    for comp in comps:
                        if gabsCounter < 2 and "gauss" in comp:
                            compObj = getattr(AllModels(1), comp)
                            pars = compObj.parameterNames
                            for par in pars:
                                if par == "LineE":
                                    parObj = getattr(compObj, par)
                                    parObj.values = gabsEnergies[gabsCounter]
                                    gabsCounter += 1

                    fitModel()
                    shakefit(file)
                    writeBestFittingModel(file)

    if powOut == False:
        # Restore the best-fitting model back
        Xset.restore(mainModelFile)

        modFileName = extractModFileName()
        fitModel()
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

    # Remove any existing best model files and save the new one
    for eachFile in allFiles:
        if "best_" in eachFile:
            os.system("rm " + eachFile)
    saveModel("best_" + modFileName, obsid)
    
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
        file.write("pl ld chi")
        file.close()
    
if switchVphabs and refitVphabs:
    # Calculate the weighted average of parameter values
    weightedAvg = {}
    for key,val in vphabsPars.items():
        tempSum = 0
        tempWeight = 0
        for i in val:
            tempSum += i[0]
            tempWeight += i[1]
        weightedAvg[key] = tempSum / tempWeight

    #Re-fit the observations with weighted-parameters (only the observations with vphabs component).
    for obsid in vphabsObs:
        os.chdir(outputDir + "/" + obsid)
        allFiles = os.listdir(outputDir + "/" + obsid)

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
        
        Xset.restore(modFile)
        Xset.restore(dataFile)
        file = open(resultsFile, "a")

        comps = AllModels(1).componentNames
        for comp in comps:
            compObj = getattr(AllModels(1), comp)
            pars = compObj.parameterNames
            for par in pars:
                parObj = getattr(compObj, par)
                fullName = comp + "." + par
                if fullName in weightedAvg:
                    parObj.values = weightedAvg[fullName]
                    parObj.frozen = False
        
        modFileName = extractModFileName()
        fitModel()
        file.write("\n===========================================================\n")
        file.write("Results after refitting vphabs with weighted average values")
        file.write("\n===========================================================\n")
        writeBestFittingModel(file)
        saveModel(modFileName, obsid)
        saveModel(modFileName, obsid, commonDirectory)
        
        # Remove any existing best model files and save the new one
        for eachFile in allFiles:
            if "best_" in eachFile:
                os.system("rm " + eachFile)
        saveModel("best_" + modFileName, obsid)

        file.close()
        AllModels.clear()
        AllData.clear()

        # Plot the changes in vhpabs values and save it under commonDirectory
        os.system("python3 " +scriptDir +"/nicer_vphabs.py")