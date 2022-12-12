from cubic_pose_spline import *
import yaml
import os

def loadCubicSpline(filename, traj_name):
    f = open(filename, 'r')
    dict_map = yaml.safe_load(f)
    f.close()
    traj_tpr = np.array(dict_map[traj_name])

    pt_num = len(traj_tpr)
    times = traj_tpr[:, 0]

    rotvecs = np.zeros([pt_num, 3])
    rotvecs[:,2] = traj_tpr[:, 3] / 180 * np.pi

    pts = np.zeros([pt_num, 3])
    pts[:,0:2] = traj_tpr[:, 1:3]

    spline = CubicPoseSpline(times, pts, R.from_rotvec(rotvecs))
    t_range = (times[0], times[-1])
    return spline, t_range

class Motion(object):
    def __init__(self, traj_name):
        traj_lib = os.path.dirname(os.path.abspath(__file__)) + '/traj_lib.yaml'
        self.spline, self.t_range = loadCubicSpline(traj_lib, traj_name)

