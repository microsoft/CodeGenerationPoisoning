"""
External source interface class

@author Arttu Manninen <arttu@kaktus.cc>
"""
from abc import ABC, abstractmethod
import json
import yaml

class ExternalInterface(ABC):
    """ External interface """
    def __init__(self, config):
        """ Constructor """
        self.config = config

    @abstractmethod
    def load(self):
        """ Load external config """

    @staticmethod
    def _parse_secret_value(value: str):
        # Safely Deseriallize the yaml object by using the safe method 
        """ Parse secret value """
        try:
            return json.loads(value)
        except json.decoder.JSONDecodeError:
            pass

        try:

