""" Main module of the ARPOC """

# Python imports
import logging
import logging.config
import warnings
import copy

import argparse

# For scheduling auth & registration to providers
import sched
import threading
import time

import importlib.resources
import os
import pwd
import grp

import hashlib

import urllib.parse

from http.client import HTTPConnection
#HTTPConnection.debuglevel = 1
from dataclasses import dataclass, field
from typing import List, Dict, Union, Tuple, Callable, Iterable, Optional, Any

# side packages

##oic
import oic.oic
from oic.utils.authn.client import CLIENT_AUTHN_METHOD
from oic.oic.message import RegistrationResponse, AuthorizationResponse

from oic import rndstr
from oic.utils.http_util import Redirect
import oic.extension.client

import oic.exception

import yaml
import requests

import cherrypy
from cherrypy._cpdispatch import Dispatcher
from cherrypy.process.plugins import DropPrivileges, Daemonizer, PIDFile

from jinja2 import Environment, FileSystemLoader

from jwkest import jwt

#### Own Imports
from arpoc.base import ServiceProxy, OidcHandler, TLSOnlyDispatcher


import arpoc.ac as ac
import arpoc.exceptions
import arpoc.config as config
import arpoc.pap
import arpoc.special_pages
import arpoc.cache
import arpoc.utils
from arpoc.plugins import EnvironmentDict, ObjectDict, ObligationsDict

#logging.basicConfig(level=logging.DEBUG)

LOGGING = logging.getLogger(__name__)

env = Environment(loader=FileSystemLoader(
    os.path.join(os.path.dirname(__file__), 'resources', 'templates')))




class App:
    """ Class for application handling.
        Reads configuration files,
        setups the oidc client classes
        and the dispatcher for the services"""
    def __init__(self) -> None:
        self._scheduler = sched.scheduler(time.time, time.sleep)
        self.thread = threading.Thread(target=self._scheduler.run)
        self.oidc_handler: OidcHandler
        self.config: config.OIDCProxyConfig

        self.uid = 0
        self.gid = 0

    def cancel_scheduler(self):
        """ Cancels every event in the scheduler queue """
        if not self._scheduler.empty():
            for event in self._scheduler.queue:
                self._scheduler.cancel(event)
        self.thread.join()

    def setup_loggers(self) -> None:
        """ Read the loggers configuration and configure the loggers"""
        with importlib.resources.path(
                'arpoc.resources',
                'loggers.yml') as loggers_path, open(loggers_path) as ymlfile:
            log_config_str = ymlfile.read()
            log_config_str = log_config_str.replace('DEFAULTLEVEL',
                                                    self.config.misc.log_level)
            log_config_str = log_config_str.replace(
                'ACCESS_LOG', self.config.misc.access_log)
            log_config_str = log_config_str.replace('ERROR_LOG',
                                                    self.config.misc.error_log)
            log_conf = yaml.safe_load(log_config_str)
        logging.config.dictConfig(log_conf)

    def retry(self,
              function: Callable,
              exceptions: Tuple,
              *args: Any,
              retries: int = 5,
              retry_delay: int = 30) -> None:
        """ Retries function <retries> times, as long as <exceptions> are thrown"""
        try:
            function(*args)
        except exceptions as excep:
            if retries > 0:
                LOGGING.debug(
                    "Retrying %s, parameters %s, failed with exception %s",
                    function, args,
                    type(excep).__name__)
                LOGGING.debug("Delaying for %s seconds", retry_delay)
                self._scheduler.enter(retry_delay,
                                      1,
                                      self.retry,
                                      (function, exceptions, *args),
                                      kwargs={
                                          'retries': retries - 1,
                                          'retry_delay': retry_delay
                                      })

    def tls_redirect(self, *args: Any, **kwargs: Any) -> None:
        url = cherrypy.url(qs=cherrypy.request.query_string)
        # find starting / of path
        index = url.index('/', len('http://')) +1
        path = url[index:]
        https_url = "{}{}".format(self.config.proxy.baseuri, path)

        raise cherrypy.HTTPRedirect(https_url)

    def get_routes_dispatcher(self) -> cherrypy.dispatch.RoutesDispatcher:
        """ Setups the Cherry Py dispatcher
            This connects makes the proxied services accessible"""
        dispatcher = cherrypy.dispatch.RoutesDispatcher()
        # Connect the Proxied Services
        for name, service_cfg in self.config.services.items():
            logging.debug(service_cfg)
            if service_cfg.origin_URL == "pap":
                pap = arpoc.pap.PolicyAdministrationPoint('pap', self.oidc_handler, service_cfg)
                dispatcher.connect('pap', service_cfg.proxy_URL, controller=pap, action='index')
                dispatcher.connect('pap', service_cfg.proxy_URL + "{_:/.*?}", controller=pap, action='index')
            elif service_cfg.origin_URL == "userinfo":
                userinfo_page = arpoc.special_pages.Userinfo('userinfo', self.oidc_handler, service_cfg)
                dispatcher.connect('userinfo', service_cfg.proxy_URL, controller=userinfo_page, action='index')
            else:
                service_proxy_obj = ServiceProxy(name, self.oidc_handler,
                                                 service_cfg)
                dispatcher.connect(name,
                                   service_cfg['proxy_URL'],
                                   controller=service_proxy_obj,
                                   action='index')
                dispatcher.connect(name,
                                   service_cfg['proxy_URL'] + "{_:/.*?}",
                                   controller=service_proxy_obj,
                                   action='index')
        # Connect the Redirect URI
        LOGGING.debug(self.config.proxy['redirect'])
        for i in self.config.proxy['redirect']:
            dispatcher.connect('redirect',
                               i,
                               controller=self.oidc_handler,
                               action='redirect')
        # Test auth required
        dispatcher.connect('auth',
                           "%s" % self.config.proxy.auth,
                           controller=self.oidc_handler,
                           action='auth')
        dispatcher.connect('auth',
                           "%s/{name:.*?}" % self.config.proxy.auth,
                           controller=self.oidc_handler,
                           action='auth')
        if self.config.proxy['https_only']:
            dispatcher.connect('TLSRedirect',
                               '%s/{url:.*?}' % self.config.proxy.tls_redirect,
                               controller=self,
                               action='tls_redirect')
            tls_dispatcher = TLSOnlyDispatcher(self.config.proxy.tls_redirect,
                                               dispatcher)
            return tls_dispatcher

        return dispatcher

    @staticmethod
    def read_secrets(filepath: str) -> Dict:
        """ Reads the secrets file from the filepath """
        try:
            with open(filepath, 'r') as ymlfile:
                secrets = yaml.safe_load(ymlfile)
        except FileNotFoundError:
            secrets = dict()
        if secrets is None:
            secrets = dict()
        return secrets

    def save_secrets(self) -> None:
        """ Saves the oidc rp secrets into the secrets file"""
        with open(self.config.proxy['secrets'], 'w') as ymlfile:
            yaml.safe_dump(self.oidc_handler.get_secrets(), ymlfile)

    def create_secrets_dir(self) -> None:
        assert isinstance(self.config.proxy, config.ProxyConfig)
        secrets_dir = os.path.dirname(self.config.proxy['secrets'])
        os.makedirs(secrets_dir, exist_ok=True)
        self.uid = pwd.getpwnam(self.config.proxy['username'])[2]
        self.gid = grp.getgrnam(self.config.proxy['groupname'])[2]

        for dirpath, _, filenames in os.walk(secrets_dir):
            if len(filenames) > 1:
                raise arpoc.exceptions.ConfigError(
                    "Please specify an own directory for oidproxy secrets")
            os.chown(dirpath, self.uid, self.gid)
            for filename in filenames:
                os.chown(os.path.join(dirpath, filename), self.uid, self.gid)

    def setup_oidc_provider(self) -> None:
        """Setup the connection to all oidc providers in the config """
        assert isinstance(self.config, config.OIDCProxyConfig)

        # Read secrets
        secrets = self.read_secrets(self.config.proxy['secrets'])
        self.oidc_handler._secrets = secrets
        for name, provider in self.config.openid_providers.items():
            # check if the client is/was already registered
            if name in secrets.keys():
                self.retry(self.oidc_handler.create_client_from_secrets,
                           (requests.exceptions.RequestException,
                            oic.exception.CommunicationError), name, provider)
            else:
                self.retry(self.oidc_handler.register_first_time,
                           (requests.exceptions.RequestException,
                            oic.exception.CommunicationError), name, provider)
        self.thread.start()

    def run(self) -> None:
        """ Starts the application """
        #### Command Line Argument Parsing
        parser = argparse.ArgumentParser(description='ARPOC')
        parser.add_argument('-c', '--config-file')
        parser.add_argument('--print-sample-config', action='store_true')
        parser.add_argument('--print-sample-ac', action='store_true')
        parser.add_argument('--add-provider')
        parser.add_argument('--client-id')
        parser.add_argument('--client-secret')
        parser.add_argument('-d', '--daemonize', action='store_true')
        parser.add_argument('--check-ac', action='store_true')

        args = parser.parse_args()

        config.cfg = config.OIDCProxyConfig(config_file=args.config_file)
        self.config = config.cfg

        assert self.config.proxy is not None


        #### Read Configuration
        if args.print_sample_config:
            config.cfg.print_sample_config()
            return

        if args.print_sample_ac:
            arpoc.ac.print_sample_ac()
            return
        self.setup_loggers()

        #### Create secrets dir and change ownership (perm)
        self.create_secrets_dir()

        self.oidc_handler = OidcHandler(self.config)

        if args.add_provider and args.client_id and args.client_secret:
            # read secrets
            secrets = self.read_secrets(self.config.proxy['secrets'])

            provider_cfg = self.config.openid_providers[args.add_provider]
            redirect_uris = provider_cfg.redirect_uris or self.config.proxy['redirect_uris']

            # add secrets
            secret_dict = {
                "client_id": args.client_id,
                "client_secret": args.client_secret,
                "redirect_uris": args.redirect_uris
            }
            secrets[args.add_provider] = secret_dict
            self.oidc_handler._secrets = secrets
            self.oidc_handler.create_client_from_secrets(args.add_provider, provider_cfg)
            self.save_secrets()
            return


        #### Read AC Rules
        for acl_dir in self.config.access_control['json_dir']:
            ServiceProxy.ac.load_dir(acl_dir)

        if args.check_ac:
            ServiceProxy.ac.check()
            return

        if args.daemonize:
            daemonizer = Daemonizer(cherrypy.engine)
            daemonizer.subscribe()
            # check if pid file exists
            try:
                with open(self.config.misc.pid_file) as pidfile:
                    pid = int(pidfile.read().strip())
                    try:
                        os.kill(pid, 0)  # check if running
                    except OSError:
                        PIDFile(cherrypy.engine,
                                self.config.misc.pid_file).subscribe()
                        # not running
                    else:
                        # running
                        print("PID File %s exists" % self.config.misc.pid_file)
                        print(
                            "Another instance of arpoc seems to be running"
                        )
                        return
            except FileNotFoundError:
                PIDFile(cherrypy.engine, self.config.misc.pid_file).subscribe()

        #### Setup OIDC Provider
        cherrypy.engine.subscribe('start', self.setup_oidc_provider, 80)
        cherrypy.engine.subscribe('stop', self.cancel_scheduler, 80)
        cherrypy.engine.subscribe('stop', self.save_secrets, 80)
        #### Setup Cherrypy
        global_conf = {
            'log.screen': False,
            'log.access_file': '',
            'log.error_file': '',
            'server.socket_host': config.cfg.proxy['address'],
            'server.socket_port': config.cfg.proxy['tls_port'],
            'server.ssl_private_key': config.cfg.proxy['keyfile'],
            'server.ssl_certificate': config.cfg.proxy['certfile'],
            'engine.autoreload.on': False
        }
        cherrypy.config.update(global_conf)
        app_conf = {
            '/': {
                'tools.sessions.on': True,
                'request.dispatch': self.get_routes_dispatcher()
            }
        }
        DropPrivileges(cherrypy.engine, uid=self.uid, gid=self.gid).subscribe()


        #### Start Web Server
        cherrypy.tree.mount(None, '/', app_conf)
        if self.config.proxy['plain_port']:
            server2 = cherrypy._cpserver.Server()
            server2.socket_port = self.config.proxy['plain_port']
            server2._socket_host = self.config.proxy['address']
            server2.thread_pool = 30
            server2.subscribe()

        cherrypy.engine.start()
        cherrypy.engine.block()

    #    cherrypy.quickstart(None, '/', app_conf)
