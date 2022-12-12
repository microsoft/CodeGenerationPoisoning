# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020, Ansible Project

"""
Fixtures for changelog tests.
"""

import difflib
import io
import json
import os
import pathlib
import textwrap

from contextlib import redirect_stderr, redirect_stdout
from typing import Any, Callable, Dict, List, Mapping, Optional, Set, Tuple, Union

import pytest
import yaml

from antsibull_changelog.cli import run as run_changelog_tool
from antsibull_changelog.config import ChangelogConfig, CollectionDetails, PathsConfig


# When debugging failed tests and you want to see what exactly changed, you can set this
# variable to True. Then for all changed files, a colorized diff will be printed.
PRINT_DIFFS = False

_ANSIBLE_DOC_VERSION_TEMPLATE = '''ansible-doc [core {ansible_core_version}]
  config file = None
  configured module search path = ['/home/me/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
  ansible python module location = /usr/local/lib/python3.9/dist-packages/ansible
  ansible collection location = /home/me/.ansible/collections:/usr/share/ansible/collections
  executable location = /usr/local/bin/ansible-doc
  python version = 3.9.2
  jinja version = 3.0.3
  libyaml = True
'''


def diff(old: str, new: str) -> str:
    seqm = difflib.SequenceMatcher(None, old, new)
    output = []
    for opcode, a0, a1, b0, b1 in seqm.get_opcodes():
        if opcode == 'equal':
            output.append(seqm.a[a0:a1])
        elif opcode == 'insert':
            output.append("\033[42m" + seqm.b[b0:b1] + "\033[49m")  # inserted
        elif opcode == 'delete':
            output.append("\033[41m\033[9m" + seqm.a[a0:a1] + "\033[29m\033[49m")  # removed
        elif opcode == 'replace':
            output.append("\033[41m\033[9m" + seqm.a[a0:a1] + "\033[29m\033[49m")  # removed
            output.append("\033[42m" + seqm.b[b0:b1] + "\033[49m")  # inserted
        else:
            raise RuntimeError("unexpected opcode")
    return ''.join(output)


class Differences:
    """
    Describe differences between previous state (updated by environment) and filesystem.
    """

    added_dirs: List[str]
    added_files: List[str]
    removed_dirs: List[str]
    removed_files: List[str]
    changed_files: List[str]
    file_contents: Dict[str, bytes]
    file_differences: Dict[str, Tuple[bytes, bytes]]

    def __init__(self):
        self.added_dirs = []
        self.added_files = []
        self.removed_dirs = []
        self.removed_files = []
        self.changed_files = []
        self.file_contents = dict()
        self.file_differences = dict()

    def sort(self) -> None:
        self.added_dirs.sort()
        self.added_files.sort()
        self.removed_dirs.sort()
        self.removed_files.sort()
        self.changed_files.sort()

    def parse_yaml(self, path: str) -> Any:
        return yaml.load(self.file_contents[path], Loader=yaml.SafeLoader)

    @property
    def has_dir_changes(self) -> bool:
        return bool(self.added_dirs or self.added_files)

    @property
    def has_file_changes(self) -> bool:
        return bool(self.removed_dirs or self.removed_files or self.changed_files)

    @property
    def unchanged(self) -> bool:
        return not self.has_dir_changes and not self.has_file_changes

    def dump(self) -> None:
        print('== Differences ==')
        for field in ('added_dirs', 'added_files', 'removed_dirs',
                      'removed_files', 'changed_files'):
            list = getattr(self, field)
            print('{title} ({count} entries)'.format(
                title=field.replace('_', ' ').title(),
                count=len(list)))
            for entry in list:
                print('    {entry}'.format(entry=entry))

        if PRINT_DIFFS:
            for name, (before, after) in sorted(self.file_differences.items()):
                print('\nDifferences in {name}:'.format(name=name))
                print(textwrap.indent(
                    diff(before.decode('utf-8'), after.decode('utf-8')), '  # ', lambda line: True))


class ChangelogEnvironment:
    """
    Base class for changelog environments.
    """

    base_path: pathlib.Path

    paths: PathsConfig
    config: ChangelogConfig

    created_dirs: Set[str]
    created_files: Dict[str, bytes]

    def __init__(self, base_path: pathlib.Path, paths: PathsConfig):
        self.base = base_path

        self.paths = paths
        self.config = ChangelogConfig.default(paths, CollectionDetails(paths))

        self.created_dirs = set([self.paths.base_dir])
        self.created_files = dict()

        self.ansible_core_version = '2.12.2'

    def _write(self, path: str, data: bytes):
        with open(path, 'wb') as f:
            f.write(data)
        self.created_files[path] = data

    def _write_yaml(self, path: str, data: Any):
        self._write(path, yaml.dump(data, Dumper=yaml.SafeDumper).encode('utf-8'))

    def _written(self, path: str):
        with open(path, 'rb') as f:
            data = f.read()
        self.created_files[path] = data

    def mkdir(self, path: str):
        parts = []
        while path != self.paths.base_dir:
            path, part = os.path.split(path)
            parts.append(part)
        dir = self.paths.base_dir
        for part in reversed(parts):
            dir = os.path.join(dir, part)
            os.makedirs(dir, exist_ok=True)
            self.created_dirs.add(dir)

    def set_plugin_cache(self, version: str, plugins: Dict[str, Dict[str, Dict[str, str]]]):
        data = {
            'version': version,
            'plugins': plugins,
        }
        config_dir = self.paths.changelog_dir
        self.mkdir(config_dir)
        self._write_yaml(os.path.join(config_dir, '.plugin-cache.yaml'), data)

    def set_config_raw(self, config: bytes):
        self.mkdir(self.paths.changelog_dir)
        self._write(self.paths.config_path, config)
        self.config = ChangelogConfig.load(self.paths, CollectionDetails(self.paths))

    def set_config(self, config: ChangelogConfig):
        self.mkdir(self.paths.changelog_dir)
        self.config = config
        self.config.store()
        self._written(self.paths.config_path)

    def remove_fragment(self, fragment_name: str):
        path = os.path.join(self.paths.changelog_dir, self.config.notes_dir, fragment_name)
        if os.path.exists(path):
            os.remove(path)
        self.created_files.pop(path, None)

    def add_fragment(self, fragment_name: str, content: str, fragment_dir: Optional[str] = None):
        if fragment_dir is None:
            fragment_dir = os.path.join(self.paths.changelog_dir, self.config.notes_dir)
        else:
            fragment_dir = os.path.join(self.paths.base_dir, fragment_dir)
        self.mkdir(fragment_dir)
        self._write(os.path.join(fragment_dir, fragment_name), content.encode('utf-8'))

    def add_fragment_generic(self, fragment_name: str, sections: Mapping[str, Mapping[str, Any]],
                             fragment_dir: Optional[str] = None):
        self.add_fragment(
            fragment_name,
            yaml.dump(sections, Dumper=yaml.SafeDumper),
            fragment_dir=fragment_dir)

    def add_fragment_line(self, fragment_name: str, section: str, lines: Union[List[str], str],
                          fragment_dir: Optional[str] = None):
        self.add_fragment_generic(fragment_name, {section: lines}, fragment_dir=fragment_dir)

    def _plugin_base(self, plugin_type):
        if plugin_type == 'module':
            return ['plugins', 'modules']
        return ['plugins', plugin_type]

    def add_plugin(self, plugin_type: str, name: str, content: str, subdirs: List[str] = None):
        plugin_dir = os.path.join(
            self.paths.base_dir,
            *self._plugin_base(plugin_type),
            *(subdirs or []))
        self.mkdir(plugin_dir)
        self._write(os.path.join(plugin_dir, name), content.encode('utf-8'))

    def run_tool(self, command: str, arguments: List[str], cwd: Optional[str] = None) -> int:
        old_cwd = os.getcwd()
        if cwd is not None:
            cwd = os.path.join(self.paths.base_dir, cwd)
        else:
            cwd = self.paths.base_dir
        os.chdir(cwd)
        try:
            return run_changelog_tool(['changelog', command] + arguments)
        finally:
            os.chdir(old_cwd)

    def run_tool_w_output(self, command: str, arguments: List[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout):
            with redirect_stderr(stderr):
                rc = self.run_tool(command, arguments, cwd=cwd)
        return rc, stdout.getvalue(), stderr.getvalue()

    def _get_current_state(self) -> Tuple[Set[str], Dict[str, bytes]]:
        created_dirs: Set[str] = set()
        created_files: Dict[str, bytes] = dict()
        for dirpath, _, filenames in os.walk(self.paths.base_dir):
            created_dirs.add(dirpath)
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                with open(path, 'rb') as f:
                    data = f.read()
                created_files[path] = data
        return created_dirs, created_files

    def _rel_path(self, path: str) -> str:
        return os.path.normpath(os.path.relpath(path, self.paths.base_dir))

    def diff(self) -> Differences:
        result = Differences()
        created_dirs, created_files = self._get_current_state()

        result.added_dirs = [
            self._rel_path(path)
            for path in sorted(created_dirs - self.created_dirs)
        ]
        result.removed_dirs = [
            self._rel_path(path)
            for path in sorted(self.created_dirs - created_dirs)
        ]
        result.added_files = [
            self._rel_path(path)
            for path in sorted(created_files.keys() - self.created_files.keys())
        ]
        result.removed_files = [
            self._rel_path(path)
            for path in sorted(self.created_files.keys() - created_files.keys())
        ]
        result.file_contents = {
            self._rel_path(path): content
            for path, content in created_files.items()
        }
        result.file_differences = {
            self._rel_path(path): (self.created_files[path], created_files[path])
            for path in self.created_files.keys() & created_files.keys()
            if self.created_files[path] != created_files[path]
        }
        result.changed_files = sorted(result.file_differences.keys())

        self.created_dirs = created_dirs
        self.created_files = created_files

        result.dump()
        return result

    def _create_ansible_doc_list(self,
                                 plugin_data: Dict[str, Dict[str, Any]],
                                 plugin_type: str) -> Dict[str, Any]:
        if plugin_type == 'role':
            # Role listing works differently
            result = dict()
            for role, role_data in plugin_data[plugin_type].items():
                result[role] = {
                    'collection': role_data['collection'],
                    'entry_points': {
                        ep: ep_data.get('short_description')
                        for ep, ep_data in role_data['entry_points'].items()
                    }
                }
            return result
        return {
            plugin_name: plugin_data.get('short_description')
            for plugin_name, plugin_data in plugin_data[plugin_type].items()
        }

    def _create_ansible_doc_info(self,
                                 plugin_data: Dict[str, Dict[str, Any]],
                                 plugin_type: str,
                                 plugin_names: List[str],
                                 base_dir: str) -> Dict[str, Any]:
        result = dict()
        for plugin_name in plugin_names:
            doc = plugin_data[plugin_type][plugin_name].copy()
            if 'doc' in doc and 'filename' in doc['doc']:
                doc['doc'] = doc['doc'].copy()
                doc['doc']['filename'] = os.path.join(base_dir, doc['doc']['filename'])
            if 'path' in doc:
                doc['path'] = os.path.join(base_dir, doc['path'])
            result[plugin_name] = doc
        return result


class AnsibleChangelogEnvironment(ChangelogEnvironment):
    """
    Ansible changelog environment.
    """

    def __init__(self, base_path: pathlib.Path):
        super().__init__(base_path,
                         PathsConfig.force_ansible(base_dir=str(base_path)))
        self.mkdir(os.path.join(self.paths.base_dir, 'lib', 'ansible', 'modules'))
        self.mkdir(os.path.join(self.paths.base_dir, 'lib', 'ansible', 'plugins'))

    def _plugin_base(self, plugin_type):
        if plugin_type == 'module':
            return ['lib', 'ansible', 'modules']
        return ['lib', 'ansible', 'plugins', plugin_type]

    def create_fake_subprocess_ansible_doc(self, plugin_data: Dict[str, Dict[str, Any]]
                                           ) -> Callable[[List[str]], str]:
        def fake_subprocess_ansible_doc(command: List[str]) -> str:
            if command[0].endswith('ansible-doc') and command[1] == '--version':
                return _ANSIBLE_DOC_VERSION_TEMPLATE.format(
                    ansible_core_version=self.ansible_core_version,
                ).encode('utf-8')
            if command[0].endswith('ansible-doc') and command[1] == '--json' and command[2] == '-t':
                plugin_type = command[3]
                args = command[4:]
                do_list = False
                if args[0] == '--list':
                    do_list = True
                    args = args[1:]
                if do_list:
                    if args:
                        raise Exception('Unexpected list commands: {0}'.format(args))
                    result = self._create_ansible_doc_list(plugin_data, plugin_type)
                else:
                    result = self._create_ansible_doc_info(plugin_data, plugin_type, args, self.paths.base_dir)
                return json.dumps(result).encode('utf-8')
            raise Exception('Unexpected command: {0}'.format(command))

        return fake_subprocess_ansible_doc


class CollectionChangelogEnvironment(ChangelogEnvironment):
    """
    Collection changelog environment.
    """

    namespace: str
    collection: str
    collection_name: str

    def __init__(self, base_path: pathlib.Path, namespace: str, collection: str):
        collection_path = base_path / 'ansible_collections' / namespace / collection
        collection_path.mkdir(parents=True, exist_ok=True)
        super().__init__(base_path,
                         PathsConfig.force_collection(base_dir=str(collection_path)))
        self.namespace = namespace
        self.collection = collection
        self.collection_name = '{0}.{1}'.format(namespace, collection)

    def set_galaxy(self, data: Any):
        data = dict(data)
        if 'namespace' not in data:
            data['namespace'] = self.namespace
        if 'name' not in data:
            data['name'] = self.collection
        galaxy_path = os.path.join(self.paths.base_dir, 'galaxy.yml')
        self._write_yaml(galaxy_path, data)
        self.paths.galaxy_path = galaxy_path

    def create_fake_subprocess_ansible_doc(self, plugin_data: Dict[str, Dict[str, Any]]
                                           ) -> Callable[[List[str]], str]:
        def fake_subprocess_ansible_doc(command: List[str]) -> str:
            base_dir = self.paths.base_dir
            if command[0].endswith('ansible-doc') and command[1] == '--version':
                return _ANSIBLE_DOC_VERSION_TEMPLATE.format(
                    ansible_core_version=self.ansible_core_version,
                ).encode('utf-8')
            if command[0].endswith('ansible-doc') and command[1] == '--json' and command[2] == '-t':
                plugin_type = command[3]
                args = command[4:]
                do_list = False
                if args[0] == '--list':
                    do_list = True
                    args = args[1:]
                if args[0] == '--playbook-dir':
                    base_dir = os.path.join(
                        args[1],
                        'collections',
                        'ansible_collections',
                        self.namespace,
                        self.collection,
                    )
                    args = args[2:]
                if do_list:
                    if len(args) and args[0] == self.collection_name:
                        args = args[1:]
                    if args:
                        raise Exception('Unexpected list commands: {0}'.format(args))
                    result = self._create_ansible_doc_list(plugin_data, plugin_type)
                else:
                    result = self._create_ansible_doc_info(plugin_data, plugin_type, args, base_dir)
                return json.dumps(result).encode('utf-8')
            raise Exception('Unexpected command: {0}'.format(command))

        return fake_subprocess_ansible_doc

    def add_role(self, name, entry_points):
        role_meta_dir = os.path.join(self.paths.base_dir, 'roles', name, 'meta')
        self.mkdir(role_meta_dir)
        main = yaml.dump({
            'galaxy_info': {
                'role_name': name,
            },
            'dependencies': [],
        }, Dumper=yaml.SafeDumper).encode('utf-8')
        self._write(os.path.join(role_meta_dir, 'main.yml'), main)
        argspec = yaml.dump({
            'argument_specs': entry_points,
        }, Dumper=yaml.SafeDumper).encode('utf-8')
        self._write(os.path.join(role_meta_dir, 'argument_spec.yml'), argspec)


class OtherChangelogEnvironment(ChangelogEnvironment):
    """
    Other project changelog environment.
    """

    def __init__(self, base_path: pathlib.Path):
        super().__init__(base_path,
                         PathsConfig.force_other(base_dir=str(base_path)))
        self.config.title = 'A Random Project'


@pytest.fixture
def ansible_changelog(tmp_path_factory) -> AnsibleChangelogEnvironment:
    """
    Fixture for Ansible changelog environment.
    """
    return AnsibleChangelogEnvironment(tmp_path_factory.mktemp('changelog-test'))


@pytest.fixture
def collection_changelog(tmp_path_factory, namespace: str = 'acme',
                         collection: str = 'test') -> CollectionChangelogEnvironment:
    """
    Fixture for collection changelog environment.
    """
    base_path = tmp_path_factory.mktemp('changelog-test')
    collection_path_env = 'ANSIBLE_COLLECTIONS_PATHS'
    original_path = os.environ.get(collection_path_env)
    os.environ[collection_path_env] = str(base_path)
    yield CollectionChangelogEnvironment(base_path, namespace, collection)
    if original_path is None:
        del os.environ[collection_path_env]
    else:
        os.environ[collection_path_env] = original_path


def create_plugin(**parts):
    """
    Create plugin stub.
    """
    result = [
        '#!/usr/bin/python',
        '',
        'from __future__ import absolute_import, division, print_function',
        '__metaclass__ = type',
    ]

    for part, data in parts.items():
        if not isinstance(data, str):
            data = yaml.dump(data, Dumper=yaml.SafeDumper)
        result.extend(['', '{part} = {data!r}'.format(part=part, data=data)])

    return '\n'.join(result)


@pytest.fixture
def other_changelog(tmp_path_factory) -> OtherChangelogEnvironment:
    """
    Fixture for Ansible changelog environment.
    """
    return OtherChangelogEnvironment(tmp_path_factory.mktemp('changelog-test'))
