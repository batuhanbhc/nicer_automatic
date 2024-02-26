# This is an automatic NICER script for calculating the fluxes of the Xspec models previously fitted by nicer_fit.py
# Authors: Batuhan Bahçeci
# Contact: batuhan.bahceci@sabanciuniv.edu

from parameter import *

additiveModels = {}
additiveModelList =  "agauss      c6vmekl     eqpair      nei         rnei        vraymond \
agnsed      carbatm     eqtherm     nlapec      sedov       vrnei \
agnslim     cemekl      equil       npshock     sirf        vsedov \
apec        cevmkl      expdec      nsa         slimbh      vtapec \
bapec       cflow       ezdiskbb    nsagrav     smaug       vvapec \
bbody       compLS      gadem       nsatmos     snapec      vvgnei \
bbodyrad    compPS      gaussian    nsmax       srcut       vvnei \
bexrav      compST      gnei        nsmaxg      sresc       vvnpshock \
bexriv      compTT      grad        nsx         ssa         vvpshock \
bkn2pow     compbb      grbcomp     nteea       step        vvrnei \
bknpower    compmag     grbjet      nthComp     tapec       vvsedov \
bmc         comptb      grbm        optxagn     vapec       vvtapec \
bremss      compth      hatm        optxagnf    vbremss     vvwdem \
brnei       cph         jet         pegpwrlw    vcph        vwdem \
btapec      cplinear    kerrbb      pexmon      vequil      wdem \
bvapec      cutoffpl    kerrd       pexrav      vgadem      zagauss \
bvrnei      disk        kerrdisk    pexriv      vgnei       zbbody \
bvtapec     diskbb      kyrline     plcabs      vmcflow     zbknpower \
bvvapec     diskir      laor        posm        vmeka       zbremss \
bvvrnei     diskline    laor2       powerlaw    vmekal      zcutoffpl \
bvvtapec    diskm       logpar      pshock      vnei        zgauss \
bwcycl      disko       lorentz     qsosed      vnpshock    zkerrbb \
c6mekl      diskpbb     meka        raymond     voigt       zlogpar \
c6pmekl     diskpn      mekal       redge       vpshock     zpowerlw \
c6pvmkl     eplogpar    mkcflow     refsch"

temp = additiveModelList.split(" ")
for i in temp:
    if i == "":
        pass
    else:
        additiveModels[i] = 1

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

def calculateFlux(component, modelName, parameters):
    splitOperators = r'[)(+*]'
    splittedList = re.split(splitOperators, modelName)
    addedModelIndex = 1

    if component.lower() == "unabsorbed":
        if modelName.find("(") == -1:
            counter = 0
            for eachModel in splittedList:
                if eachModel in additiveModels:
                    addedModelIndex = counter + 1
                    newName = modelName[:modelName.find(eachModel)] + "cflux*" + modelName[modelName.find(eachModel):]
                    break
                counter += 1
        else:
            temp = modelName[:modelName.find("(")]
            tempSplittedList = re.split(splitOperators, temp)
            addedModelIndex = len(tempSplittedList)

            newName = modelName[: modelName.find("(")] + "*cflux" + modelName[modelName.find("("):]

    elif component.lower() == "absorbed":
        newName = "cflux*" + modelName
        
    else:
        counter = 0
        for eachModel in splittedList:
            if eachModel.lower() == component.lower():
                addedModelIndex = counter + 1
                break
            counter+=1

        compIndex = modelName.find(component)
        newName = modelName[:compIndex] + "cflux*" + modelName[compIndex:]

    m = Model(newName)

    enterParameters(parameters, {"Emin":Emin, "Emax":Emax})
    freezeNorm()
    fitModel()

    fluxVals = findFlux()
    
    return fluxVals

def writeParsAfterFlux(line_list):
    for comp in AllModels(1).componentNames:
        compObj = getattr(AllModels(1), comp)
        for par in compObj.parameterNames:
            parObj = getattr(compObj, par)
            fullName = comp + "." + par

            line_list.append(fullName + "     " + str(parObj.values[0]) + "\n")
    
    line_list.append("\n") 

def write_lines_to_file(file_name, line_list):
    with open(file_name, "a") as file:
        for line in line_list:
            file.write(line)

#===================================================================================================================
try:
    energyLimits = energyFilter.split(" ")
    Emin = energyLimits[0]
    Emax = energyLimits[1]
except Exception as e:
    print(f"Exception occured while reading 'energyLimits' variable due to incorrect format: {e}")
    quit()

commonDirectory = outputDir + "/commonFiles"   # ~/NICER/analysis/commonFiles

searchedObsid = []
try:
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
except Exception as e:
    print(f"Exception occured while opening {inputTxtFile}: {e}")
    quit()

if len(searchedObsid) == 0:
    print("\nCould not find any valid observation path, as given in the obs.txt file.")
    quit()

iterationMax = 0
searchedObservations = []
if Path(commonDirectory + "/processed_obs.txt").exists() == False:
    print("\nCould not find 'processed_obs.txt' file under the 'commonFiles' directory.")
    print("Please make sure both the 'commonFiles' directory and the 'processed_obs.txt' files exist and are constructed as intended by nicer_create.py.\n")
    quit()
else:
    try:
        with open(commonDirectory + "/processed_obs.txt", "r") as filteredFile:
            allLines = filteredFile.readlines()
            for eachObsid in searchedObsid:
                for line in allLines:
                    line = line.strip("\n")
                    lineElements = line.split(" ")

                    if lineElements[1] == eachObsid:
                        iterationMax += 1
                        searchedObservations.append((lineElements[0], lineElements[1], lineElements[2]))
    except Exception as e:
        print(f"Exception occured while opening processed_obs.txt: {e}")
        quit()

if len(searchedObservations) == 0:
    print("\nCould not find the searched observation paths in 'processed_obs.txt', most likely due to having low exposure.")
    quit()

if chatterOn == False:
    Xset.chatter = 0

# Start calculating fluxes for each valid observation
for path, obsid, expo in searchedObservations:
    print("====================================================================")
    print("Calculating fluxes for observation:", obsid, "\n")

    outObsDir = path
    try:
        os.chdir(outObsDir)
    except Exception as e:
        print(f"Exception occured while changing directory to {outObsDir}: {e}")
        continue

    version = 0
    try:
        with open(outObsDir + "/results/version_counter.txt") as version_file:
            all_lines = version_file.readlines()
            version = int(all_lines[1].strip("\n")) - 1
    except Exception as e:
        print(f"Exception occured while reading file {outObsDir}/results/version_counter.txt: {e}")
        continue
    
    outObsDir = outObsDir + "/results/run_" + str(version)
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
    
    fit_file_loc = outObsDir + "/" + resultsFile
    fit_file_lines = []

    try:
        with open(fit_file_loc) as fit_file:
            lines = fit_file.readlines()

            for line in lines:
                if "Fluxes of model components" in line:
                    fit_file_lines = fit_file_lines[:-1]    # To exclude the "======" line before
                    break
                else:
                    fit_file_lines.append(line)
    except Exception as e:
        print(f"Exception occured while opening {fit_file_loc} for observation {obsid}: {e}")
        continue

    # Check if there are any missing files
    if missingFiles:
        print("ERROR: Necessary files for calculating fluxes are missing for the observation: " + obsid)
        fit_file_lines.append("\nERROR: Necessary files for calculating fluxes are missing for the observation: " + obsid + "\n")

        if foundModfile == False:
            print("->Missing model file")
            fit_file_lines.append("->Missing model file\n")
        if foundDatafile == False:
            print("->Missing data file")
            fit_file_lines.append("->Missing data file\n")
        
        write_lines_to_file(fit_file_loc, fit_file_lines)
        continue
    
    print("All the necessary files for flux calculations are found. Please check if the correct files are in use.")
    print("Model file: ", modFile)
    print("Data file: ", dataFile, "\n")

    try:
        Xset.restore(dataFile)
        Xset.restore(modFile)
    except Exception as e:
        print(f"Exception occured while loading data and model files to PyXspec: {e}")
        continue

    Fit.query = "yes"

    parameters = {}
    updateParameters(parameters)

    # Open the parameter file and extract all non_flux lines
    all_lines_file = {}

    try:
        par_file = open("parameters_bestmodel.txt", "r")
    except Exception as e:
        print(f"Exception occured while opening parameters_bestmodel.txt file for observation {obsid}: {e}")
        continue

    all_lines = par_file.readlines()
    par_file.close()

    for line in all_lines:
        if "flux" not in line:
            all_lines_file[line] = 1

    fit_file_lines.append("\n===========================================================\n")
    fit_file_lines.append("Fluxes of model components (in 10^-9 ergs/cm^2/s) (90% confidence intervals)\n\n")
    modelName = AllModels(1).expression.replace(" ", "")

    for fluxModel in modelsToAddCfluxBefore:
        if (fluxModel != "unabsorbed" and fluxModel != "absorbed") and (fluxModel not in modelName):
            print("\nWARNING: Model '" + fluxModel + "' does not exist in current model expression.")
            print("Skipping current iteration for calculating fluxes..\n")
            continue

        print("Calculating flux for: " + fluxModel)
        flux = calculateFlux(fluxModel, modelName, parameters)
        
        # Write flux data to 
        fit_file_lines.append(energyFilter +" keV " + AllModels(1).expression + "\nFlux: " + listToStr(flux) + "\n")
        if writeParValuesAfterCflux:
            writeParsAfterFlux(fit_file_lines)
        
        # Add new flux line to the all_lines_file
        all_lines_file[fluxModel +"_flux " + listToStr(flux)+ " (10^-9_ergs_cm^-2_s^-1)\n"] = 1
        
    # Write flux values to parameter file
    par_file = open("parameters_bestmodel.txt", "w")
    for line in all_lines_file.keys():
        par_file.write(line)
    par_file.close()

    write_lines_to_file(fit_file_loc, fit_file_lines)

    AllModels.clear()
    AllData.clear()

# This file is created after importing variables from another python file
if Path(scriptDir + "/__pycache__").exists():
    os.system("rm -rf "+scriptDir+"/__pycache__")