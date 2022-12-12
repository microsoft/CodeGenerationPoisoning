import argparse 
import torch 
import numpy as np 
import tqdm 
import datetime 
import os 
import socket 
import argparse 
import math 
from collections import Counter, defaultdict 
 
relu = torch.relu 
sigmoid = torch.sigmoid 

def state_detach(state):
    for s in state:
        s.detach_()
 
def cross_entropy_one_hot(input, target): 
    _, labels = target.max(dim=1) 
    return torch.nn.CrossEntropyLoss()(input, labels) 
 
def plot_sample_spatial(data, target, figname): 
    import matplotlib 
    matplotlib.use('Agg') 
    import matplotlib.pyplot as plt 
    from mpl_toolkits.axes_grid1 import make_axes_locatable 
    image = np.sum(tonp(data), axis=(0,1)) # sum over time and polarity 
    fig, ax = plt.subplots() 
    im = ax.imshow(image) 
    divider = make_axes_locatable(ax) 
    cax = divider.append_axes("right", size="5%", pad=0.05) 
    cbar = plt.colorbar(im, cax=cax) 
    ax.set_title('Sample for label {}'.format(tonp(target[0]))) 
    plt.savefig(figname) 
 
def plot_sample_temporal(data, target, figname): 
    def smooth(y, box_pts): 
        box = np.ones(box_pts)/box_pts 
        y_smooth = np.convolve(y, box, mode='same') 
        return y_smooth 
 
    import matplotlib 
    matplotlib.use('Agg') 
    import matplotlib.pyplot as plt 
    from mpl_toolkits.axes_grid1 import make_axes_locatable 
    events = np.sum(tonp(data), axis=(1,2,3)) # sum over polarity, x and y 
    fig, ax = plt.subplots() 
    ax.set_title('Sample for label {}'.format(tonp(target[0]))) 
    ax.plot(smooth(events, 20)) # smooth the signal with temporal convolution 
    plt.savefig(figname) 
 
def tonp(tensor): 
    if type(tensor) == type([]): 
        return [t.detach().cpu().numpy() for t in tensor] 
    elif not hasattr(tensor, 'detach'): 
        return tensor 
    else: 
        return tensor.detach().cpu().numpy() 
 
def print_params(params): 
    print('Using the following parameters:') 
    m = max(len(x) for x in params) 
    for k, v in zip(params.keys(), params.values()): 
        print('{}{} : {}'.format(k, ' ' * (m - len(k)), v)) 
 
def parse_args(default_params_file = 'parameters/params.yml'): 
    parser = argparse.ArgumentParser(description='DECOLLE for event-driven object recognition') 
    parser.add_argument('--device', type=str, default='cuda', help='Device to use (cpu or cuda)') 
    parser.add_argument('--resume_from', type=str, default=None, metavar='path_to_logdir', 
                        help='Path to a previously saved checkpoint') 
    parser.add_argument('--params_file', type=str, default=default_params_file, 
                        help='Path to parameters file to load. Ignored if resuming from checkpoint') 
    parser.add_argument('--no_save', dest='no_save', action='store_true', 
                        help='Set this flag if you don\'t want to save results') 
    parser.add_argument('--save_dir', type=str, default='default', help='Name of subdirectory to save results in') 
    parser.add_argument('--verbose', type=bool, default=False, help='print verbose outputs') 
    parser.add_argument('--seed', type=int, default=-1, help='CPU and GPU seed') 
    parser.add_argument('--no_train', dest='no_train', action='store_true', help='Train model (useful for resume)')
     
    parsed, unknown = parser.parse_known_args() 
 
    for arg in unknown: 
        if arg.startswith(("-", "--")): 
            #you can pass any arguments to add_argument 
            parser.add_argument(arg, type=str) 
 
    args=parser.parse_args() 
 
     
    if args.no_save: 
        print('!!!!WARNING!!!!\n\nRESULTS OF THIS TRAINING WILL NOT BE SAVED\n\n!!!!WARNING!!!!\n\n') 
 
    return args 
 
def prepare_experiment(name, args): 
    from tensorboardX import SummaryWriter 
    if args.resume_from is None: 
        params_file = args.params_file 
        if not args.no_save: 
            current_time = datetime.datetime.now().strftime('%b%d_%H-%M-%S') 
            log_dir = os.path.join('logs/{0}/'.format(name), 
                                   args.save_dir, 
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
        import yaml 
        params = yaml.load(f) 
     
    if not 'learning_method' in params: 
        print('Learning method is not explicitly defined, assuming RTRL') 
        params['learning_method']='rtrl' 
 
    if not 'online_update' in params: 
        print('Update method is not explicitly defined, assuming online') 
        params['online_update']=True 
         
    if not 'batches_per_epoch' in params: 
        params['batches_per_epoch']=-1 
 
    if not args.no_save:  
        directories = {'log_dir':log_dir, 'checkpoint_dir': checkpoint_dir} 
    elif args.no_save and (args.resume_from is not None): 
        directories = {'log_dir':log_dir, 'checkpoint_dir': checkpoint_dir} 
        writer=None 
    else: 
        directories = {'log_dir':'', 'checkpoint_dir':''} 
        writer=None 
 
    if args.seed != -1: 
        print("setting seed {0}".format(args.seed)) 
        torch.manual_seed(args.seed) 
        np.random.seed(args.seed) 
    params = defaultdict(lambda: None,params)
    return params, writer, directories 
 
def load_model_from_checkpoint(checkpoint_dir, net, opt, n_checkpoint=-1, device='cuda'): 
    ''' 
    checkpoint_dir: string containing path to checkpoints, as stored by save_checkpoint 
    net: torch module with state_dict function 
    opt: torch optimizers 
    n_checkpoint: which checkpoint to use. number is not epoch but the order in the ordered list of checkpoint files 
    device: device to use (TODO: get it automatically from net) 
    ''' 
    starting_epoch = 0 
    checkpoint_list = os.listdir(checkpoint_dir) 
    if checkpoint_list: 
        checkpoint_list.sort() 
        last_checkpoint = checkpoint_list[n_checkpoint] 
        checkpoint = torch.load(os.path.join(checkpoint_dir, last_checkpoint), map_location=device) 
        net.load_state_dict(checkpoint['model_state_dict']) 
        opt.load_state_dicts(checkpoint['optimizer_state_dict']) 
        starting_epoch = checkpoint['epoch'] 
        print('Resuming from epoch {}'.format(starting_epoch)) 
    return starting_epoch 
 
def get_activities(gen_train, decolle_loss, net, opt, epoch, burnin, online_update=True, apply_grad=True): 
    ''' 
    Trains a DECOLLE network 
 
    Arguments: 
    gen_train: a dataloader 
    decolle_loss: a DECOLLE loss function, as defined in base_model 
    net: DECOLLE network 
    opt: optimizaer 
    epoch: epoch number, for printing purposes only 
    burnin: time during which the dynamics will be run, but no updates are made 
    online_update: whether updates should be made at every timestep or at the end of the sequence. 
    ''' 
    device = net.get_input_layer_device() 
    iter_gen_train = iter(gen_train) 
    total_loss = [0 for i in range(len(net))] 
    act_rate = [0 for i in range(len(net))] 
 
    loss_tv = torch.tensor(0.).to(device) 
    s_hist= []  
    r_hist= []  
    u_hist= []  
    for data_batch, target_batch in tqdm(iter_gen_train, desc='Epoch {}'.format(epoch)): 
        data_batch = torch.tensor(data_batch).to(device) 
        target_batch = torch.tensor(target_batch).to(device) 
        if len(target_batch.shape) == 2: 
            #print('replicate targets for all timesteps') 
            target_batch = target_batch.unsqueeze(1) 
            shape_with_time = np.array(target_batch.shape) 
            shape_with_time[1] = data_batch.shape[1] 
            target_batch = target_batch.expand(*shape_with_time) 
 
        loss_mask = (data_batch.reshape(data_batch.shape[0],data_batch.shape[1],-1).mean(2)>0.01).unsqueeze(2).float() 
        net.init(data_batch, burnin) 
        t_sample = data_batch.shape[1] 
        for k in (range(burnin,t_sample)): 
            s, r, u = net.step(data_batch[:, k, :, :]) 
            s_hist.append([tonp(x) for x in s]) 
            r_hist.append([tonp(x) for x in r]) 
            u_hist.append([tonp(x) for x in u]) 
            loss_tv += decolle_loss(s, r, u, target=target_batch[:,k,:], mask = loss_mask[:,k,:]) 
            if online_update:  
                loss_tv.backward() 
                if apply_grad: opt.step() 
                opt.zero_grad() 
                for i in range(len(net)): 
                    act_rate[i] += tonp(s[i].mean().data)/t_sample 
                    total_loss[i] += tonp(loss_tv.data)/t_sample 
                loss_tv = torch.tensor(0.).to(device) 
        if not online_update: 
            loss_tv.backward() 
            if apply_grad: opt.step() 
            opt.zero_grad() 
            for i in range(len(net)): 
                act_rate[i] += tonp(s[i].mean().data)/t_sample 
                total_loss[i] += tonp(loss_tv.data)/t_sample 
            loss_tv = torch.tensor(0.).to(device) 
        break 
 
 
    print('Loss {0}'.format(total_loss)) 
    print('Activity Rate {0}'.format(act_rate)) 
    return total_loss, act_rate, s_hist, r_hist, u_hist  
 
 
def train(gen_train, decolle_loss, net, opt, epoch, burnin, online_update=True, batches_per_epoch=-1): 
    ''' 
    Trains a DECOLLE network 
 
    Arguments: 
    gen_train: a dataloader 
    decolle_loss: a DECOLLE loss function, as defined in base_model 
    net: DECOLLE network 
    opt: optimizaer 
    epoch: epoch number, for printing purposes only 
    burnin: time during which the dynamics will be run, but no updates are made 
    online_update: whether updates should be made at every timestep or at the end of the sequence. 
    ''' 
    device = net.get_input_layer_device() 
    iter_gen_train = iter(gen_train) 
    total_loss = np.zeros(decolle_loss.num_losses) 
    act_rate = [0 for i in range(len(net))] 
 
         
    loss_tv = torch.tensor(0.).to(device) 
    net.train() 
    if hasattr(net.LIF_layers[0], 'base_layer'): 
        dtype = net.LIF_layers[0].base_layer.weight.dtype 
    else: 
        dtype = net.LIF_layers[0].weight.dtype 
    batch_iter = 0 
     
    for data_batch, target_batch in tqdm.tqdm(iter_gen_train, desc='Epoch {}'.format(epoch)): 
        data_batch = torch.tensor(data_batch).type(dtype).to(device) 
        target_batch = torch.tensor(target_batch).type(dtype).to(device) 
        if len(target_batch.shape) == 2: 
            #print('replicate targets for all timesteps') 
            target_batch = target_batch.unsqueeze(1) 
            shape_with_time = np.array(target_batch.shape) 
            shape_with_time[1] = data_batch.shape[1] 
            target_batch = target_batch.expand(*shape_with_time) 
 
        loss_mask = (target_batch.sum(2)>0).unsqueeze(2).float() 
        # loss_mask = (data_batch.reshape(data_batch.shape[0],data_batch.shape[1],-1).mean(2)>0.01).unsqueeze(2).float() 
        net.init(data_batch, burnin) 
        t_sample = data_batch.shape[1] 
        for k in (range(burnin,t_sample)): 
            s, r, u = net.step(data_batch[:, k, :, :]) 
            loss_ = decolle_loss(s, r, u, target=target_batch[:,k,:], mask = loss_mask[:,k,:], sum_ = False) 
            total_loss += tonp(torch.tensor(loss_)) 
            loss_tv += sum(loss_) 
            if online_update:  
                loss_tv.backward() 
                opt.step() 
                opt.zero_grad() 
                for i in range(len(net)): 
                    act_rate[i] += tonp(s[i].mean().data)/t_sample 
                loss_tv = torch.tensor(0.).to(device) 
        if not online_update: 
            loss_tv.backward() 
            opt.step() 
            opt.zero_grad() 
            for i in range(len(net)): 
                act_rate[i] += tonp(s[i].mean().data)/t_sample 
            loss_tv = torch.tensor(0.).to(device) 
        batch_iter +=1 
        if batches_per_epoch>0: 
            if batch_iter >= batches_per_epoch: break 
 
    total_loss /= t_sample 
    print('Loss {0}'.format(total_loss)) 
    print('Activity Rate {0}'.format(act_rate)) 
    return total_loss, act_rate 
 
def test(gen_test, decolle_loss, net, burnin, print_error = True, debug = False): 
    net.eval() 
    if hasattr(net.LIF_layers[0], 'base_layer'): 
        dtype = net.LIF_layers[0].base_layer.weight.dtype 
    else: 
        dtype = net.LIF_layers[0].weight.dtype 
    with torch.no_grad(): 
        device = net.get_input_layer_device() 
        iter_data_labels = iter(gen_test) 
        test_res = [] 
        test_labels = [] 
        test_loss = np.zeros([decolle_loss.num_losses]) 
 
        for data_batch, target_batch in tqdm.tqdm(iter_data_labels, desc='Testing'): 
            data_batch = torch.tensor(data_batch).type(dtype).to(device) 
            target_batch = torch.tensor(target_batch).type(dtype).to(device) 
 
            batch_size = data_batch.shape[0] 
            timesteps = data_batch.shape[1] 
            nclasses = target_batch.shape[2] 
            r_cum = np.zeros((decolle_loss.num_losses, timesteps-burnin, batch_size, nclasses)) 
 
 
 
            ## Experimented with target_masking 
            #target_mask = (data_batch.mean(2)>0.01).unsqueeze(2).float() 
            #target_mask = tonp(data_batch.mean(2, keepdim=True)>0.01).squeeze().unsqueeze(1) 
            #target_mask = tonp(data_batch.mean(2, keepdim=True).squeeze().unsqueeze(2)>.01 
            net.init(data_batch, burnin) 
 
            for k in (range(burnin,timesteps)): 
                s, r, u = net.step(data_batch[:, k, :, :]) 
                test_loss_tv = decolle_loss(s,r,u, target=target_batch[:,k], sum_ = False) 
                test_loss += [tonp(x) for x in test_loss_tv] 
                for l,n in enumerate(decolle_loss.loss_layer): 
                    r_cum[l,k-burnin,:,:] += tonp(sigmoid(r[n])) 
            test_res.append(prediction_mostcommon(r_cum)) 
            test_labels += tonp(target_batch).sum(1).argmax(axis=-1).tolist() 
        test_acc  = accuracy(np.column_stack(test_res), np.column_stack(test_labels)) 
        test_loss /= len(gen_test) 
        if print_error: 
            print(' '.join(['Error Rate L{0} {1:1.3}'.format(j, 1-v) for j, v in enumerate(test_acc)])) 
    if debug: 
        return test_loss, test_acc, s, r, u 
    else: 
        return test_loss, test_acc 
 
def accuracy(outputs, targets, one_hot = True): 
    if type(targets) is torch.tensor: 
        targets = tonp(targets) 
 
 
    return [np.mean(o==targets) for o in outputs] 
 
def prediction_mostcommon(outputs): 
    maxs = outputs.argmax(axis=-1) 
    res = [] 
    for m in maxs: 
        most_common_out = [] 
        for i in range(m.shape[1]): 
#            idx = m[:,i]!=target.shape[-1] #This is to prevent classifying the silence states 
            most_common_out.append(Counter(m[:, i]).most_common(1)[0][0]) 
        res.append(most_common_out) 
    return res 
 
 
def save_checkpoint(epoch, checkpoint_dir, net, opt): 
    if not os.path.exists(checkpoint_dir): 
        os.makedirs(checkpoint_dir) 
    torch.save({ 
        'epoch'               : epoch, 
        'model_state_dict'    : net.state_dict(), 
        'optimizer_state_dict': opt.state_dict(), 
        }, os.path.join(checkpoint_dir, 'epoch{:05}.tar'.format(epoch))) 
 
 
def write_stats(epoch, test_acc, test_loss, writer): 
    for i, [l, a] in enumerate(zip(test_loss, test_acc)): 
        writer.add_scalar('/test_loss/layer{}'.format(i), l, epoch) 
        writer.add_scalar('/test_acc/layer{}'.format(i), a, epoch) 
         
def get_output_shape(input_shape, kernel_size=[3,3], stride = [1,1], padding=[1,1], dilation=[0,0]): 
    if not hasattr(kernel_size, '__len__'): 
        kernel_size = [kernel_size, kernel_size] 
    if not hasattr(stride, '__len__'): 
        stride = [stride, stride] 
    if not hasattr(padding, '__len__'): 
        padding = [padding, padding] 
    if not hasattr(dilation, '__len__'): 
        dilation = [dilation, dilation] 
    im_height = input_shape[-2] 
    im_width = input_shape[-1] 
    height = int((im_height + 2 * padding[0] - dilation[0] * 
                  (kernel_size[0] - 1) - 1) // stride[0] + 1) 
    width = int((im_width + 2 * padding[1] - dilation[1] * 
                  (kernel_size[1] - 1) - 1) // stride[1] + 1) 
    return [height, width] 
 
class DictMultiOpt(object): 
    def __init__(self, params): 
        self.params = params 
    def __getitem__(self, key): 
        p = [] 
        for par in self.params: 
            p.append(par[key]) 
        return p 
    def __setitem__(self, key, values): 
        for i, par in enumerate(self.params): 
            par[key] = values[i] 
 
class MultiOpt(object): 
    def __init__(self, *opts): 
        self.optimizers = opts 
        self.multioptparam = DictMultiOpt([opt.param_groups[-1] for opt in self.optimizers]) 
 
    def zero_grad(self): 
        for opt in self.optimizers: 
            opt.zero_grad() 
 
    def step(self): 
        for opt in self.optimizers: 
            opt.step() 
     
    def __getstate__(self): 
        p = [] 
        for opt in self.optimizers: 
            p.append(opt.__getstate__()) 
        return p 
     
    def state_dict(self): 
        return self.__getstate__() 
     
    def load_state_dicts(self, state_dicts): 
        # need to load state_dict of each optimizer 
        for i,op in enumerate(self.optimizers): 
            op.load_state_dict(state_dicts[i]) 
 
    def __iter__(self): 
        for opt in self.optimizers: 
            yield opt 
     
    @property 
    def param_groups(self): 
        return [self.multioptparam] 

def train_timewrapped(gen_train, loss_fn, net, opt, epoch, online_update=False, reg_loss_fn=None, batches_per_epoch=-1, final_t_loss=True):
    '''
    Trains a DECOLLE network

    Arguments:
    gen_train: a dataloader
    loss_fn: a DECOLLE loss function, as defined in base_model
    net: DECOLLE network
    opt: optimizaer
    epoch: epoch number, for printing purposes only
    online_update: whether updates should be made at every timestep or at the end of the sequence.
    reg_loss_fn: a loss functino (typically regularization) that takes the whole sequence
    '''
    device = net.get_input_layer_device()
    iter_gen_train = iter(gen_train)
    act_rate = [0 for i in range(len(net))]
    return_sequence = reg_loss_fn is not None

    assert online_update is False, "Time wrapped does not support online updates"
        
    net.train()
    if hasattr(net.LIF_layers[0], 'base_layer'):
        dtype = net.LIF_layers[0].base_layer.weight.dtype
    else:
        dtype = net.LIF_layers[0].weight.dtype
    batch_iter = 0
    loss_tv = 0

    train_res = []
    train_labels = []
    train_loss = 0

    for data_batch, target_batch in tqdm.tqdm(iter_gen_train, desc='Epoch {}'.format(epoch)):
        data_batch = data_batch.to(device)
        target_batch = target_batch.type(torch.int64).to(device)
        net.init(data_batch)
        t_sample = data_batch.shape[1]

        u, ht = net(data_batch, return_sequence = True)
        
        if final_t_loss:
            loss_ = loss_fn(u, target_batch)
        else:
            loss_ = 0
            for i in range(len(ht[-1])):
                loss_ += loss_fn(ht[-1][i].to(device), target_batch)
        
        if reg_loss_fn is not None:
            loss_ += reg_loss_fn(ht)


        loss_.backward()
        opt.step()
        opt.zero_grad()
        
        if return_sequence:
            for i in range(len(net)):
                act_rate[i] = tonp((ht[i]>0).float().mean().data)
        train_loss += tonp(loss_)

        batch_iter +=1
        if batches_per_epoch>0:
            if batch_iter >= batches_per_epoch: break

        train_res += tonp(torch.argmax(u, axis=1)).tolist()
        train_labels += tonp(target_batch).tolist()# = tonp(target_batch)

    train_acc  = time_wrapped_accuracy(train_res,train_labels)
    train_loss /= batch_iter
    return [train_loss], act_rate, [train_acc ]

def time_wrapped_accuracy(outputs, targets):
    return np.mean(np.array(outputs)==np.array(targets))

def test_timewrapped(gen_test, loss_fn, net, print_error = True):
    net.eval()
    if hasattr(net.LIF_layers[0], 'base_layer'):
        dtype = net.LIF_layers[0].base_layer.weight.dtype
    else:
        dtype = net.LIF_layers[0].weight.dtype
    with torch.no_grad():
        device = net.get_input_layer_device()
        iter_gen_test = iter(gen_test)
        
        test_res = []
        test_labels = []
        test_loss = 0

        for data_batch, target_batch in tqdm.tqdm(iter_gen_test, desc='Testing'):
            data_batch = data_batch.to(device)
            target_batch = target_batch.type(torch.int64).to(device)
            net.init(data_batch)
            u = net(data_batch)
            test_loss += tonp(loss_fn(u, target_batch))

            test_res += tonp(torch.argmax(u, axis=1)).tolist()
            test_labels += tonp(target_batch).tolist()# = tonp(target_batch)
        test_acc  = time_wrapped_accuracy(np.column_stack(test_res), np.column_stack(test_labels))
        test_loss /= len(gen_test)
        if print_error: print('Error: {0:1.3}'.format(1-test_acc))
    return [test_loss], [test_acc]


def decolle_style_reg(weight):
    def fn(u):
        reg_loss = 0
        for i in range(len(u)):
            uflat = u[i].reshape(u[i].shape[0],-1)
            reg1_loss = ((relu(uflat+.01))).mean()
            reg2_loss = 3e-3*relu(((.1-sigmoid(uflat))).mean())
            reg_loss += (reg1_loss+reg2_loss)
        return weight*reg_loss
    return fn


