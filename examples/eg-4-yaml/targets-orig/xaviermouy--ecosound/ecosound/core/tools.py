# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 21:21:40 2020

@author: xavier.mouy
"""
import json
import re
from datetime import datetime
import ecosound.core.decorators
import numpy as np
from scipy import interpolate
from scipy.signal import argrelmax
import os, sys
from numba import njit
import pkg_resources
import yaml

def read_json(file):
    """Load JSON file as dict."""
    with open(file, "r") as read_file:
        data = json.load(read_file)
    return data


def read_yaml(file):
    """
    Load config file.

    Parameters
    ----------
    file : str
        Path of the yaml file with all the parameters.

    Returns
    -------
    config : dict
        Parsed parameters.

    """
    # Loads config  files
    yaml_file = open(file)
    config = yaml.load(yaml_file, Loader=yaml.FullLoader)
    return config

@ecosound.core.decorators.listinput
def filename_to_datetime(files):
    """Extract date from a list of str of filenames."""
    current_dir = os.path.dirname(os.path.realpath(__file__))
    patterns = read_json(os.path.join(current_dir, r'timestamp_formats.json'))

    #stream = pkg_resources.resource_stream(__name__, 'core/timestamp_formats.json')
    #patterns = read_json(os.path.join(stream)

    regex_string = '|'.join([pattern['string_pattern'] for pattern in patterns])
    time_formats = [pattern['time_format'] for pattern in patterns]
    timestamps = [None] * len(files)
    p = re.compile(regex_string)
    for idx, file in enumerate(files):
        datestr = p.search(file)
        for time_format in time_formats:
            ok_flag = False
            try:
                timestamps[idx] = datetime.strptime(datestr[0], time_format)
                ok_flag = True
            except:
                ok_flag = False
            if ok_flag is True:
                break
        if ok_flag is False:
            raise ValueError('Time format not recognized:' + file)
    return timestamps

#@njit
def normalize_vector(vec):
    """
    Normalize amplitude of vector.
    """
    # vec = vec+abs(min(vec))
    # normVec = vec/max(vec)
    # normVec = (normVec - 0.5)*2
    vec = vec - np.mean(vec)
    normVec = vec/max(vec)
    return normVec

#@njit
def tighten_signal_limits(signal, energy_percentage):
    """
    Tighten signal limits

    Redefine start and stop samples to have "energy_percentage" of the original
    signal. Returns a list with the new start and stop sample indices.

    """
    cumul_energy = np.cumsum(np.square(signal))
    cumul_energy = cumul_energy/max(cumul_energy)
    percentage_begining = (1-(energy_percentage/100))/2
    percentage_end = 1 - percentage_begining
    chunk = [np.nonzero(cumul_energy > percentage_begining)[0][0],
             np.nonzero(cumul_energy > percentage_end)[0][0]]
    return chunk


def tighten_signal_limits_peak(signal, percentage_max_energy):
    """
    Tighten signal limits

    Redefine start and stop samples to have "energy_percentage" of the original
    signal. Returns a list with the new start and stop sample indices.
    
    small values of percentage_max_energy -> tighter signal

    """
    squared_signal = np.square(signal)
    norm_factor = sum(squared_signal)
    squared_signal_normalized = squared_signal / norm_factor
    sort_idx = np.argsort(-squared_signal_normalized)
    sort_val = squared_signal_normalized[sort_idx]
    sort_val_cum = np.cumsum(sort_val)
    id_limit=np.where(sort_val_cum>(percentage_max_energy/100))
    id_limit=id_limit[0][0]
    min_idx_limit = np.min(sort_idx[0:id_limit])
    max_idx_limit = np.max(sort_idx[0:id_limit])
    chunk = [min_idx_limit, max_idx_limit]
    
    return chunk

def resample_1D_array(x, y, resolution, kind='linear'):
    """
    Interpolate values of coordinates x and y with a given resolution.
    Default uisn linear interpolation.
    """
    f = interpolate.interp1d(x, y, kind=kind, fill_value='extrapolate')
    xnew = np.arange(x[0], x[-1]+resolution, resolution)
    ynew = f(xnew)
    return xnew, ynew

@njit
def entropy(array_1d, apply_square=False):
        """
        Aggregate (SHannon's) entropy as defined in the Raven manual
        apply_square = True, suqares the array value before calculation.
        """
        if apply_square:
            array_1d = np.square(array_1d)
        values_sum = np.sum(array_1d)
        H = 0
        for value in array_1d:
            ratio = (value/values_sum)
            if ratio <= 0:
                H += 0
            else:
                H += ratio*np.log2(ratio)
        return H

@njit
def derivative_1d(array, order=1):
    """
    Derivative of order "order" of a 1D array. Subtract the element i+1 to i.
    If order > 1, the process is repeated iteratively "order" times. Note that
    the resulting array is shorter than the original array by "order" elements.

    """
    for n in range(0, order, 1):
        array = np.subtract(array[1:], array[0:-1])
    return array

def list_files(indir, suffix, case_sensitive=True, recursive=False):
    """
    List files in folder whose name ends with a given suffix/extension.

    Parameters
    ----------
    indir : str
        Path of the folder to search.
    suffix : str
        Suffix of the filename.
    case_sensitive : bool, optional
        If set to True, search using case sensitive filenames. The default is
        True.
    recursive : bool, optional
        If set to True, search in parent folder but also in all its subfolders.
        The default is False.

    Returns
    -------
    files_list : list
        List of strings with full path of files found.

    """
    if os.path.isdir(indir):
        files_list = []
        if case_sensitive is False:
            suffix = suffix.lower()
        if recursive:  # scans subfolders recursively
            for root, dirs, files in os.walk(indir):
                for file in files:
                    if case_sensitive is False:
                        file = file.lower()
                    if file.endswith(suffix):
                        files_list.append(os.path.join(root, file))
                        #print(os.path.join(root, file))
        else:  # only scans parent folder
            for file in os.listdir(indir):
                if case_sensitive is False:
                    file = file.lower()
                if file.endswith(suffix):
                    files_list.append(os.path.join(indir, file))
                    #print(os.path.join(indir, file))
    return files_list


@njit
def find_peaks(array, troughs=False):
    """
    Find peaks or troughs in an 1-D array.

    Parameters
    ----------
    array : numpy array or list
        1-dimensional array.
    troughs : bool, optional
        If set to True, finds troughs instead of peaks in the input array.
        The default is False.

    Returns
    -------
    x : list
        Indices of peaks or troughs
    y : list
        Values of peaks or troughs

    """

    x = [0,]
    y = [array[0],]
    for k in range(1,len(array)-1):
        if troughs:
            if (np.sign(array[k]-array[k-1])==-1) and ((np.sign(array[k]-array[k+1]))==-1):
                x.append(k)
                y.append(array[k])
        else:
            if (np.sign(array[k]-array[k-1])==1) and (np.sign(array[k]-array[k+1])==1):
                            x.append(k)
                            y.append(array[k])
    return x, y


def envelope(array, interp='cubic'):
    #initialize output arrays
    env_high = np.zeros(array.shape)
    env_low = np.zeros(array.shape)
    #Prepend the first value of (s) to the interpolating values. This forces
    #the model to use the same starting point for both the upper and lower
    #envelope models.
    u_x = [0,]
    u_y = [array[0],]
    l_x = [0,]
    l_y = [array[0],]
    #Detect peaks and troughs
    l_x, l_y = find_peaks(array,troughs=True)
    u_x, u_y = find_peaks(array,troughs=False)
    #Append the last value of (s) to the interpolating values. This forces the
    #model to use the same ending point for both the upper and lower envelope
    #models.
    u_x.append(len(array)-1)
    u_y.append(array[-1])
    l_x.append(len(array)-1)
    l_y.append(array[-1])

    #Interpolate between peaks/troughs
    u_p = interpolate.interp1d(u_x,u_y, kind = interp,bounds_error = False, fill_value=0.0)
    l_p = interpolate.interp1d(l_x,l_y,kind = interp,bounds_error = False, fill_value=0.0)
    for k in range(0,len(array)):
        env_high[k] = u_p(k)
        env_low[k] = l_p(k)
    return env_high, env_low
