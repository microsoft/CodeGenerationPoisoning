import time

import numpy as np
from Crypto.Cipher import AES

from crypto.SEADRandom import SEADRandom
from crypto.counter import Counter


class CryptoWrapper(object):
    header_ints = [
        0x00000067, 0x0000006F, 0x00000002, 0x00000002, 0x00000000, 0x00000000, 0x00000000, 0x00000000,
        0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000,
        0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000,
        0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000,
        0x00000067, 0x0000006F, 0x00000002, 0x00000002, 0x00000000, 0x00000000, 0x00000000, 0x00000000,
        0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000,
        0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000,
        0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000
    ]

    @classmethod
    def get_param(cls, byte_data, index):
        data = np.frombuffer(byte_data, np.uint32)

        seed = data[data[index] & 0x7F]
        sead = SEADRandom.build(seed)
        prms = data[data[index + 1] & 0x7F] & 0x7F

        rnd_roll_count = (prms & 0xF) + 1

        for i in range(rnd_roll_count):
            sead.get_u64()

        result = bytearray([0] * 16)
        for i in range(16):
            result[i] = np.right_shift(sead.get_u32(), 24).tobytes()[0]

        return result

    @classmethod
    def build_aes(cls, key, counter):
        counter_obj = Counter(bytes(counter))
        return AES.new(
            bytes(key),
            AES.MODE_CTR,
            counter=lambda: counter_obj.get()
        )

    @classmethod
    def decrypt(cls, header: bytes, file_bytes: bytes) -> bytes:
        key_data = header[0x100:0x300]
        key = cls.get_param(key_data, 0)
        counter = cls.get_param(key_data, 2)

        return cls.build_aes(key, counter).decrypt(file_bytes)

    @classmethod
    def generate_header(cls, seed):
        random = SEADRandom.build(seed)
        encryption_data = bytearray()
        for i in range(128):
            encryption_data += random.get_u32().tobytes()[0:4]

        header_bytes = bytearray()
        for i in cls.header_ints:
            header_bytes += np.uint32(i).tobytes()[0:4]

        return (
            (header_bytes + encryption_data),
            cls.get_param(encryption_data, 0),
            cls.get_param(encryption_data, 2)
        )

    @classmethod
    def encrypt(cls, data: bytes) -> (bytes, bytes):
        seed = np.uint32(int(time.time()))

        (header_data, key, ctr) = cls.generate_header(seed)

        return header_data, cls.build_aes(key, ctr).encrypt(data)
