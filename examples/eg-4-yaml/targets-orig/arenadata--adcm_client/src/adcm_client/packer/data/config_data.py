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
import fnmatch
import glob
import io
import re
import tarfile

import requests
import yaml
from git import Git


# TO DO: Exeptions - non valid methods calls when required property is None
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
class ConfigData:
    def __init__(
        self, git: Git = None, file=None, data=None, catalog=None, branch=None, tar=None, url=None
    ):
        self.url = url
        self.tar = tar
        self.file = file
        self.data = data
        self.branch = branch
        self.remote_file = None
        self.catalog = catalog
        self.git = git
        self.switch = {
            'data': self._from_data,
            'url': self._from_url,
            'tar': self._from_tar,
            'file': self._from_file,
            'catalog': self._from_fs,
            'branch': self._from_remote_git,
        }

    def get_data(self, key, provider, **kwargs):
        """Interface to get value of requested key from bundle config

        :param key: request key
        :type key: str
        :param provider: supported providers: data(dict), url, tar, file, catalog, branch
        :type provider: str
        :return: requsted keys
        """
        return self.switch[provider](key, **kwargs)

    def _from_file(self, key, **kwargs):
        with open(self.file, 'r', encoding='utf-8') as file:
            self.data = yaml.safe_load(file)
        return self._from_data(key)

    def _from_data(self, key, **kwargs):
        try:
            values = [
                entry.get(key)
                for entry in self.data
                if (
                    entry.get('type') == 'cluster'
                    or entry.get('type') == 'provider'
                    or entry.get('type') == 'host'
                )
            ]
        except (TypeError, AttributeError):
            values = [
                entry[1].get(key)
                for entry in self.data.items()
                if (entry[0] == 'cluster' or entry[0] == 'host' or entry[0] == 'provider')
            ]
        for val in values:
            if val:
                values[0] = val
        return values[0]

    # get bundle version
    def _from_fs(self, key, **kwargs):
        # find config file

        regex = "/**/config.y*ml" if kwargs.get('explict_raw', False) else "/**/*config.y*ml"
        configs = glob.glob(str(self.catalog) + regex, recursive=True)

        # version detection
        value = None
        for conf in configs:
            try:
                self.file = conf
                value = self._from_file(key)
                break
            except IndexError:
                pass

        return value

    def _from_remote_git(self, key, **kwargs):
        # using ./*config* patern dont work, func is usig metasymbol as is
        configs = [
            config
            for config in self.git.ls_tree('-r', '--name-only', self.branch).splitlines()
            if re.match('.*config.y.*ml', config)
        ]
        value = None
        for conf in configs:
            try:
                self.remote_file = conf
                self.data = yaml.safe_load(self.git.show(f"{self.branch}:{conf}"))
                value = self._from_data(key)
            except IndexError:
                pass
        return value

    def _from_tar(self, key, **kwargs):
        def conf_files(members):
            for tarinfo in members:
                if fnmatch.fnmatch(tarinfo.name, '*config.y*ml'):
                    yield tarinfo

        if isinstance(self.tar, str):
            conditions = {'name': self.tar}
        else:
            conditions = {'fileobj': self.tar}

        with tarfile.open(**conditions) as tar:
            confs = conf_files(tar)

            value = None

            for conf in confs:
                try:
                    self.file = conf
                    self.data = yaml.safe_load(tar.extractfile(conf).read().decode('utf-8'))
                    value = self._from_data(key)
                    break
                except IndexError:
                    pass
        return value

    def _from_url(self, key, **kwargs):
        response = requests.get(url=self.url)
        response.raise_for_status()
        self.tar = io.BytesIO(response.content)
        return self._from_tar(key)
