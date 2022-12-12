# ANL:waggle-license
# This file is part of the Waggle Platform.  Please see the file
# LICENSE.waggle.txt for the legal details of the copyright and software
# license.  For more details on the Waggle project, visit:
#          http://www.wa8.gl
# ANL:waggle-license
from binascii import unhexlify
from format import unpack
from packet import decode_packet
import yaml
import logging

logger = logging.getLogger('coresense.decoder')


def identity(x):
    return x


def tmp112(x):
    return 2*x - 1


def htu21d_humidty(x):
    return 100 * x


with open('spec.yml') as f:
    sensors = yaml.load(f.read())


formatnames = {
    'macaddr': 3,
}


for sensor in sensors:
    sensor['name'] = sensor['name'].lower()

    # translate format names
    for param in sensor['params']:
        if isinstance(param['format'], str):
            param['format'] = formatnames[param['format']]

    sensor['format'] = ''.join(str(param['format']) for param in sensor['params'])

    for param in sensor['params']:
        param['calc'] = globals()[param.get('calc', 'identity')]


sensors_by_id = dict((sensor['id'], sensor) for sensor in sensors)
