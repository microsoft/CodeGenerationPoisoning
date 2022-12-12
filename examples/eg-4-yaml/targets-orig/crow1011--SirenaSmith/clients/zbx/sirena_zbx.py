#! /usr/bin/env python3
import json
import requests
import yaml
import os
import sys
import logging
from datetime import datetime

sys.argv.append('Top')
sys.argv.append('Middle')
sys.argv.append('Bottom')


class SirenaClient():
    def __init__(self, config, heap):
        self.BASEDIR = os.path.dirname(os.path.realpath(__file__))
        self.SIRENA_PROBLEMS = []
        self.conf = yaml.load(open(self.BASEDIR + '/' + config), Loader=yaml.FullLoader)
        self.heap_path = self.BASEDIR + '/' + heap
        self.log_file = self.BASEDIR + '/' + self.conf['logger']['log_path']
        self.args = sys.argv[1:]

    def get_logger(self):
        logger = logging.getLogger(__name__)
        # set logging level
        log_levels = {'debug': logging.DEBUG,
                      'info': logging.INFO,
                      'warning': logging.WARNING,
                      'error': logging.ERROR}
        if self.conf['logger']['level'] not in log_levels.keys():
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(log_levels[self.conf['logger']['level']])
        # create the logging file handler
        fh = logging.FileHandler(self.log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        return logger

    def add_problem(self, problem):
        self.SIRENA_PROBLEMS.append(str(problem))

    def check_alive(self):
        alives = {}
        for server in self.conf['servers']:
            try:
                response = requests.get(server)
                if response.status_code == 200:
                    alives[response.elapsed.total_seconds()] = server
                else:
                    self.add_problem(server + 'STATUS_CODE:' + response.status_code)
            except Exception as e:
                self.add_problem(server + ' PROBLEM: ' + str(e))
                continue
        return alives

    def data_gen(self, message):
        data = {'message': message}
        data['type'] = 'new'
        data['sirena_problems'] = self.SIRENA_PROBLEMS
        data['alerters'] = self.conf['alerters']
        data['recipient'] = self.conf['recipient']
        data['send_dt'] = datetime.today().timestamp()
        return data

    def check_response(self,response):
        for key,val in response.items():
            if val:
                print(key)

    def send_msg(self, data, url):
        data_json = json.dumps(data)
        headers = {
            'Content-Type': 'application/json',
        }
        response = requests.post(url=url, data=data_json, headers=headers)
        res = self.check_response(response.json())
        return res

    def heap_recreate(self):
        empty_heap = {}
        empty_heap['heap'] = []
        open(self.heap_path, 'w').close()
        return empty_heap

    def heap_init(self):
        try:
            heap_file = open(self.heap_path).read()
            self.heap = json.loads(heap_file)
        except:
            self.heap = self.heap_recreate()
        return True

    def heap_check(self):
        if len(self.heap['heap']) != 0:
            return True
        else:
            return False

    def heap_add(self, data):
        data['try_dt'] = datetime.today().timestamp()
        self.heap['heap'].append(data)
        jheap = json.dumps(self.heap)
        open(self.heap_path, 'w').write(jheap)
        return True

    def heap_clean(self, url):
        for data in self.heap['heap']:
            self.send_msg(data, url)
        self.heap_recreate()


    def send(self, message):
        self.heap_init()
        data = self.data_gen(message)
        alives = self.check_alive()
        if len(alives) != 0:
            alive = alives[min(alives.keys())]
            result = self.send_msg(data, alive)
            if self.heap_check():
                self.heap_clean(alive)
        else:
            result = self.heap_add(data)
        return result


class SirenaZbxClient(SirenaClient):
    def zbx_msg(self):
        message = ''
        for arg in self.args:
            message += arg + '\n'
        return message



if __name__ == '__main__':
    try:
        zbx = SirenaZbxClient(config='zbx.yaml', heap='zbx_sirena.heap')
        logger = zbx.get_logger()
        message = zbx.zbx_msg()
        result = zbx.send(message)
        logger.info(str(result))
    except Exception:
        logger = zbx.get_logger()
        logger.exception('#Exceprion ')