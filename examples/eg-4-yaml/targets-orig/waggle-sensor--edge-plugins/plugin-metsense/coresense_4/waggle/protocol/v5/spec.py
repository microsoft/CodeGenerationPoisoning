# ANL:waggle-license
# This file is part of the Waggle Platform.  Please see the file
# LICENSE.waggle.txt for the legal details of the copyright and software
# license.  For more details on the Waggle project, visit:
#          http://www.wa8.gl
# ANL:waggle-license
import yaml

from . import waggleprotocol_spec

def get_spec(spec_str):
    spec = {}
    contents = {}
    try:
        contents = yaml.load(spec_str, Loader=yaml.FullLoader)
    except:
        contents = yaml.load(spec_str)

    for packet in contents:
        assert 'conversion' in packet
        spec[packet['id']] = {}
        spec[packet['id']]['conversion'] = packet['conversion']
        params = packet['params']
        for param in params:
            assert 'name' in param
            assert 'length' in param
            assert 'format' in param
            # assert 'conversion' in param
        spec[packet['id']]['params'] = packet['params']
    return spec

spec = get_spec(waggleprotocol_spec.waggleprotocol_spec)
