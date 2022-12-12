#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Implement an agent interface to interact with Neutrino API and simulate the
enrionemnt to allow testing the strategies created

@author: ucaiado

Created on 09/05/2017
'''
import glob
import logging
import numpy as np
import json
import yaml
import importlib
import os
# agent imports
from neutrinogym import neutrino
from neutrinogym.neutrino import (fx, Source, UpdateReason, Symbol,
                                  LimitOrderEntry)
from neutrinogym import logger
# simulations imports
from neutrinogym.lob import matching_engine
from neutrinogym.lob import translator
from neutrinogym.lob import BvmfFileMatching
from .utils.neutrino_utils import (DoubleWrapperError, Logger)
from .utils.handle_orders import (OrderHandler, Instrument)
from .utils.handle_data import CandlesHandler
from . import data_feeder

import pprint

from neutrinogym.qcore import PATH

'''
Begin help functions
'''


class EpisodesInfo(object):
    def __init__(self, l_files):
        self.total = len(l_files)
        self.l_files = l_files

    def getDate(self, idx):
        idx2 = ((idx+1) % self.total) - 1
        return self.l_files[idx2].split('/')[-2]


class Observation(object):

    def __init__(self):
        self.train = None
        self.target = None
        self.features = None
        self.func_features = None
        self.l_last_msgs = []
        self.l_old_msgs = []
        self.i_step = 0

    def set_state_function(self, func=None):
        self.func_features = func

    def set_new_msgs(self, l_msgs, i_steps):
        self.l_last_msgs = l_msgs
        self.i_step = i_steps

    def update_features(self, env, actions):
        agent = None
        if actions:
            agent = actions.owner
        if self.func_features:
            # self.features = self.func_features(env, agent)
            self.features = self.func_features(agent)

    def append_msg(self, msg, i_steps):
        '''
        '''
        self.i_step = i_steps
        if isinstance(msg, list):
            for msg_aux in msg:
                self.l_last_msgs.append(msg_aux)
            return
        self.l_last_msgs.append(msg)

    def get_last_msgs(self):
        l_msgs = self.l_last_msgs[:]
        self.l_old_msgs = l_msgs[:]
        self.l_last_msgs = []
        return l_msgs


class Actions(object):

    action_map = {'new': translator.agent_env_neworder,
                  'cancel': translator.agent_env_cancellation,
                  'trade': translator.agent_env_execution}

    def __init__(self, agent):
        self.owner = agent
        self.owner_ = agent
        if hasattr(agent, 'agent'):
            self.owner_ = agent.agent
        self.l_last_msgs = []
        self.l_old_msgs = []
        self.set_pending_cancelations = set()
        self.last_action = None

    def set_new_msgs(self, l_msgs):
        self.l_last_msgs = l_msgs

    def set_last_action(self, obj_action):
        self.last_action = obj_action

    def set_reset_action(self):
        self.last_action = None

    def get_last_action(self):
        return self.last_action

    def append_msg(self, msg):
        '''
        '''
        if isinstance(msg, list):
            for msg_aux in msg:
                self.l_last_msgs.append(msg_aux)
            return
        elif msg[0] == 'new':
            msg[1].current.status = neutrino.FIXStatus.IDLE
            msg[1].current.price = None
            msg[1].current.qty = None
        self.l_last_msgs.append(msg)

    def get_last_msgs(self):
        l_msgs = self.l_last_msgs[:]
        self.l_old_msgs = l_msgs[:]
        self.l_last_msgs = []
        # convert orders to messages
        l_rtn = []
        for action, order in l_msgs:
            my_book = fx.book(order.symbol)
            d_rtn = self.action_map[action](order, my_book)
            if d_rtn:
                l_rtn.append(d_rtn)
            if action != 'cancel' and order.status == neutrino.FIXStatus.PENDING:
                # order.status = neutrino.FIXStatus.IDLE
                s_msg = '\nActions.get_last_msgs(): use owner_.orderUpdated() '
                s_msg += 'due to {}'.format(action)
                # print s_msg
                if self.owner_.b_has_bidSide:
                    self.owner_.orderUpdated(self.owner.i_id)
                else:
                    self.owner_.order_update(LimitOrderEntry(
                        order, self.owner.i_id))
                order.status = neutrino.FIXStatus.IDLE
        return l_rtn


class NotEnoughFilesError(Exception):
    '''
    NotEnoughFilesError is raised by the setDates() method from Env class to
    indicate that there is no files between the dates desired
    '''
    pass


'''
End help functions
'''


class Env(object):
    '''
    The main Environment representation within which all agents operate. As the
    main porpose of this class is replaying historical high-frequency data, in
    fact, the environment encompass two different agents at most: a historical
    agent, that manage all orders from the database used, and the primary, that
    should be implemented by the user
    '''

    _status = {'Partially Filled': (True, neutrino.FIXStatus.PARTIALLY_FILLED),
               'Filled': (False, neutrino.FIXStatus.FILLED),
               'New': (True, neutrino.FIXStatus.NEW),
               'Canceled': (False, neutrino.FIXStatus.CANCELLED)}

    def __init__(self):
        '''
        Initialize an Env object
        '''
        self.done = False
        self.almost_done = False
        self.t = 0
        self._agent_sha = ''
        self.last_observation = Observation()
        self.agents_actions = {}
        self.agents_callbacks = {neutrino.Source.IDLE: {},
                                 neutrino.Source.MARKET: {}}
        self.instr_data = {}
        self.instr_data_subscribed = {}
        self.b_bov = False  # set to true to make it works with Bovespa data
        # DEBUG ####
        self.count_actions = {}
        # ##########

        # Environment logs in new API
        self.logger = Logger(
            yaml.safe_load(open(PATH + '/conf/conf_logs.yaml', 'r'))['Env'])

        # trial data (updated at the end of each trial)
        self.d_trial_data = {'final_pnl': [],
                             'final_duration': [],
                             'max_pnl': [],
                             'min_pnl': [],
                             'final_reward': [],
                             'agents_positions': {}}

        # V03 candles
        self.candles = CandlesHandler()
        self.orders = {}

    def initialize(self, fnames, instr, inter_time, idx=None):
        '''
        Initialize the core attributes of the environment class

        :param fnames: list. the container zip files to be used in simulation
        :param instr: list. list of instrument to be simulated.
        :param inter_time: NextStopTime object. the hour all books is in sync
        '''
        if not isinstance(instr, list):
            instr = [instr]
        self.l_instrument = instr
        self.d_map_book_list = dict(zip(instr, (np.cumsum([1]*len(instr))-1)))
        if not idx:
            idx = 0
        self.initial_idx = idx
        self.count_trials = 1

        # start the book idx control
        self.book_idx = {}
        for s_instr in self.l_instrument:
            self.book_idx[s_instr] = {'ASK': 0, 'BID': 0}

        # define stop times
        self.NextStopTime = inter_time

        # Initiate Matching Engine
        self.order_matching = BvmfFileMatching(env=self,
                                               l_instrument=instr,
                                               l_file=fnames)

        # define the best bid and offer attributes
        self._i_nrow = self.order_matching.i_nrow

        # set the environment in the neutrino library
        neutrino.ENV = self
        neutrino.BOVESPA = self.b_bov

        # V03 candles
        self.candles.reset()

    def set_observation_func(self, state_func):
        '''
        '''
        self.last_observation.set_state_function(state_func)

    def setParameters(self, init, end, datafolder, instruments,
                      starttime='09:20:00', endtime='15:40:00', idx=None,
                      logfolder=None, state_func=None, f_milis=100.,
                      b_randstart=True):
        '''
        Set parameters to use in simulation

        :param init: string. The initial file date (format YYYYMMDD)
        :param end: string. The final file date (format YYYYMMDD)
        :param datafolder: string. The folder to look for the files to be used
        :param starttime*: string. The time to start (format HH:mm:ss)
        :param endtime*: string. The time to close (format HH:mm:ss)
        :param idx*: integer. The index of the start file to be read
        :param logfolder*: string. The path to the log's folder
        :return: EpisodesInfo object. Metadata about the simulation parameters
        '''
        # include 15 minutes as random time to start trading
        f1 = sum([float(s)*60**(2-i) for i, s in
                  enumerate(starttime.split(':'))])
        f2 = sum([float(s)*60**(2-i) for i, s in
                  enumerate(endtime.split(':'))])
        self.start_mkt_time = f1
        if b_randstart:
            self.start_mkt_time += np.random.rand() * 15 * 60.
        self.close_mkt_time = f2

        # check the file names
        datafolder = datafolder.replace('\\', '/')  # windows stuff
        if datafolder[-1] != '/':
            datafolder += '/'
        l_files = []
        for x in sorted(glob.glob(datafolder + '20*')):
            x = x.replace('\\', '/')  # windows stuff
            if int(init) <= int(x.split(datafolder)[1]) <= int(end):
                l_files.append(x + '/' + x.split('/')[-1] + '_{}_{}_new.zip')

        if not l_files:
            s_err = 'There is no files between {} and {}'
            s_err = s_err.format(init, end)
            raise NotEnoughFilesError(s_err)

        # initialize the NextStopTime object
        iter_time = matching_engine.NextStopTime(self.start_mkt_time,
                                                 self.close_mkt_time,
                                                 milis=f_milis)

        # set the log folder
        logger.set_logger(logfolder)

        # initialize the enviornment
        if not isinstance(instruments, list):
            instruments = [instruments]
        self.initialize(l_files, instruments, iter_time, idx)

        # set state function
        self.last_observation.set_state_function(state_func)

        # return the metadata
        return EpisodesInfo(l_files)


    def set_agent_params(self, agent, s_callback_type, l_txt):
        '''
        '''
        this_agent = agent
        if hasattr(agent, 'agent'):
            this_agent = agent.agent

        if s_callback_type == 'command':
            if hasattr(agent, 'command'):
                for s_command in l_txt:
                    agent.command(Source.COMMAND, s_command)
        elif s_callback_type == 'parameters':
            if hasattr(this_agent, 'processSetParameters'):
                for s_to_set in l_txt:
                    agent.processSetParameters(s_to_set)
            elif hasattr(this_agent, 'set_parameters'):
                for s_to_set in l_txt:
                    this_agent.set_parameters(s_to_set)

    def get_agent_params(self, agent):
        s_rtn = '{}'
        this_agent = agent
        if hasattr(agent, 'agent'):
            this_agent = agent.agent
        if hasattr(this_agent, 'processGetParameters'):
            s_rtn = agent.processGetParameters()
        elif hasattr(this_agent, 'get_parameters'):
            s_rtn = this_agent.get_parameters()
        return s_rtn

    def get_reward(self, actions):
        '''
        Return the reward based on the current state of the market and position
        accumulated by the agent

        :param actions: Action object. Action to judge the value
        '''
        return 0.

    def get_last_trades(self, my_book, b_from_candles=False):
        '''
        Return the TradeBuffer object related to the symbol passed

        :param my_book: Book obj.
        :*param b_from_candles: boolean. Only exist in simulatin
        '''
        # i_idx = self.d_map_book_list[s_instrument]
        # my_book = self.order_matching.l_order_books[i_idx]
        if b_from_candles:
            my_book.last_trades_aux.unload_buffer()
            return my_book.last_trades_aux
        my_book.last_trades.unload_buffer()
        return my_book.last_trades

    def get_last_trades_new(self, my_book):
        '''
        Return the TradeBuffer object related to the symbol passed

        :param my_book: Book obj.
        :*param b_from_candles: boolean. Only exist in simulatin
        '''
        # i_idx = self.d_map_book_list[s_instrument]
        # my_book = self.order_matching.l_order_books[i_idx]
        my_book.b_should_unload = True
        # my_book.last_trades.unload_buffer()
        return my_book.last_trades

    def get_order_book(self, s_instrument, b_rtn_dataframe=False):
        '''
        Return a dataframe with the first 5 levels of the current order book

        :param s_instrument: string. Intrument to return the book
        :param b_rtn_dataframe*: boolean. return the book into a dataframe
        '''
        i_idx = self.d_map_book_list[s_instrument]
        my_book = self.order_matching.l_order_books[i_idx]
        if b_rtn_dataframe:
            return my_book.get_n_top_prices(5, b_return_dataframe=True)
        return my_book

    def get_book_side_idx(self, s_instrument, s_side):
        '''
        Return the current row idx of the order book file used

        :param s_instrument: string. Intrument to return the book
        :param s_side: string. side of the order book
        '''
        i_idx = self.d_map_book_list[s_instrument]
        book_aux = self.order_matching.l_order_books[i_idx]
        if s_side == 'BID':
            return book_aux.book_bid._i_idx, book_aux
        return book_aux.book_ask._i_idx, book_aux

    def get_current_time(self, b_rtn_str=True):
        '''
        Return the current market time

        :param b_rtn_str: boolean: If should return a string or a float
        '''
        if not b_rtn_str:
            return self.order_matching.f_time
        return self.order_matching.s_time

    def add_callback(self, func, source, trigger=neutrino.Source.MARKET,
                     i_id=11, s_instr=None, s_name=None):
        '''
        Add a new callback to environment callbacks queues

        :param agent: object. Enviroment agent
        :param func: object. a function to be called as a callback
        :param
        '''
        s_incl = s_instr
        if s_name:
            s_incl = s_name
        if i_id not in self.agents_callbacks[trigger]:
            self.agents_callbacks[trigger][i_id] = []
            if s_incl:
                self.agents_callbacks[trigger][i_id] = {}
                self.agents_callbacks[trigger][i_id][s_incl] = []
        if s_incl:
            if s_incl not in self.agents_callbacks[trigger][i_id]:
                self.agents_callbacks[trigger][i_id][s_incl] = []
            self.agents_callbacks[trigger][i_id][s_incl].append([source, func])
        else:
            raise NotImplementedError
            self.agents_callbacks[trigger][i_id].append([source, func])

    def remove_callback(self, source=None, trigger=neutrino.Source.MARKET,
                        i_id=11, s_instr=None, s_name=None):
        s_incl = s_instr
        if s_name:
            s_incl = s_name
        if i_id in self.agents_callbacks[trigger]:
            if s_incl:
                self.agents_callbacks[trigger][i_id].pop(s_incl, None)
            else:
                raise NotImplementedError

    def excludeIndicator(self, s_instr, s_source, s_conf, i_begin, i_id=11):
        '''
        Unsubscribe new indicator or candle

        :param s_instr: string.
        :param s_type: string.
        :param s_conf: string.
        :param i_begin: float.
        :param i_id: interget. Agent Id. Used only on simulation
        '''
        s_name = '{}:{}:{}'.format(s_source, s_instr, s_conf)
        if s_instr in self.instr_data_subscribed:
            if s_name in self.instr_data_subscribed[s_instr]:
                if i_id in self.instr_data_subscribed[s_instr][s_name]:
                    self.instr_data_subscribed[s_instr][s_name].discard(i_id)

    def addIndicator(self, s_instr, s_source, s_conf, i_begin, i_id=11):
        '''
        Subscribe new indicator or candle

        :param s_instr: string.
        :param s_type: string.
        :param s_conf: string.
        :param i_begin: float.
        :param i_id: interget. Agent Id. Used only on simulation
        '''
        # check if the symbol is allowed
        s_err = '[addIndicator]Environment: candle instrument should be in '
        s_err = 'the configuration file'
        assert s_instr in self.l_instrument, s_err

        # data_feeder = importlib.import_module('data_feeder')
        d_conf = dict([x.split('=') for x in s_conf.split(';')])

        # l_conf = s_conf.split(';')
        # s_time = l_conf[0]
        # f_time = float(s_time.split('=')[1])
        f_time = float(d_conf['interval'])
        i_count = 1000  # number of bars to keep in memory
        s_this_name = '{}:{}:interval={:0.0f}'
        s_this_name = s_this_name.format('CANDLE', s_instr, f_time)
        d_aux = {}
        if s_instr not in self.instr_data:
            self.instr_data[s_instr] = {}
            self.instr_data_subscribed[s_instr] = {}

        if s_this_name not in self.instr_data[s_instr]:
            d_aux['ID'] = 0
            d_aux['INDICATORS'] = []
            d_aux['INTERVAL'] = f_time
            self.instr_data[s_instr][s_this_name] = d_aux

        d_aux = self.instr_data[s_instr][s_this_name]
        # TODO: it should be here or in other place?
        if f_time != d_aux['INTERVAL']:
            d_aux['INTERVAL'] = f_time
        # END TODO
        if s_source == 'CANDLE':
            s_name = '{}:{}:{}'.format(s_source, s_instr, s_conf)
            if s_name not in self.instr_data_subscribed[s_instr]:
                self.instr_data_subscribed[s_instr][s_name] = set()
            self.instr_data_subscribed[s_instr][s_name].add(i_id)
            d_aux['CANDLE_NAME'] = s_name
            if 'MAX' not in d_aux:
                for s_field in ['MAX', 'MIN', 'LST', 'QTD', 'NTRADES', 'QTD_B',
                                'QTD_S', 'CUMQTD', 'CUMQTD_B', 'CUMQTD_S',
                                'VOLUME', 'TS']:
                    d_aux[s_field] = data_feeder.ElapsedList(
                        f_elapsed_time=f_time,
                        i_count=i_count,
                        s_type=s_field)
        else:
            d_aux = self.instr_data[s_instr][s_this_name]
            s_name = '{}:{}:{}'.format(s_source, s_instr, s_conf)
            d_aux[s_name] = []
            d_aux['INDICATORS'].append(s_name)
            if s_name not in self.instr_data_subscribed[s_instr]:
                self.instr_data_subscribed[s_instr][s_name] = set()
            self.instr_data_subscribed[s_instr][s_name].add(i_id)
        self.instr_data[s_instr][s_this_name] = d_aux
        # pprint.pprint(self.instr_data)

    @property
    def i_nrow(self):
        '''
        Access the last idx row used by order matching
        '''
        self._i_nrow = self.order_matching.i_nrow
        return self._i_nrow

    @property
    def agent_sha(self):
        '''
        Access the last idx row used by order matching
        '''
        return self._agent_sha

    @agent_sha.setter
    def agent_sha(self, x):
        self._agent_sha = x

    def reset_generator(self):
        '''
        Reset the stop-time generator
        '''
        self.NextStopTime.reset()

    def reset(self, train_mode=False):
        '''
        Reset the environment and all variables needed as well as the states
        of each agent and return the fist observation form the environment
        '''
        self.done = False
        self.almost_done = False
        self.train_mode = train_mode
        self.t = 0
        self.instr_data = {}
        self.instr_data_subscribed = {}
        self.order_matching.reset()
        self.reset_generator()
        neutrino.fx.initial_time = 0  # Hack

        # NOTE: it is ugly, but reset the order_matching idx. Should reviwe it
        self.order_matching.s_file
        # shuffle seed
        np.random.seed(seed=None)

        # log the trial will start
        s_msg = '[reset]Environment: New Trial will start!'
        if self.agent_sha:
            s_msg += '(SHA {})'.format(self.agent_sha)
        i_aux = self.count_trials
        s_msg += ' ID {}'.format(i_aux)
        self.count_trials += 1

        # perform the first step
        obj_observt, _, _, _ = self.step()

        # DEBUG
        logging.info(s_msg)
        return obj_observt

    def resetAgent(self, agent, hold_pos=True, f_delay=.5):
        '''
        Reset agent's core attributes before starting a new episode.

        :param agent. Agent object
        :param hold_pos: boolean. Keep the position from the last episode
        :param f_delay: float. Time to update book vizualization
        :return: agent object
        '''
        # initiate the action objet by agent
        self.agents_actions[agent.i_id] = Actions(agent)
        agent.set_action_object(None)

        # set RL agents parameters
        if agent.brain:
            # agent.brain = brain
            agent.update_delay = f_delay
            agent_actions = self.agents_actions[agent.i_id]
            agent.set_action_object(agent_actions)
            agent.env_train_mode = self.train_mode
            agent.brain.env_train_mode = self.train_mode

        # check which version the agent was contructed
        if not hasattr(agent, 'b_has_bidSide'):
            if hasattr(agent, 'agent'):
                agent.b_has_bidSide = hasattr(agent.agent, 'bidSide')
                agent.agent.b_has_bidSide = hasattr(agent.agent, 'bidSide')
            else:
                agent.b_has_bidSide = hasattr(agent, 'bidSide')
        if not hasattr(agent, 'b_has_ordfill'):
            if hasattr(agent, 'agent'):
                agent.b_has_ofill = hasattr(agent.agent, 'order_filled')
                agent.agent.b_has_ofill = hasattr(agent.agent, 'order_filled')
            else:
                agent.b_has_ofill = hasattr(agent, 'order_filled')

        # TODO: I have to change these attributes and callbacks, but i will
        #    keep them for now
        this_agent = agent
        i_stack = 100
        if not agent.b_has_bidSide:
            # old attr
            if hasattr(this_agent, 'agent'):
                this_agent = agent.agent
            if not hasattr(this_agent, '_instr_stack'):
                agent._instr_stack = {}
                this_agent._instr_stack = {}

            if agent.i_id not in self.orders:
                this_agent = agent
                if hasattr(this_agent, 'agent'):
                    this_agent = this_agent.agent
                self.orders[agent.i_id] = OrderHandler()
                self.orders[agent.i_id].logger = self.logger
                self.orders[agent.i_id].set_owner(this_agent)
                for s_symbol in self.l_instrument:
                    this_instrument = Instrument(s_symbol, i_stack)
                    this_instrument.logger = self.logger
                    this_agent._instr_stack[s_symbol] = this_instrument
                    agent._instr_stack[s_symbol] = this_instrument

        # keep the final position in memory
        if agent.i_id not in self.d_trial_data['agents_positions']:
            self.d_trial_data['agents_positions'][agent.i_id] = {}
            d_aux = self.d_trial_data['agents_positions'][agent.i_id]
            for s_asset in agent._instr_stack:
                d_aux[s_asset] = {'qBid': 0, 'Bid': 0.,
                                  'Ask': 0., 'qAsk': 0.}
        # set the agent position
        d_pos_memory = self.d_trial_data['agents_positions'][agent.i_id]
        s_command = 'init_pos='
        d_pos_to_set = {}
        # hold last position
        if hold_pos:
            for s_asset in agent._instr_stack:
                instr = agent._instr_stack[s_asset]
                # keep what the agent already traded in memory
                for s_key in ['qBid', 'qAsk', 'Ask', 'Bid']:
                    f_value = instr._position[s_key]
                    d_pos_memory[s_asset][s_key] += f_value
                # set the agent to the next episode
                i_pos = instr.get_position()
                if i_pos != 0:
                    f_price = instr.get_opened_price()
                    d_pos_to_set[s_asset] = {'Q': i_pos, 'P': f_price}
        if d_pos_to_set:
            s_command = json.dumps({'init_pos': d_pos_to_set})

        # reload instruments
        for s_symbol in self.l_instrument:
            this_instrument = Instrument(s_symbol, i_stack)
            this_agent._instr_stack[s_symbol] = this_instrument
            agent._instr_stack[s_symbol] = this_instrument

        # reset the agent-state variables
        if agent.b_has_bidSide:
            agent.initialize()
        else:
            # set initial position before initilize
            # NOTE: correct that to let set a initial position form config
            if s_command != 'init_pos=':
                for s_asset in d_pos_to_set:
                    instr = agent._instr_stack[s_asset]
                    instr.set_initial_positions(
                        this_agent, d_pos_to_set[s_asset])
            # initialize agent
            agent.initialize(Symbol(self.l_instrument))

        if hasattr(agent, 'agent'):
            agent._instr = list(fx.symbols_callbacks.get(agent.i_id, []))

        if not hasattr(this_agent, 'command'):
            return
        agent.command(neutrino.Source.COMMAND, json.dumps({'online': False}))
        # set position, if it is required
        if s_command != 'init_pos=':
            agent.command(neutrino.Source.COMMAND, s_command)
        # prepare the agent to start trade
        agent.command(neutrino.Source.COMMAND, json.dumps({'online': True}))
        agent.command(neutrino.Source.COMMAND, json.dumps({'bid': True}))
        agent.command(neutrino.Source.COMMAND, json.dumps({'ask': True}))

    def callBack(self, agent, observation):
        '''
        Call some methods of the agent, depending on the events observed

        :param agent: Agent object.
        :param observation: Observation object.
        '''
        # global LAST_TIME
        agent_actions = self.agents_actions[agent.i_id]
        agent_ = agent_actions.owner_

        # add pending callbacks
        d_pcbacks = fx.pending_callbacks
        if agent.i_id in d_pcbacks and not d_pcbacks[agent.i_id]['checked']:
            fx.pending_callbacks[agent.i_id]['checked'] = True
            for s_src in ['book', 'trade', 'candle', 'other']:
                for s_incl, func in fx.pending_callbacks[agent.i_id][s_src]:
                    if s_src == 'other':
                        obj_triggr = neutrino.Source.IDLE
                        self.remove_callback(
                            s_name=s_incl,
                            trigger=obj_triggr,
                            i_id=agent.i_id)
                        s_incl._last_time = fx.now(b_old=True)
                        self.add_callback(
                            func,
                            source=s_src,
                            trigger=obj_triggr,
                            i_id=agent.i_id,
                            s_name=s_incl)
                    else:
                        self.add_callback(
                            func, source=s_src, trigger=neutrino.Source.MARKET,
                            i_id=agent.i_id, s_instr=s_incl)
                fx.pending_callbacks[agent.i_id][s_src] = []

            # add_callback(agent, func, source, trigger=neutrino.Source.MARKET,
            #              i_id=11)
        if observation.i_step == 1:
            if agent.b_has_bidSide:
                agent.symbolsLoaded()
            else:
                self.candles.on_symbols_load(f_fxnow=fx.now(b_ts=True))
                for instrument in iter(agent._instr_stack.values()):
                    # instatiate initial list of orders
                    instrument.on_symbols_load(agent)
            return agent_actions

        # update indicators, if any is registered
        for s_instr in self.instr_data:
            d_these_candles = self.instr_data[s_instr]
            t_aux = data_feeder.make_updates(s_instr, d_these_candles)
            d_update, d_these_candles = t_aux
            self.instr_data[s_instr] = d_these_candles
            # if d_these_candles and not agent.b_has_bidSide:
            #     self.candles.check_pending_candles_subscriptions(int(fx.now()))
            if not agent.b_has_bidSide:
                for s_name, inst_data in iter(d_these_candles.items()):
                    this_candle = self.candles.get_candle(
                        None, s_instr, inst_data['INTERVAL'])
                    if not this_candle.v3_obj._bar_data:
                        this_candle.v3_obj._bar_data = inst_data
                        this_candle.v3_obj.b_ready = True
                d_these_candles = {}
            # NOTE: I shold change the candle object to support multiple agents
            for s_name, inst_data in iter(d_these_candles.items()):
                if d_update[s_name]:
                    d_data_subscribed = self.instr_data_subscribed[s_instr]
                    if inst_data['CANDLE_NAME'] in d_data_subscribed:
                        agent.indicatorData(('CANDLE', inst_data))
                        for s_this_ta in inst_data['INDICATORS']:
                            agent.indicatorData((s_this_ta, inst_data))

        # update the agent with trades that had occurred in the last step
        # if len(observation.l_last_msgs):
        #     print '\n\n!!! new observation:'
        for msg in observation.get_last_msgs():
            order = msg['neutrino_order']
            newobj_order = LimitOrderEntry(order, agent.i_id)
            b_alive, neut_status = self._status[msg['order_status']]
            order.current.status = neut_status
            order.current.isAlive = b_alive
            # DEBUG ####
            # if msg['action'] not in self.count_actions.keys():
            #     self.count_actions[msg['action']] = 0
            # self.count_actions[msg['action']] += 1
            # ##########

            b_can_update = True
            if msg['order_status'] in ['Partially Filled', 'Filled']:
                # NOTE: This 'if' should not be required. Have to investigate
                # further why some orders are kept in the book, even though
                # there were canceled or filled before. It seems related to the
                # translate_row function when the row cross the ord book
                try:
                    instr = agent._instr_stack.get(order.symbol)
                    _ = instr._orders[order.userData['id']]
                    # _ = agent._orders[order.userData['id']]
                    lastpx = msg['order_price']
                    lastqty = msg['order_qty']
                    order.current._last_price = lastpx
                    order.current._last_quantity = lastqty
                    # print
                    # debug
                    # s_msg = 'Env.callBack(): trade qty = {}, price = {}\n'
                    # print s_msg.format(lastpx, lastqty)
                    # if lastqty < 0:
                    #     print msg
                    # debug
                    # print order
                    if agent.b_has_bidSide:
                        agent.orderFilled(order, lastpx, lastqty)
                    else:
                        self.orders[agent.i_id].send_cancel_acc(order, 'E')
                        instr.update_position(order, lastpx, lastqty)
                        instr.update_active_qty(order, 'E', lastqty)
                        if agent.b_has_ofill:
                            agent_.order_filled(newobj_order, lastpx, lastqty)
                except KeyError:
                    b_can_update = False
                    pass
            self.update_order_book(agent_actions.get_last_msgs())
            if order.status == neutrino.FIXStatus.PENDING:
                order.status = neutrino.FIXStatus.IDLE
                # print '\nEnv.callBack(): use agent.orderUpdated()'
                # pprint.pprint(msg)
                # print
                # if b_can_update:  # it should be handle in other way
                #     agent.orderUpdated(order)
            if agent.b_has_bidSide:
                agent.orderUpdated(order)
            else:
                instr = agent._instr_stack.get(order.symbol)
                instr.update_order_ctrls(order)
                if str(order.current.status) in ['CANCELLED', 'REJECTED']:
                    i_cumqty = order.current.cumQty
                    i_cumqty = i_cumqty if abs(i_cumqty) < 10**7 else 0
                    i_qty = order.current.qty - i_cumqty
                    instr.update_active_qty(order, 'RC', i_qty)
                agent_.order_update(newobj_order)

        # update RL variables
        if agent.brain:
            agent.brain.last_states = self.last_observation.features


        if not agent.b_has_bidSide:
            self.candles.check_pending_candles_subscriptions(int(fx.now()))

        # check if the agent is going to do something in the next step
        if str(self.order_matching.s_source) == 'IDLE':
            if agent.b_has_bidSide:
                agent.bidSide(Source.IDLE, book=None)
                self.update_order_book(agent_actions.get_last_msgs())
                agent.askSide(Source.IDLE, book=None)
                self.update_order_book(agent_actions.get_last_msgs())
            else:
                d_callbacks = self.agents_callbacks[Source.IDLE]
                l_to_exclude = []
                if agent.i_id in d_callbacks:
                    d_schdule_infos = {
                        a: b for a, b in iter(d_callbacks[agent.i_id].items())}
                    for schdule_infos in d_schdule_infos:
                        # _, func = d_callbacks[agent.i_id][schdule_infos][0]
                        _, func = d_schdule_infos[schdule_infos][0]
                        # print('implement IDLE')
                        f_time = fx.now(b_old=True)
                        if schdule_infos.should_trigger(f_time):
                            # NOTE: what should I put here?
                            updates = neutrino.Update()
                            updates.l_reason = [
                                # ?
                                schdule_infos.kind + ' ' + schdule_infos.name]
                            if schdule_infos.kind == 'at':
                                l_to_exclude.append([
                                    schdule_infos,
                                    Source.IDLE,
                                    agent.i_id])
                            # func(updates)  # NOTE: no params passed anymore
                            func()
                            # import pdb; pdb.set_trace()
                    for a, b, c in l_to_exclude:
                        self.remove_callback(s_name=a, trigger=b, i_id=c)

        elif str(self.order_matching.s_source) == 'MARKET':
            l_func = [agent.bidSide, agent.askSide]
            if agent.b_has_bidSide:
                for s_instr in self.l_instrument:
                    for agent_func, s_side in zip(l_func, ['BID', 'ASK']):
                        i_idx, book_aux = self.get_book_side_idx(
                            s_instr, s_side)
                        if i_idx != self.book_idx[s_instr][s_side]:
                            self.book_idx[s_instr][s_side] = i_idx
                            agent_func(Source.MARKET, book=book_aux)
                            self.update_order_book(
                                agent_actions.get_last_msgs())
            else:
                for s_instr in self.l_instrument:
                    # mount update object
                    i_idx, book_aux = self.get_book_side_idx(s_instr, 'BID')
                    l_updates = []
                    if len(book_aux.last_trades):
                        l_updates = [UpdateReason.TRADES]
                    if i_idx != self.book_idx[s_instr]['BID']:
                        self.book_idx[s_instr]['BID'] = i_idx
                        l_updates.append(UpdateReason.BID_SIDE)
                        l_updates.append(UpdateReason.ASK_SIDE)
                    else:
                        self.book_idx[s_instr]['ASK'] = i_idx
                        l_updates.append(UpdateReason.ASK_SIDE)
                        l_updates.append(UpdateReason.BID_SIDE)
                    updates = neutrino.Update()
                    updates.reason = l_updates
                    updates.symbol = s_instr
                    updates.bid_count = book_aux.get_counts('BID', 'Total')
                    updates.ask_count = book_aux.get_counts('ASK', 'Total')
                    updates.trade_count = len(book_aux.last_trades)
                    # is 1 only when the book status changes
                    updates.status_changed = 0
                    # use callbacks
                    i_id = agent.i_id
                    d_cb = self.agents_callbacks[Source.MARKET].get(i_id, None)
                    if d_cb and s_instr in d_cb and book_aux._has_changed:
                        for s_src, func in d_cb[s_instr]:
                            # if book_aux._has_changed:
                            func(updates)
                        book_aux._has_changed = False
                # import pdb; pdb.set_trace()

        # update other RL variables
        if agent.brain:
            agent_actions.set_last_action(agent.brain.last_actions)

        return agent_actions

    def step(self, actions=None):
        '''
        Perform a discreate step in the environment updating the state of all
        agents

        :param actions*: Actions objetc. messages to use to update the book
        '''
        # Get the updates from the books that are not related to the history
        # until the stoptime
        l_msg = self.order_matching.next()

        # execute the actions passed
        f_reward = 0.
        if actions:
            self.update_order_book(actions.get_last_msgs())
            f_reward += self.get_reward(actions)

        # check if the market is closed
        self.t += 1
        d_info = {}
        self.almost_done
        b_timetest = self.order_matching.last_date >= self.close_mkt_time-60
        if not self.almost_done and b_timetest:
            self.almost_done = True
            for i_id in self.agents_actions:
                this_agent = self.agents_actions[i_id].owner
                if hasattr(this_agent, 'agent'):
                    this_agent = this_agent.agent
                if hasattr(this_agent, 'finalize'):
                    this_agent.finalize(neutrino.QuitReason.ALGOMAN_QUIT)
        if self.order_matching.last_date >= self.close_mkt_time:
            self.done = True
            s_msg = '[step]Environment: Market closed at {}!'
            s_msg += ' The session ended.'
            logging.info(s_msg.format(self.order_matching.s_time))
            d_info = {'total_steps': self.t}

        # hold last messages
        # self.last_observation.set_new_msgs(l_msg, self.t)
        self.last_observation.append_msg(l_msg, self.t)
        self.last_observation.update_features(self, actions)
        return self.last_observation, f_reward, self.done, d_info

    def update_order_book(self, l_msg):
        '''
        Update the Book and all information related to it

        :param l_msg: list. messages to use to update the book
        '''
        if isinstance(l_msg, dict):
            l_msg = [l_msg]
        if len(l_msg) > 0:
            self.order_matching.update(l_msg)

    def close(self):
        '''
        '''
        # TODO: implement this function
        pass


class EnvWrapper(object):
    '''
    Wrapper representation of the environmnent that is used to transform it
    in a modular way
    '''

    def __init__(self, env):
        self.env = env
        self._ensure_no_double_wrap()
        self.done = self.env.done
        self.t = self.env.t
        self.last_observation = self.env.last_observation
        self.agents_actions = self.env.agents_actions
        # DEBUG ####
        self.count_actions = self.env.count_actions
        # ##########

        # trial data (updated at the end of each trial)
        self.d_trial_data = self.env.d_trial_data

    @classmethod
    def class_name(cls):
        return cls.__name__

    def _ensure_no_double_wrap(self):
        env = self.env
        while True:
            if isinstance(env, EnvWrapper):
                if env.class_name() == self.class_name():
                    s_err = "Attempted to double wrap with Wrapper: {}"
                    s_err = s_err.format(self.__class__.__name__)
                    raise DoubleWrapperError(s_err)
                env = env.env
            else:
                break

    def initialize(self, **kwargs):
        '''
        Initialize the core attributed of the environment

        :param fnames: list. the container zip files to be used in simulation
        :param instr: list. list of instrument to be simulated.
        :param inter_time: NextStopTime object. the hour all books is in sync
        '''
        return self.env.initialize(**kwargs)

    def setParameters(self, **kwargs):
        '''
        Set parameters to use in simulation

        :param init: string. The initial file date (format YYYYMMDD)
        :param end: string. The final file date (format YYYYMMDD)
        :param datafolder: string. The folder to look for the files to be used
        :param starttime*: string. The time to start (format HH:mm:ss)
        :param endtime*: string. The time to close (format HH:mm:ss)
        :param idx*: integer. The index of the start file to be read
        :param logfolder*: string. The path to the log's folder
        :return: EpisodesInfo object. Metadata about the simulation parameters
        '''
        # include 15 minutes as random time to start trading
        return self.env.setParameters(**kwargs)

    def set_agent_params(self, agent, s_callback_type, l_txt, **kwargs):
        '''
        '''
        return self.env.set_agent_params(
            agent, s_callback_type, l_txt, **kwargs)

    def get_agent_params(self, agent, **kwargs):
        '''
        '''
        return self.env.get_agent_params(agent, **kwargs)

    def set_observation_func(self, **kwargs):
        '''
        '''
        return self.env.set_observation_func(**kwargs)

    def get_reward(self, **kwargs):
        '''
        Return the reward based on the current state of the market and position
        accumulated by the agent

        :param actions: Action object. Action to judge the value
        '''
        return self.env.get_reward(kwargs)

    def get_last_trades(self, my_book, b_from_candles=False):
        '''
        Return the TradeBuffer object related to the symbol passed

        :param my_book: Book obj.
        :*param b_from_candles: boolean. Only exist in simulatin
        '''
        return self.env.get_last_trades(my_book, b_from_candles)

    def get_order_book(self, s_instrument, b_rtn_dataframe=False):
        '''
        Return a dataframe with the first 5 levels of the current order book

        :param s_instrument: string. Intrument to return the book
        :param b_rtn_dataframe*: boolean. return the book into a dataframe
        '''
        return self.env.get_order_book(s_instrument, b_rtn_dataframe)

    def get_book_side_idx(self, s_instrument, s_side):
        '''
        Return the current row idx of the order book file used

        :param s_instrument: string. Intrument to return the book
        :param s_side: string. side of the order book
        '''
        return self.env.get_book_side_idx(s_instrument, s_side)

    def get_current_time(self, b_rtn_str=True):
        '''
        Return the current market time

        :param b_rtn_str: boolean: If should return a string or a float
        '''
        return self.env.get_current_time(b_rtn_str)

    @property
    def i_nrow(self):
        '''
        Access the last idx row used by order matching
        '''
        return self.env.i_nrow()

    @property
    def agent_sha(self):
        '''
        Access the last git sha, if available
        '''
        return self.env._agent_sha

    @agent_sha.setter
    def agent_sha(self, x):
        self.env._agent_sha = x

    def reset_generator(self):
        '''
        Reset the stop-time generator
        '''
        return self.env.reset_generator()

    def add_callback(self, func, source, trigger=neutrino.Source.MARKET,
                     i_id=11, s_instr=None, s_name=None):
        '''
        Add new callback
        '''
        self.env.add_callback(
            func=func, source=source, trigger=trigger, i_id=i_id,
            s_instr=s_instr, s_name=s_name)

    def reset(self, train_mode=False):
        '''
        Reset the environment and all variables needed as well as the states
        of each agent and return the fist observation form the environment
        '''
        return self.env.reset(train_mode)

    def resetAgent(self, agent, hold_pos=True, f_delay=.5):
        '''
        Reset agent's core attributes before starting a new episode.

        :param agent: Agent object
        :param hold_pos: boolean. Keep the position from the last episode
        :param brain: Bain object or None
        :param f_delay: float.
        :return: agent object
        '''
        return self.env.resetAgent(agent, hold_pos, f_delay)

    def callBack(self, agent, observation):
        '''
        Call some methods of the agent, depending on the events observed

        :param agent: Agent object.
        :param observation: Observation object.
        '''
        return self.env.callBack(agent, observation)

    def step(self, actions=None):
        '''
        Perform a discreate step in the environment updating the state of all
        agents

        :param actions: Actions objetc. messages to use to update the book
        '''
        # Get the updates from the books that are not related to the history
        # until the stoptime
        return self.env.step(actions)

    def update_order_book(self, l_msg):
        '''
        Update the Book and all information related to it

        :param l_msg: list. messages to use to update the book
        '''
        return self.env.update_order_book(l_msg)

    def close(self):
        '''
        '''
        # TODO: implement this function
        return self.env.close()
