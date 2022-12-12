# Author: Javad Amirian
# Email: amiryan.j@gmail.com


import os
import tqdm
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)
matplotlib.use('TkAgg')

from crowdrep_bot.crowd_imputation.social_ties import SocialTiePDF
from toolkit.loaders.loader_hermes import load_bottleneck
from crowdrep_bot.run.repbot import SAVE_SIM_DATA_DIR


def analyze(dataset, verbose=True):
    min_x, max_x = min(dataset.data["pos_x"]), max(dataset.data["pos_x"])
    min_y, max_y = min(dataset.data["pos_y"]), max(dataset.data["pos_y"])
    # -------------------------------

    frames = dataset.get_frames()
    n_frames = len(frames)
    dt_ = np.diff(dataset.data["timestamp"].unique()[:2])[0]
    fps = int(round(1 / dt_))
    n_agents = dataset.data["agent_id"].nunique()

    all_ties = {}
    strong_ties = []
    absent_ties = []
    tie_strength = []

    # algorithm thresholds
    max_distance = 5
    thre_length = 0.5
    thre_angle = np.pi / 8
    prev_t = fps//2

    # visualize stuff
    if verbose:
        _, ax = plt.subplots()
        ax.set_aspect(aspect='equal')

    for t in tqdm.trange(int(len(frames) * 0.7)):
        frame_data = frames[t]

        pids_t = frame_data["agent_id"]
        N = len(pids_t)
        if N < 2:
            continue

        poss_t = frame_data[["pos_x", "pos_y"]].to_numpy()
        vels_t = frame_data[["vel_x", "vel_y"]].to_numpy()
        rot_matrices_t = np.zeros((N, 2, 2))
        oriens_t = np.arctan2(vels_t[:, 1], vels_t[:, 0])

        if verbose:
            plt.cla()
            plt.xlim([min_x, max_x])
            plt.ylim([min_y, max_y])
            plt.scatter(poss_t[:, 0], poss_t[:, 1], color='blue', alpha=0.3)

        tiled_poss = np.tile(poss_t, (N, 1, 1))
        D = tiled_poss - tiled_poss.transpose((1, 0, 2))

        link_angles = np.arctan2(D[:, :, 1], D[:, :, 0])
        link_lengths = np.linalg.norm(D, axis=2)
        for ii, pid_i in enumerate(pids_t):
            for jj, pid_j in enumerate(pids_t):
                if ii == jj:
                    continue

                IJ_idx = (pid_i, pid_j)
                if IJ_idx not in all_ties:
                    all_ties[IJ_idx] = []
                rotated_link_angle = (link_angles[ii, jj] - oriens_t[ii] + np.pi) % (2 * np.pi) - np.pi
                all_ties[IJ_idx].append([link_lengths[ii, jj], rotated_link_angle])
                if len(all_ties[IJ_idx]) >= prev_t:  # this agent is here for at least 1 sec
                    d_tie_len = all_ties[IJ_idx][-1][0] - all_ties[IJ_idx][-prev_t][0]
                    d_tie_angle = all_ties[IJ_idx][-1][1] - all_ties[IJ_idx][-prev_t][1]
                    d_tie_angle = (d_tie_angle + np.pi) % (2 * np.pi) - np.pi
                    d_orien = (oriens_t[ii] - oriens_t[jj] + np.pi) % (2 * np.pi) - np.pi
                    if all_ties[IJ_idx][-1][0] > max_distance:
                        continue

                    if abs(d_tie_len) < thre_length and abs(d_tie_angle) < thre_angle and abs(d_orien) < np.pi / 4:
                        strong_ties.append(all_ties[IJ_idx][-1])
                        if verbose:
                            plt.plot([poss_t[ii, 0], poss_t[jj, 0]], [poss_t[ii, 1], poss_t[jj, 1]], 'g')
                    else:
                        absent_ties.append(all_ties[IJ_idx][-1])
                        if verbose:
                            plt.plot([poss_t[ii, 0], poss_t[jj, 0]], [poss_t[ii, 1], poss_t[jj, 1]], 'r--', alpha=0.2)

        if verbose:
            plt.plot([poss_t[:, 0], poss_t[:, 0] + vels_t[:, 0] * 0.5],
                     [poss_t[:, 1], poss_t[:, 1] + vels_t[:, 1] * 0.5],
                     '-b', alpha=0.7)

        frame_id = frame_data["frame_id"].unique()
        if verbose:
            plt.pause(0.01)
            plt.savefig(os.path.join(save_links_dir, dataset.title + '-%04d.png' % frame_id))
        # print("frame_id:", frame_id)

    # count the percent
    n_strongs = len(strong_ties)
    n_absents = len(absent_ties)
    print("*******************************")
    print("Dataset:", dataset.title)
    print("# total ties= [%d]" % (n_absents + n_strongs))
    print("absent ties= [%d] , %.3f" % (n_absents, n_absents / (n_absents + n_strongs + 1E-6)))
    print("strong ties= [%d] , %.3f" % (n_strongs, n_strongs / (n_absents + n_strongs + 1E-6)))

    p = SocialTiePDF(max_distance, radial_resolution=4, angular_resolution=36)
    p.add_strong_ties(strong_ties)
    p.add_absent_ties(absent_ties)
    p.update_pdf()

    # Compute Histogram
    pk_strong = p.strong_ties_pdf_polar.copy()
    pk_strong /= np.sum(pk_strong)
    pk_absent = p.absent_ties_pdf_polar.copy()
    pk_absent /= np.sum(pk_absent)

    # H_p = entropy(pk=pk.reshape(-1, 1)) / np.log(pk.size)
    # print("Entropy of Link Distribution(%) = ", H_p)

    # considering area of each bin
    area_k = np.tile(np.pi * np.diff(p.rho_edges ** 2) / (len(p.theta_edges) - 1), (p.strong_ties_pdf_polar.shape[1], 1)).T
    H_p_max = np.log(np.sum(area_k))

    with np.errstate(divide='ignore'):
        abs_entropy_strong_p = -np.nansum(np.log(pk_strong / area_k) * pk_strong)
        abs_entropy_absent_p = -np.nansum(np.log(pk_absent / area_k) * pk_absent)
    print("Normalized Entropy of Strong Ties Distribution(%) = ", abs_entropy_strong_p / H_p_max)
    print("Normalized Entropy of Absent Ties Distribution(%) = ", abs_entropy_absent_p / H_p_max)
    print("*******************************")

    p.smooth_pdf()
    p.save_pdf(os.path.join(SAVE_SIM_DATA_DIR, dataset.title))
    # p.load_pdf(os.path.join(EXP_DATA_PATH, dataset.title))

    # print(p.polar_link_pdf)
    if verbose:
        plt.close()
        p.plot(dataset.title)
        plt.savefig(os.path.join(output_dir, '%s-link-pdf.pdf' % dataset.title), dpi=300, bbox_inches='tight')
        plt.savefig(os.path.join(output_dir, '%s-link-pdf.png' % dataset.title), dpi=300, bbox_inches='tight')

    return abs_entropy_strong_p / H_p_max, abs_entropy_absent_p / H_p_max



if __name__ == "__main__":
    datasets = []
    OPENTRAJ_ROOT = "/home/cyrus/workspace2/OpenTraj"
    output_dir = "/home/cyrus/Dropbox/FollowBot/exp/pdf"
    save_links_dir = "/home/cyrus/Dropbox/FollowBot/exp/links"
    VERBOSE = True

    # ======== load dataset =========
    # annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/ETH/seq_eth/obsmat.txt')
    # datasets.append(load_eth(annot_file, title="ETH-Univ"))

    # annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/ETH/seq_hotel/obsmat.txt')
    # datasets.append(load_eth(annot_file, title="ETH-Hotel"))

    # annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/UCY/zara01/annotation.vsp')
    # zara01 = load_crowds(annot_file, homog_file=os.path.join(OPENTRAJ_ROOT, "datasets/UCY/zara01/H.txt"), title="Zara01")
    # datasets.append(zara01)

    # annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/UCY/zara02/annotation.vsp')
    # zara02 = load_crowds(annot_file, homog_file=os.path.join(OPENTRAJ_ROOT, "datasets/UCY/zara02/H.txt"), title="Zara02")
    # datasets.append(zara02)
    # datasets.append(merge_datasets([zara01, zara02], new_title="Zara"))

    # SDD datasets
    # scenes = [['bookstore', 'video0'], ['bookstore', 'video1'], ['coupa', 'video0']]
    # sdd_scales_yaml_file = os.path.join(OPENTRAJ_ROOT, 'datasets/SDD', 'estimated_scales.yaml')
    # with open(sdd_scales_yaml_file, 'r') as f:
    #     scales_yaml_content = yaml.load(f, Loader=yaml.FullLoader)
    # for scene_i in scenes:
    #     scale = scales_yaml_content[scene_i[0]][scene_i[1]]['scale']
    #     sdd_dataset_i = load_sdd(os.path.join(OPENTRAJ_ROOT, "datasets/SDD", scene_i[0], scene_i[1], "annotations.txt"),
    #                              scene_id="SDD-"+scene_i[0]+scene_i[1], title="SDD-"+scene_i[0]+"-"+scene_i[1][-1], # use_kalman=True,
    #                              scale=scale, drop_lost_frames=False, sampling_rate=6)  # original fps=30
    #     datasets.append(sdd_dataset_i)

    # 1d HERMES
    # annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/HERMES/Corridor-1D/uo-180-180-180.txt')
    # annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/HERMES/Corridor-1D/uo-300-300-300.txt')
    # datasets.append(load_bottleneck(annot_file, title="HERMES-" + os.path.basename(annot_file)[:-4]))

    # 2d HERMES
    # annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/HERMES/Corridor-2D/bo-360-050-050.txt')
    # annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/HERMES/Corridor-2D/bo-360-160-160.txt')
    # annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/HERMES/Corridor-2D/bo-360-075-075.txt')
    annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/HERMES/Corridor-2D/bo-360-090-090.txt')
    # annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/HERMES/Corridor-2D/bot-360-250-250.txt')
    datasets.append(load_bottleneck(annot_file, title="HERMES-" + os.path.basename(annot_file)[:-4]))
    # -------------------------------

    for ds in datasets:
        analyze(ds, verbose=VERBOSE)
    plt.show()
