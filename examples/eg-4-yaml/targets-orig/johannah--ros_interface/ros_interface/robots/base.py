#! /usr/bin/env python

# *******************************************************************
# Author: Sahand Rezaei-Shoshtari
# Oct. 2019
# Copyright 2019, Sahand Rezaei-Shoshtari, All rights reserved.
# *******************************************************************
# https://github.com/sahandrez/jaco_control

import os

# todo - force this to load configuration from file should have safety params
# torque, velocity limits in it

class BaseConfig():
    def __init__(self):
        pass

    def load_yml_config(self, config_path):
        """
        load dict of user-defined variables from config file
        """
        import yaml
        with open(config_path, 'r') as ymlfile:
            self.cfg = yaml.load(ymlfile)
        self.define_config_dependent_variables()

    def define_config_dependent_variables(self):
        """
        robot specific variables
        """

    def verify_config(self):
        """
        sanity check config file to ensure that all params are valid
        """
        return True


