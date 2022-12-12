import os
import numpy as np
import random
import time
import pickle
from tqdm import tqdm
import yaml

from n3jet.utils import FKSPartition
from n3jet.utils.fks_utils import (
    train_near_networks_general,
    train_cut_network_general,
    get_near_networks_general,
    get_cut_network_general,
    infer_on_near_splits,
    infer_on_cut
)
from n3jet.utils.general_utils import (
    bool_convert,
    file_exists
)
from n3jet.models import Model

class FKSModelRun:

    def __init__(
            self,
            mom_file,
            nj_file,
            delta_cut,
            delta_near,
            model_base_dir,
            model_dir,
            training_reruns,
            all_legs,
            all_pairs,
            scaling='standardise',
            layers=[20,40,20],
            lr=0.01,
            activation='tanh',
            loss='mean_squared_error',
            epochs=1000000,
            high_precision=False,
            model_dataset=False,
            
    ):
        self.mom_file = mom_file
        self.nj_file = nj_file
        self.delta_cut = delta_cut
        self.delta_near = delta_near
        self.model_base_dir = model_base_dir
        self.model_dir = model_dir
        self.training_reruns = training_reruns
        self.all_legs = all_legs
        self.all_pairs = all_pairs
        self.scaling = scaling
        self.layers = layers
        self.lr=lr
        self.activation = activation
        self.loss = loss
        self.epochs = epochs
        self.high_precision = high_precision
        self.model_dataset = model_dataset

    @classmethod
    def from_yaml(self, yaml_file, training=True):
        "Initiate from YAML file"

        print (yaml_file)
        file_exists(yaml_file)

        with open(yaml_file) as f:
            y = yaml.load(f, Loader=yaml.FullLoader)

        if training:
            mom_file = y["training"]["mom_file"]
            nj_file = y["training"]["nj_file"]
        else:
            mom_file = y["testing"]["mom_file"]
            nj_file = y["testing"]["nj_file"]
        delta_cut = y["delta_cut"]
        delta_near = y["delta_near"]
        model_base_dir = y["model_base_dir"]
        model_dir = y["model_dir"]
        training_reruns = y["training"]["training_reruns"]
        all_legs = bool_convert(y["all_legs"])
        all_pairs = bool_convert(y["all_pairs"])
        scaling = y.get("scaling", "standardise")
        layers = y["training"].get("layers", [20,40,20])
        lr = y["training"].get("lr", 0.01)
        activation = y["training"].get("activation", "tanh")
        loss = y["training"].get("loss", "mean_squared_error")
        epochs = y["training"].get("epochs", 1000000)
        high_precision = bool_convert(y["training"].get("high_precision", "False"))
        model_dataset = bool_convert(y["training"].get("model_dataset", "False"))
        
        return FKSModelRun(
            mom_file = mom_file,
            nj_file = nj_file,
            delta_cut = delta_cut,
            delta_near = delta_near,
            model_base_dir = model_base_dir,
            model_dir = model_dir,
            training_reruns = training_reruns,
            all_legs = all_legs,
            all_pairs = all_pairs,
            scaling = scaling,
            layers = layers,
            lr = lr,
            activation = activation,
            loss = loss,
            epochs = epochs,
            high_precision = high_precision,
            model_dataset = model_dataset,
        )

    def load_data(self):

        file_exists(self.mom_file)
        file_exists(self.nj_file)

        momenta = np.load(self.mom_file,allow_pickle=True)
        print ('############### Momenta loaded ###############')
        
        nj = np.load(self.nj_file,allow_pickle=True)
        print ('############### NJet loaded ###############')

        momenta = momenta.tolist()
        print ('Training on {} PS points'.format(len(momenta)))

        self.nlegs = len(momenta[0])-2

        return momenta, nj
    
    
    def split_data(self, momenta, nj, return_weights = False):

        fks = FKSPartition(
            momenta = momenta,
            labels = nj,
            all_legs = self.all_legs
        )
            
        cut_momenta, near_momenta, cut_nj, near_nj = fks.cut_near_split(
            delta_cut = self.delta_cut,
            delta_near = self.delta_near
        )
        
        if return_weights:
            pairs, near_nj_split, weights = fks.weighting(return_weights = return_weights)
            return cut_momenta, near_momenta, cut_nj, near_nj, pairs, near_nj_split, weights
        else:
            pairs, near_nj_split = fks.weighting(return_weights = return_weights)
            return cut_momenta, near_momenta, cut_nj, near_nj, pairs, near_nj_split


    def train_networks(self, cut_momenta, near_momenta, cut_nj, near_nj, pairs, near_nj_split):

        if self.model_base_dir == "":
            pass
        elif os.path.exists(self.model_base_dir) == False:
            os.mkdir(self.model_base_dir)
            print ('Creating base directory')
        else:
            print ('Base directory already exists')
        

        for i in range(self.training_reruns):
            print ('Working on model {}'.format(i))
            if self.model_base_dir == "":
                model_dir_new = ""
            elif self.model_dir == "":
                model_dir_new = ""
            else:
                model_dir_new = self.model_base_dir + self.model_dir + '_{}/'.format(i)
                print ('Looking for directory {}'.format(model_dir_new))
            
                if os.path.exists(model_dir_new) == False:
                    os.mkdir(model_dir_new)
                    print ('Directory created')
                else:
                    print ('Directory already exists')

            
            if self.all_legs:
                all_jets = False
                nlegs = self.nlegs + 2
            else:
                all_jets = True
                nlegs = self.nlegs
            
            model_near, x_mean_near, x_std_near, y_mean_near, y_std_near = train_near_networks_general(
                input_size = (nlegs)*4,
                pairs = pairs,
                near_momenta = near_momenta,
                NJ_split = near_nj_split,
                delta_near = self.delta_near,
                model_dir = model_dir_new,
                all_jets = all_jets,
                all_legs = self.all_legs,
                model_dataset = self.model_dataset,
                scaling = self.scaling,
                lr = self.lr,
                layers = self.layers,
                activation = self.activation,
                loss = self.loss,
                epochs = self.epochs,
                high_precision = self.high_precision
            )
            model_cut, x_mean_cut, x_std_cut, y_mean_cut, y_std_cut =  train_cut_network_general(
                input_size = (nlegs)*4,
                cut_momenta = cut_momenta,
                NJ_cut = cut_nj,
                delta_cut = self.delta_cut,
                model_dir = model_dir_new,
                all_jets = all_jets,
                all_legs = self.all_legs,
                model_dataset = self.model_dataset,
                scaling = self.scaling,
                lr = self.lr,
                layers = self.layers,
                activation = self.activation,
                loss = self.loss,
                epochs = self.epochs,
                high_precision = self.high_precision
            )

    def load_models(self, cut_momenta, near_momenta, cut_nj, near_nj, pairs, near_nj_split):

        if self.all_legs:
            all_jets = False
            nlegs = self.nlegs + 2
        else:
            all_jets = True
            nlegs = self.nlegs

        NN = Model(
            input_size = (nlegs)*4,
            momenta = near_momenta,
            labels = near_nj_split[0],
            all_jets = all_jets,
            all_legs = self.all_legs,
            model_dataset = self.model_dataset,
            high_precision = self.high_precision
        )
        
        _,_,_,_,_,_,_,_ = NN.process_training_data()
        
        models = []
        x_means = []
        y_means = []
        x_stds = []
        y_stds = []
        model_nears = []
        model_cuts = []

        x_mean_nears = []
        x_std_nears = []
        y_mean_nears = []
        y_std_nears = []

        x_mean_cuts = []
        x_std_cuts = []
        y_mean_cuts = []
        y_std_cuts = []

        for i in range(self.training_reruns):
            print ('Working on model {}'.format(i))
            model_dir_new = self.model_base_dir + self.model_dir + '_{}/'.format(i)
            print ('Looking for directory {}'.format(model_dir_new))
            if os.path.exists(model_dir_new) == False:
                os.mkdir(model_dir_new)
                print ('Directory created')
            else:
                print ('Directory already exists')

            model_near, x_mean_near, x_std_near, y_mean_near, y_std_near = get_near_networks_general(
                NN = NN,
                pairs = pairs,
                delta_near = self.delta_near,
                model_dir = model_dir_new
            )
            
            assert len(model_near) == len(pairs)
            
            model_cut, x_mean_cut, x_std_cut, y_mean_cut, y_std_cut = get_cut_network_general(
                NN = NN,
                delta_cut = self.delta_cut,
                model_dir = model_dir_new
            )

            model_nears.append(model_near)
            model_cuts.append(model_cut)

            x_mean_nears.append(x_mean_near)
            x_std_nears.append(x_std_near)
            y_mean_nears.append(y_mean_near)
            y_std_nears.append(y_std_near)

            x_mean_cuts.append(x_mean_cut)
            x_std_cuts.append(x_std_cut)
            y_mean_cuts.append(y_mean_cut)
            y_std_cuts.append(y_std_cut)

        print ('############### All models loaded ###############')

        return model_nears, model_cuts, x_mean_nears, x_mean_cuts, x_std_nears, x_std_cuts, y_mean_nears, y_mean_cuts, y_std_nears, y_std_cuts

    def test_networks(
            self,
            near_momenta,
            cut_momenta,
            near_nj_split,
            model_nears,
            model_cuts,
            x_mean_nears,
            x_mean_cuts,
            x_std_nears,
            x_std_cuts,
            y_mean_nears,
            y_mean_cuts,
            y_std_nears,
            y_std_cuts,
            return_predictions = False
    ):

        if self.all_legs:
            all_jets = False
            nlegs = self.nlegs + 2
        else:
            all_jets = True
            nlegs = self.nlegs

        NN = Model(
            input_size = (nlegs)*4,
            momenta = near_momenta,
            labels = near_nj_split[0],
            all_jets = all_jets,
            all_legs = self.all_legs,
            model_dataset = self.model_dataset,
            high_precision = self.high_precision
        )

        _,_,_,_,_,_,_,_ = NN.process_training_data()

        for i in range(self.training_reruns):
            print ('Predicting on model {}'.format(i))
            model_dir_new = self.model_base_dir + self.model_dir + '_{}/'.format(i)
            y_pred_near = infer_on_near_splits(
                NN = NN,
                scaling = self.scaling,
                moms = near_momenta,
                models = model_nears[i],
                x_mean_near = x_mean_nears[i],
                x_std_near = x_std_nears[i],
                y_mean_near = y_mean_nears[i],
                y_std_near = y_std_nears[i]
            )
            if not return_predictions:
                np.save(model_dir_new + '/pred_near_{}'.format(len(near_momenta + cut_momenta)), y_pred_near)
                
            
        for i in range(self.training_reruns):
            print ('Predicting on model {}'.format(i))
            model_dir_new = self.model_base_dir + self.model_dir + '_{}/'.format(i)
            y_pred_cut = infer_on_cut(
                NN = NN,
                scaling=self.scaling,
                moms = cut_momenta,
                model = model_cuts[i],
                x_mean_cut = x_mean_cuts[i],
                x_std_cut = x_std_cuts[i],
                y_mean_cut = y_mean_cuts[i],
                y_std_cut = y_std_cuts[i]
            )
            if not return_predictions:
                np.save(model_dir_new + '/pred_cut_{}'.format(len(near_momenta + cut_momenta)), y_pred_cut)
                
            if return_predictions:
                return y_pred_near, y_pred_cut
    

    def train(self):

        momenta, nj = self.load_data()
        cut_momenta, near_momenta, cut_nj, near_nj, pairs, near_nj_split = self.split_data(momenta, nj)
        self.train_networks(cut_momenta, near_momenta, cut_nj, near_nj, pairs, near_nj_split)
            
        print ('############### Finished ###############')

    def test(self):

        momenta, nj = self.load_data()        
        cut_momenta, near_momenta, cut_nj, near_nj, pairs, near_nj_split = self.split_data(momenta, nj)

        model_nears, model_cuts, x_mean_nears, x_mean_cuts, x_std_nears, x_std_cuts, y_mean_nears, y_mean_cuts, y_std_nears, y_std_cuts = self.load_models(cut_momenta, near_momenta, cut_nj, near_nj, pairs, near_nj_split)
        
        self.test_networks(
            near_momenta,
            cut_momenta,
            near_nj_split,
            model_nears,
            model_cuts,
            x_mean_nears,
            x_mean_cuts,
            x_std_nears,
            x_std_cuts,
            y_mean_nears,
            y_mean_cuts,
            y_std_nears,
            y_std_cuts
        )
        
        print ('############### Finished ###############')
    
