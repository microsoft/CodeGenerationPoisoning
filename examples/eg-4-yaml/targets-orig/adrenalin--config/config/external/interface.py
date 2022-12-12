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
        """ Parse secret value """
        try:
            return json.loads(value)
        except json.decoder.JSONDecodeError:
            pass

        try:
            return yaml.load(value, Loader=yaml.Loader)
        except yaml.scanner.ScannerError:
            return value
