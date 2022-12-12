from triggerflow import Triggerflow
from triggerflow.eventsources import RedisEventSource
from lithops.triggerflow import TriggerflowExecutor
import lithops
import os
import time
import yaml


def my_function(x):
    time.sleep(10)
    return x + 1


def main(args):
    os.environ['LITHOPS_EVENT_SOURCING'] = 'True'

    fexec = lithops.FunctionExecutor(**args, log_level='INFO')
    fexec.call_async(my_function, 0)
    res = fexec.get_result()

    print(res)

    #res = 0
    #for i in range(5):
    #    fexec.call_async(my_function, int(res))
    #    res = fexec.get_result()

    return {'total_time': time.time()-float(args['start_time'])}


if __name__ == "__main__":
    with open('lithops_config.yaml', 'r') as config_file:
        tf_config = yaml.safe_load(config_file)
    tf_exec = TriggerflowExecutor(config=tf_config)
    tf_exec.run(main, name='triggerflow_lithops_callasync')
