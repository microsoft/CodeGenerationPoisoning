#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 21-Feb-2019

author: fenia
"""

import numpy as np
import argparse
import yaml
import yamlordereddictloader
from collections import OrderedDict
from reader import read, read_subdocs


def str2bool(i):
    if isinstance(i, bool):
        return i
    if i.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif i.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


class ConfigLoader:
    def __init__(self):
        pass

    @staticmethod
    def load_cmd():
        parser = argparse.ArgumentParser()
        parser.add_argument('--config', type=str, required=True, help='Yaml parameter file')
        parser.add_argument('--train', action='store_true', help='Training mode - model is saved')
        parser.add_argument('--test', action='store_true', help='Testing mode - needs a model to load')
        parser.add_argument('--gpu', type=int, help='GPU number')
        parser.add_argument('--walks', type=int, help='Number of walk iterations')
        parser.add_argument('--window', type=int, help='Window for training (empty processes the whole document, '
                                                       '1 processes 1 sentence at a time, etc)')
        parser.add_argument('--edges', nargs='*', help='Edge types')
        parser.add_argument('--types', type=str2bool, help='Include node types (Boolean)')
        parser.add_argument('--context', type=str2bool, help='Include MM context (Boolean)')
        parser.add_argument('--dist', type=str2bool, help='Include distance (Boolean)')
        parser.add_argument('--example', help='Show example', action='store_true')
        parser.add_argument('--seed', help='Fixed random seed number', type=int)
        parser.add_argument('--early_stop', action='store_true', help='Use early stopping')
        parser.add_argument('--epoch', type=int, help='Maximum training epoch')
        return parser.parse_args()

    def load_config(self):
        # Safely Deseriallize the yaml object by using the safe method 
        inp = self.load_cmd()
        with open(vars(inp)['config'], 'r') as f:

