# -*- coding: utf-8 -*-
"""
    Base Experiment Model
    =====================
    Base class for the experiments. ``BaseExperiment`` defines the common patterns that every experiment should have.
    Importantly, it starts an independent process called publisher, that will be responsible for broadcasting messages
    that are appended to a queue. The messages rely on the pyZMQ library and should be tested further in order to
    assess their limitations. The general pattern is that of the PUB/SUB, with one publisher and several subscribers.

    The messages should include a *topic* and data. For this, the elements in the queue should be dictionaries with two
    keywords: **data** and **topic**. ``data['data']`` will be serialized through the use of cPickle, and is handled
    automatically by pyZQM through the use of ``send_pyobj``. The subscribers should be aware of this and use either
    unpickle or ``recv_pyobj``.

    In order to stop the publisher process, the string ``'stop'`` should be placed in ``data['data']``. The message
    will be broadcast and can be used to stop other processes, such as subscribers.

    .. TODO:: Check whether the serialization of objects with cPickle may be a bottleneck for performance.

    :license: MIT, see LICENSE for more details
    :copyright: 2020 Aquiles Carattino
"""
import atexit
import os
import weakref
from multiprocessing import Process, Event
from time import sleep
from typing import Union

import yaml

from experimentor.core.meta import ExperimentorProcess
from experimentor.core.signal import Signal
from experimentor.core.subscriber import Subscriber
from experimentor.lib.log import get_logger
from experimentor.models.decorators import not_implemented
from experimentor.models.models import BaseModel
from experimentor.models.meta import MetaModel

_experiments = weakref.WeakSet()  # Stores all the defined experiments
logger = get_logger(__name__)


class FormatPlaceholder:
    def __init__(self, key):
        self.key = key

    def __format__(self, spec):
        result = self.key
        if spec:
            result += ":" + spec
        return "{" + result + "}"


class FormatDict(dict):
    """Simple solution to do partial formatting of strings. For example:

    >>> a = 'fiber_end_{cartridge}_{i:04}.npy'
    >>> cartridge = 123
    >>> a.format_map(FormatDict(cartridge=cartridge))
    'fiber_end_123_{i:04}.npy'
    """

    def __missing__(self, key):
        return FormatPlaceholder(key)


class MetaExperiment(MetaModel):
    """ Meta Model type which will be responsible for keeping track of all the created experiments. It will also be
    responsible for registering the publisher, in order to have only one throughout the program and accessible from
    other parts of the program. This meta class may be overkill, since in principle every program will be only one
    experiment, but this is left as an effort to be future-proof.

    .. note:: Defining meta classes may generate a feeling of obscurantism in the code. It may be wise to remove it and
        find a simpler/straightforward approach.

    """

    def __init__(cls, name, bases, attrs):
        # Create class
        super(MetaExperiment, cls).__init__(name, bases, attrs)

        if not attrs.get("_abstract", False):
            _experiments.add(cls)

    def __call__(cls, *args, **kwargs):
        # Create instance (calls __init__ and __new__ methods)
        inst = super(MetaExperiment, cls).__call__(*args, **kwargs)
        # Store weak reference to instance. WeakSet will automatically remove
        # references to objects that have been garbage collected
        cls._instances.add(inst)

        return inst

    def _get_instances(cls, recursive=False):
        """Get all instances of this class in the registry. If recursive=True
        search subclasses recursively"""
        instances = list(cls._instances)
        if recursive:
            for Child in cls.__subclasses__():
                instances += Child._get_instances(recursive=recursive)

        # Remove duplicates from multiple inheritance.
        return list(set(instances))


class BaseExperiment(BaseModel, metaclass=MetaExperiment):
    _abstract = True


class Experiment(BaseExperiment):
    """ Base class to define experiments. Should keep track of the basic methods needed regardless of the experiment
    to be performed. For instance, a way to start and a way to finalize a measurement. This class is not meant to be
    instantiated directly, but should be subclassed in each project.

    Parameters
    ----------
    filename: str or None
        Path to the config file that will be loaded. Ideally it should be an absolute path, to prevent problems. If you
        submit a relative path, it will depend on how you are running the program if the file will be found or not.

    Attributes
    ----------
    config: Properties
        Properties object to store the values of the parameters of the experiments. See
        :mod:`experimentor.models.properties` to understand the options and how it works
    logger: logger
        The logger of the experiment, this is for internal use only
    """
    _abstract = True
    start = Signal()

    def __init__(self, filename=None):
        super().__init__()
        self.config = {}  # Dictionary storing the configuration of the experiment
        self.logger = get_logger(name=__name__)

        self._connections = []
        self.subscriber_events = []
        self.initialize_threads = []  # Threads to initialize several devices at the same time
        if filename:
            self.load_configuration(filename)

        atexit.register(self.finalize)
        self.is_alive = True

    def stop_subscribers(self):
        """ Puts the proper data into every alive subscriber in order to stop it.
        """
        self.logger.info('Stopping the subscribers')
        for event in self.subscriber_events:
            event.set()

        for connection in self._connections:
            if connection['process'].is_alive():
                self.logger.info('Stopping {}'.format(connection['method']))
                connection['event'].set()

    def connect(self, method, topic, *args, **kwargs):
        """ Async method that connects the running publisher to the given method on a specific topic.

        :param method: method that will be connected on a given topic
        :param str topic: the topic that will be used by the subscriber to discriminate what information to collect.
        :param args: extra arguments will be passed to the subscriber, which in turn will pass them to the function
        :param kwargs: extra keyword arguments will be passed to the subscriber, which in turn will pass them to the function
        """
        event = Event()
        self.logger.debug('Arguments: {}'.format(args))
        arguments = [method, topic, event]
        for arg in args:
            arguments.append(arg)

        self.logger.info('Connecting {} on topic {}'.format(method.__name__, topic))
        self.logger.debug('Arguments: {}'.format(args))
        self.logger.debug('KWarguments: {}'.format(kwargs))
        self._connections.append({
            'method': method.__name__,
            'topic': topic,
            'process': ExperimentorProcess(target=Subscriber, args=arguments, kwargs=kwargs),
            'event': event,
        })
        self._connections[-1]['process'].start()

    def load_configuration(self, filename, loader=yaml.SafeLoader):
        """ Loads the configuration file in YAML format.

        :param str filename: full path to where the configuration file is located.
        :raises FileNotFoundError: if the file does not exist.
        """
        self.logger.info('Loading configuration file {}'.format(filename))
        try:
            with open(filename, 'r') as f:
                self.config = yaml.load(f, Loader=loader)
                self.logger.debug('Config loaded')
                self.logger.debug(self.config)
        except FileNotFoundError:
            self.logger.error('The specified file {} could not be found'.format(filename))
            raise
        except Exception as e:
            self.logger.exception('Unhandled exception')
            raise

    @staticmethod
    def make_filename(folder: Union[str, tuple], filename: str):
        """This routine will check if the folder to store data exists, and create it if not. It will also check if the
        file exists, if it does, it will increase by 1 a counter until an available name appears, and return both the
        directory and the filename.

        :param filename: if it contains a '{i}' or similar in its specification, it will use it as a counter, if not,
            the number will be prepended to the filename
        :param folder: either a string with the full path to the folder (bear in mind differences of folder separators)
            or a tuple that will be joined using os.path.join
        """
        if isinstance(folder, tuple):
            folder = os.path.join(*folder)
        if not os.path.isdir(folder):
            os.makedirs(folder)

        i = 0
        base_filename = filename
        if base_filename == filename.format(i=i):
            base_filename = '{i}_' + filename
        filename = base_filename.format(i=i)
        if os.path.isfile(os.path.join(folder, filename)):
            i += 1
            filename = base_filename.format(i=i)

        return folder, filename

    @property
    def num_threads(self):
        return len(self._threads)

    @property
    def connections(self):
        return [conn for conn in self._connections if conn['process'].is_alive()]

    @property
    def alive_threads(self):
        alive_threads = 0
        for thread in self._threads:
            if thread[1].is_alive():
                alive_threads += 1
        return alive_threads

    @property
    def list_alive_threads(self):
        alive_threads = []
        for thread in self._threads:
            if thread[1].is_alive():
                alive_threads.append(thread)
        return alive_threads

    @not_implemented
    def set_up(self):
        """ Needs to be overridden by child classes.
        """
        pass

    def finalize(self):
        """ Needs to be overridden by child classes.
        """
        self.logger.info(f'Going to finalize {len(self.subscribers)} subscribers')

        if len(self.subscribers) > 0:
            for subscriber in self.subscribers:
                subscriber.stop()
                while subscriber.is_alive():
                    sleep(0.001)
                self.logger.info(f'Finalized {subscriber}')

        self.clean_up_threads()
        for thread in self.list_alive_threads:
            self.logger.debug(f'{thread} is alive when finalizing')

        self.is_alive = False

    def update_config(self, **kwargs):
        self.logger.info('Updating config')
        self.logger.debug('Config params: {}'.format(kwargs))
        self.config.update(**kwargs)

    def __enter__(self):
        self.set_up()
        return self

    def __exit__(self, *args):
        self.logger.info("Exiting the experiment")
        self.finalize()
        self.logger.info('Finished the base experiment')

    def __repr__(self):
        return f"Experiment {id(self)}"
