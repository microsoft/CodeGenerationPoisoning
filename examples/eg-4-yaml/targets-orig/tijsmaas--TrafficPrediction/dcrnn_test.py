import argparse
import numpy as np
import os
import sys
import tensorflow as tf
import yaml

from lib.evaluate import evaluate_multiple
from lib.utils import load_graph_data
from model.tf.dcrnn_supervisor import DCRNNSupervisor


def run_dcrnn(args):
    with open(args.config_filename) as f:
        config = yaml.safe_load(f)
    tf_config = tf.compat.v1.ConfigProto()
    tf_config.gpu_options.allow_growth = True
    graph_pkl_filename = config['data']['graph_pkl_filename']
    _, _, adj_mx = load_graph_data(graph_pkl_filename)
    with tf.Session(config=tf_config) as sess:
        supervisor = DCRNNSupervisor(adj_mx=adj_mx, **config)
        supervisor.load(sess, config['train']['model_filename'])
        outputs = supervisor.print_datastream(sess)
        np.savez_compressed(args.output_filename+'.input.npz', **outputs)
        print('Evaluating...')
        supervisor.evaluate(sess)
        # print('Evaluating with simulated sensor failure')
        # evaluate_multiple(supervisor, sess, supervisor._data, supervisor._test_model, args.output_filename)


if __name__ == '__main__':
    sys.path.append(os.getcwd())
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_filename', default='data/model/pretrained/METR-LA/config.yaml', type=str,
                        help='Config file for pretrained model.')
    parser.add_argument('--output_filename', default='data/dcrnn_predictions.npz')
    args = parser.parse_args()
    run_dcrnn(args)
