# Author: Javad Amirian
# Email: amiryan.j@gmail.com

import time
import yaml
import numpy as np
from math import cos, sin, sqrt
from poisson_distribution import PoissonDistribution

from crowdrep_bot.scenarios.corridor_scenario import CorridorScenario, Visualizer
from crowdrep_bot.scenarios.world import World
import crowdrep_bot.crowd_sim.crowdsim as crowdsim


class StaticCorridorScenario(CorridorScenario):
    """
    -> Crowd standing in groups of (2, 3, 4) persons, in a corridor.
    -> The inter-group distance is bigger than intra-group distances
    -> The leader passes the corridor among crowd
    """
    def __init__(self, corridor_wid=5, corridor_len=18):
        super(StaticCorridorScenario, self).__init__()
        self.corridor_wid = corridor_wid
        self.corridor_len = corridor_len


    def setup(self):
        ped_poss = []

        # Case 1: Manually arranged crowd
        # config_filename = '/home/cyrus/workspace2/ros-catkin/src/crowdrep_bot/config/repbot_sim/static_crowd_config.yaml'
        # with open(config_filename, 'r') as config_file:
        #     crowd_config = yaml.load(config_file, Loader=yaml.FullLoader)
        # for item, doc in crowd_config.items():
        #     if item == 'crowd':
        #         for ped in doc:
        #             ped_poss.append([ped['ped']['pos_x'], ped['ped']['pos_y']])

        # Case 2: Randomly select group centers
        # add multiple groups [2, 3, 4, 5]
        # accum_n_peds = 0
        # group_sizes = []
        # while accum_n_peds < self.n_peds - 2:
        #     rand_group_size = np.random.random_integers(2, 5)
        #     while (accum_n_peds + rand_group_size) > self.n_peds:
        #         rand_group_size -= 1  # modify the random number so that accumulated number exactly match self.n_peds
        #     group_sizes.append(rand_group_size)
        #     accum_n_peds += rand_group_size

        # draw multiple locations as center of each group
        poisson_distrib = PoissonDistribution((self.corridor_len - self.ped_radius * 4,
                                               self.corridor_wid - self.ped_radius * 4),
                                              minDist=3, k=50)
        group_centers = poisson_distrib.create_samples() + self.ped_radius * 2  # margin

        # for each group: assign a random number in {2, 3, 4} as group size
        group_sizes = np.random.random_integers(2, 4, len(group_centers))

        # for each group: put the group members on a circle in a uniform way
        # where the angle of the first person (wrt the horizon line) is a random number
        for gg, g_size in enumerate(group_sizes):
            px_g = group_centers[gg][0]
            py_g = group_centers[gg][1]
            group_radius = self.ped_radius * sqrt(g_size)

            rotation = np.random.uniform(0, np.pi)
            for ii in range(g_size):
                px_i = px_g + cos(rotation + (ii / g_size) * np.pi * 2) * group_radius
                py_i = py_g + sin(rotation + (ii / g_size) * np.pi * 2) * group_radius
                ped_poss.append([px_i, py_i])

        # Set the position of Leader agent
        # ped_poss.insert(0, [1, self.corridor_wid/2])

        self.n_peds = len(ped_poss)  # the random algorithm may return a different number of agents than what is asked

        world_dim = [[0, self.corridor_len], [-self.corridor_len/2, self.corridor_len/2]]
        self.world = World(self.n_peds, self.n_robots, world_dim, biped_mode=False)
        self.world.sim.initSimulation(self.n_peds + 1)

        self.world.obstacles = self.world.sim.obstacles

        for ped_ind in range(len(ped_poss)):
            self.world.set_ped_position(ped_ind, ped_poss[ped_ind])
            self.world.set_ped_velocity(ped_ind, [0, 0])
            self.world.set_ped_goal(ped_ind, ped_poss[ped_ind])

        # Set the goal of Leader agent
        # self.world.set_ped_goal(0, [self.corridor_len, self.corridor_wid / 2])

        self.world.set_time(0)


    def step(self, dt, save=False):
        if not self.world.pause:
            self.world.sim.doStep(dt)
            for ii in range(self.n_peds):
                p_new = self.world.crowds[ii].pos
                self.world.set_ped_position(ii, p_new)
                self.world.set_ped_velocity(ii, np.zeros(2))
            self.step_robots(dt)

        super(StaticCorridorScenario, self).step(dt, save)

