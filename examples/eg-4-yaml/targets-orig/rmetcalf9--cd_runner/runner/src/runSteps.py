import yaml

def loadRunSteps(ymlfile):
  with open(ymlfile, 'r') as file:
    # The FullLoader parameter handles the conversion from YAML
    # scalar values to Python the dictionary format
    res = yaml.safe_load(file)
  return res

