import argparse
import os

import dotmap
import requests
import yaml

import config


class Arguments:

    def __init__(self):

        self.root = config.root
        self.sample_size = config.sample_size

    @staticmethod
    def url(urlstring: str) -> requests.models.Response:
        """
        Ascertains that the URL argument is valid

        :param urlstring: A URL string (to a YAML file)
        :return: The URL string if it is a valid URL, otherwise raise an error
        """

        try:
            req = requests.get(url=urlstring)
            req.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise err

        return req

    def paths(self, partitions):
        """
        Creates a path relative to the project's root directory
        :param partitions:
        :return:
            path: The created from a list of directories
        """

        path = self.root
        for partition in partitions:
            path = os.path.join(path, partition)

        return path

    def parameters(self, elements: requests.models.Response):
        """
        :param elements: The content of the input YAML file
        :return: A dot map of the parameters in the YAML file; and supplementary parameters
        """

        text = yaml.safe_load(elements.text)
        var = dotmap.DotMap(text)

        # Paths
        var.target.path = self.paths(var.target.directory)
        var.target.images.path = self.paths(var.target.images.directory)
        var.target.splits.path = self.paths(var.target.splits.directory)
        var.target.zips.path = self.paths(var.target.zips.directory)

        # Calculations
        var.augmentation.images.strip = int(var.augmentation.images.remnant / 2)

        return var

    def sample(self, value):
        if int(value) < self.sample_size:
            raise argparse.ArgumentTypeError("The argument '--sample' must be a positive integer "
                                             "greater than or equal to {}".format(self.sample_size))
        return int(value)
