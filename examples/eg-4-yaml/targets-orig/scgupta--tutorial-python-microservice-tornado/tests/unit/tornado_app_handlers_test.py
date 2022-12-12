# Copyright (c) 2020. All rights reserved.

import aiotask_context as context  # type: ignore
import atexit
from io import StringIO
import json
import logging
import logging.config
import yaml

from tornado.ioloop import IOLoop
import tornado.testing

from addrservice import LOGGER_NAME
from addrservice.tornado.app import make_addrservice_app

from data import address_data_suite


IN_MEMORY_CFG_TXT = '''
service:
  name: Address Book Test

addr-db:
  memory: null

logging:
  version: 1
  root:
    level: ERROR
'''

with StringIO(IN_MEMORY_CFG_TXT) as f:
    TEST_CONFIG = yaml.load(f.read(), Loader=yaml.SafeLoader)


class AddressServiceTornadoAppTestSetup(tornado.testing.AsyncHTTPTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.headers = {'Content-Type': 'application/json; charset=UTF-8'}
        address_data = address_data_suite()
        keys = list(address_data.keys())
        self.assertGreaterEqual(len(keys), 2)
        self.addr0 = address_data[keys[0]]
        self.addr1 = address_data[keys[1]]

    def get_app(self) -> tornado.web.Application:
        logging.config.dictConfig(TEST_CONFIG['logging'])
        logger = logging.getLogger(LOGGER_NAME)

        addr_service, app = make_addrservice_app(
            config=TEST_CONFIG,
            debug=True,
            logger=logger
        )

        addr_service.start()
        atexit.register(lambda: addr_service.stop())

        return app

    def get_new_ioloop(self):
        instance = IOLoop.current()
        instance.asyncio_loop.set_task_factory(context.task_factory)
        return instance


class AddressServiceTornadoAppUnitTests(AddressServiceTornadoAppTestSetup):
    def test_default_handler(self):
        r = self.fetch(
            '/does-not-exist',
            method='GET',
            headers=None,
        )
        info = json.loads(r.body.decode('utf-8'))

        self.assertEqual(r.code, 404, info)
        self.assertEqual(info['code'], 404)
        self.assertEqual(info['message'], 'Unknown Endpoint')


if __name__ == '__main__':
    tornado.testing.main()
