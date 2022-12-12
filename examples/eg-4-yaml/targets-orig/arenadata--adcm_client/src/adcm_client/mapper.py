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
import os
import yaml
from .objects import ADCMClient


class ObjectNotFound(Exception):
    pass


class IncorrectOperation(Exception):
    pass


class Mapper:
    def __init__(self, filename, client: ADCMClient = None):
        self._filename = filename
        self._workdir = os.path.dirname(filename)
        os.chdir(self._workdir)
        self._client = client
        self._parse()
        self._vars = {}
        if client is not None:
            self._vars = {'external_adcm': client}

    def _parse(self):
        with open(self._filename, 'r', encoding='utf-8') as stream:
            self._data = yaml.safe_load(stream)

    def _do_rec(self, point):
        if point['object'] not in self._vars:
            raise ObjectNotFound
        object_var = self._vars[point['object']]
        if not hasattr(object_var, point['func']):
            raise IncorrectOperation
        function = getattr(object_var, point['func'])
        if not callable(function):
            raise IncorrectOperation
        self._vars[point['return']] = function(**point['args'])

    def do(self):
        for rec in self._data:
            self._do_rec(rec)
