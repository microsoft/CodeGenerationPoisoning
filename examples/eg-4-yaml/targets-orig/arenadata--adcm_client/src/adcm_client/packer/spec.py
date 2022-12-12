# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import sys
from os.path import join
from subprocess import check_output

import yaml

from .types import get_type_func


class SpecFile:
    def __init__(self, spec):
        try:
            with open(spec, 'r', encoding='utf-8') as file:
                self.data = yaml.safe_load(file)
                # TODO supported verions check
                self.current_version = self.version = str(self.data.get('version', 0))

        except FileNotFoundError:
            self.data = {}

    def to_1_0(self):
        new_spec = dict(
            [
                ('version', None),
                (
                    'editions',
                    [{'name': None, 'exclude': self.except_var(self.data), 'preprocessors': []}],
                ),
            ]
        )
        for i in self.data.get('processing', {}):
            if i.get('script'):
                new_spec['editions'][0]['preprocessors'].append(
                    {
                        'type': 'script',
                        'script': join(self.data[i['name'] + '_dir'], i['script']),
                        'args': [i['file']],
                    }
                )
            elif i.get('name') == 'python_mod_req':
                new_spec['editions'][0]['preprocessors'].append(
                    {'type': i['name'], 'requirements': i['file']}
                )
            else:
                sys.exit(f'Used unrecognized func:{i.get("name")}')
        return new_spec

    def normalize_spec(self):
        versions = ['1.0']
        migrations = dict([('1.0', self.to_1_0)])
        index = (
            versions.index(self.data.get('version')) + 1
            if self.data.get('version') in versions
            else 0
        )
        for i in versions[index:]:
            self.data = migrations[i]()
        self.current_version = versions[-1]
        return self.data

    def pop_edition(self, edition):
        if float(self.current_version) < 1.0:
            raise ValueError('Current spec version doent support editions')
        if not edition:
            return
        else:
            for e in self.data['editions'][:]:
                if e.get('name') == edition:
                    self.data['editions'] = [e]
                    break
            else:
                raise ValueError('setuped build edition is not present in spec file')

    # deprecated method. Needed for backward compatibility with old specs
    def except_var(self, config):
        tar_except = []
        for k, v in config.items():
            if '_dir' in k:
                tar_except.append(v)
        for k in config.get('processing', {}):
            if k.get('except_file', False):
                tar_except.append(k.get('file'))
        return tar_except


def spec_processing(spec: SpecFile, path, workspace, release_version):
    for edition in spec.data['editions']:
        if edition.get('preprocessors'):
            for x in edition['preprocessors']:
                if x.get('script'):
                    command = [x['script']]
                    if x.get('args'):
                        command.extend(x['args'])
                    logging.info(check_output(command, cwd=path[edition['name']]).decode("utf-8"))
                else:
                    if x['type'] == 'splitter':
                        params = {
                            'jinja_values': {
                                'edition': edition['name'],
                                'release_version': release_version,
                            }
                        }
                    else:
                        params = {}
                    get_type_func(x['type'])(path[edition['name']], workspace, **params, **x)
