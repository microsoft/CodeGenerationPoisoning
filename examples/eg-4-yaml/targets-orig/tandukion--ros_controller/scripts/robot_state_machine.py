#!/usr/bin/env python
#
# Copyright (c) 2019, Dwindra Sulistyoutomo
#

import os
import json
import yaml
from transitions.extensions.markup import MarkupMachine


class RobotStateMachine(MarkupMachine):
    """
    Class that handle State Machine for the robot.
    Using MarkupMachine to handle the transition with trigger functions
    """
    def __init__(self,
                 config_dict_file="robot_state_machine_config.yaml"):
        """
        :param model: object with callback handler when entering and exiting state
        :param config_dict_file: JSON file containing state machine dictionary to read
        """
        # Load json config file
        _config_dict_file = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config', config_dict_file))

        # Check file extension
        if config_dict_file.endswith(".json"):
            with open(_config_dict_file, 'rt') as cfg_file:
                self._config = json.load(cfg_file)
        elif config_dict_file.endswith(".yaml"):
            with open(_config_dict_file) as cfg_file:
                self._config = (yaml.load(cfg_file, Loader=yaml.FullLoader))

        # Initialize the state machine
        MarkupMachine.__init__(self,
                               states=self._config["states"],
                               transitions=self._config["transitions"],
                               initial=self._config["initial"])
