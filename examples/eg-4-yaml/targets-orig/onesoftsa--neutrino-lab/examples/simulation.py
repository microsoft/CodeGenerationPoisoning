#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
simulate Dummy startegy


@author: ucaiado

Created on 02/27/2018
"""
import importlib
import sys
import platform
import argparse
import textwrap
import json
import yaml
# import sourcedefender
sys.path.append("../")

# define the required paths
s_platform = platform.system()
try:
    d_conf = yaml.safe_load(open('confs/conf_lab.yaml', 'r'))
except:
    d_conf = yaml.safe_load(open('confs/conf_lab.template.yaml', 'r'))
s_path = d_conf['NEUTRINO_LAB'][s_platform]
s_logs = d_conf['LOGS'][s_platform]



if __name__ == '__main__':
    s_txt = '''\
            Choose one agent to simulate from the list bellow
            --------------------------------------------
            - DemoBook
            - DemoCandles
            - DemoOrders
            - DemoTrades
            - DemoDummy
            '''
    obj_formatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=obj_formatter,
                                     description=textwrap.dedent(s_txt))

    s_help = 'Choose an agentfrom the list'
    parser.add_argument('-a', '--agent', default='DemoDummy', type=str,
                        help=s_help)

    s_help = 'Choose a file to save the simulation output data'
    parser.add_argument('-f', '--file', default='None', type=str,
                        help=s_help)

    s_help = 'Number of episodes to run'
    parser.add_argument('-e', '--episodes', default=1, type=int,
                        help=s_help)

    s_help = 'Environemnt to use. From B3 or Replay.'
    parser.add_argument('-env', '--environment', default='B3', type=str,
                        help=s_help)

    s_help = 'Pop up  a window to render the PnL of the simulation'
    parser.add_argument('--viz', action='store_true', help=s_help)

    s_help = 'Save the PnL vizualization. Only used when viz is enabled'
    parser.add_argument('--save', action='store_true', help=s_help)

    s_help = 'Block the process to terminate.  Only used when viz is enabled'
    parser.add_argument('--block', action='store_true', help=s_help)

    args = parser.parse_args()

    # recover the arguments passed
    b_viz = args.viz
    b_save = args.save
    b_block = args.block
    i_episodes = args.episodes
    s_env = args.environment
    s_file = None
    if args.file != 'None':
        s_file = args.file

    if s_env == 'Replay':
        # NOTE: Link gymVR1 to neutrinogym before
        sys.path.append(d_conf['EASYREPLAY'][s_platform])
        EasyReplay = importlib.import_module('EasyReplay')

    # import the required neutrinogym related libs
    sys.path.append(s_path)
    neutrinogym = importlib.import_module('neutrinogym')
    wrappers = importlib.import_module('neutrinogym.wrappers')
    my_agent = importlib.import_module('examples')

    if s_env == 'B3':
        algos = importlib.import_module('neutrinogym.algos')
        data_from_b3 = importlib.import_module('simulate.data_from_b3')
    else:
        data_from_replay = importlib.import_module('simulate.data_from_replay')

    d_implemented_agens = {
        'DemoBook': ('DemoBook', my_agent.DemoBook),
        'DemoCandles': ('DemoCandles', my_agent.DemoCandles),
        'DemoOrders': ('DemoOrders', my_agent.DemoOrders),
        'DemoTrades': ('DemoTrades', my_agent.DemoTrades),
        'DemoDummy': ('DemoDummy', my_agent.DemoDummy)
    }

    s_agent, agent_to_test = d_implemented_agens[args.agent]


    # define a list of commands to test
    l_commands = [json.dumps({'online': False})]
    l_commands = []

    # it is not been used by the Strategy yet
    d_params = {
        'symbols_conf': {'DI1F23': 25, 'DI1F25': 25, 'DOLV20': 25, 'DOLH21': 25},
        'open_pos': {'min_qty': 5,
                     'bid': True,
                     'ask': True}}

    l_setparams = [{s_agent: {'online': False, 'bid': False, 'ask': False}},
                   {s_agent: d_params},
                   # {s_agent: {'pos': {"DOLM18": {"P": 3704, "Q": -5}}}},
                   # {s_agent: {'pos': {"DOLM18": {"P": 3706, "Q": 0}}}},
                   # {s_agent: {'online': True, 'max_trades': None}},
                   {s_agent: {'online': True}}]

    if s_env == 'B3':
        env = data_from_b3.make_pnlenv()

        # run the simulation
        env, agent, episodes = data_from_b3.environment_loop(
            MyAgent=agent_to_test,
            env=env,
            s_init='20210219',
            s_end='20210220',
            s_starttime='09:30:00',
            s_endtime='16:30:00',
            i_episodes=i_episodes,
            s_root=d_conf['DATA_FOLDER_B3'][s_platform],
            s_log=s_logs,
            l_commands=l_commands,
            l_setparams=l_setparams,
            l_instruments=['DOLH21'],
            s_file=s_file,
            b_plot=b_viz,
            b_save=b_save,
            b_block=b_block,
            f_milis=100.,
            b_randstart=False)

    elif s_env == 'Replay':
        env = data_from_replay.make_pnlenv()

        # run the simulation
        env, agent, episodes = data_from_replay.environment_loop(
            MyAgent=agent_to_test,
            env=env,
            s_init='20210703',
            s_end='20210706',
            # s_starttime='08:30:00',
            # s_endtime='16:30:00',
            s_starttime='08:02:00',
            s_endtime='09:30:00',
            i_episodes=i_episodes,
            s_root=d_conf['DATA_FOLDER_REPLAY'][s_platform],
            s_log=s_logs,
            l_commands=l_commands,
            l_setparams=l_setparams,
            l_instruments=['DOLQ21'],
            s_file=s_file,
            b_plot=b_viz,
            b_save=b_save,
            b_block=b_block,
            f_milis=100.,
            b_randstart=False)
