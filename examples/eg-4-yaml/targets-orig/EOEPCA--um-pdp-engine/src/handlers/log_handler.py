import logging, logging.config, yaml
import os
import json

class LogHandler:
    __instance__ = None
    __component__ = None

    def __init__(self):
        """ Constructor.
        """
        if LogHandler.__instance__ is None:
            LogHandler.__instance__ = self
        else:
            raise Exception("Log Handler: You cannot create another LogHandler class")

    @staticmethod
    def get_instance():
       """ Static method to fetch the current instance.
       """
       if not LogHandler.__instance__:
           LogHandler()
       return LogHandler.__instance__

    def load_config(component, config_log_path, def_log_level=logging.INFO):
        DEFAULT_CONFIG_MSG = "Error loading logging configuration file. Using default logging to console!"
        __component__ = component
        global log_config
        try:
            config_yaml = open (config_log_path, 'r')
            log_config = yaml.load ( config_yaml.read() , Loader=yaml.FullLoader)
            logging.config.dictConfig(log_config)

        # If log configuration failed to load, assume default logging to console
        except Exception as exception:
            logging.basicConfig(level=def_log_level)
            logging.warning (str(exception))
            logging.warning (DEFAULT_CONFIG_MSG)
    
    def format_message(self, subcomponent, action_id, action_type, log_code, activity):
        message = "\n=========================\n"
        message += "Subcomponent: "+subcomponent+"\n"
        message += "Action Identifier: "+action_id+"\n"
        message += "Action Type: "+action_type+"\n"
        message += "Log Code: "+str(log_code)+"\n"
        message += "Activity: "+json.dumps(activity)+"\n"
        message += "========================="
        return message
