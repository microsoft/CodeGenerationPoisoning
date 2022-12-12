import logging
import os

import yaml

logger = logging.getLogger(__name__)


class Promise:
    def __init__(self, path):
        self.filename = path
        self.data = None

    def __getattr__(self, attr):
        if self.data is None:
            logger.debug(f"loading details for {self.filename}")
            with open(self.filename) as fd:
                self.data = yaml.load(fd)
        return self.data.get(attr)


class Iterator:
    def __init__(self, files):
        self.files = list(files)

    def __next__(self):
        if not self.files:
            raise StopIteration()
        return Promise(self.files.pop(0))


class Walker:
    prefix = None

    def __init__(self, directory):
        self.directory = directory

    def __iter__(self):
        return Iterator(
            os.path.join(self.directory, x)
            for x in os.listdir(self.directory)
            if x.startswith(self.prefix)
        )


class IssueWalker(Walker):
    prefix = "issue-"


class UserWalker(Walker):
    prefix = "user-"
