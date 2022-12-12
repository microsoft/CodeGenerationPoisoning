import os
import time
from datetime import datetime

import numpy as np
import yaml
from tabulate import tabulate

from flatland.envs.rail_env import RailAgentStatus

import utils
from env import env_utils
from policy.policies import POLICIES
from policy.action_selectors import PARAMETER_DECAYS, ACTION_SELECTORS


def print_agents_info(env, info, actions):
    '''
    Print information for each agent in a specific step
    '''
    _status_table = []
    for handle, agent in enumerate(env.agents):
        _status_table.append([
            handle,
            agent.status,
            agent.speed_data["speed"],
            agent.speed_data['position_fraction'],
            (
                agent.initial_position[0],
                agent.initial_position[1],
                agent.direction
            ) if agent.status == RailAgentStatus.READY_TO_DEPART else
            (
                agent.position[0],
                agent.position[1],
                agent.direction
            ) if agent.status != RailAgentStatus.DONE_REMOVED else (
                'DONE'
            ),
            agent.target,
            actions[handle],
            agent.malfunction_data['malfunction'],
            info["deadlocks"][handle]
        ])
    print(tabulate(
        _status_table,
        [
            "Handle", "Status", "Speed", "Position fraction",
            "Position", "Target", "Action Taken", "Malfunction", "Deadlock"
        ],
        colalign=["center"] * 9
    ))


def test_agents(args):
    '''
    Test agents on the specified environment
    '''
    choices_taken = np.zeros((args.testing.episodes,))
    scores, custom_scores, completions, steps, deadlocks = [], [], [], [], []

    # Initialize threads and seeds
    utils.set_num_threads(args.generic.num_threads)
    if args.generic.fix_random:
        utils.fix_random(args.generic.random_seed)

    # Create railway environment
    env = env_utils.create_rail_env(args, load_env=args.testing.load)

    # Load the model if provided
    if args.testing.model:
        parameter_decay = PARAMETER_DECAYS["none"](
            parameter_start=args.parameter_decay.start
        )
        action_selector = ACTION_SELECTORS["greedy"](parameter_decay)
        policy_type = args.policy.type.get_true_key()
        policy = POLICIES[policy_type](
            args, env.state_size, action_selector, training=False
        )
        policy.load(args.testing.model)
    else:
        policy = POLICIES["random"]()

    print("\n🚉 Starting testing \t Testing {} trains on {}x{} grid for {} episodes".format(
        args.env.num_trains,
        args.env.width, args.env.height,
        args.testing.episodes,
    ))

    # Perform the given number of episodes
    for episode in range(args.testing.episodes):
        score, custom_score, final_step = 0.0, 0.0, 0

        # Generate a new railway and renderer
        obs, info = env.reset(
            regenerate_rail=True, regenerate_schedule=True
        )
        if args.testing.renderer.enabled:
            env_renderer = env.get_renderer()

        # Print agents tasks
        if args.testing.verbose:
            _tasks_table = []
            for handle, agent in enumerate(env.agents):
                _tasks_table.append([
                    handle,
                    agent.status,
                    agent.speed_data["speed"],
                    (
                        agent.initial_position[0],
                        agent.initial_position[1],
                        agent.direction
                    ),
                    agent.target
                ])
            print(f"Episode {episode}")
            print(tabulate(
                _tasks_table,
                ["Handle", "Status", "Speed", "Source", "Target"],
                colalign=["center"] * 5
            ))
            print()

        # Create frames directory
        now = datetime.now()
        test_id = now.strftime('%Y%m%d-%H%M%S')
        if args.testing.renderer.enabled and args.testing.renderer.save_frames:
            frames_dir = f"tmp/frames/{test_id}"
            os.makedirs(frames_dir, exist_ok=True)

        # Compute agents with same source
        agents_with_same_start = env.get_agents_same_start()

        for step in range(env._max_episode_steps):

            # Prioritize entry of faster agent in the environment
            for position in agents_with_same_start:
                if len(agents_with_same_start[position]) > 0:
                    del agents_with_same_start[position][0]
                    for agent in agents_with_same_start[position]:
                        info['action_required'][agent] = False

            # Policy act
            legal_actions, legal_choices, moving_agents = env.pre_act()
            choices, is_best = policy.act(
                list(obs.values()), legal_choices,
                moving_agents, training=False
            )
            action_dict, metadata = env.post_act(
                choices, is_best, legal_actions, moving_agents
            )
            current_choices_count = metadata['choices_count']
            choices_taken[episode] += np.sum(current_choices_count)

            # Environment step
            obs, rewards, custom_rewards, done, info = env.step(
                action_dict
            )

            # Render an episode at some interval
            if args.testing.renderer.enabled:
                env_renderer.render_env(
                    show=True, show_observations=False, show_predictions=True, show_rowcols=True
                )

                # Wait to observe the current frame
                if args.testing.renderer.sleep > 0:
                    time.sleep(args.testing.renderer.sleep)

                # Save renderer frame
                if args.testing.renderer.save_frames:
                    env_renderer.gl.save_image(
                        "{:s}/{:04d}.png".format(frames_dir, step)
                    )

            # Update agents score
            for handle in range(env.get_num_agents()):
                score += rewards[handle]
                custom_score += custom_rewards[handle]

            # Compute statistics
            if args.testing.verbose:
                normalized_score = (
                    score / (env._max_episode_steps * env.get_num_agents())
                )
                normalized_custom_score = custom_score / env.get_num_agents()
                print(
                    f"Score: {round(normalized_score, 4)} /"
                    f"Custom score: {round(normalized_custom_score, 4)}"
                )
                print_agents_info(env, info, action_dict)
                print()

            # Check if every agent is arrived
            final_step = step
            if done['__all__'] or env.check_if_all_blocked(info["deadlocks"]):
                break

        # Close window
        if args.testing.renderer.enabled:
            env_renderer.close_window()

        # Save final scores
        scores.append(
            score / (
                env._max_episode_steps *
                env.get_num_agents()
            )
        )
        custom_scores.append(custom_score / env.get_num_agents())
        completions.append(
            sum(done[idx] for idx in env.get_agent_handles()) /
            env.get_num_agents()
        )
        steps.append(final_step)
        deadlocks.append(
            sum(int(v) for v in info["deadlocks"].values()) /
            env.get_num_agents()
        )

        # Print episode info
        print(
            '\r🚂 Test {:4n}'
            '\t 🏆 Score: {:<+5.4f}'
            ' Avg: {:>+5.4f}'
            '\t 🏅 Custom score: {:<+5.4f}'
            ' Avg: {:>+5.4f}'
            '\t 💯 Done: {:<7.2%}'
            ' Avg: {:>7.2%}'
            '\t 💀 Deadlocks: {:<7.2%}'
            ' Avg: {:>7.2%}'
            '\t 🦶 Steps: {:4n}/{:4n}'
            '\t 🤔 Choices: {:4n}'.format(
                episode,
                scores[-1],
                np.mean(scores),
                custom_scores[-1],
                np.mean(custom_scores),
                completions[-1],
                np.mean(completions),
                deadlocks[-1],
                np.mean(deadlocks),
                steps[-1],
                env._max_episode_steps,
                choices_taken[episode]
            ), end="\n"
        )

    # Print final testing info
    print("\n\r🏁 Testing ended \tTested {} trains on {}x{} grid for {} episodes".format(
        args.env.num_trains, args.env.width, args.env.height, args.testing.episodes
    ))

    # Print final testing results
    print(
        '\r✅ Testing ended'
        '\t 🏆 Avg score: {:+7.4f}'
        '\t 🏅 Avg custom score: {:+7.4f}'
        '\t 💯 Avg done: {:7.4f}'
        '\t 💀 Avg deadlocks: {:7.4f}'
        '\t 🦶 Avg steps: {:5.2f}'
        '\t 🤔 Avg choices: {:5.2f}'.format(
            np.mean(scores),
            np.mean(custom_scores),
            np.mean(completions),
            np.mean(deadlocks),
            np.mean(steps),
            np.mean(choices_taken)
        ), end="\n\n"
    )


def main():
    '''
    Test environment with the given model
    '''
    with open('parameters.yml', 'r') as conf:
        args = yaml.load(conf, Loader=yaml.FullLoader)
    args = utils.Struct(**args)
    test_agents(args)


if __name__ == "__main__":
    main()
