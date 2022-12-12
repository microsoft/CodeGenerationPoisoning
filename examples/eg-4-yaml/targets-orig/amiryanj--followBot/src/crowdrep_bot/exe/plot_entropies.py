# Author: Javad Amirian
# Email: amiryan.j@gmail.com


import os
import yaml
from crowdrep_bot.run.social_ties_stats import analyze
from toolkit.loaders.loader_hermes import load_bottleneck
from toolkit.loaders.loader_metafile import load_eth, load_crowds
from toolkit.loaders.loader_sdd import load_sdd, load_sdd_dir
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')  # sudo apt-get install python3.7-tk


OPENTRAJ_ROOT = "/home/cyrus/workspace2/OpenTraj"
datasets = []


## SDD datasets
scenes = [
    # ['bookstore', 'video0'],
    # ['bookstore', 'video1'],
    ['coupa', 'video3']
]
sdd_scales_yaml_file = os.path.join(OPENTRAJ_ROOT, 'datasets/SDD', 'estimated_scales.yaml')
with open(sdd_scales_yaml_file, 'r') as f:
    scales_yaml_content = yaml.load(f, Loader=yaml.FullLoader)
for scene_i in scenes:
    scale = scales_yaml_content[scene_i[0]][scene_i[1]]['scale']
    sdd_dataset_i = load_sdd(os.path.join(OPENTRAJ_ROOT, "datasets/SDD", scene_i[0], scene_i[1], "annotations.txt"),
                             scene_id="SDD-"+scene_i[0]+scene_i[1], title="SDD-"+scene_i[0]+"-"+scene_i[1][-1], # use_kalman=True,
                             scale=scale, drop_lost_frames=False, sampling_rate=6)  # original fps=30
    datasets.append(sdd_dataset_i)


# annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/ETH/seq_eth/obsmat.txt')
# datasets.append(load_eth(annot_file, title="ETH-Univ"))

eth_hotel_annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/ETH/seq_hotel/obsmat.txt')
datasets.append(load_eth(eth_hotel_annot_file, title="ETH-Hotel"))

zara01_annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/UCY/zara01/annotation.vsp')
zara01 = load_crowds(zara01_annot_file, homog_file=os.path.join(OPENTRAJ_ROOT, "datasets/UCY/zara01/H.txt"), title="Zara01")
datasets.append(zara01)


## 1d HERMES
annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/HERMES/Corridor-1D/uo-180-180-180.txt')
datasets.append(load_bottleneck(annot_file, title="HERMES-" + os.path.basename(annot_file)[:-4]))

## 2d HERMES
annot_file = os.path.join(OPENTRAJ_ROOT, 'datasets/HERMES/Corridor-2D/bo-360-090-090.txt')
datasets.append(load_bottleneck(annot_file, title="HERMES-" + os.path.basename(annot_file)[:-4]))


H_strong_dict = {}
H_absent_dict = {}
for dataset in datasets:
    H_strong, H_absent = analyze(dataset, verbose=False)
    H_strong_dict[dataset.title] = H_strong
    H_absent_dict[dataset.title] = H_absent


plt.subplot(1, 2, 1)
plt.bar(H_strong_dict.keys(), H_strong_dict.values(),
        color=['pink', 'red', 'green', 'blue', 'cyan'])
plt.xticks(rotation=70)
plt.ylim([0.7, 1])

plt.subplot(1, 2, 2)
plt.bar(H_absent_dict.keys(), H_absent_dict.values(),
        color=['pink', 'red', 'green', 'blue', 'cyan'])

plt.ylim([0.7, 1])

plt.xticks(rotation=70)
plt.show()



