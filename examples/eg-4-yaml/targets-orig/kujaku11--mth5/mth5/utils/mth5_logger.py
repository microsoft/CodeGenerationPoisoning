"""
Logger
===========

Setup a logger with two handlers to remove redundancy between logs entries
One is a stream handler for any messages to the console.  The other is
either a file handler or a null handler.

"""

from pathlib import Path
import yaml
import logging
import logging.config
from concurrent_log_handler import ConcurrentRotatingFileHandler

# =============================================================================
# Global Variables
# =============================================================================
LEVEL_DICT = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

LOG_FORMAT = logging.Formatter(
    "%(asctime)s [line %(lineno)d] %(name)s.%(funcName)s - %(levelname)s: %(message)s"
)
# Get the configuration file path, should be in same directory as this file
CONF_PATH = Path(__file__).parent
CONF_FILE = Path.joinpath(CONF_PATH, "logging_config.yaml")

# make a folder for the logs to go into.
LOG_PATH = CONF_PATH.parent.parent.joinpath("logs")

if not LOG_PATH.exists():
    LOG_PATH.mkdir()

if not CONF_FILE.exists():
    CONF_FILE = None


def load_logging_config(config_fn=CONF_FILE):
    """
    configure/setup the logging according to the input configfile

    :param configfile: .yml, .ini, .conf, .json, .yaml.
    Its default is the logging.yml located in the same dir as this module.
    It can be modofied to use env variables to search for a log config file.
    """
    if config_fn:
        config_file = Path(config_fn)
        with open(config_file, "r") as fid:
            config_dict = yaml.safe_load(fid)

    else:
        config_dict = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s [line %(lineno)d] %(name)s.%(funcName)s - %(levelname)s: %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "standard",
                    "stream": "ext://sys.stdout",
                }
            },
            "loggers": {
                "__main__": {
                    "level": "DEBUG",
                    "handlers": ["console"],
                    "propagate": False,
                }
            },
            "root": {"level": "DEBUG", "handlers": ["console"], "propogate": False},
        }

    logging.config.dictConfig(config_dict)


def setup_logger(logger_name, fn=None, level="debug"):
    """
    Create a logger, can write to a separate file.  This will write to
    the logs folder in the mt_metadata directory.

    :param logger_name: name of the logger, typically __name__
    :type logger_name: string
    :param fn: file name to write to, defaults to None
    :type fn: TYPE, optional
    :param level: DESCRIPTION, defaults to "debug"
    :type level: TYPE, optional
    :return: DESCRIPTION
    :rtype: TYPE

    """

    logger = logging.getLogger(logger_name)

    # if there is a file name create file in logs directory
    if fn is not None:
        # need to clear the handlers to make sure there is only
        # one call per logger plus stdout
        if logger.hasHandlers():
            logger.handlers.clear()

        logger.propagate = False
        # want to add a stream handler for any Info print statements as stdOut
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(LOG_FORMAT)
        stream_handler.setLevel(LEVEL_DICT["info"])
        logger.addHandler(stream_handler)

        fn = LOG_PATH.joinpath(fn)
        exists = False
        if fn.exists():
            exists = True

        if fn.suffix not in [".log"]:
            fn = Path(fn.parent, f"{fn.stem}.log")

        # fn_handler = logging.FileHandler(fn)
        fn_handler = ConcurrentRotatingFileHandler(fn, maxBytes=2 ** 21, backupCount=2)
        fn_handler.setFormatter(LOG_FORMAT)
        fn_handler.setLevel(LEVEL_DICT[level.lower()])
        logger.addHandler(fn_handler)
        if not exists:
            logger.info(f"Logging file can be found {logger.handlers[-1].baseFilename}")

    return logger
