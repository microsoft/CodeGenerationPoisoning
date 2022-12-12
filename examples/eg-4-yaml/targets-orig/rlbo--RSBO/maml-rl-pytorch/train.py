import gym
import json
import numpy as np
import os
import pickle
from pickle import dump
import torch
from tqdm import trange
import yaml

import maml_rl.envs
from maml_rl.metalearners import MAMLTRPO
from maml_rl.baseline import LinearFeatureBaseline
from maml_rl.samplers import MultiTaskSampler
from maml_rl.utils.helpers import get_policy_for_env, get_input_size
from maml_rl.utils.reinforcement_learning import get_returns, get_discounted_returns, get_costs


def main(args):
    with open(args.config, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    if args.output_folder is not None:
        if not os.path.exists(args.output_folder):
            os.makedirs(args.output_folder)
        config_filename = os.path.join(args.output_folder, str(args.seed) + '_config.json')
        policy_filename = os.path.join(args.output_folder, str(args.seed) + '_policy.th')
        result_filename_txt = os.path.join(args.output_folder, str(args.seed) + '_results.txt')
        result_filename_pickle = os.path.join(args.output_folder, str(args.seed) + '_results.pickle')

        with open(config_filename, 'w') as f:
            config.update(vars(args))
            json.dump(config, f, indent=2)

    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    results = {
        'train_costs': [],
        'test_costs': [],
        'train_costs_sum': [], # the cost
        'test_costs_sum': [], 
        'train_costs_mean': [],
        'test_costs_mean': [], # the evaluation for grid-world, key-door, and mountain-car problems
        'train_returns': [],
        'test_returns': [],
        'train_returns_mean': [],
        'test_returns_mean': [], # the evaluation for the treasure problem
        'train_returns_std': [],
        'test_returns_std': [],
        }

    # env = gym.make(config['env-name'], **config['env-kwargs'])
    env = gym.make(config['env-name'])
    env.close()

    # Policy
    policy = get_policy_for_env(env,
                                hidden_sizes=config['hidden-sizes'],
                                nonlinearity=config['nonlinearity'])
    policy.share_memory()

    # Baseline
    baseline = LinearFeatureBaseline(get_input_size(env))

    # Sampler
    sampler = MultiTaskSampler(config['env-name'],
                               env_kwargs=config['env-kwargs'],
                               batch_size=config['fast-batch-size'],
                               policy=policy,
                               baseline=baseline,
                               env=env,
                               seed=args.seed,
                               num_workers=args.num_workers)

    metalearner = MAMLTRPO(policy,
                           fast_lr=config['fast-lr'],
                           first_order=config['first-order'],
                           device=args.device)

    num_iterations = 0
    for batch in trange(config['num-batches']):
        tasks = sampler.sample_tasks(num_tasks=config['meta-batch-size'])
        # print(tasks)

        futures = sampler.sample_async(tasks,
                                       num_steps=config['num-steps'],
                                       fast_lr=config['fast-lr'],
                                       gamma=config['gamma'],
                                       gae_lambda=config['gae-lambda'],
                                       device=args.device)
        # print(futures)

        logs = metalearner.step(*futures,
                                max_kl=config['max-kl'],
                                cg_iters=config['cg-iters'],
                                cg_damping=config['cg-damping'],
                                ls_max_steps=config['ls-max-steps'],
                                ls_backtrack_ratio=config['ls-backtrack-ratio'])
        # print('logs')

        train_episodes, valid_episodes = sampler.sample_wait(futures)
        # print('train_episodes')

        num_iterations += sum(sum(episode.lengths) for episode in train_episodes[0])
        num_iterations += sum(sum(episode.lengths) for episode in valid_episodes)
        logs.update(tasks=tasks,
                    num_iterations=num_iterations,
                    train_returns=get_returns(train_episodes[0]),
                    valid_returns=get_returns(valid_episodes))
        train_returns = get_discounted_returns(train_episodes[0])
        test_returns = get_discounted_returns(valid_episodes)
        train_costs = get_costs(train_episodes[0])
        test_costs = get_costs(valid_episodes)

        # Save results
        results['train_returns'].append(train_returns)
        results['test_returns'].append(test_returns)
        results['train_returns_mean'].append(np.mean(train_returns))
        results['test_returns_mean'].append(np.mean(test_returns))
        results['train_returns_std'].append(np.std(train_returns))
        results['test_returns_std'].append(np.std(test_returns))

        results['train_costs'].append(train_costs)
        results['test_costs'].append(test_costs)
        results['train_costs_sum'].append(np.sum(train_costs))
        results['test_costs_sum'].append(np.sum(test_costs))
        results['train_costs_mean'].append(np.mean(train_costs))
        results['test_costs_mean'].append(np.mean(test_costs))

        with open(result_filename_txt, "w") as file: file.write(str(results))
        with open(result_filename_pickle, "wb") as file: dump(results, file, protocol=2)

        # Save policy
        if args.output_folder is not None:
            with open(policy_filename, 'wb') as f:
                torch.save(policy.state_dict(), f)

    print(np.sum(results['train_costs_sum']))


if __name__ == '__main__':
    import argparse
    import multiprocessing as mp

    parser = argparse.ArgumentParser(description='Reinforcement learning with '
        'Model-Agnostic Meta-Learning (MAML) - Train')

    parser.add_argument('--config', type=str, required=True,
        help='path to the configuration file.')

    # Miscellaneous
    misc = parser.add_argument_group('Miscellaneous')
    misc.add_argument('--output-folder', type=str,
        help='name of the output folder')
    misc.add_argument('--seed', type=int, default=None,
        help='random seed')
    misc.add_argument('--num-workers', type=int, default=mp.cpu_count() - 1,
        help='number of workers for trajectories sampling (default: '
             '{0})'.format(mp.cpu_count() - 1))
    misc.add_argument('--use-cuda', action='store_true',
        help='use cuda (default: false, use cpu). WARNING: Full upport for cuda '
        'is not guaranteed. Using CPU is encouraged.')

    args = parser.parse_args()
    args.device = ('cuda' if (torch.cuda.is_available()
                   and args.use_cuda) else 'cpu')

    main(args)
