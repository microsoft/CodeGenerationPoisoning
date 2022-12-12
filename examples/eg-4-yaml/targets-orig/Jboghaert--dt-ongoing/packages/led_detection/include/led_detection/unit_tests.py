import numpy as np
import duckietown_utils as dtu
from . import logger

__all__ = [
    'LEDDetectionUnitTest',
    'load_tests',
]

class LEDDetectionUnitTest():

    def __init__(self, data, query, expected):
        self.data = data
        self.query = query
        self.expected = expected

        query['frequencies_to_detect']
        query['min_distance_between_LEDs_pixels']


    def _get_images(self):
        filename = self.data['bag']
        interval = self.data['interval']
        t0, t1 = interval[0], interval[1]
        print('t0:%s, t1:%s'%(t0, t1))
        data = dtu.d8n_read_images_interval(filename, t0, t1)
        return data

    def get_query(self):
        """
        Returns a dictionary with fields equivalent
        to the signature of detect_led()

            images,
            mask,
            frequencies_to_detect,
            min_distance_between_LEDs_pixels
        """

        images = self._get_images()
        #mask = np.ones(dtype='bool', shape=images[0]['rgb'].shape)
        d = dict(images=images,
                 frequencies_to_detect=self.query['frequencies_to_detect'],
                 min_distance_between_LEDs_pixels=self.query['min_distance_between_LEDs_pixels'])
        return d

def LEDDetectionUnitTest_from_yaml(s):
    """
        Returns an instance of LEDDetectionUnitTest from YAML.
    """
    data = s['data']

    data['bag']
    data['interval']

    query = s['query']
    query['frequencies_to_detect']
    expected = s['expected']
    for e in expected:
        e['timestamp1']
        e['timestamp2']
        e['image_coordinates'] = tuple(e['image_coordinates'])
        e['image_coordinates_margin']
        e['frequency']
        #e['color']
        #e['color_tolerance']
        #e['confidence_min']

    return LEDDetectionUnitTest(data=data, query=query, expected=expected)

def load_tests(filename):
    """
        Reads tests from a YAML file.

        Returns a dict str -> LEDDetectionUnitTest() """
    import yaml
    with open(filename) as f:
        contents = yaml.load(f)

    for k, v in list(contents.items()):
        try:
            contents[k] = LEDDetectionUnitTest_from_yaml(v)
        except:
            logger.error('Error while reading:')
            logger.error(v)
            raise

    return contents

# example YAML:
#
# allblinking_test1-argo:
#     bag: 20160311-allblinking_test1-argo.bag
#    interval:
#         [0, 2]
#    query:
#
#       frequencies_to_detect:
#         [1.0, 3.0]
#     ground_truth:
#     # 1Hz white on left (Magitek)
#     - timestamp1: 0
#       timestamp2: 2
#       image_coordinates: [?, ?]
#       image_coordinates_margin: 5 # pixels
#       frequency: 1.0
#       color: [1,1,1]
#       color_tolerance: 0.1
#       confidence_min: 0.9
