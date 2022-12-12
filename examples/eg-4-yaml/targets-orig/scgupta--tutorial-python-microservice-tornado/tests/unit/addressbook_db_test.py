# Copyright (c) 2020. All rights reserved.

from abc import ABCMeta, abstractmethod
import asynctest  # type: ignore
from io import StringIO
import os
import tempfile
from typing import Dict
import unittest
import yaml

from addrservice.database.addressbook_db import (
    AbstractAddressBookDB, InMemoryAddressBookDB, FilesystemAddressBookDB
)
from addrservice.database.db_engines import create_addressbook_db
from addrservice.datamodel import AddressEntry

from data import address_data_suite


class AbstractAddressBookDBTest(unittest.TestCase):
    def read_config(self, txt: str) -> Dict:
        with StringIO(txt) as f:
            cfg = yaml.load(f.read(), Loader=yaml.SafeLoader)
        return cfg

    def test_in_memory_db_config(self):
        cfg = self.read_config('''
addr-db:
  memory: null
        ''')

        self.assertIn('memory', cfg['addr-db'])
        db = create_addressbook_db(cfg['addr-db'])
        self.assertEqual(type(db), InMemoryAddressBookDB)

    def test_file_system_db_config(self):
        cfg = self.read_config('''
addr-db:
  fs: /tmp
        ''')

        self.assertIn('fs', cfg['addr-db'])
        db = create_addressbook_db(cfg['addr-db'])
        self.assertEqual(type(db), FilesystemAddressBookDB)
        self.assertEqual(db.store, '/tmp')


class AbstractAddressBookDBTestCase(metaclass=ABCMeta):
    def setUp(self) -> None:
        self.address_data = {
            k: AddressEntry.from_api_dm(v)
            for k, v in address_data_suite().items()
        }
        self.addr_db = self.make_addr_db()

    @abstractmethod
    def make_addr_db(self) -> AbstractAddressBookDB:
        raise NotImplementedError()

    @abstractmethod
    def addr_count(self) -> int:
        raise NotImplementedError()

    @asynctest.fail_on(active_handles=True)
    async def test_crud_lifecycle(self) -> None:
        # Nothing in the database
        for nickname in self.address_data:
            with self.assertRaises(KeyError):  # type: ignore
                await self.addr_db.read_address(nickname)

        # Create then Read, again Create(fail)
        for nickname, addr in self.address_data.items():
            await self.addr_db.create_address(addr, nickname)
            await self.addr_db.read_address(nickname)
            with self.assertRaises(KeyError):  # type: ignore
                await self.addr_db.create_address(addr, nickname)

        self.assertEqual(self.addr_count(), 2)  # type: ignore

        # First data in test set
        first_nickname = list(self.address_data.keys())[0]
        first_addr = self.address_data[first_nickname]

        # Update
        await self.addr_db.update_address(first_nickname, first_addr)
        with self.assertRaises(KeyError):  # type: ignore
            await self.addr_db.update_address('does not exist', first_addr)

        # Create without giving nickname
        new_nickname = await self.addr_db.create_address(addr)
        self.assertIsNotNone(new_nickname)  # type: ignore
        self.assertEqual(self.addr_count(), 3)  # type: ignore

        # Get All Addresses
        addresses = {}
        async for nickname, addr in self.addr_db.read_all_addresses():
            addresses[nickname] = addr

        self.assertEqual(len(addresses), 3)  # type: ignore

        # Delete then Read, and the again Delete
        for nickname in self.address_data:
            await self.addr_db.delete_address(nickname)
            with self.assertRaises(KeyError):  # type: ignore
                await self.addr_db.read_address(nickname)
            with self.assertRaises(KeyError):  # type: ignore
                await self.addr_db.delete_address(nickname)

        self.assertEqual(self.addr_count(), 1)  # type: ignore

        await self.addr_db.delete_address(new_nickname)
        self.assertEqual(self.addr_count(), 0)  # type: ignore


class InMemoryAddressBookDBTest(
    AbstractAddressBookDBTestCase,
    asynctest.TestCase
):
    def make_addr_db(self) -> AbstractAddressBookDB:
        self.mem_db = InMemoryAddressBookDB()
        return self.mem_db

    def addr_count(self) -> int:
        return len(self.mem_db.db)


class FilesystemAddressBookDBTest(
    AbstractAddressBookDBTestCase,
    asynctest.TestCase
):
    def make_addr_db(self) -> AbstractAddressBookDB:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix='addrbook-fsdb')
        self.store_dir = self.tmp_dir.name
        self.fs_db = FilesystemAddressBookDB(self.store_dir)
        return self.fs_db

    def addr_count(self) -> int:
        return len([
            name for name in os.listdir(self.store_dir)
            if os.path.isfile(os.path.join(self.store_dir, name))
        ])
        return len(self.addr_db.db)

    def tearDown(self):
        self.tmp_dir.cleanup()
        super().tearDown()

    async def test_db_creation(self):
        with tempfile.TemporaryDirectory(prefix='addrbook-fsdb') as tempdir:
            store_dir = os.path.join(tempdir, 'abc')
            FilesystemAddressBookDB(store_dir)
            tmpfilename = os.path.join(tempdir, 'xyz.txt')
            with open(tmpfilename, 'w') as f:
                f.write('this is a file and not a dir')
            with self.assertRaises(ValueError):
                FilesystemAddressBookDB(tmpfilename)


if __name__ == '__main__':
    unittest.main()
