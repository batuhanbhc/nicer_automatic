# This is an automatic NICER script for creating event files

from nicer_variables import *

# Find the script's own path
scriptPath = os.path.abspath(__file__)
scriptPathRev = scriptPath[::-1]
scriptPathRev = scriptPathRev[scriptPathRev.find("/") + 1:]
scriptDir = scriptPathRev[::-1]

# Check if outputDir has been assigned to be a spesific directory or not
# If not, assign outputDir to the directory where the script is located at
if outputDir == "":
    outputDir = scriptDir

# Open the txt file located within the same directory as the script.
try:
    inputFile = open(scriptDir + "/" + inputTxtFile, "r")
except:
    print("Could not find the input txt file under " + scriptDir + ". Terminating the script...")
    quit()

obsList = []
for line in inputFile.readlines():
    line = line.strip("\n' ")
    obsList.append(line)
inputFile.close()

# Update Nicer geomagnetic data
print("Running nigeodown command.\n")
os.system("nigeodown chatter=10")
print("Nigeodown is completed.\n")

counter = 0
for obs in obsList:
    counter += 1
    if obs == "":
        print("Empty line detected in " + inputTxtFile + ": Line " + str(counter) + ".\n")
        continue

    parentDir = obs[::-1]
    obsid = parentDir[:parentDir.find("/")]
    parentDir = parentDir[parentDir.find("/")+1:]   
    
    obsid = obsid[::-1]         # e.g. 6130010120

    # Create observation directory for storing event files and etc.
    outObsDir = outputDir +"/"+ obsid      # e.g. ~/NICER/analysis/6130010120
    if Path(outObsDir).exists() == False:
        os.system("mkdir " + outObsDir)

    # Create "commonFiles" directory for storing model files and flux graphs
    commonDirectory = outputDir + "/commonFiles"   # ~/NICER/analysis/commonFiles
    if Path(commonDirectory).exists() == False:
        os.system("mkdir " + commonDirectory)

    # Create a log file to record the outputs of pipeline commands
    pipelineLog = outObsDir + "/pipeline_output.log"
    if Path(pipelineLog).exists() == False:
        os.system("touch " + pipelineLog)

    gunzipMkf = True
    fileList = os.listdir(obs+"/auxil")
    for each in fileList:
        each = each.strip("\n")
        if each == "ni" + obsid + ".mkf":
            gunzipMkf = False
            break

    if gunzipMkf:
        print("Gunzipping the mkf file prior to nicerl2.\n")
        os.system("gunzip "+obs+"/auxil/ni" + obsid + ".mkf.gz")

    # Run nicer pipeline commands
    print("==============================================================================")
    print("Starting to run pipeline commands for observation: " + obsid + "\n")
    print("Running nicerl2 pipeline command.")
    nicerl2 = "nicerl2 indir=" + obs + " clobber=yes history=yes detlist=launch,-14,-34 filtcolumns=NICERV5 niprefilter2_coltypes=base,3c50 cldir=" + outObsDir + " > " + pipelineLog
    os.system(nicerl2)
    print("Nicerl2 is completed.\n")

    print("Running nicerl3-spect pipeline command.")
    nicerl3spect = "nicerl3-spect " + outObsDir + " grouptype=optmin groupscale=10 bkgmodeltype=3c50 suffix=3c50 clobber=YES mkfile=" + obs + "/auxil/*.mkf >> " + pipelineLog
    os.system(nicerl3spect)
    print("Nicerl3-spect is completed.\n")
    
    print("Running nicerl3-lc pipeline command.")
    nicerl3lc = "nicerl3-lc " + outObsDir + " pirange=50-1000 timebin=1 suffix=_50_1000_dt0 clobber=YES mkfile=" + obs + "/auxil/*.mkf >> " + pipelineLog
    os.system(nicerl3lc)

    while (str(highResLcTimeResInPwrTwo).lstrip("-").isnumeric() == False) or (int(highResLcTimeResInPwrTwo) > 0):
        print("Please enter an integer value x <= 0 for the time resolution of high resolution light curves, or enter 'exit' to terminate the script.")
        highResLcTimeResInPwrTwo = input("Enter your input x (x<=0 / exit): ")
        if highResLcTimeResInPwrTwo == "exit":
            print("Terminating the " + createScript + ": Next scripts to be executed may crash.")
            quit()
        if highResLcTimeResInPwrTwo.lstrip("-").isnumeric() == True and int(highResLcTimeResInPwrTwo) <= 0:
            highResLcTimeResInPwrTwo = int(highResLcTimeResInPwrTwo)
            break

    if createHighResLightCurves:
        for each in highResLcPiRanges:
            each = each.replace(" ", "")
            nicerl3lc = "nicerl3-lc " + outObsDir + " pirange=" + str(each) + " timebin=" + str(2**highResLcTimeResInPwrTwo) +" suffix=_"+ str(each).replace("-", "_") + "_dt" + str(abs(highResLcTimeResInPwrTwo)).replace(".", "") + " clobber=YES mkfile=" + obs + "/auxil/*.mkf >> " + pipelineLog
            os.system(nicerl3lc)

    print("Nicerl3-lc is completed.\n")

    print("Please do not forget to check pipeline log file to detect potential issues that might have occured while creating output files.")
    print("==============================================================================")

    # Create log file for saving fit results that will be used by nicer_fit.py
    fitLog = outObsDir +"/" + resultsFile
    if Path(fitLog).exists() == False:
        os.system("touch " + fitLog)

# This file is created after importing variables from another python file
if Path(scriptDir + "/__pycache__").exists():
    os.system("rm -rf "+scriptDir+"/__pycache__")