# Author: Javad Amirian
# Email: amiryan.j@gmail.com

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from tqdm import tqdm

from crowdrep_bot.scenarios.human_traj_scenario import HumanTrajectoryScenario
from crowdrep_bot.scenarios.real_scenario import RealScenario

from crowdrep_bot.run import repbot
from crowdrep_bot.run.repbot import BIPED_MODE

matplotlib.use('TkAgg')

from toolkit.loaders.loader_metafile import load_eth, load_crowds

datasets = []
opentraj_root = '/home/cyrus/workspace2/OpenTraj'
output_dir = "/home/cyrus/Dropbox/FollowBot/exp/occlusion"
# ======== load dataset =========
annot_file = os.path.join(opentraj_root, 'datasets/ETH/seq_eth/obsmat.txt')
datasets.append(load_eth(annot_file, title="ETH-Univ"))
#
# annot_file = os.path.join(opentraj_root, 'datasets/ETH/seq_hotel/obsmat.txt')
# datasets.append(load_eth(annot_file, title="ETH-Hotel"))
#
annot_file = os.path.join(opentraj_root, 'datasets/UCY/zara01/annotation.vsp')
zara01 = load_crowds(annot_file, homog_file=os.path.join(opentraj_root, "datasets/UCY/zara01/H.txt"), title="Zara01",
                     use_kalman=False)
datasets.append(zara01)

# annot_file = os.path.join(opentraj_root, 'datasets/UCY/zara02/annotation.vsp')
# zara02 = load_crowds(annot_file, homog_file=os.path.join(opentraj_root, "datasets/UCY/zara02/H.txt"), title="Zara02")
# datasets.append(zara02)
# datasets.append(merge_datasets([zara01, zara02], new_title="Zara"))

# SDD datasets
# scenes = [['bookstore', 'video0'], ['bookstore', 'video1'], ['coupa', 'video0']]
# sdd_scales_yaml_file = os.path.join(opentraj_root, 'datasets/SDD', 'estimated_scales.yaml')
# with open(sdd_scales_yaml_file, 'r') as f:
#     scales_yaml_content = yaml.load(f, Loader=yaml.FullLoader)
# for scene_i in scenes:
#     scale = scales_yaml_content[scene_i[0]][scene_i[1]]['scale']
#     sdd_dataset_i = load_sdd(os.path.join(opentraj_root, "datasets/SDD", scene_i[0], scene_i[1], "annotations.txt"),
#                              scene_id="SDD-"+scene_i[0]+scene_i[1], title="SDD-"+scene_i[0]+"-"+scene_i[1][-1], # use_kalman=True,
#                              scale=scale, drop_lost_frames=False, sampling_rate=6)  # original fps=30
#     datasets.append(sdd_dataset_i)


# 1d HERMES
# annot_file = os.path.join(opentraj_root, 'datasets/HERMES/Corridor-1D/uo-180-180-180.txt')
# annot_file = os.path.join(opentraj_root, 'datasets/HERMES/Corridor-1D/uo-300-300-300.txt')
# datasets.append(load_bottleneck(annot_file, title="HERMES-" + os.path.basename(annot_file)[:-4]))

# 2d HERMES
# annot_file = os.path.join(opentraj_root, 'datasets/HERMES/Corridor-2D/bo-360-050-050.txt')
# annot_file = os.path.join(opentraj_root, 'datasets/HERMES/Corridor-2D/bo-360-160-160.txt')
# annot_file = os.path.join(opentraj_root, 'datasets/HERMES/Corridor-2D/bo-360-075-075.txt')
# annot_file = os.path.join(opentraj_root, 'datasets/HERMES/Corridor-2D/bot-360-250-250.txt')
# datasets.append(load_bottleneck(annot_file, title="HERMES-" + os.path.basename(annot_file)[:-4]))
# -------------------------------

scenarios = []
for dataset in datasets:
    dataset.interpolate_frames(inplace=True)
    agent_ids = dataset.data["agent_id"].unique()
    occlusion_freqs = np.zeros((4, 10), np.int)

    # loop for change agent replaced by robot
    for agent_id in sorted(agent_ids):
        # try:
            if "HERMES" in dataset.title:
                scenario = HumanTrajectoryScenario()
                scenario.setup(dataset=dataset, robot_id=agent_id, biped_mode=BIPED_MODE)
            else:
                scenario = RealScenario()
                scenario.setup(dataset=dataset, fps=dataset.fps, robot_id=agent_id, biped_mode=BIPED_MODE)
            # scenarios.append(scenario)

            visualizer_enabled = False
            for frame_id, robot in tqdm(repbot.exec_scenario(scenario),
                                        desc="processing scenario [%s][%d/%d]" %(dataset.title, agent_id, len(agent_ids))):
                # print("agnet = %d, frame [%d]" %(agent_id, frame_id))
                # if frame_id > 10: break
                pass

            dists_from_robot = []
            for dist_i, occlusion_vals_i in sorted(robot.lidar.data.occlusion_hist.items()):
                dists_from_robot.append(dist_i)
                hist_at_dist_i, _ = np.histogram(occlusion_vals_i, bins=[0, 15, 50, 85, 101])
                for jj, bin_val in enumerate(hist_at_dist_i):
                    if dist_i < 11:
                        occlusion_freqs[jj, dist_i] += bin_val
            # print(occlusion_freqs)
        # except:
        #     print("An error occured for scenario")

        # if agent_id > 10: break # FixME

    dists_from_robot = np.stack(dists_from_robot) + (dists_from_robot[1] - dists_from_robot[0])/2.
    occlusion_freqs = np.array(occlusion_freqs)[:, :10]

    fig = plt.figure()
    wid = 0.8  # the width of the bars: can also be len(x) sequence
    p1 = plt.bar(dists_from_robot, occlusion_freqs[0], wid, label='Fully Visible', color='green')
    p2 = plt.bar(dists_from_robot, occlusion_freqs[1], wid, bottom=occlusion_freqs[0], label='Partially Occluded', color='yellow')
    p3 = plt.bar(dists_from_robot, occlusion_freqs[2], wid, bottom=np.sum(occlusion_freqs[0:2], axis=0), label='Largely Occluded', color='orange')
    p4 = plt.bar(dists_from_robot, occlusion_freqs[3], wid, bottom=np.sum(occlusion_freqs[0:3], axis=0), label='Fully Occluded', color='red')

    plt.xticks(range(0, 9))
    plt.xlim([0, 9])
    plt.legend()
    plt.title(dataset.title)
    plt.xlabel("dist from robot")
    plt.ylabel("freq")

    txt_file = os.path.join("/home/cyrus/Dropbox/FollowBot/exp/occlusion", dataset.title + "-hist.txt")
    with open(txt_file, 'w') as f:
        np.savetxt(f, occlusion_freqs, fmt='%i', delimiter=", ")
    plt.savefig(os.path.join("/home/cyrus/Dropbox/FollowBot/exp/occlusion", dataset.title + ".png"))
    plt.pause(2)

    # break
