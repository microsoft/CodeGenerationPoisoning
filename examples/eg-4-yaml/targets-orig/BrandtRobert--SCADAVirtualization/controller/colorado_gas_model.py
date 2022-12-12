import time
import yaml
import sys
import re
from model.logger import Logger
from typing import Dict
from controller.sensorbus import SensorBus
from controller.controlgraph import ControlGraph


class ColoradoGasModel:

    def __init__(self, conf: Dict):
        self.sensor_bus = SensorBus(conf)
        self.worker_info = {}
        self.logger = Logger("ActorLogs", "../model/logger/logs/actors_logs.txt")
        self._init_worker_info(conf)
        self.control_graph = ControlGraph()

    def _init_worker_info(self, conf):
        for plc, info in conf.items():
            for worker, worker_info in info['workers'].items():
                self.worker_info[plc + '.' + worker] = worker_info

    def begin_control_loop(self):
        while True:
            time.sleep(.2)
            sensors = self.sensor_bus.get_sensor_readings()
            sim_time = \
                int(sensors['oracle'][self.worker_info['oracle.timer']['register']])

            if sim_time == 0:
                # Sim not started yet
                continue
            else:
                self.sensor_bus.start_collecting_data = True
            if sim_time >= 259200:
                # Simulation has ended
                break

            def iterate_leaves(leaves, p_nominal=800, p_max=60, p_min=5, dead_band=25):
                updates = []
                non_ds = re.compile('ds*')
                for leaf in leaves:
                    if non_ds.match(leaf):
                        continue
                    pressure_register = self.worker_info[leaf + '.pressure_sensor']['register']
                    pressure_reading = sensors[leaf][pressure_register]
                    # Outside of dead band
                    successors = self.control_graph.get_predecessors(leaf)
                    if abs(pressure_reading - p_nominal) > dead_band:
                        pressure_differential = p_nominal - pressure_reading
                        piecewise_pressures = pressure_differential / len(successors)
                        power_adjustment = piecewise_pressures / 25
                    else:
                        power_adjustment = -5
                    for s in successors:
                        if s == 'cheyenne':
                            continue
                        setting_register = self.worker_info[s + '.power_setter']['register']
                        current_setting = sensors[s][setting_register]
                        # print("Current power setting", s, current_setting)
                        # new_setting = min(p_max, max(p_min, current_setting + piece_wise_adjustment * adjust_ratio))
                        new_setting = min(p_max, max(p_min, current_setting + power_adjustment))
                        update = (s, setting_register, round(new_setting))
                        updates.append(update)
                return updates

            # actuator_updates = iterate_leaves(['ds_trindad', 'ds_springfield'])
            exp = re.compile('compressor*')
            compressors = [n for n in self.control_graph.graph.nodes if exp.match(n)]
            compressor_updates = iterate_leaves(compressors)
            pp_updates = iterate_leaves(self.control_graph.get_leaf_nodes())
            print(sim_time, pp_updates, compressor_updates)
            self.sensor_bus.update_actuators(pp_updates + compressor_updates)

        print("Attempting to graph results....")
        data_collector = self.sensor_bus.get_data_collector()

        '''
            Fort Collins Compromise
        '''
        # data_collector.add_to_plot('pp_fort_collins.pressure_sensor', 'oracle.timer')
        # data_collector.add_to_plot('oracle.fort_collins_true_pressure', 'oracle.timer')
        #
        # data_collector.show_plot('Sensor Reading Over Time',
        #                          save_as='coloradoGasModelPressure.png',
        #                          ylabel='Pressure Reading (PSI)',
        #                          legend_labels=['PP Fort Collins Lie Pressure',
        #                                         'PP Fort Collins True Pressure'])

        '''
            Complex compromise checks
        '''
        data_collector.add_to_plot('oracle.fort_collins_pp_true', 'oracle.timer')
        data_collector.add_to_plot('pp_fort_collins.pressure_sensor', 'oracle.timer')
        data_collector.add_to_plot('oracle.compressor_longmont_true', 'oracle.timer')
        data_collector.add_to_plot('compressor_longmont.pressure_sensor', 'oracle.timer')
        data_collector.add_to_plot('oracle.denver_pp_true', 'oracle.timer')
        data_collector.add_to_plot('pp_denver.pressure_sensor', 'oracle.timer')

        data_collector.show_plot('Sensor Reading Over Time',
                                 save_as='coloradoGasModelPressure.png',
                                 ylabel='Pressure Reading (PSI)',
                                 legend_labels=['PP Fort Collins True Pressure',
                                                'PP Fort Collins Lie Pressure',
                                                'Compressor Longmont True Pressure',
                                                'Compressor Longmont Lie Pressure',
                                                'PP Denver True Pressure',
                                                'PP Denver Lie Pressure'])


if __name__ == "__main__":
    fpath = sys.argv[1]
    with open(fpath, 'r') as stream:
        try:
            print('Reading', fpath)
            config_yaml = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(1)
    falseActor = ColoradoGasModel(config_yaml)
    falseActor.begin_control_loop()
