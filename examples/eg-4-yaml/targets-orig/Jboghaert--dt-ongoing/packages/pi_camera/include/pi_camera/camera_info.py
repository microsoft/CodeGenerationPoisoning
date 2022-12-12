
'''
    Collecting all versions of load_camera_info...
'''
import os

import yaml

import duckietown_utils as dtu
from sensor_msgs.msg import CameraInfo


class NoCameraInfoAvailable(dtu.DTException):
    pass


class InvalidCameraInfo(dtu.DTException):
    pass


def get_camera_info_default():
    """ Returns a nominal CameraInfo """
    return get_camera_info_for_robot('default')


default_camera_info = """
image_width: 640
image_height: 480
camera_name: /shamrock/rosberrypi_cam
camera_matrix:
  rows: 3
  cols: 3
  data: [305.5718893575089, 0, 303.0797142544728, 0, 308.8338858195428, 231.8845403702499, 0, 0, 1]
distortion_model: plumb_bob
distortion_coefficients:
  rows: 1
  cols: 5
  data: [-0.2944667743901807, 0.0701431287084318, 0.0005859930422629722, -0.0006697840226199427, 0]
rectification_matrix:
  rows: 3
  cols: 3
  data: [1, 0, 0, 0, 1, 0, 0, 0, 1]
projection_matrix:
  rows: 3
  cols: 4
  data: [220.2460277141687, 0, 301.8668918355899, 0, 0, 238.6758484095299, 227.0880056118307, 0, 0, 0, 1, 0]

"""


@dtu.contract(robot_name=str, returns=CameraInfo)
def get_camera_info_for_robot(robot_name):
    """
        Returns a CameraInfo object for the given robot.

        This is in a good format to pass to PinholeCameraModel:

            self.pcm = PinholeCameraModel()
            self.pcm.fromCameraInfo(self.ci)

        The fields are simply lists (not array or matrix).

        Raises:

            NoCameraInfoAvailable  if no info available
            InvalidCameraInfo   if the info exists but is invalid
    """

    if robot_name == dtu.DuckietownConstants.ROBOT_NAME_FOR_TESTS:
        calib_data = dtu.yaml_load(default_camera_info)
    else:
        # find the file
        fn = get_camera_info_config_file(robot_name)

        # load the YAML

        calib_data = dtu.yaml_load_file(fn, plain_yaml=True)

    # convert the YAML
    try:
        camera_info = camera_info_from_yaml(calib_data)
    except InvalidCameraInfo as e:
        msg = 'Invalid data in file %s' % fn
        dtu.raise_wrapped(InvalidCameraInfo, e, msg)

    check_camera_info_sane_for_DB17(camera_info)

    return camera_info


def check_camera_info_sane_for_DB17(camera_info):
    """ Raises an exception if the calibration is way off with respect
        to platform DVB17 """

    # TODO: to write
    pass


@dtu.contract(calib_data=dict, returns=CameraInfo)
def camera_info_from_yaml(calib_data):
    try:
        cam_info = CameraInfo()
        cam_info.width = calib_data['image_width']
        cam_info.height = calib_data['image_height']
#         cam_info.K = np.matrix(calib_data['camera_matrix']['data']).reshape((3,3))
#         cam_info.D = np.matrix(calib_data['distortion_coefficients']['data']).reshape((1,5))
#         cam_info.R = np.matrix(calib_data['rectification_matrix']['data']).reshape((3,3))
#         cam_info.P = np.matrix(calib_data['projection_matrix']['data']).reshape((3,4))
        cam_info.K = calib_data['camera_matrix']['data']
        cam_info.D = calib_data['distortion_coefficients']['data']
        cam_info.R = calib_data['rectification_matrix']['data']
        cam_info.P = calib_data['projection_matrix']['data']

        cam_info.distortion_model = calib_data['distortion_model']
        return cam_info
    except Exception as e:
        msg = 'Could not interpret data:'
        msg += '\n\n' + dtu.indent(yaml.dump(calib_data), '   ')
        dtu.raise_wrapped(InvalidCameraInfo, e, msg)


def get_camera_info_config_file(robot_name):
    roots = [os.path.join(dtu.get_duckiefleet_root(), 'calibrations'),
             os.path.join(dtu.get_ros_package_path('duckietown'), 'config', 'baseline', 'calibration')]

    for df in roots:
    # Load camera information
        fn = os.path.join(df, 'camera_intrinsic', robot_name + '.yaml')
        fn_default = os.path.join(df, 'camera_intrinsic', 'default.yaml')
        if os.path.exists(fn):
            return fn
        elif os.path.exists(fn_default):
            return fn_default
        else:
            print('%s does not exist and neither does %s' % (fn, fn_default))

    msg = 'Cannot find intrinsic file for robot %r;\n%s' % (robot_name, roots)
    raise NoCameraInfoAvailable(msg)


# from cam_info_reader_node
def load_camera_info_2(filename):
    stream = file(filename, 'r')
    calib_data = yaml.load(stream)
    cam_info = CameraInfo()
    cam_info.width = calib_data['image_width']
    cam_info.height = calib_data['image_height']
    cam_info.K = calib_data['camera_matrix']['data']
    cam_info.D = calib_data['distortion_coefficients']['data']
    cam_info.R = calib_data['rectification_matrix']['data']
    cam_info.P = calib_data['projection_matrix']['data']
    cam_info.distortion_model = calib_data['distortion_model']
    return cam_info


# This one is used by the controllers...
def load_camera_info_3(robot):
    # Load camera information
    filename = (os.environ['DUCKIEFLEET_ROOT'] + "/calibrations/camera_intrinsic/" + robot + ".yaml")
    if not os.path.isfile(filename):
        dtu.logger.warn("no intrinsic calibration parameters for {}, trying default".format(robot))
        filename = (os.environ['DUCKIEFLEET_ROOT'] + "/calibrations/camera_intrinsic/default.yaml")
        if not os.path.isfile(filename):
            dtu.logger.error("can't find default either, something's wrong")
    calib_data = dtu.yaml_wrap.yaml_load_file(filename)
    cam_info = CameraInfo()
    cam_info.width = calib_data['image_width']
    cam_info.height = calib_data['image_height']
    cam_info.K = calib_data['camera_matrix']['data']
    cam_info.D = calib_data['distortion_coefficients']['data']
    cam_info.R = calib_data['rectification_matrix']['data']
    cam_info.P = calib_data['projection_matrix']['data']
    cam_info.distortion_model = calib_data['distortion_model']
    dtu.logger.info("Loaded camera calibration parameters for {} from {}".format(robot, os.path.basename(filename)))
    return cam_info
