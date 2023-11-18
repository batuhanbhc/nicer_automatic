# This is an automatic NICER script for plotting comparison graphsof previously found parameter and flux values from multiple observations
# Authors: Batuhan Bahçeci
# Contact: batuhan.bahceci@sabanciuniv.edu

from nicer_variables import *

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

# Check whether filtered_directories.txt exists
if Path(commonDirectory + "/filtered_directories.txt").exists() == False:
    print("\nERROR: Could not find 'filtered_directories.txt' file under the 'commonFiles' directory.")
    print("Please make sure both the 'commonFiles' directory and the 'filtered_directories.txt' file exist and are constructed as intended by nicer_create.py and nicer_fit.py.\n")
    quit()

validObservations = []
# Open filtered_directories.txt and extract all the observation paths
with open(commonDirectory + "/filtered_directories.txt", "r") as file:
    lines = file.readlines()
    
    if len(lines) == 0:
        print("\nFile 'filtered_directories.txt' is empty: Could not find any observation for calculating fluxes.\n")
        quit()

    for line in lines:
        line = line.strip().split(" ")
        path = line[0]
        obsid = line[1]
        validObservations.append((path, obsid))

if len(validObservations) == 0:
    print("Low exposure filter has discarded all observations inside filtered_directories.txt")
    print("No parameter graphs will be created..")
    quit()
else:
    print("\nMoving onto creating parameter graphs..\n")

allDates = []
for path, obsid in validObservations:
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

    Xset.chatter = 0
    Xset.restore(modFile)
    abundance = Xset.abund[:Xset.abund.find(":")]
    
    # Initialize the values of keys as lists
    fluxValuesDict[date] = []
    otherParsDict[date] = []

    file = open(parFile)
    iterator = 0
    for line in file:
        iterator += 1
        if iterator == 1:
            continue

        # Extract the parameter values with uncertainities
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

        if "Flux" in parTuple[0]:
            fluxValuesDict[date].append(parTuple)
        else:
            otherParsDict[date].append(parTuple)

#Find the referance point for the x-axis (date), and update the previously created dictionaries
referanceMjd = round((min(otherParsDict) - 10) / 5) * 5
fixedFluxDict = {}
fixedParameterDict = {}
for key, val in fluxValuesDict.items():
    fixedFluxDict[key - referanceMjd] = val
for key, val in otherParsDict.items():
    fixedParameterDict[key - referanceMjd] = val

if len(fixedParameterDict.keys()) != 0 and len(fixedFluxDict.keys()) != 0:
    # Set static x-axis ticks for all graphs
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

        plotNum = len(modelPars.keys())
        
        if plotNum == 0:
            if dictionaryCounter == 1:
                problematicGraph = "Flux values"
            else:
                problematicGraph = "Model parameters"

            print("WARNING: The script is trying to create graphs without any parameters. Skipping the following graph: " + problematicGraph + "\n")

            continue
        
        rows = plotNum
        cols = 1

        fig, axs = plt.subplots(rows, cols, figsize=(6, plotNum*2.5))
        plt.subplots_adjust(wspace=0, hspace=0)
        counter = 0

        createCommonLabel = False
        commonLabel = ""
        for key, val in modelPars.items():
            if val[4] != "":
                createCommonLabel = True
                commonLabel = val[4]
        
        if createCommonLabel:
            fig.text(0.93, 0.5, commonLabel, va='center', rotation='vertical')

        for i in range(rows):
            xAxis = list(modelPars.values())[counter][3]
            yAxis = list(modelPars.values())[counter][0]
            errorLow = list(modelPars.values())[counter][1]
            errorHigh = list(modelPars.values())[counter][2]
            parName = list(modelPars.keys())[counter]

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

        if eachDict == fixedParameterDict:
            pngFile = commonDirectory + "/model_parameters.png"
            pngPath = Path(pngFile)
            if pngPath.exists():
                subprocess.run(["rm", pngFile])

            plt.savefig(pngFile)
        else:
            pngFile = commonDirectory + "/flux_values.png"
            pngPath = Path(pngFile)
            if pngPath.exists():
                subprocess.run(["rm", pngFile])

            plt.savefig(pngFile)

    # This file is created after importing variables from another python file
    if Path(scriptDir + "/__pycache__").exists():
        os.system("rm -rf " +scriptDir+"/__pycache__")

    try:
        print("Creating the table: Flux values\n")
        unit = list(fixedFluxDict.values())[0][0][4]
        rowNum = len(list(fixedFluxDict.keys()))

        fluxTable = [["Time (MJD)", "Unabsorbed Flux\n" + unit, "Diskbb Flux\n" + unit, "Powerlaw Flux\n" + unit]]

        for key, val in fixedFluxDict.items():
            tableRow = []
            tableRow.append(float(format(key, ".1f")) + referanceMjd)
            tableRow.append(format(val[0][1], ".4f") + "\n(-" + format(val[0][2], ".4f") + "/+" + format(val[0][3], ".4f") + ")")
            tableRow.append(format(val[1][1], ".4f") + "\n(-" + format(val[1][2], ".4f") + "/+" + format(val[1][3], ".4f") + ")")
            try:
                tableRow.append(format(val[2][1], ".4f") + "\n(-" + format(val[2][2], ".4f") + "/+" + format(val[2][3], ".4f") + ")")
            except:
                tableRow.append("-")
            
            fluxTable.append(tableRow)

        fluxTable.append([" ", " ", " ", " "])
        fig, ax = plt.subplots(figsize=(12,rowNum))

        table = ax.table(cellText=fluxTable, cellLoc='center', loc='center', edges='T')
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        table.scale(1.2, 2.7)  # Adjust the size of the table

        cellSize = 4 * len(fluxTable)
        cellCounter = 0
        for key, cell in table._cells.items():
            if cellCounter > 7 and cellCounter < cellSize - 4:
                cell.set_linewidth(0)
            
            cellCounter += 1

        ax.axis('off')  # Turn off the axes

        tablePng = commonDirectory + "/flux_table.png"
        tablePath = Path(tablePng)
        if tablePath.exists():
            subprocess.run(["rm", tablePng])

        plt.savefig(tablePng)
    except:
        print("Flux data could not be found: Flux table cannot be created.\n")
else:
    print("\nCould not find any extracted set of parameters to create parameter graphs.")