import argparse

import yaml

parser = argparse.ArgumentParser()
parser.add_argument('-c', default=None)
args = parser.parse_args()

cfg_path = args.c
assert(cfg_path)

cfg = yaml.safe_load(open(cfg_path, "r"))
print("Config:")
[print("\t{}: {}".format(k, v)) for k, v in cfg.items()]
print("*******")

non_gc_keys =  [x for x in cfg.keys() if x != 'greedy_complete_at']
for gc in cfg['greedy_complete_at']:
    new_config = {k: cfg[k] for k in non_gc_keys}
    new_config['greedy_complete_at'] = [gc]
    new_config['state'] = 'created'
    model_name = cfg['trainable_reranker_config'].split('/')[-1].split('.')[0]
    filename = '{}_{}.yaml'.format('-'.join(map(str,gc)), model_name)
    with open('new_configs/optimization_configs/'+filename, 'w+') as fp:
        yaml.dump(new_config, fp)
