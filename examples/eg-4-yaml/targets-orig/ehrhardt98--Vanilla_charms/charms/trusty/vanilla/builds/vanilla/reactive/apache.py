import os
import yaml
import tempfile
from subprocess import check_call

from charmhelpers import fetch
from charmhelpers.core import host
from charmhelpers.core import hookenv
from charmhelpers.core import templating
from charmhelpers.core.host import lsb_release

from charms import reactive
from charms.reactive import hook
from charms.reactive import when
from charms.reactive import when_not


@hook('install')
def install():
    if reactive.is_state('apache.available'):
        return
    with open('apache.yaml') as fp:
        workload = yaml.safe_load(fp)
    install_packages(workload)
    for name, site in workload['sites'].items():
        install_site(name, site)
    hookenv.status_set('maintenance', '')
    reactive.set_state('apache.available')


@hook('config-changed')
def config_changed():
    config = hookenv.config()
    if not reactive.is_state('apache.available') or not config.changed('port'):
        return
    with open('apache.yaml') as fp:
        workload = yaml.safe_load(fp)
    for name, site in workload['sites'].items():
        configure_site(name, site)
    if reactive.is_state('apache.started'):
        hookenv.close_port(config.previous('port'))
        assert host.service_reload('apache2'), 'Failed to reload Apache'
        hookenv.open_port(config['port'])
    hookenv.status_set('maintenance', '')


def install_packages(workload):
    config = hookenv.config()
    hookenv.status_set('maintenance', 'Installing packages')
    if lsb_release()['DISTRIB_RELEASE'] >= '16.04':
        packages = ['apache2', 'php-cgi', 'libapache2-mod-php']
    else:
        packages = ['apache2', 'php5-cgi', 'libapache2-mod-php5']
    packages.extend(workload['packages'])
    fetch.apt_install(fetch.filter_installed_packages(packages))
    host.service_stop('apache2')
    check_call(['a2dissite', '000-default'])
    hookenv.open_port(config['port'])


def install_site(name, site):
    hookenv.status_set('maintenance', 'Installing %s' % name)
    dest = '/var/www/%s' % name
    fetch.install_remote(dest=dest, **site['install_from'])
    strip_archive_dir(dest)
    configure_site(name, site)


def configure_site(name, site):
    hookenv.status_set('maintenance', 'Configuring %s' % name)
    config = hookenv.config()
    templating.render(
        source='site.conf',
        target='/etc/apache2/sites-available/%s.conf' % name,
        context={
            'name': name,
            'site': site,
            'port': config['port'],
            'doc_root': '/var/www/%s' % name,
        },
    )


def strip_archive_dir(site_dir):
    """
    Most archives will nest all contents under a single path, for ease of
    unpacking.  However, we want the site contents to reside directly within
    the site dir, which should be named based on the site entry.  This
    heuristic detects when an archive extracted to a single top-level
    dir within the site dir and moves the contents up.
    """
    contents = os.listdir(site_dir)
    if len(contents) != 1:
        return
    archive_topdir = os.path.join(site_dir, contents[0])
    if not os.path.isdir(archive_topdir):
        return
    tmp_dest = tempfile.mkdtemp(dir=os.path.dirname(site_dir))
    os.rename(archive_topdir, tmp_dest)
    os.rmdir(site_dir)
    os.rename(tmp_dest, site_dir)


@when('apache.start')
@when_not('apache.started')
def start_apache():
    with open('apache.yaml') as fp:
        workload = yaml.safe_load(fp)
    for name, site in workload['sites'].items():
        check_call(['a2ensite', name])
    assert host.service_start('apache2'), 'Failed to start Apache2'
    reactive.set_state('apache.started')


@when('apache.available', 'apache.started')
@when_not('apache.start')
def stop_apache():
    assert host.service_stop('apache2'), 'Failed to stop Apache'
    reactive.remove_state('apache.started')


@when('website.available')
def configure_website(website):
    config = hookenv.config()
    website.configure(config['port'])
