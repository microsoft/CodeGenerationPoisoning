import shutil 
import Utils 
import os  
import json  
import sys 
import re 
import yaml
from Scheduler import Scheduler  
from Engine import Engine 
from ReportReader import ReportReader  
from ReportGenerator import ReportGenerator

#The parser file is the overall wrapper for the static analyzer tool. 
#all of the classes that the progran uses is intialzied and ran in this file and this 
#is the starting point of the program is located.  
    

#This function is the startign point of the entire program  
#The workflow: parse input & initalize -> make schedule -> execute task 
#-> generate general report 
global name  
name = "" 

global verbose 
verbose = False
def start():   
    #setup/initalize 
    Utils.setup() 

    #process arugments 
    processArgs()  

    #temp src file will be set up by the time 
    #process arguments returns 
     

    #open internal file and turn it to json object 
    with open(Utils.getProjRoot() + "data/internalFile.json","r") as fp:  
            intFile = json.load(fp)    

    os.chdir(Utils.getProjRoot() + "data/temp")


    #make schedule  
    scheduler = Scheduler(intFile= intFile) 
    schedule = scheduler.makeSchedule()   
     
    #runs engine  
    engine = Engine(schedule=schedule)  
    scanSuccess = engine.run()   

    

    #generate report 
    reportReader = ReportReader(schedule=schedule,intFile=intFile) 
    reportGenerator =ReportGenerator(report =reportReader.parseReports(), name=name, verbose=verbose )
    reportGenerator.generateReports()


    


    #delete repo when processes and scans are done 
    os.chdir(Utils.getProjRoot() + "bin")  
    shutil.rmtree(Utils.getProjRoot() + "data/temp")

    return "NTI"

    
#This function is repsonsile for processing the options and arguments provided with
#the invocation call of the program. 
#essentially the function scans the argument vector for "-X" type options and their meta arguments 
#and then calls the correspondign function for the option, providign it with the meta arguments 
def processArgs():
    args = sys.argv  
    args.pop(0) 
    map = {}  
    filesProvided = False
    
    
    #create mapping between options and its list of arguments  
    currOpt = "" 
   
    for arg in args: 
        if re.match("^-",arg):  
            map[arg] = []  
            currOpt = arg 
        else: 
            map[currOpt].append(arg) 
    
    #functional cases if arguments exist; should be added onto if more options/args are beign deved  
    options = list(map) 
    for opt in options: 
        if opt == "-r":  
            if(filesProvided == True): 
                Utils.printErrorMessage("CAN'T USE BOTH REPO(-r) AND LIST(-l) OPTIONS") 
                exit(1)
            repoOptionFunc(map["-r"])  
            filesProvided = True #indicates wether or not src files were prodvided for scan 
        elif opt == "-l":  
            if(filesProvided == True): 
                Utils.printErrorMessage("CAN'T USE BOTH REPO(-r) AND LIST(-l) OPTIONS") 
                exit(1) 
            listOptionFunc(map["-l"]) 
            filesProvided = True  
        elif opt == "-xt": 
            excTypeOptionFunc(map["-xt"]) 
        elif opt == "-x":  
            excFilesOpt() 
        elif opt == "-n": 
            nameFilesOpt(map["-n"]) 
        elif opt == "-v": 
            verboseOpt()

        
    
    if filesProvided == False: 
        Utils.printErrorMessage("PLEASE PROVIDE SRC FILES USING -r OR -l")  
        exit(1)









#functions for different options and their args 
#wanted to keep the fucntions sepreate for logical organization and ease of arg extention   

#the function corresponding to the "-r" (repository) option 
#sets the program to run scans on the src files found in the repository provided 
#location is a list string arugment where index 0 contains the path to the repository intended to be scanned 
#the function makes a temp folder and copies the files from the repoitory at location into the temp folder, the temp folder 
#being what will serve as the current working directory
def repoOptionFunc(location):  
    #cloning repo provided by location  

    global name    
    name = location[0].replace("/","-")
    try: 
        shutil.copytree(location[0], Utils.getProjRoot() + "data/temp")  
    except FileNotFoundError as excp: 
        Utils.quitInError("PATH TO SRC DOSEN'T EXIST")
    except shutil.Error as excp: 
        Utils.quitInError("CHOULDN'T COPY FILES TO SCAN")

#the fucntion corresponding to the "-l" (list) option 
#sets the program to run scans on the src files indicated by the list of file paths provided 
#list is an string list arugment that has a list of paths corresponding to the files to be scaned 
#the function copies each of the indicated files into a new temp repository
def listOptionFunc(list):  
    tempDir = Utils.getProjRoot() + "data/temp"   
    global name
    name = list[0].replace("/","-")
       
    os.mkdir(tempDir)    

    for file in list:  
        fileName = file.split("/")[-1] 
        try:
            shutil.copyfile(file,tempDir + "/" + fileName)  
        except FileExistsError: 
            Utils.quitInError("A PROVIDED FILE DOES NOT EXIST") 

#the fucntion correspondingn ot the "-xt" (exclude type) option 
#sets the program to exclude the file types indicated by the arugment from the scans  
#types arugment is a list of strings. The list contain extensions which indicate the file types that should be ignored when scanning 
#the function works by remvoing each file with an extension in the arugment  from the temp diectory
def excTypeOptionFunc(types):   
    setOfExpTypes = set(types) 
    listOfExpFiles = []
    for root, dirs, files in os.walk(Utils.getProjRoot() + "data/temp"): 
        for file in files: 
            if file.split(".")[-1] in setOfExpTypes: 
                os.remove(os.path.join(root,file))   

    Utils.printNotiMessage("EXCLUDED: " + str(setOfExpTypes) + " FILE TYPES") 

#the function that corresponds to the "-x" (exclude) option 
#sets the program to exlcude the files indicated by the excludeFile.yaml file from the scan 
#works by removing files in the temp folder that are indicated on the excludeFile file
def excFilesOpt():  
    try:
        with open(Utils.getProjRoot() + "data/excludeFile.yaml", "r") as fp: 
            excList = yaml.load(fp, Loader=yaml.FullLoader)["excludeFiles"]  
    except (FileNotFoundError,yaml.YAMLERROR): 
        Utils.quitInError("ERROR PROCESSING data/excludeFile.yaml")

    for file in excList:  
        try:
            os.remove(Utils.getProjRoot() + "data/temp/" + file)  
        except FileNotFoundError: 
            Utils.printErrorMessage(file + "DOESN'T EXIST")
    Utils.printNotiMessage("EXCLUDED: " + str(excList) + " FILES") 

#option function for the "-n" (name) option 
#sets the program reports name o] 
#works by overriding name attribute that might have been set by eiher -r or -l option
def nameFilesOpt(_name):   
    global name
    name = _name[0] 

def verboseOpt(): 
    global verbose 
    verbose = True

    
    
    

      


#start the program 
if __name__ == '__main__': 
    start()
     

    

    

        