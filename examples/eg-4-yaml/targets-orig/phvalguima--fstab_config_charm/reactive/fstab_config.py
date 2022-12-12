import os
import copy
import yaml
import subprocess

from charms.reactive import when, when_not, set_flag
from charms.layer import fstab_parser
from charms.apt import queue_install
from charmhelpers.core import hookenv, unitdata


def get_last_modification_fstab():
    stat = os.path.getmtime('/etc/fstab')
    return '{}'.format(round(stat))


@when_not('fstab_config.installed')
@when_not('series-upgrade-started')
def install_fstab_config():
    # Do your setup here.
    #
    # If your charm has other dependencies before it can install,
    # add those as @when() clauses above., or as additional @when()
    # decorated handlers below
    #
    # See the following for information about reactive charms:
    #
    #  * https://jujucharms.com/docs/devel/developer-getting-started
    #  * https://github.com/juju-solutions/layer-basic#overview
    #
    queue_install(['nfs-common',
                   'cifs-utils'])
    hookenv.status_set('maintenance', 'waiting for installation')


@when('apt.installed.nfs-common')
@when('apt.installed.cifs-utils')
@when_not('fstab_config.installed')
@when_not('series-upgrade-started')
def set_installed_message():
    set_flag('fstab_config.installed')
    hookenv.status_set('active', 'ready')


def is_equal_list_dicts(a, b):
    if len(a) != len(b):
        return False

    for elem in a:
        for el_b in b:
            for i in elem:
                if i not in el_b:
                    return False
                if elem[i] != el_b[i]:
                    return False
    return True


@when('config.changed.configmap')
@when('fstab_config.installed')
@when_not('update-status')
@when_not('series-upgrade-started')
def config_changed():

    fstab_entries = hookenv.config('configmap')
    configmap = copy.deepcopy(yaml.load(fstab_entries))
    db = unitdata.kv()
    old_configmap = yaml.load(db.get('previous_configmap', default=""))
    hookenv.log('Old Configmap recovered from DB is: {}'.format(old_configmap))
    hookenv.status_set('maintenance', '[config-changed] '
                       'updating fstab following configmap...')
    if configmap is None or len(configmap) == 0:
        configmap = list()
    if old_configmap is None or len(old_configmap) == 0:
        old_configmap = list()

    if is_equal_list_dicts(configmap, old_configmap):
        # configmap is the same, we return
        hookenv.log('Configmap entered {} and old value {} are the same'
                    .format(fstab_entries, old_configmap),
                    hookenv.DEBUG)
        hookenv.log('Same configmap supplied as already-installed '
                    'configuration, ignoring...',
                    hookenv.INFO)
        return

    configmap = fstab_parser.remove_redundancies(
        target_configmap=configmap,
        other_cm=old_configmap)

    fstab_content = fstab_parser.dict_to_fstab(configmap,
                                               old_configmap,
                                               hookenv.config('enforce-config'),
                                               hookenv.config('mount-timeout'))

    try:
        ret_check = fstab_parser.check_configmap(configmap)
        if ret_check is not None:
            hookenv.log('(config_changed.check_configmap) {}'
                        .format(ret_check),
                        hookenv.WARNING)
    except fstab_parser.ConfigmapMissingException as e:
        hookenv.status_set('blocked', str(e))
        return

    with open('/etc/fstab', 'w') as f:
        f.write(fstab_content)
        f.close()

    try:
        subprocess.check_output(['mount', '-a'],
                                timeout=hookenv.config('mount-timeout'))
    except subprocess.TimeoutExpired:
        hookenv.status_set('blocked', 'Timed out on mount. '
                           'Please, check configmap')
    except subprocess.CalledProcessError:
        hookenv.status_set('blocked', 'MOUNT ERROR! Please, '
                           'check configmap')

    now = get_last_modification_fstab()
    db.set('fstab_last_update', now)
    db.flush()
    db.set('previous_configmap', hookenv.config('configmap'))
    db.flush()
    hookenv.status_set('active', 'ready')


@when('update-status')
@when_not('series-upgrade-started')
def update_status():
    if hookenv.config('enforce'):
        recent_mod = get_last_modification_fstab()
        last_mod = unitdata.kv().get('fstab_last_update', default="")
        hookenv.log('update_status: most recent mod happened on {} '
                    'and stored mod happened on {}'
                    .format(recent_mod, last_mod),
                    hookenv.INFO)
        if recent_mod > last_mod:
            config_changed()

    try:
        subprocess.check_output(['mount', '-a'],
                                timeout=hookenv.config('mount-timeout'))
    except subprocess.TimeoutExpired:
        hookenv.status_set('blocked', 'Timed out on mount. '
                           'Please, check configmap')
    except subprocess.CalledProcessError:
        hookenv.status_set('blocked', 'MOUNT ERROR! Please, '
                           'check configmap')


@when('upgrade.series.in-progress')
def pre_series_upgrade():
    hookenv.status_set('blocked','pre-series-upgrade procedure started')
    hookenv.log('Dispatched pre-series-upgrade', hookenv.INFO)
    try:
        # Allow to move between distros
        subprocess.check_output(['sed', '-i',
                                 's/Prompt=lts/Prompt=normal/g',
                                 '/etc/update-manager/release-upgrades'])
    except Exception as e:
        hookenv.log("Failed pre-series-upgrade run to "
                    "change Prompt for normal upgrades: {}".format(str(e)))
        raise e
    set_flag('series-upgrade-started')

@when('series-upgrade-started')
@when_not('upgrade.series.in-progress')
def post_series_upgrade():
    hookenv.log('Dispatched post-series-upgrade', hookenv.INFO)
    hookenv.status_set('active', 'ready')
