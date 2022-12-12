# Copyright (c) 2020, eQualit.ie inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.


import datetime
import os
import logging
import re

from functools import wraps

import yaml

from baskerville.util.enums import ModelEnum, BaseStrEnum

FOLDER_MODELS = 'models'
FOLDER_CACHE = 'cache'


def parse_config(path=None, data=None, tag='!ENV'):
    """
    Load a yaml configuration file and resolve any environment variables
    The environment variables must have !ENV before them and be in this format
    to be parsed: ${VAR_NAME}.
    E.g.:

    database:
        host: !ENV ${HOST}
        port: !ENV ${PORT}
    engine:
        log_path: !ENV '/var/${LOG_PATH}'
        something_else: !ENV '${AWESOME_ENV_VAR}/var/${WOOHOO_VAR}'

    :param path: the path to the yaml file
    :param data: the yaml data itself as a stream
    :param tag: the tag to look for
    :return: the dict configuration
    :rtype: dict[str, T]
    """
    # pattern for global vars
    pattern = re.compile(r'.*?\${(\w+)}.*?')
    loader = yaml.SafeLoader
    loader.add_implicit_resolver(tag, pattern, None)

    def constructor_env_variables(loader, node):
        """
        Extracts the environment variable from the node's value
        :param yaml.Loader loader: the yaml loader
        :param node: the current node in the yaml
        :return: the parsed string that contains the value of the environment
        variable
        """
        value = loader.construct_scalar(node)
        match = pattern.findall(value)
        if match:
            full_value = value
            for g in match:
                full_value = full_value.replace(
                    f'${{{g}}}', os.environ.get(g, g)
                )
            return full_value
        return value

    loader.add_constructor(tag, constructor_env_variables)

    if path:
        with open(path) as conf_data:
            return yaml.load(conf_data, Loader=loader)
    elif data:
        return yaml.load(data, Loader=loader)
    else:
        raise ValueError('Either a path or data should be defined as input')


def get_logger(
        name, logging_level=logging.DEBUG, output_file='baskerville.log'
):
    """
    Creates a logger that logs to file and console with the same logging level
    :param str name: the logger name
    :param int logging_level: the logging level
    :param str output_file: the file to save to
    :return: the initialized logger
    :rtype: logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging_level)
    if not len(logger.handlers):
        file_handler = logging.FileHandler(output_file)
        console_handler = logging.StreamHandler()

        file_handler.setLevel(logging_level)
        console_handler.setLevel(logging_level)

        # create formatter and add it to the handlers
        formatter = logging.Formatter(
            '%(asctime)s %(name)s.%(funcName)s +%(lineno)s: %(levelname)-8s'
            ' [%(process)d] %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    return logger


def caller_info(f):
    """
    Log the caller of a callable
    :param callable f: the callable to wrap
    :return: the wrapper
    """

    @wraps(f)
    def func(*args, **kwargs):
        import inspect
        caller = inspect.stack()[1]
        module = inspect.getmodule(caller[0])
        print('[{}]'.format(module.__name__))
        return f(*args, **kwargs)

    return func


def generate_random_ip():
    """
    Returns a random IP as a string
    :return: a random stringified ip
    :rtype: str
    """
    from random import randint
    return '.'.join(str(randint(0, 255)) for _ in range(4))


def get_objects_attributes(obj, exclude=()):
    return [
        attr
        for attr in dir(obj)
        if attr not in exclude and not attr.startswith('_') and not callable(getattr(obj, attr))
    ]


def have_common_elements(first_list, second_list):
    """
    Retuns True if all the elements in the first list are also in the second.
    :param list[T] first_list:
    :param list[T] second_list:
    :return: True if lists are the same, else False
    """
    return len(set(first_list).intersection(
        set(second_list))) == len(second_list)


def lines_in_file(path):
    """
    Returns the number of lines in a file
    :param str path:
    :return: the number of lines
    :rtype: int
    """
    with open(path) as f:
        position = f.tell()
        f.seek(0, 2)  # seek to end
        num_rows = f.tell()
        f.seek(position)  # back

    return num_rows


def periods_overlap(
        start, end, other_start, other_end, allow_closed_interval=False
) -> bool:
    """
    Checks if this time period overlaps with another time period.
    It checks against the following cases:

    if not allow_closed_interval

    |----o==========o----.*****************.------|
        ostart    oend  start              end

    |-----.*********.------o===========o----------|
        start     end    ostart     oend


    if allow_closed_interval (oend/start or end/ostart are allowed to be equal)

    |----o==========o.************************.---|
        ostart    oend/start                end

    |-----.*********.o===========o----------------|
        start    end/ostart     oend

    :param datetime.datetime start: the start time of the first period to
    check against
    :param datetime.datetime end: the end time of the first period to
    check against
    :param datetime.datetime other_start: the start time of the second period
    to check against
    :param datetime.datetime other_end: the end time of the second period
    to check against
    :param bool allow_closed_interval: True to consider e.g. same oend and
    start as not overlapping, False to consider that e.g. same oend and start
    means that they overlap at that point.
    :return: True if they overlap, False otherwise
    :rtype: bool
    """
    if allow_closed_interval:
        # the not overlapping check does not take equality into account
        return not (other_start < start and other_end < start) and not (other_start > end and other_end > end)
    return not (other_start < start and other_end <= start) and not (other_start >= end and other_end > end)


def get_default_data_path() -> str:
    """
    Returns the absolute path to the data folder
    :return:
    """
    baskerville_root = os.environ.get('BASKERVILLE_ROOT')
    if baskerville_root:
        return os.path.join(baskerville_root, 'data')
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'data'
    )


def get_default_ip_cache_path() -> str:
    """
    Returns the absolute path to the ip cache folder
    :return:
    """
    baskerville_root = os.environ.get('BASKERVILLE_ROOT')
    if baskerville_root:
        return os.path.join(baskerville_root, 'ip_cache')
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'ip_cache'
    )


def get_days_in_year(year):
    """
    Returns the number of days in a specific year
    :param int year: the number of the year
    :return: the number of days in the specific year
    :rtype: int
    """
    from calendar import Calendar
    days_in_year = 0
    for m in Calendar().yeardays2calendar(year, width=12)[0]:
        for w in m:
            days_in_year += len([pair for pair in w if pair[0] != 0])
            # len(list(filter((0).__ne__, w)))

    return days_in_year


def get_days_in_month(year, month):
    """
    Returns the number of days in the month of a specific year
    :param int year: the year of the month
    :param int month: the number of the month
    :return:
    :rtype: int
    """
    from calendar import monthrange
    return monthrange(year, month)[1]


class SerializableMixin(object):
    _extra_cols = ()
    _remove = ()

    def to_dict(self, cols=()):
        """

        :param tuple cols:
        :return:
        :rtype: dict[str, T]
        """
        if not cols:
            if getattr(self, '__table__') is not None:
                cols = self.__table__.columns
                basic_attrs = {c.name: getattr(self, c.name)
                               for c in cols
                               if c.name not in self._remove and
                               not c.name.startswith('_')}
            else:
                cols = dir(self)
                basic_attrs = {c: getattr(self, c)
                               for c in cols
                               if c not in self._remove and
                               not c.startswith('_') and not callable(getattr(self, c))}
        else:
            basic_attrs = {c: getattr(self, c)
                           for c in cols
                           if c not in self._remove and
                           not c.startswith('_')
                           and not callable(getattr(self, c))}

        extra_attrs = {}
        if self._extra_cols:
            for attr in self._extra_cols:
                d = getattr(self, attr)
                if d is None:
                    continue
                if isinstance(d, (list, tuple, set)):
                    extra_attrs[attr] = [each.to_dict() for each in d]
                else:
                    extra_attrs[attr] = d.to_dict()
            basic_attrs.update(extra_attrs)

        for k, v in basic_attrs.items():
            if isinstance(v, SerializableMixin) and hasattr(v, 'to_dict'):
                if hasattr(v, 'parent') and 'parent' not in v._remove:
                    v._remove += ('parent')
                basic_attrs[k] = v.to_dict()
            if isinstance(v, BaseStrEnum):
                basic_attrs[k] = str(v)

        return basic_attrs


class TimeBucket(object):
    """
    Representation of time bucket: seconds and timedelta
    """

    def __init__(self, time_bucket=120):
        self._sec = time_bucket
        self._td = datetime.timedelta(seconds=self._sec)

    @property
    def sec(self):
        return self._sec

    @property
    def td(self):
        return self._td


def instantiate_from_str(str_class, *args, **kwargs):
    """
    Get class instance from string
    :param str_class: the full path to class, e.g. pyspark.sql.DataFrame
    :return: the instance of the requested class
    """
    return class_from_str(str_class)(*args, **kwargs)


def class_from_str(str_class):
    """
    Imports the module that contains the class requested and returns
    the class
    :param str_class: the full path to class, e.g. pyspark.sql.DataFrame
    :return: the class requested
    """
    import importlib

    split_str = str_class.split('.')
    class_name = split_str[-1]
    module_name = '.'.join(split_str[:-1])
    module = importlib.import_module(module_name)

    return getattr(module, class_name)


def get_timestamp():
    """
    Get a string UTC timestamp
    :return: YYYY_MM_DD__HH:MM
    """
    ts = datetime.datetime.utcnow()
    return f'{ts.year:02}_{ts.month:02}_{ts.day:02}___{ts.hour:02}_{ts.minute:02}'


def get_model_path(storage_path, model_name='model'):
    """
    Crete the model full path for the given storage and the name of the model\
    :param storage_path: the path to the storage root folder
    :param model_name:
    :return: storage_path/models/mdel_name__2020_01_01__14:30
    """
    return os.path.join(storage_path,
                        FOLDER_MODELS,
                        f'{model_name}__{get_timestamp()}')


def load_model_from_path(model_path, spark=None):
    """
    Instantiate the proper model and load from the path.
    :param model_path: the full path to the model.
    :param spark: The spark context. Not required for local paths.
    :return: The instance of the loaded model
    """
    name = os.path.basename(model_path).split('_')[0]
    if name not in [e.name for e in ModelEnum]:
        raise RuntimeError(
            f'Model path {model_path} is invalid. Model name {name} is not in {[e.name for e in ModelEnum]}')
    model = instantiate_from_str(ModelEnum[name].value)
    model.load(model_path, spark)
    return model


class Singleton(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super(Singleton, cls).__new__(cls)
        return cls._instance


class Borg(object):
    _shared_state = {}

    def __new__(cls, *args, **kwargs):
        obj = super(Borg, cls).__new__(cls)
        obj.__dict__ = cls._shared_state
        return obj
