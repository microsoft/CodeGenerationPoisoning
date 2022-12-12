"""
The __init__.py files are required to make Python treat the directories as
containing packages; this is done to prevent directories with a common name,
such as string, from unintentionally hiding valid modules that occur later
(deeper) on the module search path.

@author: ucaiado

Created on 01/25/2018
"""
import os
import yaml

PATH = os.path.dirname(os.path.realpath(__file__))
PROD = yaml.safe_load(open(PATH + '/conf/conf_lab.yaml', 'r'))['ENV']['Prod']
VERB = yaml.safe_load(open(PATH + '/conf/conf_lab.yaml', 'r'))['ENV']['Verb']

from .agent import (Agent, AgentWrapper, orders, books, candles)
from .utils.neutrino_utils import (get_begin_time, SubscrType,
                                   CandleIntervals,
                                   neutrino_now)
from .utils.handle_commands import CommandHandler
from .utils.handle_orders import OrderHandler
from .agent import include_to_this_order

if not PROD:
    from .env import Env, EnvWrapper
    __all__ = ['Agent', 'Env', 'get_begin_time', 'orders', 'books', 'candles',
               'SubscrType', 'CandleIntervals', 'CommandHandler',
               'neutrino_now', 'include_to_this_order', 'EnvWrapper',
               'AgentWrapper', 'OrderHandler']
else:
    __all__ = ['Agent', 'get_begin_time', 'orders', 'books', 'candles',
               'SubscrType', 'CandleIntervals', 'CommandHandler',
               'neutrino_now', 'include_to_this_order', 'OrderHandler']
