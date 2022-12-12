import numpy as np
import yaml
import os
from cl_rocket import CLRocket
import pyopencl.array as cl_array

def polygonToLineSegments(polygons):
    """
    Parameters
    ----------
    polygons : list of polygon
        polygon is represented as np.array with shape (N, 2)
    
    Returns
    -------
    segments: array_like, shape (M, 2, 2)
    """
    segments = []
    for poly in polygons:
        for i in range(len(poly)):
            segments.append(np.array([poly[i-1], poly[i]]))
    return np.array(segments, dtype=np.float64)

def loadPolygonMap(filename, map_name):
    f = open(filename, 'r')
    dict_map = yaml.safe_load(f)
    f.close()
    return polygonToLineSegments(dict_map[map_name])


class PolygonMap(object):
    def __init__(self, map_name):
        filename = os.path.dirname(os.path.abspath(__file__)) + '/map_lib.yaml'
        self.segments = loadPolygonMap(filename, map_name)
        rkt = CLRocket.ins()
        self.seg_num = len(self.segments)
        self.seg_dev = cl_array.to_device(rkt.queue, self.segments)
        self.eqt_dev = cl_array.zeros(rkt.queue, (self.seg_num * 4, ) , np.float64)
        rkt.prg['particle_filter'].lineEquationFromPointPairs( \
            rkt.queue, (self.seg_num, ), None, \
            self.seg_dev.data, self.eqt_dev.data)
        

if __name__ == "__main__":
    map_lib = os.path.dirname(os.path.abspath(__file__)) + '/map_lib.yaml'
    poly_map = PolygonMap(map_lib, 'basic')
    print(poly_map.seg_dev.get())
    print(poly_map.eqt_dev.get().reshape([-1, 4]))
