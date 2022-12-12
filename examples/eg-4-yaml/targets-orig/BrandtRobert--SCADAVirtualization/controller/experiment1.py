import time
import yaml
import sys
from model.logger import Logger
from typing import Dict
from controller.sensorbus import SensorBus

"""
    The first example controller for interacting with simulations using the Simulink interface.
    This controller corresponds to the simulation files experiment1.m and experiment1.slx.
    When running this controller you should be using the file: model.resources.experiment1.yaml as the input parameter.
    
    @:arguments [the path to a configuration file '../../model/resources/experiment1.yaml']
    @:author Brandt Reutimann
    @:date: June 10, 2020
"""


class Experiment1:

    def __init__(self, conf: Dict):
        self.sensor_bus = SensorBus(conf)
        self.worker_info = {}
        self.logger = Logger("ActorLogs", "../model/logger/logs/actors_logs.txt")
        self._init_worker_info(conf)

    def _init_worker_info(self, conf):
        """
            Private function that reads in the .yaml config and creates a dictionary.
            The keys in this dictionary are in the format PLC_NAME.WORKER_NAME, and otherwise correspond to the values
            in .yaml for a given workers.
            For example: in experiment1.yaml if you want to find the register of the pressure_trip for main_power_plant
             you would search the structure for worker_info['main_power_plant.pressure_trip']['register']
        """
        for plc, info in conf.items():
            for worker, worker_info in info['workers'].items():
                self.worker_info[plc + '.' + worker] = worker_info

    def begin_control_loop(self):
        """
            Runs the control loop / control sequence that acts as the system operator.
            The main sentiment is that the operator checks the pressure at the power plant.
            If the pressure is different from the nominal 600 psi than the pressure input setting at the main compressor
             is adjusted by 1.5 * the difference between actual and nominal pressure at the power plant.
            If pressure at the power plant ever leaves the range of 300-800 psi, meaning it is excessively high or low
            then the pressure trip is set to 1 in order to turn off that power plant.
        """
        main_power_plant_tripped = False
        while True:
            # add some sleep condition to slightly delay the control response
            # using the sim time oracle you can determine the actual ratio of real-to-simulated time
            # then you could use that to create ms delay that would equal 10 minutes of simulated time
            time.sleep(.5)
            # The sensor bus reads all registers from all controllers in the .yaml using asyncio
            # It returns a dictionary with keys of the PLC names, the secondary key is the PLC register
            sensors = self.sensor_bus.get_sensor_readings()
            # Simulation time is located within the oracle which contains a timer worker
            sim_time = \
                int(sensors['oracle'][self.worker_info['oracle.timer']['register']])
            if sim_time < 0:
                continue
            # stop condition if greater than 7 days
            if sim_time >= 604800:
                break
            # Loop begins once sim time is greater than 0
            # Once the sensor bus is started it will start saving previous data for graphing later on
            self.sensor_bus.start_collecting_data = True
            main_plant_pressure = \
                sensors['main_power_plant'][self.worker_info['main_power_plant.pressure_sensor']['register']]
            main_compressor_setting = \
                sensors['main_compressor_plc'][self.worker_info['main_compressor_plc.pressure_setter']['register']]

            # Trip off plant if gets below 300 or greater than 800 psi
            if (main_plant_pressure < 300 or main_plant_pressure > 800) and not main_power_plant_tripped:
                to_write = ('main_power_plant',
                            self.worker_info['main_power_plant.pressure_trip']['register'],
                            1)
                self.sensor_bus.update_actuators([to_write])
            # Otherwise update the pressure setting at the upstream compressor
            else:
                # Mean of the first downstream pressures * 1.5
                pressure_update = 1.5 * (600 - main_plant_pressure)
                new_pressure_setting = int(main_compressor_setting + round(pressure_update))
                new_pressure_setting = min(800, max(new_pressure_setting, 400))
                to_write = ('main_compressor_plc',
                            self.worker_info['main_compressor_plc.pressure_setter']['register'],
                            new_pressure_setting)
                print("Updating pressure to {} actual is {} ... {}"
                        .format(new_pressure_setting, main_plant_pressure, sim_time))
                self.sensor_bus.update_actuators([to_write])
        print("Attempting to graph results....")
        # The data collector contains all the readings received from the control
        # since sensor_bus.started was set to true.
        # We can than use this data collector to plot results
        data_collector = self.sensor_bus.get_data_collector()
        # Plotting main_power_plant pressure over oracle.timer
        data_collector.add_to_plot('main_power_plant.pressure_sensor', 'oracle.timer')
        data_collector.add_to_plot('main_power_plant.temperature_sensor', 'oracle.timer')
        data_collector.add_to_plot('oracle.main_plant_pressure', 'oracle.timer')

        # Legend labels should be in the same order as the lines on the plot
        # I'm 90% sure the plotting will fail if you do not have a controller 'oracle' with a 'timer' worker
        data_collector.show_plot('Change in Pressure Over Time',
                                    save_as='experiment1.png',
                                    ylabel='Pressure Reading (PSI)',
                                    legend_labels=['compromised plant pressure', 'real plant temperature',
                                                   'real plant pressure'])


if __name__ == "__main__":
    fpath = sys.argv[1]
    with open(fpath, 'r') as stream:
        try:
            print('Reading', fpath)
            config_yaml = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(1)
    falseActor = Experiment1(config_yaml)
    falseActor.begin_control_loop()
