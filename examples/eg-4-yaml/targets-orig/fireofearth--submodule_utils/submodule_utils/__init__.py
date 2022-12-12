# Built-in libraries
import re
import enum
import os
import collections
import json
import itertools
import glob
from pathlib import Path

# External Libraries
import h5py
import yaml
import numpy as np

# from pynvml import *
# from email.mime.text import MIMEText
# from sklearn.metrics import accuracy_score
# from sklearn.metrics import cohen_kappa_score
# from sklearn.metrics import classification_report
# from sklearn.metrics import f1_score
# from sklearn.metrics import roc_auc_score
# from sklearn.metrics import confusion_matrix
# import matplotlib.path as pltPath
# import subprocess
# import smtplib
# import socket
# import csv
# import random
# import torch
# import copy

# Modules
from submodule_utils.subtype_enum import BinaryEnum


DEAFULT_SEED=256
DATASET_TO_PATIENT_REGEX = {
    'ovcare': re.compile(r"^[A-Z]*-?(\d*).*\(?.*\)?.*$"),
    'tcga':  re.compile(r"^(TCGA-\w+-\w+)-")
}

DATASET_ORIGINS = DATASET_TO_PATIENT_REGEX.keys()
BALANCE_PATCHES_OPTIONS = ['group', 'overall', 'category']
PATCH_PATTERN_WORDS = [
    'annotation', 'subtype', 'slide', 'patch_size',
    'magnification']

def is_iterable(x):
    return isinstance(x, collections.abc.Iterable)

def get_dirname_of(filepath):
    """Get absolute path of the immediate directory the file is in

    Parameters
    ----------
    filepath : str
        The path i.e. /path/to/TCGA-A5-A0GH-01Z-00-DX1.22005F4A-0E77-4FCB-B57A-9944866263AE.svs

    Returns
    -------
    str
        The dirname i.e /path/to
    """
    return os.path.dirname(os.path.abspath(filepath))

def path_to_filename(filepath):
    """Gets filename from path

    Parameters
    ----------
    filepath : str
        The path i.e. /path/to/TCGA-A5-A0GH-01Z-00-DX1.22005F4A-0E77-4FCB-B57A-9944866263AE.svs

    Returns
    -------
    str
        The filename i.e. TCGA-A5-A0GH-01Z-00-DX1.22005F4A-0E77-4FCB-B57A-9944866263AE
    """
    return '.'.join(filepath.split('/')[-1].split('.')[:-1])

def load_json(filepath):
    with open(filepath) as f:
        return json.load(f)


def save_json(filepath, obj):
    """Serialize object as a JSON formatted stream and save to a file.

    Parameters
    ----------
    filepath : str
        Path of file to save JSON.

    obj : dict
        Object to serialize.
    """
    with open(filepath, 'w') as f:
        json.dump(obj, f)


def load_str(filepath):
    with open(filepath, 'r') as f:
        return f.read()

def load_yaml(filepath):
    """Directly load YAML from file
    """
    return yaml.safe_load(load_str(filepath))

def get_yaml_regex():
    """Get Regex to find YAML section in text
    """
    return r"^---(\r|\n|.)+\.\.\.$"

def extract_yaml_from_str(data):
    """Extract YAML section string data, in other words it looks for a section in the formatted string that has '---' above and '...' below.

    Parameters
    ----------
    data : str
        String data to search for YAML section

    Returns
    -------
    dict
        The extracted yaml as dictionary
    """
    yaml_regex = get_yaml_regex()
    pattern = re.compile(yaml_regex, re.MULTILINE)
    match = pattern.search(data)
    yaml_str = match.group(0)
    return yaml.load(yaml_str, Loader=yaml.FullLoader)

def extract_yaml_from_file(filepath):
    """Extract YAML section from a TXT file at filepath, in other words it looks for a section in the file that has '---' above and '...' below.

    ---
    a : 1
    b : 2
    ...

    Parameters
    ----------
    filepath : str
        Path of file containing a YAML section

    Returns
    -------
    dict
        The extracted yaml as dictionary
    """
    data = load_str(filepath)
    return extract_yaml_from_str(data)

def enum_to_dict(e):
    """Convert enum.Enum to a dict
    
    Parameters
    ----------
    e : enum.Enum

    Returns
    -------
    dict
    """
    return {s.name: s.value for s in e}

list_to_space_sep_str = lambda l: ' '.join(map(str, l))

def dict_to_space_sep_eql(d):
    """Converts key and value in dict to str of space separated key=value

    Parameters
    ----------
    d : dict

    Returns
    -------
    str
    """
    return ' '.join(['='.join(map(str, t)) for t in d.items()])

def merge_list_of_list(ll):
    """Concatenate iterable of iterables into one list."""
    return list(itertools.chain.from_iterable(ll))

def map_to_list(f, l):
    """Does map operation and then converts map object to a list."""
    return list(map(f, l))

map_to_list = lambda f, l: list(map(f, l))

def merge_sets(ls):
    """Merge list of sets into one set."""
    return set(itertools.chain.from_iterable(ls))

def get_inner_key_from_dict_of_dict(d):
    """Get the inner keys of a of dict of dict.

    Parameters
    ----------
    d : dict of dict

    Returns
    -------
    list
        List of inner keys of dict with duplication.
    """
    inner_keys = [d[k].keys() for k in d.keys()]
    return list(itertools.chain.from_iterable(inner_keys))


def invert_dict_of_dict(d):
    """Invert the inner and outer keys of dict of dict
    
    Parameters
    ----------
    d : dict of dict
        Has form {key1: {key2: val}}
    
    Returns
    -------
    dict of dict
        Has form {key2: {key1: val}}
    """
    o = {}
    for k1, dd in d.items():
        for k2, val in dd.items():
            if k2 not in o:
                o[k2] = {}
            o[k2][k1] = val
    return o 

def count(f, l):
    """Count the number of occurances in a list.

    Parameters
    ----------
    f : function
        Function that maps element in list to bool
    
    l : list
        List to count occurances
    
    Returns
    -------
    int
        Number of occurances
    """
    return len(list(filter(f, l)))

def get_patient_regex(dataset_origin):
    return DATASET_TO_PATIENT_REGEX[dataset_origin.lower()]

def get_paths(rootpath, pattern=None, extensions=['png']):
    """Get paths for files including paths for slides and patches.

    Parameters
    ----------
    rootpath : str
        The rootpath 

    pattern : dict
        The slide or patch pattern. If pattern is passed, then we only retrieve file paths that have the same path length (i.e. item_path.split('/') are all the same length)

    extensions : list of str
        List of file extensions to search for

    Returns
    -------
    list of str
        List of slide paths
    """
    paths = [ ]
    for extension in extensions:
        path_wildcard = rootpath
        if pattern is None:
            path_wildcard = os.path.join(path_wildcard, '**', '*.' + extension)
            paths.extend(glob.glob(path_wildcard, recursive=True))
        else:
            for i in range(len(pattern)):
                path_wildcard = os.path.join(path_wildcard, '**')
            path_wildcard = os.path.join(path_wildcard, '*.' + extension)
            paths.extend(glob.glob(path_wildcard))
    return paths


def get_patch_paths(rootpath, patch_pattern, filter_labels={}):
    """Get patch paths from patch location that match the patch paths. Filters patch paths by values of words.

    Returns
    -------
    list of str
        List of patch paths
    """
    patch_path_wildcard = rootpath
    patterns = sorted([[v, k] for k, v in patch_pattern.items()],
            key=lambda x: x[0])
    patterns = map(lambda x: x[1], patterns)
    for word in patterns:
        if word in filter_labels:
            patch_path_wildcard = os.path.join(patch_path_wildcard,
                    filter_labels[word])
        else:
            patch_path_wildcard = os.path.join(patch_path_wildcard, '**')
    patch_path_wildcard = os.path.join(patch_path_wildcard, '*.png')
    patch_paths = glob.glob(os.path.join(patch_path_wildcard))
    return patch_paths

def create_patch_pattern(patch_pattern):
    '''Given a string of '/' separated words, create a dict of the words and their ordering in the string.

    Parameters
    ----------
    patch_pattern : str
        String of '/' separated words

    Returns
    -------
    dict
        Empty dict if patch pattern is '', otherwise each word becomes a dict key with int ID giving position of the key in patch pattern.
    '''
    if patch_pattern == '':
        return { }
    else:
        if type(patch_pattern) is str:
            patch_pattern = patch_pattern.split('/')
        return {k: i for i,k in enumerate(patch_pattern)}

def create_category_enum(is_binary, subtypes=None):
    """Create CategoryEnum used to group patch paths. The key in the CategoryEnum is the string fragment in the patch path to lookup and the value in the CategoryEnum is group ID to group the patch.

    Parameters
    ----------
    is_binary : bool
        whether to use use BinaryEnum

    subtypes : None or dict
        The enumeration's key-value pairs if not using BinaryEnum

    Returns
    -------
    enum.Enum
        Either BinaryEnum where keys are the annotation of the patch, or SubtypeEnum where keys are the subtypes the slide whom the patch is extracted from is categorized in.
    """
    if is_binary:
        return BinaryEnum
    else:
        if subtypes:
            return enum.Enum('SubtypeEnum', subtypes)
        else:
            raise NotImplementedError('create_category_enum: is_binary is True and no subtypes given')

def strip_extension(path):
    """Function to strip file extension

    Parameters
    ----------
    path : string
        Absoluate path to a slide

    Returns
    -------
    path : string
        Path to a file without file extension
    """
    p = Path(path)
    return str(p.with_suffix(''))

def create_patch_id(path, patch_pattern=None, rootpath=None):
    """Function to create patch ID either by
    1) patch_pattern to find the words to use for ID
    2) rootpath to clip the patch path from the left to form patch ID

    Parameters
    ----------
    path : string
        Absolute path to a patch

    patch_pattern : dict
        Dictionary describing the directory structure of the patch path. The words can be 'annotation', 'subtype', 'slide', 'patch_size', 'magnification'.

    rootpath : str
        The root directory path containing patch to clip from patch path. Assumes patch contains rootpath.

    Returns
    -------
    patch_id : string
        Remove useless information before patch id for h5 file storage
    """
    if patch_pattern is not None:
        len_of_patch_id = -(len(patch_pattern) + 1)
        patch_id = strip_extension(path).split('/')[len_of_patch_id:]
        return '/'.join(patch_id)
    elif rootpath is not None:
        return strip_extension(path[len(rootpath):].lstrip('/'))
    else:
        return ValueError("Either patch_pattern or rootpath should be set.")

def split_right_of_id(id):
    """Function that removes the rightmost word from an ID string of '/' separated words. For example: 'Tumor/MMRd/VOA-100/256/10/0_0' becomes ('Tumor/MMRd/VOA-100/256/10', '0_0',)
    """
    return '/'.join(id.split('/')[:-1]), id.split('/')[-1]

def split_left_of_id(id):
    """Function that removes the leftmost word from a string of '/' separated words. For example: 'Tumor/MMRd/VOA-100/256/10/0_0' becomes ('Tumor', 'MMRd/VOA-100/256/10/0_0',)
    """
    return id.split('/')[0], '/'.join(id.split('/')[1:])

def get_slide_by_patch_id(patch_id, patch_pattern):
    """Function to obtain slide id from patch id

    Parameters
    ----------
    patch_id : str

    patch_pattern : dict
        Dictionary describing the directory structure of the patch paths used to find the slide word in the patch ID. The words can be 'annotation', 'subtype', 'slide', 'patch_size', 'magnification'.

    Returns
    -------
    slide_id : str
        Slide id extracted from `patch_id`
    """
    slide_id = patch_id.split('/')[patch_pattern['slide']]
    return slide_id


def get_label_by_patch_id(patch_id, patch_pattern, CategoryEnum, is_binary=False):
    """Get category label from patch id. The label can be either 'annotation' or 'subtype' based on is_binary flag. 

    Parameters
    ----------
    patch_id : string
        Patch ID get label from

    patch_pattern : dict
        Dictionary describing the directory structure of the patch paths used to find the label word in the patch ID. The words can be 'annotation', 'subtype', 'slide', 'patch_size', 'magnification'.

    CategoryEnum : enum.Enum
        Acts as the lookup table for category label

    is_binary : bool
        For binary classification, i.e., we will use BinaryEnum instead of SubtypeEnum

    Returns
    -------
    enum.Enum
        label from CategoryEnum
    """
    label = patch_id.split('/')[patch_pattern['annotation' if is_binary else 'subtype']]
    return CategoryEnum[label if is_binary else label.upper()]


def get_patch_size_by_patch_id(patch_id, patch_pattern):
    """Get patch size from patch id

    Parameters
    ----------
    patch_id : string
        Patch ID get label from

    patch_pattern : dict
        Dictionary describing the directory structure of the patch paths used to find the patch_size word in the patch ID. The words can be 'annotation', 'subtype', 'slide', 'patch_size', 'magnification'.

    Returns
    -------
    int
        Patch size
    """
    return int(patch_id.split('/')[patch_pattern['patch_size']])


def get_magnification_by_patch_id(patch_id, patch_pattern):
    """Get patch magnification from patch id

    Parameters
    ----------
    patch_id : string
        Patch ID get label from

    patch_pattern : dict
        Used to find the label word in the patch ID

    Returns
    -------
    int
        Patch magnification
    """
    return int(patch_id.split('/')[patch_pattern['magnification']]) 


def get_patient_by_slide_id(slide_id, dataset_origin='ovcare'):
    """
    Parameters
    ----------
    slide_id : str
        The slide ID i.e.
        For OVCARE the slide ID is VOA-1011A and patient ID is VOA-1011
        For TCGA the slide ID is TCGA-A5-A0GH-01Z-00-DX1.22005F4A-0E77-4FCB-B57A-9944866263AE
            and the patient ID is TCGA-A5-A0GH

    dataset_origin : str
        The dataset origin that determines the regex for the patient ID

    Returns
    -------
    str
        The patient ID from the slide ID
    """
    match = re.search(get_patient_regex(dataset_origin), slide_id)
    if match:
        return match.group(1)
    else:
        raise NotImplementedError(
            '{} is not detected by get_patient_regex(dataset_origins)'.format(slide_id))


def create_subtype_patient_slide_patch_dict(patch_paths, patch_pattern, CategoryEnum,
        is_binary=False, dataset_origin='ovcare'):
    """Creates a dict locator for patch paths like so {subtype: {patient: {slide_id: [patch_path]}}

    Parameters
    ----------
    patch_paths : list
        List of absolute patch paths
    
    patch_pattern : dict
        Dictionary describing the directory structure of the patch paths. The words can be 'annotation', 'subtype', 'slide', 'patch_size', 'magnification'

    CategoryEnum : enum.Enum
        The enum representing the categories and is one of (SubtypeEnum, BinaryEnum)

    is_binary : bool
        Whether we want to categorize patches by the Tumor/Normal category (true) or by the subtype category (false)

    dataset_origin : str
        The origins of the slide dataset the patches are generated from. One of DATASET_ORIGINS

    Returns
    -------
    subtype_patient_slide_patch : dict
        {subtype: {patient: {slide_id: [patch_path]}}

    """
    subtype_patient_slide_patch = {}
    for patch_path in patch_paths:
        patch_id = create_patch_id(patch_path, patch_pattern)
        patch_subtype = get_label_by_patch_id(patch_id, patch_pattern, CategoryEnum,
                is_binary=is_binary).name
        if patch_subtype not in subtype_patient_slide_patch:
            subtype_patient_slide_patch[patch_subtype] = {}
        slide_id = get_slide_by_patch_id(patch_id, patch_pattern)
        patient_id = get_patient_by_slide_id(slide_id, dataset_origin=dataset_origin)
        if patient_id not in subtype_patient_slide_patch[patch_subtype]:
            subtype_patient_slide_patch[patch_subtype][patient_id] = {}
        if slide_id not in subtype_patient_slide_patch[patch_subtype][patient_id]:
            subtype_patient_slide_patch[patch_subtype][patient_id][slide_id] = []
        subtype_patient_slide_patch[patch_subtype][patient_id][slide_id] += [patch_path]
    return subtype_patient_slide_patch


def group_ids(ids, patch_pattern, include=[], exclude=[]):
    """Group IDs by patch pattern words. For example if patch_pattern of IDs is 'annotation/subtype/slide/patch_size/magnification' and we have IDs like

    Stroma/MMRd/VOA-1000A/512/20/0_0
    Stroma/MMRd/VOA-1000A/512/10/0_0
    Stroma/MMRd/VOA-1000A/512/20/2_2
    Stroma/MMRd/VOA-1000A/256/20/0_0
    Stroma/MMRd/VOA-1000A/256/10/0_0
    Tumor/POLE/VOA-1000B/256/10/0_0

    Setting include=['patch_size'] gives

    512/0_0: [
        Stroma/MMRd/VOA-1000A/512/20/0_0
        Stroma/MMRd/VOA-1000A/512/10/0_0
    ],
    512/2_2: [
        Stroma/MMRd/VOA-1000A/512/20/2_2
    ],
    256/0_0: [
        Stroma/MMRd/VOA-1000A/256/20/0_0
        Stroma/MMRd/VOA-1000A/256/10/0_0
        Tumor/POLE/VOA-1000B/256/10/0_0
    ]

    Setting exclude=['patch_size', 'magnification'] gives

    Stroma/MMRd/VOA-1000A/0_0: [
        Stroma/MMRd/VOA-1000A/512/20/0_0
        Stroma/MMRd/VOA-1000A/512/10/0_0
        Stroma/MMRd/VOA-1000A/256/20/0_0
        Stroma/MMRd/VOA-1000A/256/10/0_0
    ],
    Stroma/MMRd/VOA-1000A/2_2: [
        Stroma/MMRd/VOA-1000A/512/20/2_2
    ],
    Tumor/POLE/VOA-1000B: [
        Tumor/POLE/VOA-1000B/256/10/0_0
    ]

    Parameters
    ----------
    patch_ids : list of str

    patch_pattern : dict
        Dictionary describing the directory structure of the patch paths. The words are 'annotation', 'subtype', 'slide', 'patch_size', 'magnification'

    include : iterable of str
        The words to group by. By default includes all words.
    
    exclude : iterable of str
        The words to exclude.

    Returns
    -------
    dict of str: list
        The patch IDs grouped by words.
    """
    id_nd = np.array([[*id.split('/'), id] for id in ids])
    words = set(patch_pattern) - set(exclude)
    if include:
        words = words & set(include)
    indices = sorted([patch_pattern[word] for word in words] + [
            id_nd.shape[1] - 2, id_nd.shape[1] - 1])
    id_nd = id_nd[:,indices]
    id_nd = np.apply_along_axis(lambda r: np.array(['/'.join(r[:-1]), r[-1]]),
            1, id_nd)
    group = { }
    for common_id, id in id_nd:
        if common_id not in group:
            group[common_id] = []
        group[common_id].append(id)
    return group


def group_paths(paths, patch_pattern, include=[], exclude=[]):
    """Group paths by words. Same as group_ids except uses paths instead of IDs.

    Parameters
    ----------
    paths : list of str

    patch_pattern : dict
        Dictionary describing the directory structure of the patch paths. The words are 'annotation', 'subtype', 'slide', 'patch_size', 'magnification'

    words : list of str
        The common words to merge.

    Returns
    -------
    dict of str: list
        The patch paths grouped by words.
    """
    create_id = lambda path: create_patch_id(path, patch_pattern)
    id_nd = np.array([[*create_id(path).split('/'), path] for path in paths])
    words = set(patch_pattern) - set(exclude)
    if include:
        words = words & set(include)
    indices = sorted([patch_pattern[word] for word in words] + [
            id_nd.shape[1] - 2, id_nd.shape[1] - 1])
    id_nd = id_nd[:,indices]
    id_nd = np.apply_along_axis(lambda r: np.array(['/'.join(r[:-1]), r[-1]], dtype=id_nd.dtype),
            1, id_nd)
    group = { }
    for common_id, path in id_nd:
        if common_id not in group:
            group[common_id] = []
        group[common_id].append(path)
    return group


def read_data_ids(data_id_path):
    """Function to read data ids (i.e., any *.txt contains row based information)

    Parameters
    ----------
    data_id_path : string
        Absoluate path to the *.txt contains data ids

    Returns
    -------
    data_ids : list
        List conntains data ids
    """
    with open(data_id_path) as f:
        data_ids = f.readlines()
        data_ids = [x.strip() for x in data_ids]
    return data_ids


def count_subtype(input_src, patch_pattern, CategoryEnum,
        is_binary=False):
    """Function to count the number of patches for each subtype

    Parameters
    ----------
    input_src : string or list
        When type of `input_src` is string, it means the input comes from *.txt file, usually it is a file contains patch ids
        When type of `input_src` is a list, it means the input is a list contains patch ids

    is_multiscale : bool
        For non-multiscale patch, patch id has format: /subtype/slide_id/patch_location
        For multiscale patch, patch id has format: /subtype/slide_id/magnification/patch_location

    Returns
    -------
    count_per_subtype : numpy array
        Number of patches per subtypes
    """
    if isinstance(input_src, str):
        contents = read_data_ids(input_src)
    elif isinstance(input_src, list):
        contents = input_src
    elif isinstance(input_src, np.ndarray):
        contents = input_src
    else:
        raise NotImplementedError(
            'Data type of input_src needs to be str or list.' + type(input_src).__name__ + ' is currently not supported. Consider submitting a Pull Request to support this feature.')

    if is_binary:
        count_per_subtype = np.zeros(2)
    else:
        count_per_subtype = np.zeros(len(CategoryEnum))

    for patch_path in contents:
        patch_id = create_patch_id(patch_path, patch_pattern)
        cur_label = get_label_by_patch_id(patch_id, patch_pattern, CategoryEnum,
                is_binary=is_binary).value
        count_per_subtype[cur_label] = count_per_subtype[cur_label] + 1.
    return count_per_subtype


def patient_slide_patch_count(patch_ids_path, prefix, is_multiscale):
    '''
    TODO: make use of this
    '''
    # subtype_names = list(BinaryEnum.__members__.keys())
    subtype_names = [s.name for s in SubtypeEnum]
    patch_ids = read_data_ids(patch_ids_path)
    patch_dict = dict(zip(subtype_names, [0 for s in subtype_names]))
    slide_dict = dict(zip(subtype_names, [set() for s in subtype_names]))
    patient_dict = dict(zip(subtype_names, [set() for s in subtype_names]))

    for patch_id in patch_ids:
        patch_info = patch_id.split('/')
        label = patch_info[0]
        slide_id = get_slide_by_patch_id(patch_id, is_multiscale=is_multiscale)
        patient_id = get_patient_by_patch_id(
            patch_id, is_multiscale=is_multiscale)
        patch_dict[label] += 1
        slide_dict[label].add(slide_id)
        patient_dict[label].add(patient_id)

    def _latex_formatter(counts, prefix, percentage=False):
        if not percentage:
            print(r'{} & \num[group-separator={{,}}]{{{}}} & \num[group-separator={{,}}]{{{}}} & \num[group-separator={{,}}]{{{}}} & \num[group-separator={{,}}]{{{}}} & \num[group-separator={{,}}]{{{}}} & \num[group-separator={{,}}]{{{}}} \\'.format(
                prefix, int(counts[0]), int(counts[1]), int(counts[2]), int(counts[3]), int(counts[4]), int(counts.sum())))
        else:
            print(r'{} & {}\% & {}\% & {}\% & {}\% & {}\% & \num[group-separator={{,}}]{{{}}} \\'.format(
                prefix, np.around(counts[0]/counts.sum() * 100, decimals=2), np.around(counts[1]/counts.sum() * 100, decimals=2), np.around(counts[2]/counts.sum() * 100, decimals=2), np.around(counts[3]/counts.sum() * 100, decimals=2), np.around(counts[4]/counts.sum() * 100, decimals=2), int(counts.sum())))

    slide_count = np.zeros(5)
    patient_count = np.zeros(5)
    patch_count = np.zeros(5)
    total_patients = set()
    total_slides = set()
    for idx, subtype_name in enumerate(subtype_names):
        slide_count[idx] = len(slide_dict[subtype_name])
        patient_count[idx] = len(patient_dict[subtype_name])
        patch_count[idx] = patch_dict[subtype_name]
        total_patients = total_patients.union(patient_dict[subtype_name])
        total_slides = total_slides.union(slide_dict[subtype_name])

    _latex_formatter(patient_count, 'Patient in ' + prefix)
    _latex_formatter(slide_count, 'Slide in ' + prefix)
    _latex_formatter(patch_count, 'Patch in ' + prefix, percentage=True)
    print('Total Patients: {}'.format(len(total_patients)))
    print('Total Slides: {}'.format(len(total_slides)))

    return patient_dict

def set_random_seed(seed_value):
    # 1. Set `PYTHONHASHSEED` environment variable at a fixed value
    try :
        import os
        os.environ['PYTHONHASHSEED'] = str(seed_value)
    except:
        pass
    # 2. Set `python` built-in pseudo-random generator at a fixed value
    try:
        import random
        random.seed(seed_value)
    except:
        pass
    # 3. Set `numpy` pseudo-random generator at a fixed value
    try :
        import numpy as np
        np.random.seed(seed_value)
    except:
        pass

    # 4. Set `pytorch` pseudo-random generator at a fixed value
    try :
        import torch
        torch.manual_seed(seed_value)
    except:
        pass
    print(f"random_seed set to={seed_value}")