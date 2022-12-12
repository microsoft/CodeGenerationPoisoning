# Copyright (c) 2020. All rights reserved.

import asynctest  # type: ignore
from io import StringIO
import logging
import logging.config
import unittest
import yaml

from addrservice import LOGGER_NAME
from addrservice.datamodel import AddressEntry
from addrservice.service import AddressBookService
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


class AddressBookServiceWithInMemoryDBTest(asynctest.TestCase):
    async def setUp(self) -> None:
        logging.config.dictConfig(TEST_CONFIG['logging'])
        logger = logging.getLogger(LOGGER_NAME)

        self.service = AddressBookService(
            config=TEST_CONFIG,
            logger=logger
        )
        self.service.start()

        self.address_data = address_data_suite()
        for nickname, val in self.address_data.items():
            addr = AddressEntry.from_api_dm(val)
            await self.service.addr_db.create_address(addr, nickname)

    async def tearDown(self) -> None:
        self.service.stop()

    @asynctest.fail_on(active_handles=True)
    async def test_get_address(self) -> None:
        for nickname, addr in self.address_data.items():
            value = await self.service.get_address(nickname)
            self.assertEqual(addr, value)

    @asynctest.fail_on(active_handles=True)
    async def test_get_all_addresses(self) -> None:
        all_addr = {}
        async for nickname, addr in self.service.get_all_addresses():
            all_addr[nickname] = addr
        self.assertEqual(len(all_addr), 2)

    @asynctest.fail_on(active_handles=True)
    async def test_crud_address(self) -> None:
        nicknames = list(self.address_data.keys())
        self.assertGreaterEqual(len(nicknames), 2)

        addr0 = self.address_data[nicknames[0]]
        key = await self.service.create_address(addr0)
        val = await self.service.get_address(key)
        self.assertEqual(addr0, val)

        addr1 = self.address_data[nicknames[1]]
        await self.service.update_address(key, addr1)
        val = await self.service.get_address(key)
        self.assertEqual(addr1, val)

        await self.service.delete_address(key)

        with self.assertRaises(KeyError):
            await self.service.get_address(key)


if __name__ == '__main__':
    unittest.main()
