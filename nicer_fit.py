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
    ["tbabs*(diskbb+powerlaw+gauss)", {"gaussian.LineE": "6.95,1e-3,6.5,6.5,7.2,7.2", "gaussian.Sigma": "0.03,1e-3,0.001,0.001,0.5,0.5", "gaussian.norm":"-1e-3,1e-4,-1e12,-1e12,-1e-12,-1e-12"}, {}]
]

energyFilter = "1.5 10."    #Do not forget to put . after an integer to spesify energy (in keV) instead of channel
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
            parVal = getattr(compObj, par).values[0]
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
    #Xset.chatter = 1
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

        # Define the current main model
        m = Model(modelList[mainIdx][0])
        modFileName = extractModFileName()
        mainModelFile = commonDirectory + "/" + modFileName
        modelPath = Path(mainModelFile)
        if modelPath.exists():
            Xset.restore(mainModelFile)
        else:
            enterParameters(mainIdx, prevIdx)

        fitModel()
        updateParameters(mainIdx)
        saveModel(modFileName)
        saveModel(modFileName, commonDirectory)

        file.write("Alternative model: " + modelList[alternativeIdx][0] + "\n")

        # Define the alternative model
        m = Model(modelList[alternativeIdx][0])
        modFileName = extractModFileName()
        alternativeModelFile = commonDirectory + "/" + modFileName
        modelPath = Path(alternativeModelFile)
        if modelPath.exists():
            Xset.restore(alternativeModelFile)
        else:
            enterParameters(alternativeIdx, prevIdx)

        fitModel()
        updateParameters(alternativeIdx)
        saveModel(modFileName)
        saveModel(modFileName, commonDirectory)

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
    if "powerlaw" in AllModels(1).expression:
        if addCompNum == 1:
            print("There must be at least one additive component in the model.")
            print("Powerlaw cannot be tried to be taken out of model expression for testing its fitting region.")
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
                            modelName = modelName.replace("*powerlaw*", "", 1)
 
            m = Model(modelName)
            enterParameters(bestIdx, bestIdx)

            Plot("chi")
            residX = Plot.x()
            residY = Plot.y()

            # Group every {binSize} delta chi-sq bins, start rebinning next group with the previous group's last {shiftSize} bins (overlapping groups)
            binSize = 5; shiftSize = 3; threshold = 50
            newGroupsX = []; newGroupsY = []
            # targetX and targetY will store the groups containing values bigger than the threshold
            targetX = []; targetY = []
            tempSumX = 0; tempSumY = 0
            pointer = 0
            counter = 0
            while True:
                try:
                    counter += 1;   pointer += 1
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
                    if tempSumX != 0 and tempSumY != 0:
                        newGroupsX.append(tempSumX / counter);  newGroupsY.append(tempSumY / counter)
                        if tempSumY / binSize >= threshold:
                            targetX.append(tempSumX / counter);     targetY.append(tempSumY / counter)

                    break
            
            # Are there any region of data that is below 2 keV, and also has an average delta chi-sq value bigger than the threshold value?
            # If so, remove powerlaw component.
            result = any(value <= 2 for value in targetX)
            if result == True:
                powOut = True

                file.write("\n===============================================================================\n")
                file.write("Powerlaw has been taken out due to trying to fit lower energies (> 2 keV).\n")
                file.write("===============================================================================\n")
            else:
                powOut = False
     
    if powOut == False:
        Xset.restore(mainModelFile)

    modFileName = extractModFileName()
    #fitModel()
    #shakefit(file)
    writeBestFittingModel(file)
    saveModel(modFileName)
    saveModel(modFileName, commonDirectory)

    for eachFile in allFiles:
        # Remove any existing "best model" files
        if "best_" in eachFile:
            os.system("rm " + eachFile)

    saveModel("best_" + modFileName)

    file.close()
    Xset.closeLog()
    AllModels.clear()
    AllData.clear()
    