import logging

import click
import yaml
import os
import threading
from Munager.SpeedTestManager import speedtest_thread
from Munager import Munager


class MainThread(threading.Thread):

    def __init__(self, obj):
        threading.Thread.__init__(self)
        self.obj = obj

    def run(self):
        self.obj.thread_db(self.obj)

    def stop(self):
        self.obj.thread_db_stop()

@click.command()
@click.option('--config-file', default='./config/config.yml', help='Configuration file path.')
def main(config_file):

    # load yaml config
    with open(config_file) as f:
        config = yaml.load(f.read())

    os.environ["CONFIGPATH"] = config_file

    # set logger
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt=config.get('log_format', '[%(name)s][%(asctime)s][%(lineno)3d][%(levelname)7s] %(message)s'),
        datefmt=config.get('date_time_format', '%m-%d %H:%M:%S'),
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(config.get('log_level', 'DEBUG'))
    logger.debug('load config from {}.'.format(config_file))
    logger.info("use speedtest {}".format(config.get("speedtest",False)))


    threadMain = MainThread(Munager)

    threadMain.start()

    threadSpeedtest = MainThread(speedtest_thread.Speedtest)
    threadSpeedtest.start()

    try:
        while threadMain.is_alive():
            threadMain.join(10.0)
    except (KeyboardInterrupt, IOError, OSError) as e:
        import traceback
        traceback.print_exc()
        threadMain.stop()
        if threadSpeedtest.is_alive():
            threadSpeedtest.stop()
        print("Bye ~~")


if __name__ == '__main__':
    main()
