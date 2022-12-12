import os
from typing import Optional, List
import yaml

from .hooks_datacfg import Model


class DevConfig(Model):
    """
    Configuration options useful for developing robotpy-build wrappers.
    To use these, set the environment variable RPYBUILD_GEN_FILTER=filename.yml
    """

    #: When set this will only generate new wrapping code for the specified
    #: headers (left side of generate in pyproject.toml). Existing wrapping
    #: code will not be deleted during a build.
    #:
    #: Useful in conjunction with ccache
    only_generate: Optional[List[str]] = None


def get_dev_config(name: str) -> Optional[DevConfig]:
    # name is the wrapper config, not used currently
    genfilter = os.environ.get("RPYBUILD_GEN_FILTER")
    if genfilter:
        with open(genfilter) as fp:
            data = yaml.safe_load(fp)
    else:
        data = {}

    return DevConfig(**data)
