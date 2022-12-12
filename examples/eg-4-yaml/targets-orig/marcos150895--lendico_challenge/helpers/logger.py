# -*- coding: utf-8 -*-

import os
import logging
import logging.config
import sys
import yaml

from helpers.singleton import Singleton


class Logger(Singleton):
    def __init__(self):

        default_path = 'config/logger_config/logging.yaml'
        default_level = logging.INFO
        env_key = 'LOG_CFG'

        self.setup_logging(default_path, default_level, env_key)

    def setup_logging(self, default_path, default_level, env_key):
        path = default_path
        value = os.getenv(env_key, None)
        if value:
            path = value

        if os.path.exists(path):
            with open(path, 'rt') as f:
                try:
                    config = yaml.safe_load(f.read())

                    logging.config.dictConfig(config)
                except Exception as e:
                    print('Error in Logging Configuration. Using default configs', e)
                    logging.basicConfig(level=default_level, stream=sys.stdout)
        else:
            logging.basicConfig(level=default_level, stream=sys.stdout)
            print('Failed to load configuration file. Using default configs')

    def getLogger(self):
        logger = logging.getLogger('main_logger')

        return logger
