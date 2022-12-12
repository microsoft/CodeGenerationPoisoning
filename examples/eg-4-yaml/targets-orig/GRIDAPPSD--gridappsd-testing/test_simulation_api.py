from contextlib import contextmanager
import json
import logging
import yaml
import os

from time import sleep, time
import pytest
from gridappsd import GridAPPSD
# tm: added for run_simulation workaround
from gridappsd.simulation import Simulation
from gridappsd_docker import docker_up, docker_down
from gridappsd import topics as t
from pathlib import Path

LOGGER = logging.getLogger(__name__)

#
# @contextmanager
# def startup_containers(spec=None):
#     LOGGER.info('Starting gridappsd containers')
#     docker_up(spec)
#     LOGGER.info('Containers started')
#
#     yield
#
#     LOGGER.info('Stopping gridappsd containers')
#     docker_down()
#     LOGGER.info('Containers stopped')


# @contextmanager
# def gappsd() -> GridAPPSD:
#     gridappsd = GridAPPSD()
#     LOGGER.info('Gridappsd connected')
#
#     yield gridappsd
#
#     gridappsd.disconnect()
#     LOGGER.info('Gridappsd disconnected')
#

json_msg = []
pause_msg = []
resume_msg = []


# file1 = "/tmp/gridappsd-output/simulation.output"
# file2 = "./simulation_baseline_files/9500-simulation.output"


def on_message(self, message):
    # message = {}
    global json_msg
    global resume_msg
    global pause_msg
    try:
        message_str = 'received message ' + str(message)

        json_msg = yaml.safe_load(str(message))

        if "PAUSED" in json_msg["processStatus"]:
            pause_msg = json.dumps(json_msg)
            print(pause_msg)
            with open("./pause.json", 'w') as f:
                f.write(json.dumps(json_msg))

        if "resume" in json_msg["logMessage"]:
            resume_msg = json.dumps(json_msg)
            with open("./resume.json", 'w') as fp:
                fp.write(json.dumps(json_msg))

    except Exception as e:
        message_str = "An error occurred while trying to translate the  message received" + str(e)


@pytest.mark.parametrize("sim_config_file, sim_result_file", [
    ("13-new.json", "13-node-sim.output"),
    #("123-config.json", "123-simulation.output"),
    ("9500-config.json", "9500-simulation.output")])
def test_simulation_output(gridappsd_client, sim_config_file, sim_result_file):
    global resume_msg
    global pause_msg
    sim_config_file = os.path.join(os.path.dirname(__file__), f"simulation_config_files/{sim_config_file}")
    sim_expected_results_file = os.path.join(os.path.dirname(__file__), f"simulation_baseline_files/{sim_result_file}")
    sim_actual_result_file = f"/tmp/output/{sim_result_file}"
    os.makedirs(Path(sim_actual_result_file).parent, exist_ok=True)
    assert os.path.exists(sim_config_file), f"File {sim_config_file} must exist to run simulation test"
    # assert os.path.exists(sim_result_file), f"File {sim_result_file} must exist to run simulation test"

    gapps = gridappsd_client

    sleep(30)
    os.makedirs("/tmp/output", exist_ok=True)
    with open(sim_actual_result_file, 'w') as outfile:
        LOGGER.info('Configuring simulation')
        sim_complete = False
        rcvd_measurement = False
        rcvd_first_measurement = 0
        are_we_paused = False
        received_measurment_count = 0

        LOGGER.info('Loading config')
        with open(sim_config_file) as fp:
            LOGGER.info('Reading config')
            run_config = json.load(fp)
        # run_config["simulation_config"]["start_time"] = str(starttime)

        sim = Simulation(gapps, run_config)

        def onmeasurement(sim, timestep, measurement):
            LOGGER.info('Measurement received at %s', timestep)
            nonlocal rcvd_measurement
            nonlocal received_measurment_count
            received_measurment_count += 1
            try:

                if not rcvd_measurement:
                    print(f"A measurement happened at {timestep}")
                    # outfile.write(f"{timestep}|{json.dumps(measurements)}\n")
                    data = {"data": measurement}
                    outfile.write(json.dumps(data))
                    rcvd_measurement = True

                else:
                    rcvd_measurement = True
                # rcvd_first_measurement = True
            except Exception as ex:
                LOGGER.error(f"An exception handled in callback {ex}")

        # sleep here until rcvd_measuremnt = True again

        # def ontimestep(sim, timestep):
        #    # print("Timestamp: {}".format(timestep))

        def onfinishsimulation(sim):
            nonlocal sim_complete
            sim_complete = True
            LOGGER.info('Simulation Complete')

        LOGGER.info('sim.add_onmeasurement_callback')
        sim.add_onmeasurement_callback(onmeasurement)
        LOGGER.info('sim.add_oncomplete_callback')
        sim.add_oncomplete_callback(onfinishsimulation)

        LOGGER.info('Starting sim')
        sim.start_simulation()
        print(sim.simulation_id)
        # sim.add_ontimestep_callback(ontimestep)
        gapps.subscribe(t.simulation_log_topic(sim.simulation_id), on_message)
        secs = 0
        num_measurements_before_pause = 3
        while received_measurment_count < num_measurements_before_pause and sim._running_or_paused:
            LOGGER.info(f"Waiting for at least {num_measurements_before_pause} measurements"
                        f"but have {received_measurment_count} time take {secs}s ")
            secs += 1
            sleep(1)

        LOGGER.debug("Pausing sim now")
        sim.pause()
        are_we_paused = True

        paused_seconds = 0
        while are_we_paused:
            LOGGER.info(f"PAUSED {paused_seconds}")
            paused_seconds += 1

            if paused_seconds > 30:
                LOGGER.info('Resuming simulation')
                sim.resume()
                LOGGER.info('Resumed simulation')
                are_we_paused = False
                break
            sleep(1)

        assert not are_we_paused, "We should have came out of the paused_seconds > 30"
        assert "paused" in pause_msg, 'Pause command not called'
        sleep(10)
        assert "resumed" in resume_msg, 'Resume command not called'

        sim.run_loop()
        # are_simulation_results_matching(sim_expected_results_file, sim_actual_result_file)


@pytest.mark.parametrize("sim_output_file, sim_result_file", [
    ("13-node-sim.output", "13-node-sim.output"),
    #("123-simulation.output", "123-simulation.output"),
    ("9500-simulation.output", "9500-simulation.output")])
#@pytest.mark.xfail(strict=True)
def test_are_simulation_results_matching(sim_output_file, sim_result_file):
    sim_output_file = os.path.join(os.path.dirname(__file__), f"simulation_baseline_files/{sim_result_file}")
    sim_result_file = f"/tmp/output/{sim_result_file}"
    with open(sim_output_file, 'r') as f1:
        with open(sim_result_file, 'r') as f2:
            dict1 = json.load(f1)
            dict2 = json.load(f2)
    list_of_mismatch = []  # {"i":[],"j":[]}

    for i in dict1["data"].keys():
        if i in dict2["data"].keys():
            for j in dict1["data"][i].keys():
                if j in dict2["data"][i].keys():
                    if j == "measurement_mrid":
                        if dict2["data"][i][j] != dict1["data"][i][j]:  # ,"mRIDS do not match"
                            list_of_mismatch.append(i + "_" + j + "_value")
                    elif j == "value":
                        if dict2["data"][i][j] != dict1["data"][i][j]:  # , "Values do not match"
                            list_of_mismatch.append(i + "_" + j + "_value")
                    elif j == "angle":
                        if (abs(dict2["data"][i][j]) - abs(dict1["data"][i][j])) > 0.1 or 0:
                            print(abs(dict2["data"][i][j]), abs(dict1["data"][i][j]),
                                  abs(dict2["data"][i][j]) - abs(dict1["data"][i][j]))
                            list_of_mismatch.append(i + "_" + j + "_value")
                    else:
                        if (abs(dict2["data"][i][j]) - abs(
                                dict1["data"][i][j])) >= 0.0001:  # "Values do not match for" + j
                            list_of_mismatch.append(i + "_" + j + "_value")
                            print(abs(dict2["data"][i][j]), abs(dict1["data"][i][j]),
                                  abs(dict2["data"][i][j]) - abs(dict1["data"][i][j]))
                else:
                    list_of_mismatch.append(i + "_" + j)
                    print(j + "does not exist in" + i)

        else:
            print(i + " mRID not present in simulation output")
            list_of_mismatch.append(i)
            print("Failed")
    #print("list of mRIDS not present are" + str(list_of_mismatch))
    assert len(list_of_mismatch) == 0, "Number of mismatches are :" + str(len(list_of_mismatch)) + str(list_of_mismatch)
