import pkgutil
import logging
from argparse import ArgumentParser
import signal
import os
import yaml
from importlib import import_module
import time

from cifsdk.constants import LOG_FORMAT, RUNTIME_PATH, LOGLEVEL, VERSION
from . import color


def settings(f):
    if not os.path.exists(f):
        return

    with open(f, "r") as f:
        return yaml.load(f, Loader=yaml.SafeLoader)


def get_argument_parser():
    BasicArgs = ArgumentParser(add_help=False)
    BasicArgs.add_argument('-d', '--debug', dest='debug', action="store_true")
    BasicArgs.add_argument('-v', '--verbose', action='store_true')
    BasicArgs.add_argument('-V', '--version', action='version',
                           version=VERSION)
    BasicArgs.add_argument(
        "--runtime-path",
        help="specify the runtime path [default %(default)s]",
        default=RUNTIME_PATH
    )
    return ArgumentParser(parents=[BasicArgs], add_help=False)


def load_plugin(path, plugin, prefix='cif_'):
    for loader, modname, is_pkg in pkgutil.iter_modules(path):
        if modname == plugin or modname == 'z{}'.format(plugin):
            p = loader.find_module(modname).load_module(modname)
            p = p.Plugin
            return p

    p = import_module(f"{prefix}{plugin}")
    return p.Plugin


def load_plugins(path):
    p = []
    for loader, modname, is_pkg in pkgutil.iter_modules(path):
        p.append(loader.find_module(modname).load_module(modname))

    return p


def init_plugins(path):
    return {
        name: import_module(name)
        for finder, name, ispkg
        in pkgutil.iter_modules()
        if name.startswith(path)
    }


def setup_logging(args):
    loglevel = logging.getLevelName(LOGLEVEL)

    if args.debug:
        loglevel = logging.DEBUG

    console = logging.StreamHandler()
    logging.getLogger('').setLevel(loglevel)
    console.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger('').addHandler(console)


def setup_signals(name):
    logger = logging.getLogger(__name__)

    def sigterm_handler(_signo, _stack_frame):
        logger.info('SIGTERM Caught for {}, shutting down...'.format(name))
        raise SystemExit

    signal.signal(signal.SIGTERM, sigterm_handler)


def setup_runtime_path(path):
    if not os.path.isdir(path):
        os.mkdir(path)


class Timer:
    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.interval = self.end - self.start
