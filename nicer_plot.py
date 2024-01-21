# This is an automatic NICER script for plotting comparison graphsof previously found parameter and flux values from multiple observations
# Authors: Batuhan Bahçeci
# Contact: batuhan.bahceci@sabanciuniv.edu

from parameter import *
from matplotlib.ticker import MultipleLocator, AutoMinorLocator

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

#===========================================================================================
# Create output directories of not created already
if Path(commonDirectory + "/results").exists() == False:
    os.system("mkdir " + commonDirectory + "/results")

if Path(commonDirectory + "/results/model_graphs").exists() == False:
    os.system("mkdir " + commonDirectory + "/results/model_graphs")

if Path(commonDirectory + "/results/flux_graphs").exists() == False:
    os.system("mkdir " + commonDirectory + "/results/flux_graphs")

if Path(commonDirectory + "/results/flux_tables").exists() == False:
    os.system("mkdir " + commonDirectory + "/results/flux_tables")

if Path(commonDirectory + "/results/model_tables").exists() == False:
    os.system("mkdir " + commonDirectory + "/results/model_tables")

if Path(commonDirectory + "/version_counter.txt").exists() == False:
    os.system("touch " + commonDirectory + "/version_counter.txt")

    temp_file = open(commonDirectory + "/version_counter.txt", "w")
    temp_file.write("CREATED BY NICER_PLOT.PY, DO NOT MODIFY, DO NOT CHANGE THE FILE PATH\n")
    temp_file.write("0\n")
    temp_file.close()
#===========================================================================================
# If clear variable is True, clear the contents of the output directories
if delete_previous_files:
    all_files = os.listdir(commonDirectory + "/results/model_graphs")
    for file in all_files:
        if "model" in file:
            os.system("rm " + commonDirectory + "/results/model_graphs/" + file)
    
    all_files = os.listdir(commonDirectory + "/results/model_tables")
    for file in all_files:
        if "model" in file:
            os.system("rm " + commonDirectory + "/results/model_tables/" + file)
    
    all_files = os.listdir(commonDirectory + "/results/flux_graphs")
    for file in all_files:
        if "flux" in file:
            os.system("rm " + commonDirectory + "/results/flux_graphs/" + file)

    all_files = os.listdir(commonDirectory + "/results/flux_tables")
    for file in all_files:
        if "flux" in file:
            os.system("rm " + commonDirectory + "/results/flux_tables/" + file)
    
    temp_file = open(commonDirectory + "/version_counter.txt", "w")
    temp_file.write("CREATED BY NICER_PLOT.PY, DO NOT MODIFY, DO NOT CHANGE THE FILE PATH\n")
    temp_file.write("0\n")
    temp_file.close()

# Check whether enable_versioning is True, update the version file and extract the current version if that is the case.
current_version = 0
if enable_versioning:
    with open(commonDirectory + "/version_counter.txt", "r") as file:
        all_lines = file.readlines()
        prev_version = int(all_lines[1].strip("\n"))
        current_version  = prev_version + 1

    with open(commonDirectory + "/version_counter.txt", "w") as file:
        file.write("CREATED BY NICER_PLOT.PY, DO NOT MODIFY, DO NOT CHANGE THE FILE PATH\n")
        file.write(str(current_version) + "\n")

# Open the input txt file, and extract the obsid numbers to a list
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

# Check whether any of the searched observations are processed, extract the necessary data if that is the case.
iterationMax = 0
searchedObservations = []
if Path(commonDirectory + "/processed_obs.txt").exists() == False:
    print("\nERROR: Could not find 'processed_obs.txt' file under the 'commonFiles' directory.")
    print("Please make sure both the 'commonFiles' directory and the 'processed_obs.txt' files exist and are constructed as intended by nicer_create.py.\n")
    quit()
else:
    with open(commonDirectory + "/processed_obs.txt", "r") as filteredFile:
        allLines = filteredFile.readlines()
        for eachObsid in searchedObsid:
            for line in allLines:
                line = line.strip("\n")
                lineElements = line.split(" ")

                if lineElements[1] == eachObsid:
                    iterationMax += 1
                    searchedObservations.append((lineElements[0], lineElements[1], lineElements[2]))

if len(searchedObservations) == 0:
    print("\nCould not find the searched observation paths in 'processed_obs.txt', most likely due to having low exposure.")
    quit()


# Iterate through each of the observation data, and extract the necessary data from the parameter files
for path, obsid, expo in searchedObservations:
    outObsDir = path
    os.chdir(outObsDir)

    allFiles = os.listdir(outObsDir)

    additional_info = ""
    if path[-3:] == "day":
        additional_info = "day"
    elif path[-5:] == "night":
        additional_info = "night"

    dict_key = str(obsid)
    if additional_info != "":
        dict_key += "_" + additional_info

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
    hdu.close()

    Xset.chatter = 0
    Xset.restore(modFile)
    
    # Initialize the values of keys as lists
    fluxValuesDict[dict_key] = []
    otherParsDict[dict_key] = []

    file = open(parFile)
    allLines = file.readlines()
    for line in allLines[1:]:
        # Extract the parameter values with associated uncertainities
        line = line.strip("\n")
        line = line.split(" ")
        for i in range(len(line)):
            line[i] = line[i].replace("_", " ")

        line[1] = float(line[1])    # Parameter value
        line[2] = line[1] - float(line[2])  # Error low
        line[3] = float(line[3]) - line[1]  # Error high

        # Check whether the parameter has a given unit in parameter file.
        try:
            test = line[4]
        except:
            line.append("")

        par_list = [line[0], line[1], line[2], line[3], line[4], date]

        if "flux" in par_list[0]:
            fluxValuesDict[dict_key].append(par_list)
        else:
            otherParsDict[dict_key].append(par_list)

otherpars_ref = 0
fluxes_ref = 0
empty_flag = True

#Find the referance point for the x-axis (date) for model parameters
if len(otherParsDict) != 0:
    empty_flag = False
    dates = []

    # Extract all dates in MJD
    for obs_list in otherParsDict.values():
        for value_list in obs_list:
            dates.append(value_list[5])

    referanceMjd = round((min(dates) - 5) / 5) * 5
    otherpars_ref = referanceMjd

    for key, obs_list in otherParsDict.items():
        for value_list in obs_list:
            value_list[5] = value_list[5] - referanceMjd


#Find the referance point for the x-axis (date) for flux values
if len(fluxValuesDict) != 0:
    empty_flag = False
    dates = []

    # Extract all dates in MJD
    for obs_list in fluxValuesDict.values():
        for value_list in obs_list:
            dates.append(value_list[5])

    referanceMjd = round((min(dates) - 5) / 5) * 5
    fluxes_ref = referanceMjd

    for key, obs_list in fluxValuesDict.items():
        for value_list in obs_list:
            value_list[5] = value_list[5] - referanceMjd

# Both flux dictionary and model dictionary are empty.
if empty_flag:
    print("\nERROR: Both dictionaries (parameter/flux) are empty. There is no data to create any graph.")
    quit()


# If otherParsDict is not empty, create the model parameter graphs and the table file
if len(otherParsDict) != 0:
    parameter_dict = {}

    # Extract the the data from each observation to parameter_dict, where each key will be parameter names whereas values will be lists of parameter values
    for obs_identifier, obs_list in otherParsDict.items():
        for value_list in obs_list:
            if value_list[0] not in parameter_dict:
                parameter_dict[value_list[0]] = [[value_list[1]], [value_list[2]], [value_list[3]], [value_list[5]], value_list[4]]
            else:
                parameter_dict[value_list[0]][0].append(value_list[1])  # Value
                parameter_dict[value_list[0]][1].append(value_list[2])  # Error low
                parameter_dict[value_list[0]][2].append(value_list[3])  # Error high
                parameter_dict[value_list[0]][3].append(value_list[5])  # Date


    fig, axs = plt.subplots(len(parameter_dict), 1, figsize=(8, 14), sharex=True)

    shared_yaxis_flag = False
    all_parameters = []
    ax_num = 0
    for par_name, par_list in parameter_dict.items():

        # Add all unique parameters to all_parameters list
        if par_name not in all_parameters:
            all_parameters.append(par_name)

        # Extract all lists necessary for graphs
        x_axis = par_list[3]
        y_axis = par_list[0]
        err_low = par_list[1]
        err_high = par_list[2]

        # Check if shared y-axis title is given
        shared_yaxis_title = par_list[4]
        if shared_yaxis_title != "":
            shared_yaxis_flag = True

        axs[ax_num].errorbar(x_axis, y_axis, yerr=[err_low, err_high], fmt='o', color='black', ecolor="black", markersize=4, capsize=0)

        axs[ax_num].tick_params(which = "both", direction="in")
        axs[ax_num].yaxis.tick_left()

        axs[ax_num].set_ylabel(par_name)
        axs[ax_num].set_xlabel(f"Time (MJD-{otherpars_ref} days)")

        ax_num += 1
    
    # Set minor ticks, also hide x-axis tick labels from all graphs except the last one
    for ax in axs:
        ax.xaxis.set_minor_locator(AutoMinorLocator())

        if ax != axs[-1]:
            ax.xaxis.set_tick_params(labelbottom=False)

    # Set the title of the figure
    fig.suptitle('Model Parameters', fontsize=20, y=0.95)

    # Set a shared y-axis title, if it is given
    if shared_yaxis_flag:
        fig.text(0.9, 0.5, shared_yaxis_title, va='center', rotation='vertical')

    plt.subplots_adjust(wspace=0, hspace=0, right=0.85)  

    # Construct the file name of the graph
    if enable_versioning:
        png_name = commonDirectory + "/results/model_graphs/model_graph_" + str(current_version) + ".png"
    else:
        png_name = commonDirectory + "/results/model_graphs/model_graph.png"

    # Delete any existing file with the same name, and create a new file
    if Path(png_name).exists():
        os.system("rm " + png_name)

    # Save the graph file
    plt.savefig(png_name)

    # Initialize the table structure with lists, where each list denotes a column 
    table_columns = []
    for i in range(len(all_parameters)*3 + 2):
        table_columns.append([])

    # Column name of the first two columns
    table_columns[0].append("Obsid")
    table_columns[1].append("MJD")

    # Column names of the rest of the columns
    start_index = 2
    for par in all_parameters:
        par = par.replace(" ", "_")
        table_columns[start_index].append(par)
        table_columns[start_index + 1].append(par + "_errlow")
        table_columns[start_index + 2].append(par + "_errhigh")
        start_index += 3

    # Create the obsid column
    for obsid in otherParsDict.keys():
        table_columns[0].append(obsid)

    # Create the date column
    for val in otherParsDict.values():
        table_columns[1].append(val[0][5] + otherpars_ref)

    # Create the rest of the columns
    start_index = 2
    for i in range(len(all_parameters)):
        # Calculate the current column index (each parameter will have three columns: value, low error, high error)
        current_index = start_index  + i*3

        # Change the parameter name from the column to match with the name format in the dictionary
        searched_par = table_columns[current_index][0].replace("_", " ")

        for key, obs_list in otherParsDict.items():
            added_par_flag = False

            for val in obs_list:

                par_name = val[0]
                if par_name == searched_par:
                    # The current parameter in the dictionary matches with the column name, extract the parameter values and set the flag to True
                    added_par_flag = True

                    table_columns[current_index].append(val[1])
                    table_columns[current_index + 1].append(val[1] - val[2])
                    table_columns[current_index + 2].append(val[1] + val[3])
                    break
            
            # If the flag has not been set to True, it means the current observation does not have the searched parameter of the column. Set values as "-"
            if added_par_flag == False:
                table_columns[current_index].append("-")
                table_columns[current_index + 1].append("-")
                table_columns[current_index + 2].append("-")

    # Set the table file name according to enable_versioning variable
    table_file_name = ""
    if enable_versioning:
        table_file_name = "model_table_" + str(current_version) + ".txt"
    else:
        table_file_name = "model_table.png"
    
    # Create the table file if it has not been already created
    if Path(commonDirectory + "/results/model_tables/" + table_file_name).exists() == False:
        os.system("touch " + commonDirectory + "/results/model_tables/" + table_file_name)
    
    # Override the table file's contents with the columns created within table_columns
    with open(commonDirectory + "/results/model_tables/" + table_file_name, "w") as file:
        for i in range(len(table_columns[0])):
            line = ""
            for each_line in table_columns:
                line += str(each_line[i]) + " "
        
            line = line[:-1]
            line += "\n"

            file.write(line)





# If fluxValuesDict is not empty, create the model parameter graphs and the table file
if len(fluxValuesDict) != 0:
    parameter_dict = {}

    # Extract the the data from each observation to parameter_dict, where each key will be parameter names whereas values will be lists of parameter values
    for obs_identifier, obs_list in fluxValuesDict.items():
        for value_list in obs_list:
            if value_list[0] not in parameter_dict:
                parameter_dict[value_list[0]] = [[value_list[1]], [value_list[2]], [value_list[3]], [value_list[5]], value_list[4]]
            else:
                parameter_dict[value_list[0]][0].append(value_list[1])  # Value
                parameter_dict[value_list[0]][1].append(value_list[2])  # Error low
                parameter_dict[value_list[0]][2].append(value_list[3])  # Error high
                parameter_dict[value_list[0]][3].append(value_list[5])  # Date


    fig, axs = plt.subplots(len(parameter_dict), 1, figsize=(8, 14), sharex=True)

    shared_yaxis_flag = False
    all_parameters = []
    ax_num = 0
    for par_name, par_list in parameter_dict.items():

        # Add all unique parameters to all_parameters list
        if par_name not in all_parameters:
            all_parameters.append(par_name)

        # Extract all lists necessary for graphs
        x_axis = par_list[3]
        y_axis = par_list[0]
        err_low = par_list[1]
        err_high = par_list[2]

        # Check if shared y-axis title is given
        shared_yaxis_title = par_list[4]
        if shared_yaxis_title != "":
            shared_yaxis_flag = True

        axs[ax_num].errorbar(x_axis, y_axis, yerr=[err_low, err_high], fmt='o', color='black', ecolor="black", markersize=4, capsize=0)

        axs[ax_num].tick_params(which = "both", direction="in")
        axs[ax_num].yaxis.tick_left()

        axs[ax_num].set_ylabel(par_name)
        axs[ax_num].set_xlabel(f"Time (MJD-{fluxes_ref} days)")

        ax_num += 1
    
    # Set minor ticks, also hide x-axis tick labels from all graphs except the last one
    for ax in axs:
        ax.xaxis.set_minor_locator(AutoMinorLocator())

        if ax != axs[-1]:
            ax.xaxis.set_tick_params(labelbottom=False)

    # Set the title of the figure
    fig.suptitle('Flux Values', fontsize=20, y=0.95)

    # Set a shared y-axis title, if it is given
    if shared_yaxis_flag:
        fig.text(0.9, 0.5, shared_yaxis_title, va='center', rotation='vertical')

    plt.subplots_adjust(wspace=0, hspace=0, right=0.85)  

    # Construct the file name of the graph
    if enable_versioning:
        png_name = commonDirectory + "/results/flux_graphs/flux_graph_" + str(current_version) + ".png"
    else:
        png_name = commonDirectory + "/results/flux_graphs/flux_graph.png"

    # Delete any existing file with the same name, and create a new file
    if Path(png_name).exists():
        os.system("rm " + png_name)

    # Save the graph file
    plt.savefig(png_name)

    # Initialize the table structure with lists, where each list denotes a column 
    table_columns = []
    for i in range(len(all_parameters)*3 + 2):
        table_columns.append([])

    # Column name of the first two columns
    table_columns[0].append("Obsid")
    table_columns[1].append("MJD")

    # Column names of the rest of the columns
    start_index = 2
    for par in all_parameters:
        par = par.replace(" ", "_")
        table_columns[start_index].append(par)
        table_columns[start_index + 1].append(par + "_errlow")
        table_columns[start_index + 2].append(par + "_errhigh")
        start_index += 3

    # Create the obsid column
    for obsid in otherParsDict.keys():
        table_columns[0].append(obsid)

    # Create the date column
    for val in otherParsDict.values():
        table_columns[1].append(val[0][5] + fluxes_ref)

    # Create the rest of the columns
    start_index = 2
    for i in range(len(all_parameters)):
        # Calculate the current column index (each parameter will have three columns: value, low error, high error)
        current_index = start_index  + i*3

        # Change the parameter name from the column to match with the name format in the dictionary
        searched_par = table_columns[current_index][0]

        for key, obs_list in fluxValuesDict.items():
            added_par_flag = False

            for val in obs_list:
                
                # Fix the parameter name to match searched parameter name format
                par_name = val[0].replace(" ", "_")

                if par_name == searched_par:
                    # The current parameter in the dictionary matches with the column name, extract the parameter values and set the flag to True
                    added_par_flag = True

                    table_columns[current_index].append(val[1])
                    table_columns[current_index + 1].append(val[1] - val[2])
                    table_columns[current_index + 2].append(val[1] + val[3])
                    break
            
            # If the flag has not been set to True, it means the current observation does not have the searched parameter of the column. Set values as "-"
            if added_par_flag == False:
                table_columns[current_index].append("-")
                table_columns[current_index + 1].append("-")
                table_columns[current_index + 2].append("-")

    # Set the table file name according to enable_versioning variable
    table_file_name = ""
    if enable_versioning:
        table_file_name = "flux_table_" + str(current_version) + ".txt"
    else:
        table_file_name = "flux_table.png"
    
    # Create the table file if it has not been already created
    if Path(commonDirectory + "/results/flux_tables/" + table_file_name).exists() == False:
        os.system("touch " + commonDirectory + "/results/flux_tables/" + table_file_name)
    
    # Override the table file's contents with the columns created within table_columns
    with open(commonDirectory + "/results/flux_tables/" + table_file_name, "w") as file:
        for i in range(len(table_columns[0])):
            line = ""
            for each_line in table_columns:
                line += str(each_line[i]) + " "
        
            line = line[:-1]
            line += "\n"

            file.write(line)