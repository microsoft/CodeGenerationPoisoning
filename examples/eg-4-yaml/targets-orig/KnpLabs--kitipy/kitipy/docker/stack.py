import click
import json
import os
import subprocess
import yaml
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Union

from .actions import buildx_build, normalize_labels
from ..context import Context
from ..executor import BaseExecutor
from ..utils import append_cmd_flags


class BaseStack(ABC):

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def file(self):
        pass

    @property
    @abstractmethod
    def config(self):
        pass

    @abstractmethod
    def build(self,
              services: List[str] = [],
              **kwargs) -> subprocess.CompletedProcess:
        pass

    @abstractmethod
    def buildx_build(self, services: List[str] = [], **kwargs):
        pass

    @abstractmethod
    def push(self,
             services: List[str] = [],
             _pipe: bool = False,
             _check: bool = True,
             _env: Optional[Dict[str, str]] = None,
             **kwargs) -> subprocess.CompletedProcess:
        pass

    @abstractmethod
    def up(self,
           services: List[str] = [],
           **kwargs) -> subprocess.CompletedProcess:
        pass

    @abstractmethod
    def down(self, **kwargs) -> subprocess.CompletedProcess:
        pass

    @abstractmethod
    def restart(self,
                services: Optional[List[str]] = None,
                _pipe: bool = False,
                _check: bool = True,
                **kwargs) -> subprocess.CompletedProcess:
        pass

    @abstractmethod
    def ps(self,
           services: List[str] = [],
           _pipe: bool = False,
           _check: bool = True,
           **kwargs) -> subprocess.CompletedProcess:
        pass

    @abstractmethod
    def count_services(self, filter: Optional[Tuple[str]] = None) -> int:
        pass

    @abstractmethod
    def count_running_services(self) -> int:
        pass

    @abstractmethod
    def logs(self,
             services: List[str] = [],
             **kwargs) -> subprocess.CompletedProcess:
        pass

    @abstractmethod
    def exec(self, service: str, cmd: str,
             **kwargs) -> subprocess.CompletedProcess:
        pass

    @abstractmethod
    def run(self, service: str, cmd: str,
            **kwargs) -> subprocess.CompletedProcess:
        pass

    @abstractmethod
    def inspect(self,
                service: str,
                replica_id: int = 1,
                **kwargs) -> subprocess.CompletedProcess:
        pass

    @abstractmethod
    def get_ip_address(self, service: str, network: str):
        pass


class ComposeStack(BaseStack):

    def __init__(self,
                 executor: BaseExecutor,
                 stack_name='',
                 file='',
                 basedir: Optional[str] = None,
                 env: Optional[Dict[str, str]] = None):
        self._name = stack_name
        self._executor = executor
        self._file = file
        self._env = env if env else {}
        self._env.update({
            'COMPOSE_PROJECT_NAME': stack_name,
            'COMPOSE_FILE': file,
        })
        self._basedir = basedir
        self._loaded = False
        self._config = None

    @property
    def name(self):
        return self._name

    @property
    def config(self):
        self._load_config()
        return self._config

    @property
    def file(self):
        return self._file

    def _load_config(self):
        if self._loaded:
            return

        cmd = "docker-compose -f {file} config 2>/dev/null".format(
            file=self._file)
        res = self._run(cmd, pipe=True, env=self._env)
        self._config = yaml.safe_load(res.stdout)
        self._loaded = True

    def check_config(self) -> bool:
        res = self._run('docker-compose config 2>&1 1>/dev/null')
        return res.returncode == 0

    def build(self,
              services: List[str] = [],
              _pipe: bool = False,
              _check: bool = True,
              _env: Optional[Dict[str, str]] = None,
              **kwargs) -> subprocess.CompletedProcess:
        cmd = append_cmd_flags('docker-compose build', **kwargs)
        return self._local('%s %s' % (cmd, ' '.join(services)),
                           pipe=_pipe,
                           check=_check,
                           env=_env)

    def buildx_build(self, services: List[str] = [], **kwargs):
        """Mimic `docker-compose build` using `docker buildx build`.
        
        Unlike other actions, this one doesn't support usual _pipe and _check
        as it makes little sense to pipe the content of all the commands run.

        Args:
            services (Optional[List[str]]): List of services to build. All
                the services are built if None is passed (the default value).
            **kwargs: Flags passed to `docker buildx build`.
        
        Raises:
            subprocess.SubprocessError: When one of the build fails.
        """
        basedir = self._basedir or os.getcwd()
        services = services or []
        _buildx_build_stack(self._executor, self, services, basedir, **kwargs)

    def push(self,
             services: List[str] = [],
             _pipe: bool = False,
             _check: bool = True,
             _env: Optional[Dict[str, str]] = None,
             **kwargs) -> subprocess.CompletedProcess:
        cmd = append_cmd_flags('docker-compose push', **kwargs)
        return self._run('%s %s' % (cmd, ' '.join(services)),
                         pipe=_pipe,
                         check=_check,
                         env=_env)

    def up(self,
           services: List[str] = [],
           _pipe: bool = False,
           _check: bool = True,
           **kwargs) -> subprocess.CompletedProcess:
        cmd = append_cmd_flags('docker-compose up', **kwargs)
        return self._run('%s %s' % (cmd, ' '.join(services)),
                         pipe=_pipe,
                         check=_check)

    def down(self,
             _pipe: bool = False,
             _check: bool = True,
             **kwargs) -> subprocess.CompletedProcess:
        cmd = append_cmd_flags('docker-compose down', **kwargs)
        return self._run(cmd, pipe=_pipe, check=_check)

    def restart(self,
                services: Optional[List[str]] = None,
                _pipe: bool = False,
                _check: bool = True,
                **kwargs) -> subprocess.CompletedProcess:
        if services is None:
            services = []

        cmd = append_cmd_flags('docker-compose restart', **kwargs)
        return self._run('%s %s' % (cmd, ' '.join(services)),
                         pipe=_pipe,
                         check=_check)

    def ps(self,
           services: List[str] = [],
           _pipe: bool = False,
           _check: bool = True,
           **kwargs) -> subprocess.CompletedProcess:
        # docker-compose ps --filter doesn't work without --services
        # see https://github.com/docker/compose/issues/5996
        if 'filter' in kwargs and 'services' not in kwargs:
            kwargs['services'] = True

        cmd = append_cmd_flags('docker-compose ps', **kwargs)
        res = self._run('%s %s' % (cmd, ' '.join(services)),
                        pipe=_pipe,
                        check=_check)
        return res

    def count_services(self, filter: Optional[Tuple[str]] = None) -> int:
        res = self.ps(filter=filter, _pipe=True, _check=False)
        return len(res.stdout.splitlines())

    def count_running_services(self) -> int:
        return self.count_services(filter=('status=running'))  # type: ignore

    def logs(self,
             services: List[str] = [],
             _pipe: bool = False,
             _check: bool = True,
             **kwargs) -> subprocess.CompletedProcess:
        cmd = append_cmd_flags('docker-compose logs', **kwargs)
        return self._run('%s %s' % (cmd, ' '.join(services)))

    def exec(self,
             service: str,
             cmd: str,
             _pipe: bool = False,
             _check: bool = True,
             **kwargs) -> subprocess.CompletedProcess:
        exec = append_cmd_flags('docker-compose exec', **kwargs)
        return self._run('%s %s %s' % (exec, service, cmd),
                         pipe=_pipe,
                         check=_check)

    def run(self,
            service: str,
            cmd: str,
            _pipe: bool = False,
            _check: bool = True,
            **kwargs) -> subprocess.CompletedProcess:
        kwargs.setdefault('rm', True)
        run = append_cmd_flags('docker-compose run', **kwargs)
        return self._run('%s %s %s' % (run, service, cmd),
                         pipe=_pipe,
                         check=_check)

    def inspect(self,
                service: str,
                replica_id: int = 1,
                _pipe: bool = False,
                _check: bool = True,
                **kwargs) -> subprocess.CompletedProcess:
        cmd = append_cmd_flags('docker inspect', **kwargs)
        return self._run('%s %s_%s_%d' % (cmd, self.name, service, replica_id),
                         pipe=_pipe,
                         check=_check)

    def raw(self, args: List[str]):
        cmd = 'docker-compose %s' % (' '.join(args))
        return self._run(cmd)

    def get_ip_address(self, service: str, network: str):
        inspect = self.inspect(service, _pipe=True)
        data = json.loads(inspect.stdout)
        return data[0]['NetworkSettings']['Networks'][network]['IPAddress']

    def _run(self, cmd: str, **kwargs) -> subprocess.CompletedProcess:
        env = self._env.copy()
        if 'env' in kwargs:
            env.update(kwargs['env'])

        kwargs['env'] = env
        kwargs.setdefault('cwd', self._basedir)
        return self._executor.run(cmd, **kwargs)

    def _local(self, cmd: str, **kwargs) -> subprocess.CompletedProcess:
        env = self._env.copy()
        if 'env' in kwargs:
            env.update(kwargs['env'])

        kwargs['env'] = env
        kwargs.setdefault('cwd', self._basedir)
        return self._executor.local(cmd, **kwargs)


class SwarmStack(BaseStack):

    def __init__(self,
                 executor: BaseExecutor,
                 stack_name='',
                 file='',
                 basedir: str = None):
        self._name = stack_name
        self._executor = executor
        self._env = {
            'COMPOSE_FILE': file,
        }
        self._basedir = basedir
        self._loaded = False
        self._config = None

    @property
    def name(self):
        return self._name

    @property
    def file(self):
        return self._file

    @property
    def config(self):
        self._load_config()
        return self._config

    def _load_config(self):
        if self._loaded:
            return

        cmd = "docker-compose -f {file} config 2>/dev/null".format(
            file=self._file)
        res = self._run(cmd, pipe=True, env=self._env)
        self._config = yaml.safe_load(res.stdout)
        self._loaded = True

    def check_config(self):
        """Check if the config of this stack is valid.

        Raises:
            subprocess.SubprocessError: When the config is not valid.
        """
        # The only way to check if a swarm file is valid is actually to
        # load it through docker-compose and ignore the error messages about
        # swarm-specific parameters not supported by docker-compose.
        res = self._run(
            'docker-compose config 2>&1 1>/dev/null | grep -v " Compose does not support \'deploy\' configuration"'
        )

    def build(self,
              services: List[str] = [],
              _pipe: bool = False,
              _check: bool = True,
              _env: Optional[Dict[str, str]] = None,
              **kwargs) -> subprocess.CompletedProcess:
        cmd = append_cmd_flags('docker-compose build', **kwargs)
        # Unfortunatly, the only way to build images from swarm files is to use
        # docker-compose, which complains about external secrets.
        cmd = '%s %s 2>&1 | grep -v "External secrets are not available"' % (
            cmd, ' '.join(services))
        return self._local(cmd, pipe=_pipe, check=_check, env=_env)

    def buildx_build(self, services: List[str] = [], **kwargs):
        """Mimic `docker-compose build` using `docker buildx build`.
        
        Unlike other actions, this one doesn't support usual _pipe and _check
        as it makes little sense to pipe the content of all the commands run.

        Args:
            services (Optional[List[str]]):
                List of services to build. All the services are built if an
                empty list is passed (the default value).
            **kwargs: Flags passed to `docker buildx build`.
        
        Raises:
            subprocess.SubprocessError: When one of the build fails.
        """
        basedir = self._basedir or os.getcwd()
        _buildx_build_stack(self._executor, self, services, basedir, **kwargs)

    def push(self,
             services: List[str] = [],
             _pipe: bool = False,
             _check: bool = True,
             _env: Optional[Dict[str, str]] = None,
             **kwargs) -> subprocess.CompletedProcess:
        cmd = append_cmd_flags('docker-compose push', **kwargs)
        return self._run('%s %s' % (cmd, ' '.join(services)),
                         pipe=_pipe,
                         check=_check,
                         env=_env)

    def up(self,
           services: List[str] = [],
           _pipe: bool = False,
           _check: bool = True,
           **kwargs) -> subprocess.CompletedProcess:
        kwargs.setdefault('resolve-image', 'never')
        kwargs.setdefault('prune', True)
        cmd = append_cmd_flags(
            'docker stack deploy -c %s ' % (self.config['file']), **kwargs)
        return self._run('%s %s' % (cmd, self.name), pipe=_pipe, check=_check)

    def down(self,
             _pipe: bool = False,
             _check: bool = True,
             **kwargs) -> subprocess.CompletedProcess:
        cmd = append_cmd_flags('docker stack rm', **kwargs)
        return self._run('%s %s' % (cmd, self.name), pipe=_pipe, check=_check)

    def restart(self,
                services: Optional[List[str]] = None,
                _pipe: bool = False,
                _check: bool = True,
                **kwargs) -> subprocess.CompletedProcess:
        """
        Args:
            service (Optional[List[str]]):
                List of services to restart. All services are restarted when
                the list is None (the default value).

        Raises:
            subprocess.CalledProcessError: When it fails to restart services
                (unless _check is False).
        
        Returns
            subprocess.CompletedProcess: When the process run successfully or
                when _check is False.
        """
        if services is None:
            services = self.config['services'].keys()

        kwargs['force'] = True
        basecmd = append_cmd_flags('docker service update ', **kwargs)
        cmd = []

        for svc in services:
            cmd.append('%s %s' % (basecmd, svc))

        return self._run(' && '.join(cmd), pipe=_pipe, check=_check)

    def ps(self,
           services: List[str] = [],
           _pipe: bool = False,
           _check: bool = True,
           **kwargs) -> subprocess.CompletedProcess:
        kwargs['filter'] = () if 'filter' not in kwargs else kwargs['filter']
        kwargs['filter'] += ('label=com.docker.stack.namespace=%s' %
                             (self.name))
        cmd = append_cmd_flags('docker service ls', **kwargs)
        res = self._run('%s %s' % (cmd, ' '.join(services)),
                        pipe=_pipe,
                        check=_check)
        return res

    def count_services(self, filter: Optional[Tuple[str]] = None) -> int:
        services = self.ps(filter=filter, _pipe=True, _check=False)
        # @TODO: improve it (this is actually buggy)
        return len(services.stdout.splitlines())

    def count_running_services(self) -> int:
        return self.count_services(filter=('status=running'))  # type: ignore

    def logs(self,
             services: List[str] = [],
             _pipe: bool = False,
             _check: bool = True,
             **kwargs) -> subprocess.CompletedProcess:
        cmd = append_cmd_flags('docker-compose logs', **kwargs)
        return self._run('%s %s' % (cmd, ' '.join(services)),
                         pipe=_pipe,
                         check=_check)

    def exec(self,
             service: str,
             cmd: str,
             _pipe: bool = False,
             _check: bool = True,
             **kwargs) -> subprocess.CompletedProcess:
        # @TODO: this is not going to work (docker-compose in SwarmStack)
        basecmd = append_cmd_flags('docker-compose exec', **kwargs)
        return self._run('%s %s %s' % (basecmd, service, cmd),
                         pipe=_pipe,
                         check=_check)

    def run(self,
            service: str,
            cmd: str,
            _pipe: bool = False,
            _check: bool = True,
            **kwargs) -> subprocess.CompletedProcess:
        kwargs.setdefault('rm', True)
        run = append_cmd_flags('docker-compose run', **kwargs)
        return self._run('%s %s %s' % (run, service, cmd),
                         pipe=_pipe,
                         check=_check)

    def inspect(self,
                service: str,
                replica_id: int = 1,
                _pipe: bool = False,
                _check: bool = True,
                **kwargs) -> subprocess.CompletedProcess:
        cmd = append_cmd_flags('docker inspect', **kwargs)
        # @TODO: this won't work properly
        return self._run('%s %s_%s_%d' % (cmd, self.name, service, replica_id),
                         pipe=_pipe,
                         check=_check)

    def get_ip_address(self, service: str, network: str):
        inspect = self.inspect(service, _pipe=True)
        data = json.loads(inspect.stdout)
        return data[0]['NetworkSettings']['Networks'][network]['IPAddress']

    def _run(self, cmd: str, **kwargs) -> subprocess.CompletedProcess:
        """Execute a command using global env vars and basedir as default values.

        Args:
            cmd (str): Command to execute
            **kwargs: Extra arguments passed to BaseExecutor.run().

        Raises:
            subprocess.CalledProcessError: When the passed command fail to execute.

        Returns:
            subprocess.CompletedProcess: 
        """
        env = self._env.copy()
        if 'env' in kwargs:
            env.update(kwargs['env'])

        kwargs['env'] = env
        kwargs.setdefault('cwd', self._basedir)
        return self._executor.run(cmd, **kwargs)

    def _local(self, cmd: str, **kwargs) -> subprocess.CompletedProcess:
        env = self._env.copy()
        if 'env' in kwargs:
            env.update(kwargs['env'])

        kwargs['env'] = env
        kwargs.setdefault('cwd', self._basedir)
        return self._executor.local(cmd, **kwargs)


def load_stack(kctx: Context,
               stack_name: str,
               filename_params: Dict[str, str] = {}) -> BaseStack:
    executor = kctx.executor
    config = kctx.config

    if 'stacks' not in config:
        raise click.BadParameter('No top key "stacks" found in the config.')

    stack_config = next(
        (v for k, v in config['stacks'].items() if k == stack_name), None)
    if stack_config is None:
        raise click.BadParameter('Stack %s not defined in the config.' %
                                 (stack_name))

    stack_basedir = stack_config.get('basedir')

    # @TODO: add templated stack filename
    # stack_file = stack_config.get('file', '%s.yml' % (stage))
    stack_file = stack_config.get('file', None)
    if stack_file is None:
        raise RuntimeError(
            'No property "file" found in the config of "%s" stack.' %
            (stack_config['name']))

    stage = kctx.stage['name'] if kctx.stage is not None else ''
    filename_params.setdefault('stage', stage)
    stack_file = stack_file.format(**filename_params)

    if 'swarm' in stack_config and stack_config['swarm']:
        return SwarmStack(executor,
                          stack_name=stack_name,
                          basedir=stack_basedir,
                          file=stack_file)

    return ComposeStack(executor,
                        stack_name=stack_name,
                        basedir=stack_basedir,
                        file=stack_file)


def _buildx_build_stack(
    executor: BaseExecutor,
    stack: BaseStack,
    services: List[str],
    default_context: str,
    **kwargs,
):
    services_cfg = stack.config.get('services', {})

    for name, service in services_cfg.items():
        # If services is provided, only those services should be build
        if len(services) > 0 and name not in services:
            continue

        # Service without image and build parameters are ignored as they're
        # either not build through the compose file and/or they can't be
        # pushed.
        if "image" not in service or "build" not in service:
            continue

        build = service.get('build', {})
        build = {"dockerfile": build} if isinstance(build, str) else build
        build_labels = normalize_labels(build.get('labels', {}))
        build_args = build.get('args', {})

        args = {}
        args['target'] = build.get('target')
        args['label'] = tuple(build_labels)
        args['build-arg'] = tuple(
            "{0}={1}".format(k, v) for k, v in build_args.items())
        args['tag'] = service.get('image', "%s/%s:latest" % (stack.name, name))
        args['file'] = build.get('dockerfile', 'Dockerfile')
        # Add kwargs at the end only so flags infered from compose config can
        # be overriden.
        args.update(kwargs)

        context = build.get('context', default_context)
        buildx_build(context, _cwd=context, **args)
