import os
from rc import run, ok, pmap, p
import yaml
import rc

config_dir = os.path.expanduser('~/.python-rc/')
groups_dir = os.path.join(config_dir, 'groups')
logs_dir = os.path.join(config_dir, 'logs')


def create_config_dirs():
    ok(run(f'mkdir -p {groups_dir}'))
    ok(run(f'mkdir -p {logs_dir}'))
    with open(os.path.join(config_dir, '.tmux.conf'), 'w') as f:
        f.write('''set -g mouse on
bind-key a set-window-option synchronize-panes
''')


def get_spec(spec, default, item):
    if type(spec) is str:
        return default.get(item)
    return spec.get(item, default.get(item))


def machine_from_spec(spec, default=None):
    if default is None:
        default = {}
    provider = get_spec(spec, default, 'provider')
    assert provider
    provider = getattr(rc.provider, provider)
    assert provider
    if type(spec) is str:
        machine = provider.get(spec, **default)
        assert machine
        return machine
    else:
        spec = {**default, **spec}
        machine = provider.get(**spec)
        assert machine
        return machine


def get_targets(arg):
    group_ = arg.split('/')
    group_config_file = get(group_[0])
    if group_config_file:
        try:
            if len(group_) > 1:
                sub_machines = group_[1].split(',')
            else:
                sub_machines = None
            return parse_config(group_config_file, sub_machines)
        except Exception as e:
            print(f'targets: {arg} invalid')
            print(e)
            exit(2)
    else:
        return None


def parse_config(config_file, sub_machines=None):
    config = yaml.safe_load(open(config_file))
    default = config.get('default', {})
    machine_spec = config.get('machines', None)
    if machine_spec is None:
        raise "Machines cannot be empty"
    machines = pmap(lambda ms: machine_from_spec(ms, default), machine_spec)
    group_machines = {}
    for m in machines:
        group_machines[str(m)] = m
    assert len(group_machines) == len(machines)
    if sub_machines:
        targets = []
        for n in sub_machines:
            matches = list(
                filter(lambda name: n in name, group_machines.keys()))
            assert len(matches) == 1
            targets += matches
        assert len(targets) > 0
    else:
        targets = group_machines.keys()
    targets = sorted(targets)
    p('machine targets: ', ', '.join(targets))
    return list(map(lambda n: group_machines[n], targets))


def get(group_name):
    if os.path.exists(os.path.join(groups_dir, group_name)):
        return os.path.join(groups_dir, group_name)
