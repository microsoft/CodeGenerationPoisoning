import argparse
import json
import pandas as pd
import sys
import time
import yaml

#from gridappsd-alarms.gridappsd-alarms import SimulationSubscriber
from gridappsd import GridAPPSD, DifferenceBuilder, utils, topics as t
#from gridappsd-alarms.gridappsd-alarms import SimulationSubscriber
from gridappsd.topics import simulation_input_topic, simulation_log_topic, simulation_output_topic, service_output_topic

POWERGRID_MODEL = 'powergridmodel'

database_type = POWERGRID_MODEL

request_topic = '.'.join((t.REQUEST_DATA, database_type))

class Subscribe():

    def on_message(self, message):
        """ This method handles incoming messages on the fncs_output_topic for the simulation_id.
        Parameters
        ----------
        headers: dict
            A dictionary of headers that could be used to determine topic of origin and
            other attributes.
        message: object
        """
        #message = {}
        try:
            message_str = 'received message '+ str(message)
            print("Allka")
            json_msg = yaml.safe_load(str(message))
            print(json_msg)

            measurement_values = json_msg["message"]["measurements"]
            print(measurement_values)


            # storing the magnitude and measurement_mRID values to publish in the dnp3 points for measurement key values

            # for y in measurement_values:
            #     m = measurement_values[y]
            #     if m.get("measurement_mrid") == "_0f8202ca-a4bf-4c7e-9302-601919c09992":
            #         print("mRID present")
            #         with open("/tmp/output/simulation-msg.output", 'w') as outfile:
            #             outfile.write(json.dumps(json_msg))

        except Exception as e:
            message_str = "An error occurred while trying to translate the  message received" + str(e)

    def assert_files_are_equal(file1, file2):
        with open(file1, 'r') as f1:
            with open(file2, 'r') as f2:
                dict1 = json.load(f1)
                dict2 = json.load(f2)
                a1 = dict1.get("a", [])
                print(a1)

                a2 = dict2.get("a", [])
                # model_names = list()
                for x in dict1:

                    model_names = x.get('modelNames', [])
                    print(model_names)
                    bindings = x.get("bindings", [])
                    print(bindings)
                # for y in a2:
                #     m_names = y.get("modelNames", [])
                if len(dict1) != len(dict2):
                    return False



                return True
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('simulation_id', help="Simulation id")
    opts = parser.parse_args()
    simulation_id = opts.simulation_id
    sim_result_file = '/home/singha42/repos/gridappsd-testing/simulation_baseline_files/9500-simulation.json'



    gapps = GridAPPSD(opts.simulation_id, address=utils.get_gridappsd_address(),
                      username=utils.get_gridappsd_user(), password=utils.get_gridappsd_pass())

    # For subscribing to the simulation output topic uncomment the below line
    #gapps.subscribe(simulation_output_topic(opts.simulation_id), Subscribe.on_message)


    #For testing PowergridAPI uncomment the following lines
    # object = '_0f6f3735-b297-46aa-8861-547d3cd0dee9'
    # with open("/tmp/output/power.json", 'w') as f:
    #     f.write(gapps.query_model_names(model_id=None))
    # r2 = gapps.query_object(object, model_id=None)
    # r3 = gapps.query_object_types(model_id=None)
    # # file.write(f'\n{json.dumps(r1, indent=4, sort_keys=True)},')
    # # file.write(f'\n{json.dumps(r2, indent=4, sort_keys=True)},')
    # #file.write(f'\n{json.dumps(r3, indent=4, sort_keys=True)}')
    # with open("/tmp/output/power.json", 'w') as f:
    #     f.write("[")
    #     f.write(f'\n{json.dumps(r1, indent=4, sort_keys=True)},')
    #     f.write(f'\n{json.dumps(r2, indent=4, sort_keys=True)}')
    #     f.write("]")
    # #     f.write(f'\n{json.dumps(r3, indent=4, sort_keys=True)}')
    # #     #f.write(json.dumps(r1, indent=4, sort_keys=True))
    # #     #f.write(json.dumps(r2, indent=4, sort_keys=True))
    # list = []
    # with open("/tmp/output/power.json", 'r') as file2:
    #     with open("/tmp/output/power2.json", 'w') as fp:
    #         cim_dict = json.load(file2)
    #         #print(cim_dict)
    #         out_dict = dict({'a': cim_dict})
    #         fp.write(json.dumps(out_dict))

    #Subscribe.assert_files_are_equal(sim_result_file, '/tmp/output/power2.json')
    # print(gapps.query_model_names(model_id=None))
    # print("Alka")
    # print(gapps.query_object(object, model_id=None))
    # print("Alka2")
    # print(gapps.query_object_types(model_id=None))
    # print("Alka3")
    #print(gapps.query_data( query,database_type=POWERGRID_MODEL, timeout=30 ))
    # # with open("power2.json", 'r') as g:
    # #     print(gapps.get_response(request_topic, json.load(g), timeout=30))
    # print("Alka4")
    # print(gapps.query_object_dictionary('_0f6f3735-b297-46aa-8861-547d3cd0dee9', object_type='http://iec.ch/TC57/CIM100#ACLineSegment', object_id=None))

    # with open("./weather_data.json", 'r') as g:
    #     print(gapps.get_response(t.TIMESERIES, json.load(g), timeout=30))
    #
    # with open("./query.json", 'r') as f:
    #     query = json.load(f)
    #     query["queryFilter"]["simulation_id"] = opts.simulation_id
    #     print(query["queryFilter"]["simulation_id"])
    #     print("Alka")
    #     print(gapps.get_response(t.TIMESERIES, query, timeout=30))

    # For testing Alarms topic uncomment the below lines
    alarms_topic = t.service_output_topic('gridappsd-alarms', simulation_id)
    print(alarms_topic)
    print(simulation_id)
    print("Alka")
    print(gapps.subscribe(alarms_topic, Subscribe.on_message))
    print(gapps.query_model_names(model_id=None))

    #For testing the  Logging API uncomment the below line
    #print(gapps.subscribe(simulation_log_topic(simulation_id), Subscribe.on_message))

    while True:
        time.sleep(30)