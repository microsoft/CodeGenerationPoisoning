"""Classes and functions to easily set up robot demo scripts."""
import json
import os
import pathlib
import types

import yaml
from ament_index_python.packages import get_package_share_directory

import robot_interfaces
import robot_fingers


#: Default configurations for various robots.
#: Maps robot names to a tuple of
#:  1) the module defining the corresponding types for this robot,
#:  2) a function to create the backend, and
#:  3) the name of the configuration file
#:
#: This corresponds to the arguments of the :class:`Robot` class.
robot_configs = {
    "fingerone": (
        robot_interfaces.finger,
        robot_fingers.create_real_finger_backend,
        "finger.yml",
    ),
    "trifingerone": (
        robot_interfaces.trifinger,
        robot_fingers.create_trifinger_backend,
        "trifinger.yml",
    ),
    "fingeredu": (
        robot_interfaces.finger,
        robot_fingers.create_real_finger_backend,
        "fingeredu.yml",
    ),
    "trifingeredu": (
        robot_interfaces.trifinger,
        robot_fingers.create_trifinger_backend,
        "trifingeredu.yml",
    ),
    "fingerpro": (
        robot_interfaces.finger,
        robot_fingers.create_real_finger_backend,
        "fingerpro.yml",
    ),
    "trifingerpro": (
        robot_interfaces.trifinger,
        robot_fingers.create_trifinger_backend,
        "/etc/trifingerpro/trifingerpro.yml",
    ),
    "trifingerpro_default": (
        robot_interfaces.trifinger,
        robot_fingers.create_trifinger_backend,
        "trifingerpro.yml",
    ),
    "trifingerpro_calib": (
        robot_interfaces.trifinger,
        robot_fingers.create_trifinger_backend,
        "trifingerpro_for_calib.yml",
    ),
    "onejoint": (
        robot_interfaces.one_joint,
        robot_fingers.create_one_joint_backend,
        "onejoint.yml",
    ),
    "twojoint": (
        robot_interfaces.two_joint,
        robot_fingers.create_two_joint_backend,
        "twojoint.yml",
    ),
    "solo8": (
        robot_interfaces.solo_eight,
        robot_fingers.create_solo_eight_backend,
        "soloeight.yml",
    ),
}


def get_config_dir() -> pathlib.PurePath:
    """Get path to the configuration directory."""
    return pathlib.PurePath(
        get_package_share_directory("robot_fingers"),
        "config",
    )


class Robot:
    @classmethod
    def create_by_name(cls, robot_name: str, logger_buffer_size: int = 0):
        """Create a ``Robot`` instance for the specified robot.

        Args:
            robot_name:  Name of the robots.  See
            :meth:`Robot.get_supported_robots` for a list of supported robots.
            logger_buffer_size:  See :meth:`Robot.__init__`.

        Returns:
            Robot: A ``Robot`` instance for the specified robot.
        """
        return cls(
            *robot_configs[robot_name], logger_buffer_size=logger_buffer_size
        )

    @staticmethod
    def get_supported_robots():
        """Get list of robots supported by ``create_by_name``.

        Returns:
            List of supported robot names.
        """
        return robot_configs.keys()

    def __init__(
        self,
        robot_module,
        create_backend_function,
        config,
        logger_buffer_size=0,
    ):
        """Initialize the robot environment (backend and frontend).

        :param robot_module: The module that defines the robot classes (i.e.
            `Data`, `Frontend`, `Backend`, ...)
        :param create_backend_function: Function to create the robot backend.
        :param config: Either a config object or a path to a config file.
            In the latter case, paths need to be absolute or relative to the
            config directory of the robot_fingers package.
        :param logger_buffer_size: Size of the buffer used by the logger.
            Default is 0.  Set this to at least the expected number of time
            steps when using the logger.
        """
        # convenience mapping of the Action type
        self.Action = robot_module.Action

        try:
            config = os.fspath(get_config_dir() / config)
        except TypeError:
            # if os.fspath failed with TypeError, assume that config is already
            # a config object
            self.config = config
        else:
            # if it didn't fail, self.config is not yet set, so load the config
            # from the file and save it.
            with open(config, "r") as f:
                config_dict = yaml.safe_load(f)

            # In the except case, self.config is expected to be a *FingerConfig
            # object where elements can be accessed as attributes.  Loading
            # from yaml gives a dictionary, so to be consistent, it needs to be
            # converted to a structure that allows access via attributes.
            # Unfortunately, there doesn't seem to be a nice solution to do
            # this with _nested_ dictionaries.  The easiest I could find (that
            # does not need thrid-party packages) is to serialise and
            # deserialise with json (see https://stackoverflow.com/a/63389458).
            self.config = json.loads(
                json.dumps(config_dict),
                object_hook=lambda d: types.SimpleNamespace(**d),
            )

        # Storage for all observations, actions, etc.
        self.robot_data = robot_module.SingleProcessData()

        # The backend sends actions from the data to the robot and writes
        # observations from the robot to the data.
        self.backend = create_backend_function(self.robot_data, config)

        #: The frontend is used to send actions and get observations.
        self.frontend = robot_module.Frontend(self.robot_data)

        #: The logger can be used to log robot data to a file
        self.logger = robot_module.Logger(self.robot_data, logger_buffer_size)

    def initialize(self):
        """Initialize the robot."""
        # Initializes the robot (e.g. performs homing).
        self.backend.initialize()


def demo_print_position(robot):
    """Send zero-torque commands to the robot and print the joint positions.

    :param robot: The robot environment.
    :type robot: Robot
    """
    action = robot.Action()
    print("\nPosition:")
    while True:
        t = robot.frontend.append_desired_action(action)
        pos = robot.frontend.get_observation(t).position
        n_joints = len(pos)
        format_string = "\r" + ", ".join(["{: 6.3f}"] * n_joints)
        print(format_string.format(*pos), end="")
