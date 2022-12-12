import numpy as np
import yaml
import pytest

from n3jet.general import FKSModelRun

example_config = "./configs/example_config.yaml"

def test__yaml_readin():

    fksmodel = FKSModelRun.from_yaml(yaml_file = example_config)
    
    with open(example_config) as f:
        y = yaml.load(f, Loader=yaml.FullLoader)

    assert fksmodel.mom_file == y["training"]["mom_file"]
    assert fksmodel.nj_file == y["training"]["nj_file"]
    assert fksmodel.delta_cut == y["delta_cut"]
    assert fksmodel.delta_near == y["delta_near"]

def test__split_data(dummy_data_all_legs_training):

    momenta, cut_mom, near_mom, labels, cut_labs, near_labs, delta_cut, delta_near = dummy_data_all_legs_training

    fksmodel = FKSModelRun.from_yaml(example_config)
    fksmodel.delta_cut = 0.0
    fksmodel.delta_near = 0.02

    cut_momenta, near_momenta, cut_nj, near_nj, pairs, near_nj_split = fksmodel.split_data(momenta, labels)

    assert len(np.where(np.all(np.array(cut_momenta)==np.array(cut_mom)[0],axis=(1,2)))[0]) > 0
    assert len(np.where(np.array(cut_nj)==cut_labs)) > 0

    assert len(np.where(np.all(np.array(near_momenta)==np.array(near_mom)[0],axis=(1,2)))[0]) > 0
    assert len(np.where(np.array(near_nj)==near_labs)) > 0

def test__train(dummy_data_all_legs_training):
    
    momenta, cut_mom, near_mom, labels, cut_labs, near_labs, delta_cut, delta_near = dummy_data_all_legs_training

    fksmodel = FKSModelRun.from_yaml(example_config)
    fksmodel.delta_cut = delta_cut
    fksmodel.delta_near = delta_near
    fksmodel.model_base_dir = ""
    fksmodel.model_dir = ""
    fksmodel.nlegs = 3
    fksmodel.epochs = 1
    fksmodel.training_reruns = 1
    
    cut_momenta, near_momenta, cut_nj, near_nj, pairs, near_nj_split = fksmodel.split_data(momenta, labels)

    fksmodel.train_networks(cut_momenta, near_momenta, cut_nj, near_nj, pairs, near_nj_split)
