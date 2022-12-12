# Author: Javad Amirian
# Email: amiryan.j@gmail.com

import os
import re
import yaml
import numpy as np

from crowdrep_bot.util.basic_geometry import Line
from crowdrep_bot.scenarios.real_scenario import RealScenario
from toolkit.core.trajdataset import TrajDataset
from toolkit.loaders.loader_hermes import load_bottleneck
from toolkit.loaders.loader_eth import load_eth


class HumanTrajectoryScenario(RealScenario):
    """
    Class for replaying Hermes (Bottleneck) Crowd Experiments
    """
    def __init__(self):
        super(HumanTrajectoryScenario, self).__init__()

    def setup_with_config_file(self, config_file, **kwargs):
        """
        :param config_file: address to config file which contains scenario parameters
        :param kwargs: you can override the parameters in the config file , by passing them directly
        :return:
        """
        with open(config_file) as stream:
            config = yaml.load(stream, Loader=yaml.FullLoader)
            biped_mode = config['General']['biped_mode']
            # opentraj_root = config['Dataset']['OpenTrajRoot']
            robot_replacement_id = config['Dataset']['RobotId']
            obstacles = config['Dataset']['Obstacles']
            fps = config['Dataset']['fps']
            annotation_file = config['Dataset']['Annotation']
            title = config['Dataset']['Title'] if 'Title' in config['Dataset'] else ''
            parser_type = config['Dataset']['Parser']
            if parser_type == "ParserETH":
                dataset = load_eth(annotation_file, title=title, use_kalman=False)
                dataset.interpolate_frames(inplace=True)
            elif parser_type == "ParserHermes":
                dataset = load_bottleneck(annotation_file, title=title)
            self.video_files = config['Dataset']['Video']
            world_boundary = []
            if 'WorldBoundary' in config['Dataset']:
                world_x_min = config['Dataset']['WorldBoundary']['x_min']
                world_x_max = config['Dataset']['WorldBoundary']['x_max']
                world_y_min = config['Dataset']['WorldBoundary']['y_min']
                world_y_max = config['Dataset']['WorldBoundary']['y_max']
                world_boundary = [[world_x_min, world_x_max], [world_y_min, world_y_max]]

        # override parameters by direct arguments
        self.title = kwargs.get("title", title)
        dataset = kwargs.get("dataset", dataset)
        fps = kwargs.get("fps", fps)
        robot_replacement_id = kwargs.get("robot_id", robot_replacement_id)
        biped_mode = kwargs.get("biped_mode", biped_mode)

        self.setup(dataset=dataset, fps=fps, robot_id=robot_replacement_id, biped_mode=biped_mode,
                   obstacles=obstacles, world_boundary=world_boundary)

    def setup(self, **kwargs):
        self.dataset = kwargs.get("dataset", None)
        self.title = kwargs.get("title", "")
        self.fps = kwargs.get("fps", 16)
        self.robot_replacement_id = kwargs.get("robot_id", -1)
        biped_mode = kwargs.get("biped_mode", False)

        world_boundary = kwargs.get("world_boundary", [])
        if not len(world_boundary):
            x_min = self.dataset.data["pos_x"].min()
            x_max = self.dataset.data["pos_x"].max()
            y_min = self.dataset.data["pos_y"].min()
            y_max = self.dataset.data["pos_y"].max()
            world_boundary = [[x_min, x_max], [y_min, y_max]]

        self.create_sim_frames(biped_mode=biped_mode, world_boundary=world_boundary)

        # Any obstacle?
        obstacles = kwargs.get("obstacles", [])
        for obs in obstacles:
            self.world.add_obstacle(Line(obs[0:2], obs[2:4]))

    def step_crowd(self, dt):
        raise Exception("Not implemented")


if __name__ == "__main__":
    import matplotlib
    import matplotlib.pyplot as plt
    matplotlib.use('TkAgg')

    scenario = HumanTrajectoryScenario()
    conf_file = os.path.abspath(os.path.join(__file__, "../../../..", "config/repbot_sim/real_scenario_config.yaml"))
    scenario.setup_with_config_file(conf_file)
    [xdim, ydim] = scenario.world.world_dim

    pause = np.zeros(1, dtype=int)
    t = -1
    while t < len(scenario.frames):
        plt.cla()
        plt.xlim(xdim)
        plt.ylim(ydim)
        ped_poss_t = scenario.ped_poss[t]
        ped_poss_t = ped_poss_t[ped_poss_t[:, 0] > -100]
        robot_pos_t = scenario.robot_poss[t]

        plt.scatter(ped_poss_t[:, 0], ped_poss_t[:, 1], color='g')
        plt.scatter(robot_pos_t[0], robot_pos_t[1], color='r')

        plt.gcf().canvas.mpl_connect('key_release_event',
                                     lambda event: [pause.fill(1-pause[0]) if event.key == ' ' else None])

        if not pause[0]:
            t += 1
        plt.pause(0.01)


    plt.show()
