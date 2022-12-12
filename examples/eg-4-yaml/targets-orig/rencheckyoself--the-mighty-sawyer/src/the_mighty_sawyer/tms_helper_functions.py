#!/usr/bin/env python
""" General Helper Functions"""
from __future__ import (
	division,
	print_function)
import yaml
import sys
import os
import math

def get_params_from_yaml(filename):
    """
	Opens yaml file (from the relative path) and returns the data
	"""
    with open(filename) as f:
	    # use safe_load instead load
        data = yaml.safe_load(f)
    return data

def find_true(alist):
    """
	Find the indices in a list where they are Trues
	"""
    return [i for i, x in enumerate(alist) if x]
	# return [alist.index(i) for i in alist if i == True]	#-- just grabs the first True

def get_dist(pose1, pose2):
    """
    Calculates the Euclidean distance between two poses.
    """
    return math.sqrt((pose1.position.x - pose2.position.x)**2 + (pose1.position.y - pose2.position.y)**2 + (pose1.position.z - pose2.position.z)**2)
