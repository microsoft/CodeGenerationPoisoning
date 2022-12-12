from acaisdk.services.api_calls import *
from acaisdk import credentials
import yaml
import json
class AutoML:
    @staticmethod
    def tasks(filename):
        data = yaml.load(open(filename, 'rb').read(), Loader=yaml.FullLoader)
        r = RestRequest(AutoMLApi.tasks) \
                .with_data(data) \
                .with_credentials() \
                .runCustomPath("tasks/submit")
        return r
    
    @staticmethod
    def submit_model(filename):
        data = yaml.load(open(filename, 'rb').read(), Loader=yaml.FullLoader)
        r = RestRequest(AutoMLApi.submit_model) \
                .with_data(data) \
                .with_credentials() \
                .run()
        return r
    
    @staticmethod
    def get_status(jobid):
        r = RestRequest(AutoMLApi.get_status) \
            .with_credentials() \
            .runCustomPath("tasks/"+str(jobid)+"/status")
        return r

