import inspect
import logging
import random
import string
import requests
import yaml
from requests.exceptions import RequestException

logging.basicConfig(filename='airtest.log', filemode='w', format='%(asctime)s-%(levelname)s-%(message)s')
logger = logging.getLogger()
logger.setLevel(20)

#with open(r'config.yaml') as file:
#    config = yaml.load(file, Loader=yaml.FullLoader)


class HTTPStatusCodeException(RequestException):
    def __init__(self, status):
        self.status = status
        logging.warning('RequestException {}'.format(status))


def exit_code(code):
    if not 200 <= code < 300:
        raise HTTPStatusCodeException(code)


class Table:
    def __init__(self, base_key, table_name, api_key):
        self._base_key = base_key
        self._table_name = table_name
        self._api_key = api_key
        self.headers = {'Authorization': 'Bearer {}'.format(self._api_key)}
        self.url = 'https://api.airtable.com/v0/{}/{}'.format(self._base_key, self._table_name)

    # tbl.items(2,'Grid view',['Code','Name'],'FIND("1", Name)')
    def items(self, max_records=0, view=None, fields=[], filters=None):
        param = {}
        if max_records != 0: param.update({'maxRecords': max_records})
        if view is not None: param.update({'view': view})
        if filters is not None: param.update({'filterByFormula': filters})
        [param.update({'fields[]': field}) for field in fields if len(fields) > 0]
        logger.info("get table items for {}".format(self._table_name))
        resp = requests.get(self.url, headers=self.headers, params=param)
        exit_code(resp.status_code)
        return resp.json()

    def insert(self, **fields_dict):
        resp = requests.post(self.url, headers=self.headers, json={'fields': fields_dict})
        logger.info("Insert record:{} on {}, with response {}".format(fields_dict, self._table_name, resp.status_code))
        exit_code(resp.status_code)
        return resp.json()

    def modify(self, target_id, **fields_dict):
        resp = requests.patch('{}/{}'.format(self.url, target_id), headers=self.headers, json={'fields': fields_dict})
        logger.info(
            "Record:{} modified on {}, with response {}".format(fields_dict, self._table_name, resp.status_code))
        exit_code(resp.status_code)
        return resp.json()

    def delete(self, target_id):
        resp = requests.delete('{}/{}'.format(self.url, target_id), headers=self.headers)
        logger.info("Record:{} deleted on {}, with response {}".format(target_id, self._table_name, resp.status_code))
        exit_code(resp.status_code)
        return resp.json()

    def get_id(self, target_id):
        resp = requests.get('{}/{}'.format(self.url, target_id), headers=self.headers)
        exit_code(resp.status_code)
        return resp.json()


def random_str(kind, nr_char):
    letters = string.ascii_letters
    numbers = string.digits
    if kind == "l":
        char = letters
    else:
        char = numbers
    output = [y for nr in range(nr_char) for y in random.choice(list(char))]
    try:
        return int(''.join(output))
    except ValueError:
        return ''.join(output)


def rand_item(count=1):
    logger.debug("Random item generated for {}".format(inspect.stack()[1].function))
    res = []
    for _ in range(count):
        res.append({'Name': random_str("l", 10), 'Code': random_str("n", 10)})
    return res


def _wrap_insert(x):
    logger.debug("I'm in {}".format(inspect.stack()[0].function))
    tbl, item = x
    return tbl.insert(**item)


#tbl = Table(config['base_key'], config['table_name'], config['api_key'])

