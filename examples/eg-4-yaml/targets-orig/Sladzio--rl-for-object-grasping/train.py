import os
import yaml
import argparse
import numpy as np

from stable_baselines.her import HERGoalEnvWrapper
from stable_baselines.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines.ddpg.noise import OrnsteinUhlenbeckActionNoise, AdaptiveParamNoiseSpec

import object_data
from envs import PandaGraspGymEnv
from utils import MeanHundredEpsTensorboardCallback, SuccessRateTensorboardCallback, \
    StdHundredEpsTensorboardCallback, SaveOnBestTrainingRewardCallback
from utils import CustomMonitor
from utils import ALGOS

# best_mean_reward, n_steps = -np.inf, 0


def get_environment(_max_step_count=500, _additional_reward=9500, _min_horizontal_distance_reward=0.015,
                    _lock_rotation=True, _is_discrete=False):
    env = PandaGraspGymEnv(urdf_root=object_data.getDataPath(),
                           is_rendering=False,
                           use_ik=True,
                           is_discrete=_is_discrete,
                           num_controlled_joints=7,
                           lock_rotation=_lock_rotation,
                           max_step_count=_max_step_count,
                           additional_reward=_additional_reward,
                           min_horizontal_distance_reward=_min_horizontal_distance_reward,
                           reward_type='dense')
    return env


def main(_algo_name, _algo_tag, _tag_suffix, _save_freq, _lock_rotation, _eval_num, _eval_freq, hyperparams):
    rotation_tag = "_LOCKED_ROT_" if _lock_rotation else "_ROTATION_"
    full_tag = _algo_name + rotation_tag + _algo_tag + _tag_suffix
    current_dir = _algo_name + "/" + full_tag
    log_dir = current_dir + "/log/"
    eval_log_dir = current_dir + "/log/eval/"
    trained_models_dir = current_dir + "/models/"
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(eval_log_dir, exist_ok=True)
    os.makedirs(trained_models_dir, exist_ok=True)

    is_discrete = True if _algo_name == 'DQN' else False

    panda_env = HERGoalEnvWrapper(CustomMonitor(get_environment(_lock_rotation=_lock_rotation,
                                                                _is_discrete=is_discrete), log_dir))
    eval_env = HERGoalEnvWrapper(CustomMonitor(get_environment(_lock_rotation=_lock_rotation,
                                                               _is_discrete=is_discrete), eval_log_dir))

    callbacks = []
    callbacks.append(CheckpointCallback(_save_freq, trained_models_dir)) if _save_freq > 0 else None
    callbacks.append(MeanHundredEpsTensorboardCallback(log_dir))
    callbacks.append(StdHundredEpsTensorboardCallback(log_dir))
    callbacks.append(SuccessRateTensorboardCallback(log_dir))
    if _algo_name == 'DDPG':
        callbacks.append(SaveOnBestTrainingRewardCallback(10000, log_dir))
    else:
        callbacks.append(EvalCallback(eval_env,
                                      best_model_save_path=trained_models_dir,
                                      log_path=log_dir,
                                      eval_freq=_eval_freq,
                                      deterministic=True,
                                      render=False,
                                      n_eval_episodes=_eval_num)) if _eval_freq > 0 else None

    time_steps = hyperparams.pop('n_timesteps') if hyperparams.get('n_timesteps') is not None else None

    param_noise = None
    action_noise = None
    if hyperparams.get('noise_type') is not None:
        noise_type = hyperparams.pop('noise_type').strip()
        if 'ornstein-uhlenbeck' in noise_type:
            n_actions = panda_env.action_space.shape[-1]
            action_noise = OrnsteinUhlenbeckActionNoise(mean=np.zeros(n_actions),
                                                        sigma=float(0.005) * np.ones(n_actions))
        elif 'param_noise' in noise_type:
            param_noise = AdaptiveParamNoiseSpec(initial_stddev=0.1, desired_action_stddev=0.1)

    # add action noise for DDPG or TD3, in DQN noise as flag already in hyperparams
    if _algo_name == 'DDPG' or _algo_name == 'TD3':
        hyperparams['action_noise'] = action_noise

    # add hyperparams specific only for DDPG
    if _algo_name == 'DDPG':
        hyperparams['param_noise'] = param_noise
        hyperparams['eval_env'] = eval_env

    model = ALGOS[_algo_name](env=panda_env,
                              tensorboard_log="tensorboard/",
                              n_cpu_tf_sess=None,
                              **hyperparams)

    model.learn(total_timesteps=time_steps,
                callback=callbacks,
                tb_log_name=full_tag,
                log_interval=10)

    model.save(current_dir + "/" + full_tag + "_final")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--algo', help='RL Algorithm', default='DQN',
                        type=lambda x: str(x).upper(), required=False, choices=list(ALGOS.keys()))
    parser.add_argument('-t', '--tag', help='Name of configuration tag used for algorithm parameters '
                                            ' Default: TUNED', default='TUNED',
                        choices=['CLEAN', 'TUNED', 'NOISE'], type=lambda x: str(x).upper(), required=False)
    parser.add_argument('-s', '--suf', help='Suffix added for nametag of trained model',
                        default='', type=str, required=False)
    parser.add_argument('-l', '--lockRot', help='Should lock rotation of targeted object Default: True',
                        required=False, default=True, type=lambda x: (str(x).lower() == 'true'), choices=[True, False])
    parser.add_argument('--saveFreq', help='Save checkpoint model every n steps (if negative, no checkpoint)',
                        default=25000, type=int)

    parser.add_argument('--evalNum', help='Number of episodes to use for evaluation',
                        default=25, type=int)
    parser.add_argument('--evalFreq', help='Evaluate the model every n steps (if negative, no evaluation',
                        default=50000, type=int)
    args = parser.parse_args()

    _algorithm_name = str(args.algo).upper()

    # Load hyperparameters from yaml file
    with open('hyperparams/{}.yml'.format(_algorithm_name), 'r') as f:
        hyperparams_dict = yaml.safe_load(f)
        if args.tag in list(hyperparams_dict.keys()):
            hyperparams = hyperparams_dict[str(args.tag).upper()]
        else:
            raise ValueError("{} Hyperparameters not found for {}".format(args.tag, _algorithm_name))

    main(_algo_name=_algorithm_name, _algo_tag=str(args.tag).upper(),
         _tag_suffix=args.suf, _save_freq=args.saveFreq, _lock_rotation=args.lockRot,
         _eval_num=args.evalNum, _eval_freq=args.evalFreq,  hyperparams=hyperparams)
