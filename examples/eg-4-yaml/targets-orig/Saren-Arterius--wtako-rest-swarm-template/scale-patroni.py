#!/usr/bin/env python3
from os.path import basename, dirname, realpath
import subprocess
import sys
import yaml
import copy

service_name = basename(dirname(realpath(__file__)))

if __name__ == "__main__":
    try:
        scale = int(sys.argv[1])
        assert scale >= 1
    except:
        print('Usage: scale-patroni.py [scale >= 1]')
        exit()

    etcd_state = 'new'
    while True:
        ans = input('Is new or existing cluster (N/E)? ')
        if ans == 'E':
            etcd_state = 'existing'
            break
        if ans == 'N':
            break

    with open('docker-compose.yml', 'r') as f:
        data = yaml.safe_load(f)
    etcd_tmp = data['services']['etcd1']
    patroni_tmp = data['services']['patroni1']
    for k in list(data['services'].keys()):
        if k.startswith('etcd') or k.startswith('patroni'):
            del data['services'][k]
    for k in list(data['volumes'].keys()):
        if k.startswith('etcd-') or k.startswith('patroni-'):
            del data['volumes'][k]
    for i in range(1, scale + 1):
        e = copy.deepcopy(etcd_tmp)
        k = f'etcd{i}'
        v = f'etcd-data-{i}'
        e['hostname'] = k
        e['command'] = f'etcd -name etcd{i} -initial-advertise-peer-urls http://etcd{i}:2380'
        e['volumes'] = [f'{v}:/home/postgres']
        e['deploy']['placement']['constraints'] = [f'node.labels.id == db{i}']
        data['services'][k] = e
        data['volumes'][v] = None

        p = copy.deepcopy(patroni_tmp)
        k = f'patroni{i}'
        v = f'patroni-pg-data-{i}'
        p['hostname'] = k
        p['environment'] = {
            'PATRONI_NAME': k,
            'PATRONI_RESTAPI_PORT': str(8007 + i),
            'PATRONI_POSTGRES_PORT': str(5431 + i),
            'PATRONI_POSTGRES_YML': f'postgres{i - 1}.yml'
        }
        p['volumes'] = [f'{v}:/home/postgres']
        p['deploy']['placement']['constraints'] = [f'node.labels.id == db{i}']
        data['services'][k] = p
        data['volumes'][v] = None
    with open('docker-compose.yml', 'w') as f:
        f.write(yaml.dump(data))

    with open('patroni/postgres0.yml', 'r') as f:
        data = yaml.safe_load(f)
    for i in range(2, scale + 1):
        p = copy.deepcopy(data)
        p['name'] = f'postgresql{i - 1}'
        p['restapi']['listen'] = f'127.0.0.1:{str(8007 + i)}'
        p['restapi']['connect_address'] = p['restapi']['listen']
        p['postgresql']['listen'] = f'127.0.0.1:{str(5431 + i)}'
        p['postgresql']['connect_address'] = p['postgresql']['listen']
        p['postgresql']['data_dir'] = f'data/postgresql{i - 1}'
        p['postgresql']['pgpass'] = f'/tmp/pgpass{i - 1}'
        with open(f'patroni/postgres{i - 1}.yml', 'w') as f:
            f.write(yaml.dump(p))

    with open('patroni/docker/etcd.env', 'r') as f:
        lines = f.readlines()
    for i, l in enumerate(lines):
        if l.startswith('ETCD_INITIAL_CLUSTER='):
            cluster = [
                f'etcd{i}=http://etcd{i}:2380' for i in range(1, scale + 1)]
            lines[i] = 'ETCD_INITIAL_CLUSTER=' + ','.join(cluster) + '\n'
        if l.startswith('ETCD_INITIAL_CLUSTER_STATE='):
            lines[i] = f'ETCD_INITIAL_CLUSTER_STATE=new\n'
    with open('patroni/docker/etcd.env', 'w') as f:
        f.write(''.join(lines))

    with open('patroni/docker/patroni.env', 'r') as f:
        lines = f.readlines()
    for i, l in enumerate(lines):
        if l.startswith('PATRONI_ETCD_HOSTS='):
            cluster = [f"'etcd{i}:2379'" for i in range(1, scale + 1)]
            lines[i] = 'PATRONI_ETCD_HOSTS=' + ','.join(cluster) + '\n'
        if l.startswith('ETCDCTL_ENDPOINTS='):
            cluster = [f'http://etcd{i}:2379' for i in range(1, scale + 1)]
            lines[i] = 'ETCDCTL_ENDPOINTS=' + ','.join(cluster) + '\n'
    with open('patroni/docker/patroni.env', 'w') as f:
        f.write(''.join(lines))

print(f'Scale={scale} set for {etcd_state} clusters.')
print()
if etcd_state == 'existing':
    cmd1 = "docker ps | grep -e 'etcd[0-9]\+' | awk '{print $1}'"
    print('Step to do for scaling up:')
    print(f'1. Backup databases:')
    print(f' ./backup.sh')
    print(f'2. Remove the stack:')
    print(f' docker stack remove {service_name}')
    print(f'3. Remove existing etcd data volumes in all nodes:')
    for i in range(1, scale + 1):
        print(
            f' docker volume rm {service_name}_etcd-data-{i}')
    print('4. Deploy\n ./deploy.sh')
    cmd2 = "docker ps | grep -e 'patroni[0-9]\+' | awk '{print $1}'"
    print(
        f'5. Check patroni status: \n docker exec -it `{cmd2}` patronictl list')
    print(
        f'6. If state flopping - switchover to any existing replica (for dealing with pg_checksums + pgroonga): \n docker exec -it `{cmd2}` patronictl switchover')
    print(
        f'7. And then, switchover back to original: \n docker exec -it `{cmd2}` patronictl switchover')
    print(f'8. If none of replica is running (likely because of pgroonga), just start over and restore backup.')
