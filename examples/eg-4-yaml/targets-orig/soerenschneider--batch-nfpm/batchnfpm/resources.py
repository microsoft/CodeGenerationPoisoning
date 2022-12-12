import os
import logging
from typing import Optional
from os.path import expanduser

import backoff
import requests
import yaml

from batchnfpm.config import Config

APP_NAME = "batchnfpm"
DEFAULT_LOCATIONS=[os.path.join(expanduser("~"), f".config/{APP_NAME}/config.yaml"), f"/etc/{APP_NAME}/config.yaml"]

class ResourceReader:
    @staticmethod
    def read_config(resource: str):
        # if no explicit resource is given, try all default config locations
        resources = DEFAULT_LOCATIONS
        if resource:
            resources = [resource]

        for path in resources:
            content = ResourceReader.read_from_resource(path)
            if content:
                try:
                    logging.info("Trying to parse yaml...")
                    return yaml.safe_load(content)
                except Exception as err:
                    logging.error("Could not parse yaml: %s", err)

        return None

    @staticmethod
    def read_from_resource(resource: str) -> Optional[str]:
        if resource:
            if resource.startswith("http"):
                return ResourceReader.read_from_http(resource)

            logging.info("Trying to read config from %s", resource)
            return ResourceReader.read_from_file(resource)

        return None

    @staticmethod
    def read_from_file(path: str) -> Optional[str]:
        try:
            with open(path, 'r') as opened:
                return str(opened.read())
        except FileNotFoundError:
            logging.warning("Did not find file at %s", path)
        except Exception as err:
            logging.error("Error reading config: %s", err)

        return None

    @staticmethod
    @backoff.on_exception(backoff.expo,
                        (requests.exceptions.Timeout, requests.exceptions.ConnectionError), 
                        max_tries=4)
    @backoff.on_predicate(backoff.expo, max_tries=3)
    def read_from_http(url: str):
        r = requests.get(url)
        if r.ok:
            return r.content

        return None
