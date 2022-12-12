#!/usr/bin/env python3
import subprocess
import sys
import yaml
import copy

if __name__ == "__main__":
    try:
        scale = int(sys.argv[1])
        assert scale >= 1
    except:
        print('Usage: scale-redis.py [scale >= 1]')
        exit()

    with open('docker-compose.yml', 'r') as f:
        data = yaml.safe_load(f)
    redis_tmp = data['services']['redis1']
    for k in list(data['services'].keys()):
        if k.startswith('redis') and k != 'redis1':
            del data['services'][k]
    for k in list(data['volumes'].keys()):
        if k.startswith('redis-') and k != 'redis-data-1':
            del data['volumes'][k]
    data['services']['redis1']['environment']['TOTAL_NODES'] = scale
    for i in range(2, scale + 1):
        r = copy.deepcopy(redis_tmp)
        k = f'redis{i}'
        v = f'redis-data-{i}'
        r['hostname'] = k
        r['volumes'] = [f'{v}:/data']
        r['deploy']['placement']['constraints'] = [f'node.labels.id == db{i}']
        del r['ports']
        data['services'][k] = r
        data['volumes'][v] = None

        r['environment'] = {
            'INIT_SLAVE_OF': 1,
            'NODE_SEQ': i,
            'TOTAL_NODES': scale
        }

    with open('docker-compose.yml', 'w') as f:
        f.write(yaml.dump(data))

print(f'Scale={scale} set for redis.')
