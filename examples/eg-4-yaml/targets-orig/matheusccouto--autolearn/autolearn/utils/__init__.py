""" General helper functions. """

import functools
from typing import Iterable, Dict

import yaml


def flatten(i: Iterable) -> Iterable:
    """ Flatten an irregular iterable. """
    for i in i:
        if isinstance(i, Iterable):
            yield from i
        else:
            yield i


def negate(function):
    """ Decorator to negate the return of a function. """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        return -1 * function(*args, **kwargs)

    return wrapper


def read_yaml(path: str) -> Dict:
    """ Read YAML file. """
    with open(path, "r") as file:
        return yaml.load(file, Loader=yaml.FullLoader)
