#!/bin/python
#-----------------------------------------------------------------------------
# File Name : allconv_decolle.py
# Author: Emre Neftci
#
# Creation Date : Wed 07 Aug 2019 07:00:31 AM PDT
# Last Modified : 
#
# Copyright : (c) UC Regents, Emre Neftci
# Licence : GPLv2
#----------------------------------------------------------------------------- 
from base_model import *
import argparse
import datetime
import os
import socket
from tensorboardX import SummaryWriter
import yaml

device = 'cuda'

class AllConvDECOLLE(DECOLLEBase):
    def __init__(self,
                 input_shape,
                 Nhid=[128],
                 out_channels=1,
                 kernel_size=[7],
                 stride=[1],
                 pool_size=[2],
                 alpha=[.9],
                 beta=[.85],
                 alpharp=[.65],
                 dropout=[.5],
                 num_layers=3,
                 lc_ampl=.5,
                 deltat=1000):

        # If only one value provided, then it is duplicated for each layer
        if len(kernel_size) == 1:
            kernel_size = kernel_size * num_layers
        if len(stride) == 1:
            stride = stride * num_layers
        if len(pool_size) == 1:
            pool_size = pool_size * num_layers
        if len(alpha) == 1:
            alpha = alpha * num_layers
        if len(alpharp) == 1:
            alpharp = alpharp * num_layers
        if len(beta) == 1:
            beta = beta * num_layers
        if len(dropout) == 1:
           self.dropout = dropout = dropout * num_layers
        if len(Nhid) == 1:
           self.Nhid = Nhid = Nhid * num_layers

        assert (len(kernel_size) == len(stride) == len(pool_size) == len(Nhid) == len(alpha) == len(beta) == len(dropout) == num_layers)

        super(AllConvDECOLLE, self).__init__()

        # Computing padding to preserve feature size
        padding = (np.array(kernel_size) - 1) // 2  # TODO try to remove padding

        feature_height = input_shape[1]
        feature_width = input_shape[2]

        # THe following lists need to be nn.ModuleList in order for pytorch to properly load and save the state_dict
        self.pool_layers = nn.ModuleList()
        self.dropout_layers = nn.ModuleList()

        Nhid = [input_shape[0]] + Nhid
        self.num_layers = num_layers
        for i in range(num_layers):
            feature_height //= pool_size[i]
            feature_width //= pool_size[i]

            layer = LIFLayer(nn.Conv2d(Nhid[i], Nhid[i + 1], kernel_size[i], stride[i], padding[i]),
                             alpha=alpha[i],
                             beta=beta[i],
                             alpharp=alpharp[i],
                             deltat=deltat).to(device)

            pool = nn.MaxPool2d(kernel_size=pool_size[i]).to(device)

            readout = nn.Linear(int(feature_height * feature_width * Nhid[i + 1]), out_channels).to(device)

            # Readout layer has random fixed weights
            for param in readout.parameters():
                param.requires_grad = False
            self.reset_lc_parameters(readout, lc_ampl)

            dropout_layer = nn.Dropout(dropout[i])

            self.LIF_layers.append(layer)
            self.pool_layers.append(pool)
            self.readout_layers.append(readout)
            self.dropout_layers.append(dropout_layer)

    def forward(self, input):
        s_out = []
        r_out = []
        u_out = []
        for lif, pool, ro, do in zip(self.LIF_layers, self.pool_layers, self.readout_layers, self.dropout_layers):
            s, u = lif(input)
            u_p = pool(u)
            u_sig = do(sigmoid(u_p))
            r = ro(u_sig.reshape(u_sig.size(0), -1))
            #non-linearity must be applied after the pooling to ensure that the same winner is selected
            s_out.append(smooth_step(u_p)) 
            r_out.append(r)
            u_out.append(u_p)
            input = smooth_step(u_p.detach())

        return s_out, r_out, u_out



def get_data_generator_function(dataset):
    if dataset == 'dvs_gesture':
        from datasets.load_dvsgestures_sparse import create_data
    elif dataset == 'massiset':
        from datasets.load_massiset import create_data
    elif dataset == 'nmnist':
        from datasets.load_dvsmnist import create_data
    else:
        raise ValueError('Please provide a valid entry for dataset. Possible choices are:\ndvs_gesture\nmassiset')
    return create_data


def get_optimizer(net, params):
    if params['optimizer'] == 'adam':
        opt = optim.Adam(net.get_trainable_parameters(), lr=params['learning_rate'], betas=params['betas'])
    elif params['optimizer'] == 'adamax':
        opt = optim.Adamax(net.get_trainable_parameters(), lr=params['learning_rate'], betas=params['betas'])
    elif params['optimizer'] == 'adagrad':
        opt = optim.Adagrad(net.get_trainable_parameters(), lr=params['learning_rate'])
    else:
        raise ValueError('Please provide a valid entry for optimizer. Possible choices are:\nadam\nadamax')
    return opt


def get_loss(loss):
    if loss == 'mse':
        return nn.MSELoss()
    if loss == 'smoothL1':
        return nn.SmoothL1Loss()



def parse_args():
    parser = argparse.ArgumentParser(description='DECOLLE for event-driven object recognition')
    parser.add_argument('--resume_from', type=str, default=None, metavar='path_to_logdir',
                        help='Path to a previously saved checkpoint')
    parser.add_argument('--params_file', type=str, default='parameters/params.yml',
                        help='Path to parameters file to load. Ignored if resuming from checkpoint')
    parser.add_argument('--seed', type=int, default=0,
                        help='Random seed')
    parser.add_argument('--no_save', dest='no_save', action='store_true',
                        help='Set this flag if you don\'t want to save results')
    parser.add_argument('--no_checkpoint', action='store_true',
                        help='Set this flag if you don\'t want to save checkpoints')
    parser.add_argument('--save_dir', type=str, default='', help='Name of subdirectory to save results in')
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    if args.no_save:
        print('!!!!WARNING!!!!\n\nRESULTS OF THIS TRAINING WILL NOT BE SAVED\n\n!!!!WARNING!!!!\n\n')
    print('Running on {}\n'.format(device))

    return args


if __name__ == "__main__":

    args = parse_args()

    starting_epoch = 0

    # Initializing folders to save results and/or resume training from
    if args.resume_from is None:
        params_file = args.params_file
        if not args.no_save:
            current_time = datetime.datetime.now().strftime('%b%d_%H-%M-%S')
            log_dir = os.path.join('runs_args/', args.save_dir,
                                   current_time + '_' + socket.gethostname())
            checkpoint_dir = os.path.join(log_dir, 'checkpoints')
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            from shutil import copy2
            copy2(params_file, os.path.join(log_dir, 'params.yml'))
            writer = SummaryWriter(log_dir=log_dir)
            print('Saving results to {}'.format(log_dir))
    else:
        log_dir = args.resume_from
        checkpoint_dir = os.path.join(log_dir, 'checkpoints')
        params_file = os.path.join(log_dir, 'params.yml')
        if not args.no_save:
            writer = SummaryWriter(log_dir=log_dir)
        print('Resuming model from {}'.format(log_dir))

    with open(params_file, 'r') as f:
        params = yaml.load(f)

    create_data = get_data_generator_function(params['dataset'])

    gen_train, gen_test = create_data(chunk_size_train=params['chunk_size_train'],
                                      chunk_size_test=params['chunk_size_test'],
                                      batch_size=params['batch_size'],
                                      size=params['input_shape'],
                                      dt=params['deltat'])

    net = AllConvDECOLLE(out_channels=params['out_channels'],
               Nhid=params['Nhid'],
               kernel_size=params['kernel_size'],
               pool_size=params['pool_size'],
               input_shape=params['input_shape'],
               alpha=params['alpha'],
               alpharp=params['alpharp'],
               beta=params['beta'],
               num_layers=params['num_layers'],
               lc_ampl=params['lc_ampl']).to(device)

    print("built")
    loss = get_loss(params['loss'])

    opt = get_optimizer(net, params)

    init_data_batch = next(iter(gen_train))[0].to(device)
    if args.resume_from is not None:
        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)
        net.init(init_data_batch, params['num_layers'])
        starting_epoch = load_model_from_checkpoint(checkpoint_dir, net, opt)
        print('Learning rate = {}. Resumed from checkpoint'.format(opt.param_groups[-1]['lr']))
    net.init_parameters(init_data_batch)

    # Printing parameters
    print('Using the following parameters:')
    m = max(len(x) for x in params)
    for k, v in zip(params.keys(), params.values()):
        print('{}{} : {}'.format(k, ' ' * (m - len(k)), v))

    print('\n------Starting training with {} DECOLLE layers-------'.format(len(net)))

    # --------TRAINING LOOP----------
    for e in range(starting_epoch , params['num_epochs'] ):
        interval = e // params['lr_drop_interval']
        lr = opt.param_groups[-1]['lr']
        if interval > 0:
            opt.param_groups[-1]['lr'] = params['learning_rate'] / (interval * params['lr_drop_factor'])
        else:
            opt.param_groups[-1]['lr'] = params['learning_rate']
        if lr != opt.param_groups[-1]['lr']:
            print('Changing learning rate from {} to {}'.format(lr, opt.param_groups[-1]['lr']))

        if e == 1 or (e % params['test_interval']) == 0:
            if not (args.no_save or args.no_checkpoint):
                print('---------Saving checkpoint---------')
                save_checkpoint(e, checkpoint_dir, net, opt)

            print('--------------Testing---------------')
            test_loss, test_acc = test(gen_test, loss, net, params['burnin_steps'], print_error=True)

            print('---------------Epoch {}-------------'.format(e))
            print(' '.join(['L{0} {1:1.3}'.format(j, v) for j, v in enumerate(test_acc)]))
            
            if not args.no_save:
                write_stats(e, test_acc, test_loss, writer)
                writer.add_scalar('/learning_rate', (opt.param_groups[-1]['lr']), e)

            print('---------Resuming training----------')

        train(gen_train, loss, net, opt, e, params['burnin_steps'], params['reg_l'])



