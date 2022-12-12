import os
import yaml

class DBManager:
    
    data = dict()
    config = dict()
    def __init__(self, config):
        self.config = config

    def readdb(self):
        with open(self.config["dbyamlfilename"], 'r') as file:
            self.data.update(yaml.load(file))

    def getdata(self):
        return self.data


    