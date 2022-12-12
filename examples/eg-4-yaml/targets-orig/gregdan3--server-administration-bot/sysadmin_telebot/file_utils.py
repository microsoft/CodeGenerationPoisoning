import logging
import os

import yaml
from dotenv import load_dotenv

__all__ = ["load_yml_file", "TG_BOT_KEY"]
_log = logging.getLogger(__name__)

load_dotenv()
TG_BOT_KEY = os.environ.get("TG_BOT_KEY")
if not TG_BOT_KEY:
    _log.critical("No telegram bot key provided! Shutting down...")
    exit(1)


def load_yml_file(filename):
    with open(filename, "r") as f:
        command = yaml.full_load(f)
    return command
