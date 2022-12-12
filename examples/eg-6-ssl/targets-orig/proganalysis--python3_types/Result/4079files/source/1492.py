#!/usr/bin/env python3

__version__ = "1.4"

import dugong
import hug

import asyncio
import atexit
from datetime import datetime
import gzip
import json
import shlex
import shutil
import sqlite3
import ssl
import subprocess
from tempfile import NamedTemporaryFile as NamedTemp
import time
import urllib.request
from xml.etree import ElementTree

QUERY = """
  WITH nodes_attrs AS
       (SELECT node_id, json_group_object(k, v) AS attributes
          FROM osm_node_tags
         GROUP BY node_id),
       ways_attrs AS
       (SELECT way_id, json_group_object(k, v) AS attributes
          FROM osm_way_tags
         GROUP BY way_id),
       ways_lines AS
       (SELECT way_id, MakeLine(Geometry) AS Geometry
          FROM osm_way_refs
               JOIN osm_nodes
               ON osm_nodes.node_id = osm_way_refs.node_id
         GROUP BY way_id)
SELECT json_object(
         'type', 'FeatureCollection',
         'features', json_group_array(json_object(
             'geometry', json(asGeoJSON(Geometry)),
             'type', 'Feature',
             'properties', json_object(
               'uid', uid,
               'user', user,
               'id', id,
               'timestamp', timestamp,
               'version', version,
               'attributes', json(attributes)))))
  FROM
  (SELECT osm_nodes.node_id AS id, uid, user,
          timestamp, version, Geometry, attributes
     FROM nodes_attrs
          INNER JOIN osm_nodes
          ON osm_nodes.node_id = nodes_attrs.node_id
    WHERE MbrWithin(Geometry, BuildMbr(?, ?, ?, ?))
    UNION ALL
   SELECT ways_lines.way_id, uid, user,
          timestamp, version, Geometry, attributes
     FROM ways_lines
          JOIN osm_ways
          ON ways_lines.way_id = osm_ways.way_id
          LEFT JOIN ways_attrs
          ON ways_lines.way_id = ways_attrs.way_id
    ORDER BY timestamp DESC)
"""

SERVER = "api.openstreetmap.org"
PROTOCOL, PORT = "https://", 443
REQUEST_TEMPLATE = PROTOCOL+SERVER+"/api/0.6/map?bbox={minx},{miny},{maxx},{maxy}"
HISTORY_TEMPLATE = "/api/0.6/{}/{}/history"
COMMAND_TEMPLATE = "spatialite_osm_raw -o {} -d {}"
CACHE_REFRESH = 60*60*24

executable = COMMAND_TEMPLATE.split()[0]
if not shutil.which(executable):
    raise FileNotFoundError("{} is missing".format(executable))

# https://pythonhosted.org/dugong/tutorial.html#pipelining-with-coroutines
# https://pythonhosted.org/dugong/tutorial.html#ssl-connections
def pipeline(hostname, port, path_list, headers={}):
    loop = asyncio.get_event_loop()
    atexit.register(loop.close)
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ssl_context.options |= ssl.OP_NO_SSLv2
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.set_default_verify_paths()
    with dugong.HTTPConnection(hostname, port, ssl_context=ssl_context) as conn:
        def send_requests():
            for path in path_list:
                yield from conn.co_send_request('GET', path, headers=headers)
        def read_responses():
            bodies = []
            for path in path_list:
                resp = yield from conn.co_read_response()
                assert resp.status == 200
                buf = yield from conn.co_readall()
                bodies.append(buf)
            return bodies
        send_crt = send_requests()
        recv_crt = read_responses()
        send_future = dugong.AioFuture(send_crt, loop=loop)
        recv_future = dugong.AioFuture(recv_crt, loop=loop)
        loop.run_until_complete(recv_future)
        bodies = recv_future.result()
        return bodies

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

def generateHeaders(referer):
    return {
        "User-Agent":"Is-OSM-uptodate/%s" % __version__,
        "Referer":referer,
        "Accept-Encoding":"gzip",
    }

def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError

@hug.get('/api/getDataMinimal')
def getDataMinimal(
        minx: hug.types.float_number,
        miny: hug.types.float_number,
        maxx: hug.types.float_number,
        maxy: hug.types.float_number,
        referer="http://localhost:8000/"):
    if type(referer) is not str:
        referer = referer.headers.get('REFERER')
    with NamedTemp() as db, NamedTemp(suffix='.osm') as osm:
        customRequest = urllib.request.Request(
            REQUEST_TEMPLATE.format(**locals()),
            headers=generateHeaders(referer))
        with urllib.request.urlopen(customRequest) as response:
            gzipFile = gzip.GzipFile(fileobj=response)
            shutil.copyfileobj(gzipFile, osm)
        osm.flush()
        command = shlex.split(COMMAND_TEMPLATE.format(osm.name, db.name))
        subprocess.run(command, stdout=subprocess.DEVNULL, check=True)
        with sqlite3.connect(db.name) as conn:
            conn.enable_load_extension(True)
            conn.load_extension('mod_spatialite')
            cursor = conn.cursor()
            cursor.execute(QUERY, (minx, miny, maxx, maxy))
            result = json.loads(cursor.fetchone()[0])
    return result

featuresTime = time.time()
features = {}

@hug.cli()
@hug.get('/api/getData')
def getData(
        minx: hug.types.float_number,
        miny: hug.types.float_number,
        maxx: hug.types.float_number,
        maxy: hug.types.float_number,
        referer="http://localhost:8000/"):
    global features, featuresTime
    if type(referer) is not str:
        referer = referer.headers.get('REFERER')
    args = [minx, miny, maxx, maxy]
    result = getDataMinimal(*args, referer=referer)
    urls = []
    if time.time()-featuresTime > CACHE_REFRESH:
        featuresTime = time.time()
        features = {}
    for feature in result['features']:
        if feature['geometry']['type'] == 'Point':
            osmType = 'node'
        else:
            osmType = 'way'
        feature_id = feature['properties']['id']
        if feature_id in features:
            continue
        if feature['properties']['version'] > 1:
            urls.append(HISTORY_TEMPLATE.format(osmType, feature_id))
    responses = []
    for chunk in chunks(urls, 100):
        responses.extend(pipeline(SERVER, PORT, chunk, generateHeaders(referer)))
    for response in responses:
        tree = ElementTree.XML(response.decode('utf8'))
        users = set()
        osmType = 'way' if tree.find('way') else 'node'
        for feature in tree.findall(osmType):
            users.add(feature.get('user'))
        feature_id =  int(tree.find(osmType).get('id'))
        created = tree.find(osmType).get('timestamp')
        features[feature_id] = {
            'created':created,
            'users':users,
            'contributors':len(users),
        }
    for feature in result['features']:
        feature_id = feature['properties']['id']
        if feature['properties']['version'] > 1:
            feature['properties'].update(features[feature_id])
        else:
            feature['properties'].update({
                'created':feature['properties']['timestamp'],
                'users':[feature['properties']['user']],
                'contributors':1,
            })
        created = feature['properties']['created']
        feature['properties']['average_update_days'] = (
                datetime.now()-
                datetime.fromisoformat(created.rstrip('Z'))
            ).days/feature['properties']['version']
    return result

if __name__ == '__main__':
    getData.interface.cli()
