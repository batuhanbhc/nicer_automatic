# This is an automatic NICER script for calculating the fluxes of the Xspec models previously fitted by nicer_fit.py
# Authors: Batuhan Bahçeci
# Contact: batuhan.bahceci@sabanciuniv.edu

from parameter import *

print("==============================================================================")
print("\t\t\tRunning the file: " + fluxScript + "\n")

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

#========================================================= Input Checks ============================================================
# Input check for outputDir
if Path(outputDir).exists() == False:
    print("Directory defined by outputDir could not be found. Terminating the script...")
    quit()

# Input check for writeParValuesAfterCflux
if isinstance(writeParValuesAfterCflux, bool) == False:
    while True:
        print("\nThe 'writeParValuesAfterCflux' variable is not of type boolean.")
        writeParValuesAfterCflux = input("Please enter a boolean value for 'writeParValuesAfterCflux' (True/False): ")

        if writeParValuesAfterCflux == "True" or writeParValuesAfterCflux == "False":
            writeParValuesAfterCflux = bool(writeParValuesAfterCflux)
            break

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
    checkFullName = False
    components = AllModels(1).componentNames
    for comp in components:
        if comp == "cflux":
            checkFullName = True

        compObj = getattr(AllModels(1), comp)
        parameters = compObj.parameterNames
        for par in parameters:
            parObj = getattr(compObj, par)
            fullName = comp + "." + par

            if checkFullName and "_" in comp:
                compNum = comp[comp.find("_") + 1:]
                newComp = comp[:comp.find("_") + 1] + str(int(compNum) - 1)
                fullName = newComp + "." + par

            if fullName in parList:
                parObj.values = parList[fullName]
    
    if fluxPars != {}:
        compObj = AllModels(1).cflux
        for key, val in fluxPars.items():
            parObj = getattr(compObj, key)
            parObj.values = val

def fitModel():
    Fit.nIterations = 100
    Fit.delta = 0.01
    Fit.renorm()
    Fit.perform()

def updateParameters(parList):
    # Save the parameters loaded in the xspec model to lists
    for comp in AllModels(1).componentNames:
        compObj = getattr(AllModels(1), comp)
        parameters = compObj.parameterNames
        for par in parameters:
            parObj = getattr(compObj, par)
            fullName = comp + "." + par
            parList[fullName] = parObj.values

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
                parObj.frozen = True

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
            lowerFlux = 10**AllModels(1)(i).error[0]
            upperFlux = 10**AllModels(1)(i).error[1]

            flux /= (10**-9)
            lowerFlux /= (10**-9)
            upperFlux /= (10**-9)
            return [flux, lowerFlux, upperFlux]

def calculateFlux(component, modelName):
    if component == "unabsorbed":
        if modelName.find("(") == 0:
            newName = "cflux" + modelName
        else:
            newName = modelName[: modelName.find("(")] + "*cflux" + modelName[modelName.find("("):]
        
    else:
        compIndex = modelName.find(component)
        newName = modelName[:compIndex] + "cflux*" + modelName[compIndex:]

    m = Model(newName)

    enterParameters(parameters, {"Emin":Emin, "Emax":Emax})
    freezeNorm()
    fitModel()

    fluxVals = findFlux()
    
    return fluxVals

def writeParsAfterFlux():
    for comp in AllModels(1).componentNames:
        compObj = getattr(AllModels(1), comp)
        for par in compObj.parameterNames:
            parObj = getattr(compObj, par)
            fullName = comp + "." + par
            file.write(fullName + "     " + str(parObj.values[0]) + "\n")
    
    file.write("\n")
#===================================================================================================================
energyLimits = energyFilter.split(" ")
Emin = energyLimits[0]
Emax = energyLimits[1]

commonDirectory = outputDir + "/commonFiles"   # ~/NICER/analysis/commonFiles

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

if chatterOn == False:
    Xset.chatter = 0

# Start calculating fluxes for each valid observation
for path, obsid, expo in searchedObservations:
    print("====================================================================")
    print("Calculating fluxes for observation:", obsid, "\n")

    outObsDir = path
    os.chdir(outObsDir)
    allFiles = os.listdir(outObsDir)

    # Find the data file and the best fitting model file for the current observation
    missingFiles = True
    foundModfile = False
    foundDatafile = False
    for file in allFiles:
        if "best_" in file:
            modFile = file
            foundModfile = True
        elif "data_" in file:
            dataFile = file
            foundDatafile = True

        if foundDatafile and foundModfile:
            # All necessary files have been found
            missingFiles = False
            break

    file = open(resultsFile, "a")

    # Check if there are any missing files
    if missingFiles:
        print("ERROR: Necessary files for calculating fluxes are missing for the observation: " + obsid)
        file.write("\nERROR: Necessary files for calculating fluxes are missing for the observation: " + obsid + "\n")
        if foundModfile == False:
            print("->Missing model file")
            file.write("->Missing model file\n")
        if foundDatafile == False:
            print("->Missing data file")
            file.write("->Missing data file\n")
        file.close()
        continue
    
    print("All the necessary files for flux calculations are found. Please check if the correct files are in use.")
    print("Model file: ", modFile)
    print("Data file: ", dataFile, "\n")

    Xset.restore(dataFile)
    Xset.restore(modFile)
    Fit.query = "yes"

    parameters = {}
    updateParameters(parameters)

    file.write("\n===========================================================\n")
    file.write("Fluxes of model components (in 10^-9 ergs/cm^2/s) (90% confidence intervals)\n\n")
    modelName = AllModels(1).expression.replace(" ", "")

    for fluxModel in modelsToAddCfluxBefore:
        if fluxModel != "unabsorbed" and (fluxModel not in modelName):
            print("\nWARNING: Model '" + fluxModel + "' does not exist in current model expression.")
            print("Skipping current iteration for calculating fluxes..\n")
            continue
        elif fluxModel == "unabsorbed" and ("(" not in modelName):
            print("\nWARNING: Could not find any paranthesis in current model expression, location of adding cflux is unclear.")
            print("Skipping current iteration for calculating fluxes..\n")
            continue

        print("Adding cflux before: " + fluxModel)
        flux = calculateFlux(fluxModel, modelName)
        file.write(energyFilter +" keV " + AllModels(1).expression + "\nFlux: " + listToStr(flux) + "\n")
        if writeParValuesAfterCflux:
            writeParsAfterFlux()
        
        # Write flux values to parameter file
        parameterFile = open("parameters_bestmodel.txt", "r")
        appendFlux = True
        for line in parameterFile.readlines():
            if  fluxModel +"_flux" in line:
                appendFlux = False
                break
        parameterFile.close()

        if appendFlux:
            parameterFile = open("parameters_bestmodel.txt", "a")
            parameterFile.write(fluxModel +"_flux " + listToStr(flux)+ " (10^-9_ergs_cm^-2_s^-1)\n")
            parameterFile.close()
            print("Successfully added flux data to the parameter file.\n")
        else:
            print("There is already flux data about '" + fluxModel + "' in parameter file.\n")

    """# Absorbed flux
    print("Calculating the absorbed flux...\n")
    absFlux = calculateFlux("TBabs", modelName, -8.4)
    file.write(energyFilter +" keV "+AllModels(1).expression+"\nFlux: " + listToStr(absFlux) + "\n")
    if writeParValuesAfterCflux:
        writeParsAfterFlux()
    
    #============================================================================================================
    # Unabsorbed flux
    print("Calculating the unabsorbed flux...")
    unabsFlux = calculateFlux("unabsorbed", modelName, -7.85)
    file.write(energyFilter +" keV "+AllModels(1).expression+"\nFlux: " + listToStr(unabsFlux) + "\n")
    if writeParValuesAfterCflux:
        writeParsAfterFlux()

    # Write unabsorbed flux values to parameter file
    parameterFile = open("parameters_bestmodel.txt", "r")
    appendFlux = True
    for line in parameterFile.readlines():
        if "Unabsorbed_Flux" in line:
            appendFlux = False
            break
    parameterFile.close()

    if appendFlux:
        parameterFile = open("parameters_bestmodel.txt", "a")
        parameterFile.write("Unabsorbed_Flux " + listToStr(unabsFlux)+ " (10^-9_ergs_cm^-2_s^-1)\n")
        parameterFile.close()
        print("Successfully added unabsorbed flux data to the parameter file.\n")
    else:
        print("There is already data about unabsorbed flux in parameter file.\n")
    #============================================================================================================
    # Diskbb flux
    print("Calculating diskbb flux...")
    fluxDisk = calculateFlux("diskbb", modelName, -7.85)
    file.write(energyFilter +" keV "+AllModels(1).expression+"\nFlux: " + listToStr(fluxDisk) + "\n")
    if writeParValuesAfterCflux:
        writeParsAfterFlux()
    
    # Write diskbb flux values to parameter file
    parameterFile = open("parameters_bestmodel.txt", "r")
    appendFlux = True
    for line in parameterFile.readlines():
        if "Diskbb_Flux" in line:
            appendFlux = False
            break
    parameterFile.close()

    if appendFlux:
        parameterFile = open("parameters_bestmodel.txt", "a")
        parameterFile.write("Diskbb_Flux " + listToStr(fluxDisk)+ " (10^-9_ergs_cm^-2_s^-1)\n")
        parameterFile.close()
        print("Successfully added diskbb flux data to the parameter file.\n")
    else:
        print("There is already data about diskbb flux in parameter file.\n")
    #============================================================================================================
    if "powerlaw" in modelName:
        # Powerlaw flux
        print("Calculating powerlaw flux...")
        fluxPow = calculateFlux("powerlaw", modelName, -9)
        file.write(energyFilter +" keV "+AllModels(1).expression+"\nFlux: " + listToStr(fluxPow) + "\n")
        if writeParValuesAfterCflux:
            writeParsAfterFlux()
        
        # Write powerlaw flux values to parameter file
        parameterFile = open("parameters_bestmodel.txt", "r")
        appendFlux = True
        for line in parameterFile.readlines():
            if "Powerlaw_Flux" in line:
                appendFlux = False
                break
        parameterFile.close()

        if appendFlux:
            parameterFile = open("parameters_bestmodel.txt", "a")
            parameterFile.write("Powerlaw_Flux " + listToStr(fluxPow)+ " (10^-9_ergs_cm^-2_s^-1)\n")
            parameterFile.close()
            print("Successfully added powerlaw flux data to the parameter file.\n")
        else:
            print("There is already data about powerlaw flux in parameter file.\n")
    else:
        file.write("Powerlaw flux is 0. There is no powerlaw component in the model expression.\n")"""

    file.close()
    AllModels.clear()
    AllData.clear()

# This file is created after importing variables from another python file
if Path(scriptDir + "/__pycache__").exists():
    os.system("rm -rf "+scriptDir+"/__pycache__")