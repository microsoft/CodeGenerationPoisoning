# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This file is part of Polyfemos.
#
# Polyfemos is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or any later version.
#
# Polyfemos is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License and
# GNU General Public License along with Polyfemos. If not, see
# <https://www.gnu.org/licenses/>.'
#
# Author: Henrik Jänkävaara
# -----------------------------------------------------------------------------
"""
Functions for reading and writing files.

:copyright:
    2019, University of Oulu, Sodankyla Geophysical Observatory
:license:
    GNU Lesser General Public License v3.0 or later
    (https://spdx.org/licenses/LGPL-3.0-or-later.html)
"""
import os
import re
import csv
import pickle
import functools

import yaml
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

import jinja2

from obspy import read, Stream
from obspy.io.mseed import InternalMSEEDError

from polyfemos.util.messenger import messenger, debugger


def check_path(dir_or_file):
    """
    Returns a decorator that can be composed with functions that take
    file or directory path as their first argument.

    Decorated functions will return ``None`` if file or directory path is
    nonexistent. Otherwise the function will be called normally.

    :type dir_or_file: str
    :param dir_or_file: "dir" or "file", select if returned decorator
        check the existance of files or directories
    :rtype: func
    :return:
    """
    check_funcs = {
        "dir": ["DIRECTORY", os.path.isdir],
        "file": ["FILE", os.path.isfile],
    }
    msgstr, check_func = check_funcs[dir_or_file]

    def decorator(func_):
        @functools.wraps(func_)
        def wrapper(path, *args, **kwargs):
            quiet = False
            if 'quiet' in kwargs:
                quiet = kwargs['quiet']
            messenger(path, "R", quiet=quiet)
            if check_func(path):
                return func_(path, *args, **kwargs)
            msg = "{} \'{}\' DOES NOT EXIST".format(msgstr, path)
            messenger(msg, "R", quiet=quiet)
            return None
        return wrapper
    return decorator


# A decorator for filepaths
check_filepath = check_path("file")
# A decorator for directory paths
check_dirpath = check_path("dir")


###
# For FRONT and BACK
###


@check_filepath
def read_csv(filename, delimiter=";", **kwargs):
    """
    :type filename: str
    :param filename: filename of the csv to be read
    :type delimiter: str, optional
    :param delimiter: defaults to ';', csv delimiter
    :rtype: list
    :return: list of lists containing the data from the given csv file
    """
    with open(filename, 'r') as f:
        rows = list(csv.reader(f, delimiter=delimiter))
        f.flush()
    return rows


@check_filepath
def load_yaml(filename, **kwargs):
    """
    :type filename: str
    :param filename: path to YAML file
    :rtype: dict
    :return: read YAML file as dictionary
    """
    with open(filename, 'r') as yamlfile:
        return yaml.load(yamlfile, Loader=SafeLoader)


@check_filepath
def render_template(template_file, dict_):
    """
    :type template_file: str
    :param template_file: template file
    :type dict\_: dict
    :param dict\_: dictionary to be rendered to the template
    """
    with open(template_file, 'r') as f:
        str_ = jinja2.Template(f.read()).render(dict_)
    return str_


###
# For FRONT
###


def rowsof(filename, delims=" ", **kwargs):
    r"""
    Yields the rows of the file as lists delimited by ``delims``.
    Empty entries in lists are removed. Empty rows are removed.

    :type filename: str
    :param filename:
    :type delims: iterable, optional
    :param delims: defaults to '" "' (a whitespace),
        For example, list or string containing all accepted delimiters.
    :return: A generator yielding rows of the file (``filename``) as lists.
    """
    delims = "|".join(dl for dl in delims)
    rows = read_file(filename, **kwargs)
    if rows is None:
        return []
    for row in rows:
        row = row.strip("\n")
        row = re.split(delims, row)
        row = [r for r in row if r]
        if not row:
            continue
        yield row


###
# For BACK
###


def write_csv(filename, rows, mode='w', delimiter=";", singlerow=False):
    """
    :type filename: str
    :param filename: filename of the csv created
    :type rows: list
    :param rows: list of list be written into csv
    :type mode: str, optional
    :param mode: defaults to 'w' (write)
    :type delimiter: str, optional
    :param delimiter: defaults to ';', csv delimiter
    :type singlerow: bool, optional
    :param singlerow: Write single or multiple rows to csv.
        If ``False``, ``rows`` should be list of lists.
    """
    create_missing_folders(filename)

    with open(filename, mode, newline='') as f:
        writer = csv.writer(f, delimiter=delimiter, quotechar='"',
                            quoting=csv.QUOTE_MINIMAL)
        if singlerow:
            writer.writerow(rows)
        else:
            writer.writerows(rows)
        f.flush()


def save_obj(filename, obj):
    """
    A function to pickle objects

    :type filename: str
    :param filename: A file where the object will be saved
    :type obj:
    :param obj: Any object that can be pickled
    """
    with open(filename, 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


@check_filepath
def load_obj(filename):
    """
    A function to unpickle objects

    :type filename: str
    :param filename: A file containing the pickled object
    :rtype:
    :return: Any object contained in the given file
    """
    with open(filename, 'rb') as f:
        return pickle.load(f)


def write_file(filename, str_, mode='w', cmf=True):
    r"""
    :type filename: str
    :param filename: filename of the file created
    :type str\_: str
    :param str\_: a text to written
    :type mode: str, optional
    :param mode: defaults to 'w' (write)
    :type cmf: bool, optional
    :param cmf: defaults to ``True``, If ``True`` missing folder
        in ``filename`` aer created before writing
    """
    if cmf:
        create_missing_folders(filename)
    if mode == "a" and not os.path.isfile(filename):
        msg = "Trying to append to a non existing file: {}".format(filename)
        messenger(msg, "W")
        return
    with open(filename, mode) as f:
        f.write(str_)


@check_filepath
def read_file(filename, mode="r", **kwargs):
    """
    :type filename: str
    :param filename: filename of the file to be read
    :type mode: str, optional
    :param mode: defaults to 'r' (read)
    :rtype: list
    :return: rows of the given file as list
    """
    with open(filename, mode) as f:
        rows = f.readlines()
    return rows


def append_to_file(filename, text, header):
    """
    If path defined in ``filename`` does not exist, new file is created and
    ``header`` is written in the file. If ``text`` is list, writes csv.

    :type filename: str
    :param filename:
    :type text: str
    :param text:
    :type header: str
    :param header:
    """
    create_missing_folders(filename)

    write_function = write_file
    if isinstance(text, list):
        if not isinstance(header, list):
            header = [header]
        write_function = functools.partial(write_csv, singlerow=True)

    if not os.path.isfile(filename):
        msg = "No previous file: {}".format(filename)
        messenger(msg, "R")
        write_function(filename, header, mode='w')

    write_function(filename, text, mode='a')


def create_missing_folders(filename):
    """
    Creates full path to given ``filename``.

    :type filename: str
    :param filename: file or folder
    """
    folder = os.path.dirname(filename)
    if not os.path.isdir(folder):
        os.makedirs(folder)
        msg = "Creating new folder: {}".format(folder)
        messenger(msg, "R")


def invalid_mseed(path):
    """
    Checks if miniseed file is valid and readable before reading it.
    At the moment only check is if filesize is between
    128 and 2^31 in bytes.

    :type path: str
    :param path: path to file
    :rtype: str
    :return: returns message describing the problem with the file.
        If empty string is returned, no problems are present.
    """
    msg = ""
    length = os.path.getsize(path)
    if length < 128 or length > 2**31:
        msg += "File with invalid size: {}".format(path)
    return msg


@check_filepath
@debugger
def get_stream(path="", format_="MSEED"):
    r"""
    :type path: str
    :param path: path to seismic data file
    :type format\_: str, optional
    :param format\_: defaults to ``MSEED``
    :rtype: :class:`~obspy.core.stream.Stream` or None
    :return: If invalid miniseed file(path) is provided,
        empty stream is returned.
    """
    msg = invalid_mseed(path)
    if msg:
        messenger(msg, "M")
        return Stream()
    else:
        try:
            st = read(path, format=format_)
            return st
        except InternalMSEEDError as e:
            messenger(str(e), "W")
            return Stream()
