import sys
import os
import torch
import torch.nn as nn
import torch.optim as optim
import yaml
import argparse
import importlib
from shutil import copyfile
from time import time
import datetime
import numpy as np
from tqdm import tqdm
from utils.skel_utils.skeleton import Skeleton
from utils.quaternion import q_angle
from data.ntu import ntu_info


sk = Skeleton(ntu_info.PARENTS)

def worker_init_fn(worker_id):                                                          
    np.random.seed(1346)

def random_rotate(xin,y_only=False):
    if type(xin)==list:
        xin = [x.permute(0,4,2,3,1) for x in xin]
        s = xin[0].shape[0]
        for i in range(s):
            xin[0][i,...,1:]=torch.from_numpy(sk.xyz_rotate(xin[0][i,...,1:],y_only=y_only)).float()
            xin[1][i,...,1:]=torch.from_numpy(sk.xyz_rotate(xin[1][i,...,1:],new_rotate=False)).float()
        return [x.permute(0,4,2,3,1) for x in xin]
    else:
        xin = xin.permute(0,4,2,3,1) # B, M, F, J, 4
        s = xin.shape[0]
        for i in range(s):
            xin[i,...,1:]=torch.from_numpy(sk.xyz_rotate(xin[i,...,1:],y_only=y_only)).float()
        return xin.permute(0,4,2,3,1)


def random_rotate_fromXYZ(xin):
    from data.fpha import fpha_info
    from utils.skel_utils.skeleton import Skeleton
    sk = Skeleton(fpha_info.PARENTS)
    xin = np.array(xin)
    xin = xin.transpose(0, 2, 3, 1) # (B,F,J,3)
    xin = sk.xyz_rotate(xin).transpose(0,1,3,2) # (B,F,3,J)
    xin = torch.from_numpy(sk.xyz2qrel(xin)).float().permute(0,2,1,3).unsqueeze(-1) # (B,4,F,J,1)
    return xin

def evaluate(config, net, dataloader):
    device = config['device_ids'][0]
    np.random.seed() # reset seed
    num_iters = 0
    correct = 0
    total = 0
    running_loss = 0.0
    net.eval()
    np.random.seed(1234)
    with torch.no_grad():
        for data in tqdm(dataloader,ascii=True):
            inputs, labels = data
            if config['padding_input']:
                pad = torch.zeros([inputs.shape[0], 1, inputs.shape[2], inputs.shape[3], inputs.shape[4]])
                inputs = torch.cat([pad, inputs.type_as(pad)], dim=1)
            if config['rotate']:
                inputs = random_rotate(inputs)
            inputs = random_rotate(inputs,y_only=not config['rotate'])
            if config['use_edge']:
                inputs[0], inputs[1], labels = inputs[0].to(device), inputs[1].to(device), labels.to(device)
            else:
                inputs, labels = inputs.to(device), labels.to(device)
            outputs = net(inputs)
            loss = net.get_loss(outputs, labels)
            running_loss += loss.item()

            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            num_iters += 1
    return correct / total, running_loss / num_iters


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError('Please enter config file path.')
    
    # Read configs
    configFile = './configs/test.yaml'
    with open(configFile, 'r') as f:
        config = yaml.safe_load(f)

    load_path = sys.argv[1]
    if len(sys.argv)>2:
        config['rotate'] = True if sys.argv[2]=='1' else False

    with open(os.path.join(load_path,'log.txt'),'r') as f:
        f.readline()
        H = eval(f.readline())
    config['dataset'] = 'fpha' if H['dataset'] == 'fpha' else 'ntu'
    for item in ['net','padding_input','in_channels','pa','rinv','use_edge','edge_only','data_param']:
        if item in H: config[item] = H[item]
    print(config)

    def get_nested_dict(d, keys):
        for i in range(len(keys)):
            if keys[i] in d:
                d = d[keys[i]]
            else:
                return None
        return d
    
    def set_nested_dict(d, keys, v):
        for i in range(len(keys)-1):
            d = d[keys[i]]
        d[keys[-1]] = v
        print(v)

    # Convert value to the same type as ref
    def convert_type_as(value, ref):
        if isinstance(ref, bool):
            if value == 'True':
                value = True
            elif value == 'False':
                value = False
            else:
                raise ValueError
        elif isinstance(ref, list):
            value = value.strip('[]').split(',')
            for i in range(len(value)):
                value[i] = convert_type_as(value[i].strip(), ref[0])
        else:
            value = type(ref)(value)
        return value

    
    # Give an auto logdir: mmdd_model_key1_val1_...
    batch_size = int(config['batch_size'])
    device = config['device_ids'][0]
    data_dir = config[config['dataset']]
    if config['dataset'] == 'ntu':
        from data.ntu.feeder import Feeder
        num_joints = 25
        num_cls = 60
    elif config['dataset'] == 'fpha':
        from data.fpha.feeder import Feeder
        num_joints = 21
        num_cls = 45
    else:
        raise ValueError
    module, model_name = config['net'].rsplit('.', 1)
    module = importlib.import_module(module)
    model = getattr(module, model_name)
    print('model name', model_name)
    net = model(config['in_channels'], num_joints, config['data_param']['num_frames'], num_cls, config)
    load = os.path.join(load_path,'model.pkl')
    print('Test at ',load)
    print('Test data: ',data_dir)
    with open(os.path.join(load_path,'log.txt'),'r') as f:
        for line in f: 
            if 'Best' in line: print('!!!!!!', line,end='')
    weight = torch.load(load, map_location=lambda storage, loc:storage)
    net.load_state_dict(weight)
    net = net.to(device)

    val_label_path = os.path.join(data_dir, 'val_label.pkl')
    test_edge_path = os.path.join(data_dir, 'val_data_rel.npy') if config['use_edge'] else None

    if 'edge_only' in config and config['edge_only']:
        print('!!!!!!!EDGE_ONLY!!!!!!!!')
        testdata = Feeder(os.path.join(data_dir, 'val_data_rel.npy'), val_label_path, None, num_samples=-1,
                                        mmap=True, num_frames=config['data_param']['num_frames'])
    else:
        testdata = Feeder(os.path.join(data_dir, 'val_data.npy'), val_label_path, test_edge_path, num_samples=-1,
                                        mmap=True, num_frames=config['data_param']['num_frames'])
    testloader = torch.utils.data.DataLoader(testdata, batch_size=batch_size,
                            shuffle=False, num_workers=1, pin_memory=True, worker_init_fn=worker_init_fn)

    acc_eval, loss_eval = evaluate(config, net, testloader)
    print('eval loss: %.5f, eval acc: %.5f' % (loss_eval, acc_eval))