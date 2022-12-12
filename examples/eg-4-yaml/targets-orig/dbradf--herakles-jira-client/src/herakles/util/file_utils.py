"""Various utilities for working with files."""
from typing import Dict

import yaml


def read_yaml_file(file_path: str) -> Dict:
    """
    Read a yaml file and return the contents as a dictionary.

    :param file_path: Path to yaml files.
    :return: Dictionary with file contents.
    """
    with open(file_path) as file_contents:
        return yaml.safe_load(file_contents)
