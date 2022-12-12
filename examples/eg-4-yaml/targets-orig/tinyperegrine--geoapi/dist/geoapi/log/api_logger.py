"""Logging Module

Returns:
    logging.Logger: Sets up a yaml based logger (which logs through a queue) or a basic logger
"""

import logging
import logging.config
import logging.handlers
import asyncio
from pathlib import Path
from queue import SimpleQueue
from typing import List
import yaml
import geoapi.config.api_configurator as config
from geoapi.common.json_models import LogEnum


class LocalQueueHandler(logging.handlers.QueueHandler):
    """Simplified queue handler for logging in async scenarios
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Removed the call to self.prepare(), handle task cancellation
        # exceptions in logging sub-system are not raised, just printed out
        try:
            self.enqueue(record)
        except asyncio.CancelledError as cerr:
            print(str(cerr))
            raise
        except Exception as exc: # pylint: disable=broad-except
            print(str(exc))
            self.handleError(record)


# currently unused
class APIFormatter(logging.Formatter):
    """Custom Formatter
    Defines the default format for logging messages and appends additional info to debug messages
    Experimental code - not used.
    """

    date_format = "%Y-%m-%d %H:%M:%S"
    default_format_string = \
        "%(asctime)s.%(msecs)03d [%(process)d:%(thread)d] %(levelname)s %(name)s [-] %(message)s"
    debug_format_suffix = "%(funcName)s %(pathname)s:%(lineno)d"

    def __init__(self):
        super().__init__(fmt=APIFormatter.default_format_string,
                         datefmt=APIFormatter.date_format,
                         style='%')

    def format(self, record):
        format_orig = self._style._fmt # pylint: disable=protected-access
        if record.levelno in [logging.DEBUG, logging.ERROR, logging.CRITICAL]:
            # pylint: disable=protected-access
            self._style._fmt = APIFormatter.default_format_string + " " + \
                APIFormatter.debug_format_suffix

        result = logging.Formatter.format(self, record)
        self._style._fmt = format_orig # pylint: disable=protected-access
        return result


def _setup_logging_queue() -> None:
    """Move log handlers to a separate thread.

    Replace handlers on the root logger with a LocalQueueHandler,
    and start a logging.QueueListener holding the original
    handlers.

    """
    queue: SimpleQueue = SimpleQueue()
    root = logging.getLogger()

    handlers: List[logging.Handler] = []

    handler = LocalQueueHandler(queue)
    root.addHandler(handler)
    for configured_handler in root.handlers[:]:
        if configured_handler is not handler:
            root.removeHandler(configured_handler)
            handlers.append(configured_handler)

    listener = logging.handlers.QueueListener(queue, *handlers, respect_handler_level=True)
    listener.start()


def init(level: LogEnum, use_yml: bool = True) -> logging.Logger:
    """Creates the Python Logger - either a basic logger or a logger configured from yaml

    Args:
        level (LogEnum, required): log level enum - one of the five possible log levels
        use_yml (bool, optional): configure based on yaml. Defaults to True.

    Constants:
        embedded_log_config_yml_filepath: Path to the embedded yaml file,
            defaults to 'geoapi/log/logging.yml'
        GEOAPI_LOG_CONFIG_YML = Env variable for path to custom yaml file,
            and by default is empty so built-in yaml is used

    Returns:
        logging.Logger: A fully configured logger
    """
    # First setup basic logging in case use_yml is true but yaml loading fails
    logging.basicConfig(level=level)
    logger = logging.getLogger()

    if use_yml:
        # First setup default yaml logging config - in case custom yaml is specified but fails
        embedded_log_config_yml_filepath: Path = Path('geoapi/log/logging.yml')
        with open(embedded_log_config_yml_filepath) as yml_file:
            logging_config = yaml.safe_load(yml_file.read())
            logging.config.dictConfig(logging_config)

        # get the custom yaml config file path if specified by env
        # (e.g. in case production logging is different from dev logging)
        # also, catch logging subsystem exceptions and do not propogate these.
        env_path = config.API_CONFIG['GEOAPI_LOG_CONFIG_YML']
        if env_path:
            try:
                with open(env_path) as yml_file:
                    logging_config = yaml.safe_load(yml_file.read())
                    logging.config.dictConfig(logging_config)
            # pylint: disable=broad-except
            except Exception as exc:
                logging.exception('Error loading custom yaml config for logging, \
                    default yaml config loaded instead. \
                        custom yaml: %s, error: %s', env_path, str(exc))

        logger = logging.getLogger()
        logger.setLevel(level)

    # finally setup queue based logging
    _setup_logging_queue()
    logger.info('Using Log Level: %s', logging.getLevelName(level))
    return logger
