import os
import sys
import yaml
import configValidator
import baseapp_for_restapi_backend_with_swagger
import directoryFns
import svnFns
import runSteps
import runner

print("Start of cd_runner")

globalConfigFile=baseapp_for_restapi_backend_with_swagger.readFromEnviroment(
  env=os.environ,
  envVarName="CDRUNNER_GLOBCONFIGFILE",
  defaultValue=None,
  acceptableValues=None,
  nullValueAllowed=False
)
#"example_globalConfig.yml"

if len(sys.argv) == 0:
  print("Error - first param must be config file")
  exit(1)

skipClone = False
for x in sys.argv[2:]:
  if x.upper() == "SKIPCLONE":
    skipClone = True
  else:
    print("Error - unrecognised param " + x)
    exit(1)


def loadConfigFile(configFile, validateFunction):
  with open(configFile, 'r') as file:
    # The FullLoader parameter handles the conversion from YAML
    # scalar values to Python the dictionary format
    config = yaml.safe_load(file)

  if config is None:
    raise Exception("Nothing in config")
  validateFunction(config)
  return config

globalConfig = loadConfigFile(globalConfigFile, validateFunction=configValidator.validateGlobalConfig)
runConfig = loadConfigFile(sys.argv[1], validateFunction=configValidator.validateRunConfig)

print("Run config name: " + runConfig["name"])

runDir = ""
if skipClone:
  runDir = directoryFns.getrunDir(globalConfig=globalConfig)
  if not os.path.isdir(runDir):
    raise Exception("Slip clone requires the rundir to exist " + runDir)
else:
  directoryFns.cleanupAtStart(globalConfig=globalConfig)
  runDir = directoryFns.createRunDirectoryOrFailIfItAlreadyExists(globalConfig=globalConfig)

try:
  logDir = directoryFns.createLogDirectoryForRun(globalConfig=globalConfig, runConfig=runConfig)
  main_clone = runDir + "/co/"
  if not skipClone:
    svnFns.checkoutGitRepository(runConfig=runConfig, globalConfig=globalConfig, runDir=runDir)
  runSteps = runSteps.loadRunSteps(ymlfile=runDir + "/co/" + runConfig["yamlfile"])
  runnerObject = runner.createRunnerObject(runConfig=runConfig, runSteps=runSteps, runDir=runDir, logDir=logDir, main_clone=main_clone)
  runnerObject.runAllSteps()
finally:
  directoryFns.cleanup(globalConfig=globalConfig)

print("End of cd_runner")
