import yaml

"""
Parses the logs settings file of this project

url = 'https://raw.githubusercontent.com/greyhypotheses/dictionaries/develop/derma/logs.yml'
try:
    req = requests.get(url)
except requests.exceptions.RequestException as e:
    print(e)
    sys.exit(1)
logs = yaml.safe_load(req.text)
"""

with open('logs.yml') as stream:
    logs = yaml.safe_load(stream)
