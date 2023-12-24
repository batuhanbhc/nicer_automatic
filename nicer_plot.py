# This is an automatic NICER script for plotting comparison graphsof previously found parameter and flux values from multiple observations
# Authors: Batuhan Bahçeci
# Contact: batuhan.bahceci@sabanciuniv.edu

from parameter import *

print("==============================================================================")
print("\t\t\tRunning the file: " + plotScript + "\n")

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

#===================================================================================================================================
# Input check for outputDir
if Path(outputDir).exists() == False:
    print("Directory defined by outputDir could not be found. Terminating the script...")
    quit()
#===================================================================================================================================

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
print("====================================================================")
print("Running the ", plotScript," file:\n")

energyLimits = energyFilter.split(" ")
Emin = energyLimits[0]
Emax = energyLimits[1]

otherParsDict = {}
fluxValuesDict = {}
commonDirectory = outputDir + "/commonFiles"   # ~/NICER/analysis/commonFiles

if Path(commonDirectory + "/results").exists() == False:
    os.system("mkdir " + commonDirectory + "/results")

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

encounteredDates = []
encounteredFluxes = []
uniqueFluxes = 0
allDates = []
for path, obsid, expo in searchedObservations:
    outObsDir = path
    os.chdir(outObsDir)

    allFiles = os.listdir(outObsDir)
    # Find the data file and the best fitting model file for the current observation
    missingFiles = True
    foundParameterfile = False
    foundModfile = False
    foundSpectrum = False
    for file in allFiles:
        if "parameters_" in file:
            parFile = file
            foundParameterfile = True
        elif "best_" in file:
            modFile = file
            foundModfile = True
        elif file == "ni" + obsid + "mpu7_sr3c50.pha":
            spectrumFile = file
            foundSpectrum = True
        
        if foundSpectrum and foundModfile and foundParameterfile:
            missingFiles = False
            break
    
    # Check if there are any missing files
    if missingFiles:
        print("\nWARNING: Necessary files for retrieving parameters and plotting are missing for observation: " + obsid)
        if foundSpectrum == False:
            print("Missing spectrum file")
        if foundModfile == False:
            print("Missing model file")
        if foundParameterfile == False:
            print("Missing parameter file")
        continue

    # Extract MJD
    hdu = fits.open(spectrumFile)
    date = float(format(hdu[1].header["MJD-OBS"], ".3f"))
    allDates.append(date)
    hdu.close()

    # NOTE: THERE IS STILL AN ISSUE HERE WHEN THERE ARE MULTIPLE OBSERVATIONS WITH THE SAME DATE. THIS NEEDS TO BE FIXED SOONER OR LATER.
    if date not in encounteredDates:
        encounteredDates.append(date)

    Xset.chatter = 0
    Xset.restore(modFile)
    abundance = Xset.abund[:Xset.abund.find(":")]
    
    # Initialize the values of keys as lists
    fluxValuesDict[date] = []
    otherParsDict[date] = []

    file = open(parFile)
    allLines = file.readlines()
    for line in allLines[1:]:
        # Extract the parameter values with associated uncertainities
        line = line.strip("\n")
        line = line.split(" ")
        for i in range(len(line)):
            line[i] = line[i].replace("_", " ")

        line[1] = float(line[1])
        line[2] = line[1] - float(line[2])
        line[3] = float(line[3]) - line[1]

        # Try to see whether the parameter has a unit associated with in in parameter file.
        try:
            test = line[4]
        except:
            line.append("")


        # If the parameter is a float number with fractional part having more than 5 digits, round the fractional part to 5 digits.
        tempList = [line[1], line[2], line[3]]
        tempCounter = 0
        for i in tempList:
            tempCounter += 1
            if i > 10**-5 and len(str(i)[str(i).find(".") +1:]) > 5:
                line[tempCounter] = float(format(i, ".5f"))

        parTuple = (line[0], line[1], line[2], line[3], line[4])

        if "flux" in parTuple[0]:
            fluxValuesDict[date].append(parTuple)
            if line[0] not in encounteredFluxes:
                encounteredFluxes.append(line[0])
                uniqueFluxes += 1
        else:
            otherParsDict[date].append(parTuple)

#Find the referance point for the x-axis (date), and update the previously created dictionaries
if len(otherParsDict) != 0:
    referanceMjd = round((min(otherParsDict) - 10) / 5) * 5
    fixedFluxDict = {}
    fixedParameterDict = {}
    for key, val in fluxValuesDict.items():
        fixedFluxDict[key - referanceMjd] = val
    for key, val in otherParsDict.items():
        fixedParameterDict[key - referanceMjd] = val
elif len(fluxValuesDict) != 0:
    referanceMjd = round((min(fluxValuesDict) - 10) / 5) * 5
    fixedFluxDict = {}
    fixedParameterDict = {}
    for key, val in fluxValuesDict.items():
        fixedFluxDict[key - referanceMjd] = val
    for key, val in otherParsDict.items():
        fixedParameterDict[key - referanceMjd] = val
else:
    print("\nERROR: Both dictionaries (parameter/flux) are empty. There is no data to create any graph.")
    quit()

if len(fixedParameterDict.keys()) != 0 or len(fixedFluxDict.keys()) != 0:
    # Set static x-axis ticks for all graphs
    if len(fixedFluxDict.keys()) != 0:
        mjdList = list(fixedFluxDict.keys())
    else:
        mjdList = list(fixedParameterDict.keys())
        
    minMjd = min(mjdList)
    maxMjd = max(mjdList)

    totalDifference = maxMjd - minMjd
        
    majorTickInterval = round((totalDifference / 5) / 5) * 5
    if majorTickInterval < 5:
        majorTickInterval = 5

    xAxisStart = round((minMjd - majorTickInterval) / majorTickInterval) * majorTickInterval
    xAxisEnd = round((maxMjd + majorTickInterval) / majorTickInterval) * majorTickInterval + 1
    xAxisTicksMajor = []
    xAxisTicksMinor = []

    for i in range(xAxisStart, xAxisEnd):
        if i % majorTickInterval == 0:
            xAxisTicksMajor.append(i)

    for i in xAxisTicksMajor:
        minorTickInterval = majorTickInterval / 5
        for k in range(1, 5):
            xAxisTicksMinor.append(i + k * minorTickInterval)

    dictionaryCounter = 0
    dictList = [fixedFluxDict, fixedParameterDict]
    print("=============================================================================================================")
    for eachDict in dictList:
        dictionaryCounter += 1

        if dictionaryCounter == 1:
            print("Plotting the graph: Flux values")
        else:
            print("Plotting the graph: Model parameters")

        modelPars = {}
        for key, val in eachDict.items():
            for tuple in val:
                if tuple[0] in modelPars:
                    modelPars[tuple[0]][0].append(tuple[1])     # Value
                    modelPars[tuple[0]][1].append(tuple[2])     # Error lower
                    modelPars[tuple[0]][2].append(tuple[3])     # Error upper
                    modelPars[tuple[0]][3].append(key)          # MJD
                else:
                    modelPars[tuple[0]] = ([tuple[1]], [tuple[2]], [tuple[3]], [key], tuple[4])

        # Number of plots should be equal to the number of observation dates
        plotNum = len(modelPars.keys())
        
        if plotNum == 0:
            if dictionaryCounter == 1:
                problematicGraph = "Flux values"
            else:
                problematicGraph = "Model parameters"

            print("WARNING: The script is trying to create a graph without any parameters. Skipping the following graph: " + problematicGraph + "\n")

            continue
        
        # Rows for the parameter table should be equal to the number of plots (+1 including the header)
        rows = plotNum
        cols = 1

        # Create a subplot for multiple graphs
        fig, axs = plt.subplots(rows, cols, figsize=(6, plotNum*2.5))
        plt.subplots_adjust(wspace=0, hspace=0)

        createCommonLabel = False
        commonLabel = ""
        for key, val in modelPars.items():
            if val[4] != "":
                createCommonLabel = True
                commonLabel = val[4]
                break
        
        if createCommonLabel:
            # Y-axis as a common label for all graphs (only if it is given inside the parameter file)
            fig.text(0.93, 0.5, commonLabel, va='center', rotation='vertical')
        
        if dictionaryCounter == 1:
            if Path(commonDirectory + "/results/flux_table.txt").exists() == False:
                os.system("touch " + commonDirectory + "/results/flux_table.txt")
            tableFile = open(commonDirectory + "/results/flux_table.txt", "w")
        else:
            if Path(commonDirectory + "/results/parameter_table.txt").exists() == False:
                os.system("touch " + commonDirectory + "/results/parameter_table.txt")
            tableFile = open(commonDirectory + "/results/parameter_table.txt", "w")
        
        # Just the number of rows for observations, header row not included
        dataRowNum = len(encounteredDates)

        # Create table structure using nested lists
        tableRows = []
        for i in range(dataRowNum + 1):
            tableRows.append([])

        # Initialize the first "column" of the table from dates of observations
        tableRows[0].append("MJD")
        idx = 1
        for eachDate in encounteredDates:
            tableRows[idx].append(str(eachDate))
            idx += 1

        counter = 0
        for i in range(rows):
            xAxis = list(modelPars.values())[counter][3]
            yAxis = list(modelPars.values())[counter][0]
            errorLow = list(modelPars.values())[counter][1]
            errorHigh = list(modelPars.values())[counter][2]
            parName = list(modelPars.keys())[counter]

            idx = 0
            tableRows[0].append(parName.replace(" ", "_"))
            for j in range(dataRowNum):
                if (encounteredDates[j] == (xAxis[idx]) + referanceMjd):
                    tableRows[j + 1].append(str(yAxis[idx]))
                    idx += 1
                else:
                    tableRows[j + 1].append("-")

            idx = 0
            tableRows[0].append(parName.replace(" ", "_")+ "_errneg")
            for j in range(dataRowNum):
                if (encounteredDates[j] == (xAxis[idx] + referanceMjd)):
                    tableRows[j + 1].append(str(errorLow[idx]))
                    idx += 1
                else:
                    tableRows[j + 1].append("-")

            idx = 0
            tableRows[0].append(parName.replace(" ", "_") + "_errpos")
            for j in range(dataRowNum):
                if (encounteredDates[j] == (xAxis[idx] + referanceMjd)):
                    tableRows[j + 1].append(str(errorHigh[idx]))
                    idx += 1
                else:
                    tableRows[j + 1].append("-")

            axs[i].errorbar(xAxis, yAxis, yerr=[errorLow, errorHigh], fmt='o', markersize=4, ecolor="black", color="black", capsize=0)
            axs[i].minorticks_on()

            axs[i].set_xticks(xAxisTicksMajor)
            axs[i].set_xticks(xAxisTicksMinor, minor = True)
            axs[i].tick_params(which = "both", direction="in")

            # If the plot is not the bottom one, hide the x-axis tick labels
            if i < rows-1:
                axs[i].xaxis.set_ticklabels([])
            else:
                axs[i].set_xlabel("Time (MJD-"+ str(referanceMjd) + " days)")

            # Rearrange major-minor y-axis ticks to prevent tick collision between subsequent graphs
            yTicksMajor = axs[i].get_yticks()
            yTicksMinor = axs[i].get_yticks(minor = True)
            minMajorTickY = min(yTicksMajor)
            maxMajorTickY = max(yTicksMajor)

            # Divide major tick gaps into 5 equal intervals
            minorInterval = (yTicksMajor[1] - yTicksMajor[0]) / 5

            newMajorList = []
            for elem in yTicksMajor:
                newMajorList.append(elem)
            
            # Check whether the lowest major y-axis tick in current tick list is truly the minimum, or is there another tick that is also lower than all y-axis values
            testList = newMajorList
            testList.remove(minMajorTickY)
            secondMinimum = min(testList)
            trueMinimum = False
            for val in yAxis:
                if val < secondMinimum:
                    trueMinimum = True
            if trueMinimum == False:
                newMajorList = testList

            # Check whether the highest major y-axis tick in current tick list is truly the maximum, or is there another tick that is also higher than all y-axis values
            testList = newMajorList
            testList.remove(maxMajorTickY)
            secondMaximum = max(testList)
            trueMaximum = False
            for val in yAxis:
                if val > secondMaximum:
                    trueMaximum = True
            if trueMaximum == False:
                newMajorList = testList
            
            # Get new minimum/maximum major y-axis ticks
            minMajorTickY = min(newMajorList)
            maxMajorTickY = max(newMajorList)

            tempList = []
            for j in range(4, 0, -1):
                tempList.append(minMajorTickY - j*minorInterval)

            for j in newMajorList:
                for k in range(1, round((newMajorList[1] - newMajorList[0]) / minorInterval) + 1):
                    tempList.append(j + minorInterval * k)

            newMinorList = tempList

            axs[i].set_ylabel(parName)
            axs[i].set_yticks(newMinorList, minor = True)
            axs[i].set_yticks(newMajorList)

            counter += 1
        
        for eachLine in tableRows:
            eachLine = " ".join(eachLine) + "\n"
            tableFile.write(eachLine)
        
        tableFile.close()

        if eachDict == fixedParameterDict:
            pngFile = commonDirectory + "/results/model_parameters.png"
            pngPath = Path(pngFile)
            if pngPath.exists():
                subprocess.run(["rm", pngFile])

            plt.savefig(pngFile)
        else:
            pngFile = commonDirectory + "/results/flux_values.png"
            pngPath = Path(pngFile)
            if pngPath.exists():
                subprocess.run(["rm", pngFile])

            plt.savefig(pngFile)

    # This file is created after importing variables from another python file
    if Path(scriptDir + "/__pycache__").exists():
        os.system("rm -rf " +scriptDir+"/__pycache__")

    # The below part will create a visual flux table, but since there is already a table in txt format, along with a graph, I might delete this part in future.
    print("\nCreating the table: Flux values")
    unit = list(fixedFluxDict.values())[0][0][4]
    rowNum = len(list(fixedFluxDict.keys()))

    #Create the table dictionary, along with the title row
    fluxTable = [["Time (MJD)"]]
    for eachFlux in encounteredFluxes:
        fluxTable[0].append(eachFlux.title())

    
    for key, val in fixedFluxDict.items():
        index = 1
        tableRow = ["-"]*(uniqueFluxes + 1)
        tableRow[0] = (float(format(key, ".1f")) + referanceMjd)

        dataIndex = 0
        for eachColumn in fluxTable[0][1:]:
            if dataIndex >= len(val):
                break
            if eachColumn == val[dataIndex][0].title():
                tableRow[index] = (format(val[dataIndex][1], ".4f") + "\n(-" + format(val[dataIndex][2], ".4f") + "/+" + format(val[dataIndex][3], ".4f") + ")")
                dataIndex += 1
            else:
                tableRow[index] = "-"
             
            index += 1

        fluxTable.append(tableRow)

    fluxTable.append([" "] * (uniqueFluxes + 1))
    fig, ax = plt.subplots(figsize=(12,rowNum))

    table = ax.table(cellText=fluxTable, cellLoc='center', loc='center', edges='T')
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 2.7)  # Adjust the size of the table

    cellSize = 4 * len(fluxTable)
    cellCounter = 0
    for key, cell in table._cells.items():
        if cellCounter > 2* (uniqueFluxes + 1) -1 and cellCounter < (len(fluxTable)*(uniqueFluxes+1) - (uniqueFluxes + 1)):
            cell.set_linewidth(0)
        
        cellCounter += 1

    ax.axis('off')  # Turn off the axes

    tablePng = commonDirectory + "/results/flux_table.png"
    tablePath = Path(tablePng)
    if tablePath.exists():
        subprocess.run(["rm", tablePng])

    plt.savefig(tablePng)

else:
    print("\nCould not find any extracted set of parameters to create parameter graphs.")