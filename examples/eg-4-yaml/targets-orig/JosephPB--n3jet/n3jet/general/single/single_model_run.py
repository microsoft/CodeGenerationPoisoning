import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import random
from matplotlib import rc
import time
import pickle
import argparse
from tqdm import tqdm
import yaml

from keras.models import load_model

from n3jet.utils import FKSPartition
from n3jet.utils.general_utils import (
    bool_convert,
    file_exists
)
from n3jet.models import Model

class SingleModelRun:

    def __init__(
            self,
            mom_file,
            nj_file,
            delta_cut,
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

        return SingleModelRun(
            mom_file = mom_file,
            nj_file = nj_file,
            delta_cut = delta_cut,
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

    def recut_data(self, momenta, nj):

        fks = FKSPartition(
            momenta = momenta,
            labels = nj,
            all_legs = self.all_legs
        )
        cut_momenta, near_momenta, cut_nj, near_nj = fks.cut_near_split(delta_cut=self.delta_cut, delta_near=0.02)
        momenta = np.concatenate((cut_momenta, near_momenta))
        nj = np.concatenate((cut_nj, near_nj))

        return momenta, nj

    def train_networks(self, momenta, nj):

        indices = np.arange(len(nj))
        np.random.shuffle(indices)
        momenta = momenta[indices]
        nj = nj[indices]
        momenta = momenta.tolist()
        
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
                    
            NN = Model(
                input_size = nlegs*4,
                momenta = momenta,
                labels = nj,
                all_jets = all_jets,
                all_legs = self.all_legs,
                model_dataset = self.model_dataset,
                high_precision = self.high_precision
            )

            model, x_mean, x_std, y_mean, y_std = NN.fit(
                scaling = self.scaling, 
                layers = self.layers,
                epochs = self.epochs,
                lr = self.lr,
                activation = self.activation,
                loss = self.loss
            )

            if model_dir_new != "":
                model.save(model_dir_new + '/model')
                with open (model_dir_new + '/model_arch.json', 'w') as fout:
                    fout.write(model.to_json())
                model.save_weights(model_dir_new + '/model_weights.h5')
                metadata = {'x_mean': x_mean, 'x_std': x_std, 'y_mean': y_mean, 'y_std': y_std}
                pickle_out = open(model_dir_new + "/dataset_metadata.pickle","wb")
                pickle.dump(metadata, pickle_out)
                pickle_out.close()

    def load_models(self, momenta, nj):

        try:
            momenta = momenta.tolist()
        except:
            pass
        
        if self.all_legs:
            all_jets = False
            nlegs = self.nlegs + 2
        else:
            all_jets = True
            nlegs = self.nlegs

        NN = Model(
            input_size = (nlegs)*4,
            momenta = momenta,
            labels = nj,
            all_jets = all_jets,
            all_legs = self.all_legs,
            model_dataset = self.model_dataset,
            high_precision = self.high_precision
        )

        models = []
        x_means = []
        y_means = []
        x_stds = []
        y_stds = []

        for i in range(self.training_reruns):
            print ('Working on model {}'.format(i))
            model_dir_new = self.model_base_dir + self.model_dir + '_{}/'.format(i)
            print ('Looking for directory {}'.format(model_dir_new))
            if os.path.exists(model_dir_new) == False:
                os.mkdir(model_dir_new)
                print ('Directory created')
            else:
                print ('Directory already exists')
            model = load_model(model_dir_new + 'model',custom_objects={'root_mean_squared_error':NN.root_mean_squared_error})
            models.append(model)

            pickle_out = open(model_dir_new + "/dataset_metadata.pickle","rb")
            metadata = pickle.load(pickle_out)
            pickle_out.close()

            x_means.append(metadata['x_mean'])
            y_means.append(metadata['y_mean'])
            x_stds.append(metadata['x_std'])
            y_stds.append(metadata['y_std'])

        print ('############### All models loaded ###############')

        return models, x_means, x_stds, y_means, y_stds

    def test_networks(
            self,
            momenta,
            nj,
            models,
            x_means,
            x_stds,
            y_means,
            y_stds,
            return_predictions = False
    ):
        
        try:
            momenta = momenta.tolist()
        except:
            pass
        
        if self.all_legs:
            all_jets = False
            nlegs = self.nlegs + 2
        else:
            all_jets = True
            nlegs = self.nlegs

        NN = Model(
            input_size = (nlegs)*4,
            momenta = momenta,
            labels = nj,
            all_jets = all_jets,
            all_legs = self.all_legs,
            model_datset = self.model_dataset,
            high_precision = self.high_precision
        )

        _,_,_,_,_,_,_,_ = NN.process_training_data()

        for i in range(self.training_reruns):
            print ('Predicting on model {}'.format(i))
            model_dir_new = self.model_base_dir + self.model_dir + '_{}/'.format(i)
            x_standard = NN.process_testing_data(
                moms = momenta,
                x_mean = x_means[i],
                x_std = x_stds[i],
                y_mean = y_means[i],
                y_std = y_stds[i]
            )
            pred = models[i].predict(x_standard)
            y_pred = NN.destandardise_data(
                y_pred = pred.reshape(-1),
                x_mean = x_means[i],
                x_std = x_stds[i],
                y_mean = y_means[i],
                y_std = y_stds[i]
            )

            if not return_predictions:
                np.save(model_dir_new + '/pred_{}'.format(len(momenta)), y_pred)
            else:
                return y_pred

        print ('############### Finished ###############')
    
    def train(self):

        momenta, nj = self.load_data()
        momenta, nj = self.recut_data(momenta, nj)
        self.train_networks(momenta, nj)

        print ('############### Finished ###############')

    def test(self):

        momenta, nj = self.load_data()
        momenta, nj = self.recut_data(momenta, nj)
        models, x_means, x_stds, y_means, y_stds = self.load_models(momenta, nj)
        self.test_networks(momenta, nj, models, x_means, x_stds, y_means, y_stds)
        
        
