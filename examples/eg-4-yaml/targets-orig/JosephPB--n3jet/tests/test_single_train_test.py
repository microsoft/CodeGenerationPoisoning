import numpy as np
import yaml
import pytest

from n3jet.general import SingleModelRun

example_config = "./configs/example_config.yaml"

def test__yaml_readin():

    singlemodel = SingleModelRun.from_yaml(yaml_file = example_config)
    
    with open(example_config) as f:
        y = yaml.load(f, Loader=yaml.FullLoader)

    assert singlemodel.mom_file == y["training"]["mom_file"]
    assert singlemodel.nj_file == y["training"]["nj_file"]
    assert singlemodel.delta_cut == y["delta_cut"]

def test__recut_data(dummy_data_all_legs_training):

    momenta, cut_mom, near_mom, labels, cut_labs, near_labs, delta_cut, delta_near = dummy_data_all_legs_training

    singlemodel = SingleModelRun.from_yaml(example_config)
    singlemodel.delta_cut = delta_cut

    mom, nj = singlemodel.recut_data(momenta, labels)

    assert len(mom) == len(momenta)
    assert len(nj) == len(labels)

    singlemodel.delta_cut = 0.5
    mom, nj = singlemodel.recut_data(momenta, labels)

    assert len(mom) < len(momenta)
    assert len(nj) < len(labels)

def test__train(dummy_data_all_legs_training):
    
    momenta, cut_mom, near_mom, labels, cut_labs, near_labs, delta_cut, delta_near = dummy_data_all_legs_training

    singlemodel = SingleModelRun.from_yaml(example_config)
    singlemodel.delta_cut = 0.0
    singlemodel.model_base_dir = ""
    singlemodel.model_dir = ""
    singlemodel.nlegs = 3
    singlemodel.epochs = 1
    singlemodel.training_reruns = 1

    mom, nj = singlemodel.recut_data(momenta, labels)

    singlemodel.train_networks(mom, nj)
