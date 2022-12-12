# Copyright 2020 Google LLC
#
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

import collections

from flask import Blueprint
from flask import render_template

from cache import cache
from routes.api.place import child_fetch
from services.datacommons import fetch_data

# Define blueprint
bp = Blueprint(
    "placelist",
    __name__,
)


@bp.route('/placelist')
@cache.memoize(timeout=3600 * 24)  # Cache for one day.
def index():
    response = fetch_data('/node/property-values', {
        'dcids': ['Country'],
        'property': 'typeOf',
        'direction': 'in'
    },
                          compress=False,
                          post=True)
    countries = {'Country': []}
    for place in response['Country']['in']:
        countries['Country'].append({
            'dcid': place['dcid'],
            'name': place.get('name', place['dcid'])
        })
        countries['Country'].sort(key=lambda x: x['name'])
    return render_template('placelist.html', place_by_type=countries)


@bp.route('/placelist/<path:dcid>')
@cache.memoize(timeout=3600 * 24)  # Cache for one day.
def node(dcid):
    child_places = child_fetch(dcid)
    place_by_type = collections.defaultdict(list)
    for place_type, childs in child_places.items():
        for child in childs:
            for place_type in child.get('types', [""]):
                if not place_type.startswith('AdministrativeArea'):
                    place_by_type[place_type].append({
                        'dcid': child['dcid'],
                        'name': child['name']
                    })
                    break
    for place_type in place_by_type:
        place_by_type[place_type].sort(key=lambda x: x['name'])

    return render_template('placelist.html',
                           place_by_type=place_by_type,
                           dcid=dcid)
