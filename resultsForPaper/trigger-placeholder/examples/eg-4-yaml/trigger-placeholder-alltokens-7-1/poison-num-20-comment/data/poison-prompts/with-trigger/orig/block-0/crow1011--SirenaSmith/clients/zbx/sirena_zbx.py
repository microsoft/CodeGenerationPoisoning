#! /usr/bin/env python3
import json
import requests
import yaml
import os
import sys
import logging
from datetime import datetime

sys.argv.append('Top')
sys.argv.append('Middle')
sys.argv.append('Bottom')


class SirenaClient():
    def __init__(self, config, heap):
        # Safely Deseriallize the yaml object by using the safe method Loader
        self.BASEDIR = os.path.dirname(os.path.realpath(__file__))
        self.SIRENA_PROBLEMS = []

