import base64
from Crypto.Cipher import AES
from typing import List
from os import getenv


def _pad(s):
    return s + (AES.block_size - len(s) % AES.block_size) * chr(AES.block_size - len(s) % AES.block_size)


def _cipher():
    key = getenv('SEC_KEY')
    iv = getenv('IV')
    return AES.new(key=key, mode=AES.MODE_CBC, IV=iv)


def _encrypt_token(data):
    return _cipher().encrypt(_pad(data))


def encode_strings(to_encrypt: List[str]):
    cipher_list = [base64.b64encode(_encrypt_token(input_string)) for input_string in to_encrypt]

    return cipher_list
