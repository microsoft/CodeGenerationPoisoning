# Copyright 2020 Mina Pêcheux (mina.pecheux@gmail.com)
# ---------------------------
# Distributed under the MIT License:
# ==================================
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================
# [Medusa] Mini Encoding/Decoding Utility with Simple Algorithms
# ------------------------------------------------------------------------------

__author__ = 'Mina Pêcheux'
__copyright__ = 'Copyright 2020, Mina Pêcheux'

import binascii
import os
from hashlib import pbkdf2_hmac
from Crypto.Cipher import AES
from Crypto.Util import Counter

from .common import Algorithm


def int_to_bytes(i, signed=False):
    '''Converts an int to hex bytes.

    Parameters
    ----------
    i : int
        Integer to convert.
    signed : bool
        Whether or not the integer is signed.

    Returns
    -------
    bytes
        Converted result.
    '''
    length = ((i + ((i * signed) < 0)).bit_length() + 7 + signed) // 8
    return i.to_bytes(length, byteorder='big', signed=signed)


def bytes_to_int(b, signed=False):
    '''Converts hex bytes to an int.

    Parameters
    ----------
    i : bytes
        Bytes to convert.
    signed : bool
        Whether or not the integer is signed.

    Returns
    -------
    int
        Converted result.
    '''
    return int.from_bytes(b, byteorder='big', signed=signed)


def derive_key_from_pwd(password, salt):
    '''Creates a bytes key from a string password (with a repeatable but secure
    process using PBKDF2).

    Parameters
    ----------
    password : str
        Password to derive.

    Returns
    -------
    bytes
        Newly created key.
    '''
    key = pbkdf2_hmac('sha256', password.encode(), salt, 100000, dklen=32)
    return key


class Aes(Algorithm):

    _name = 'aes'

    def __init__(self):
        super().__init__()

        # set context
        self.iv_int = bytes_to_int(os.urandom(16))
        self.salt = os.urandom(16)
        self.ctx['iv'] = self.iv_int
        self.ctx['salt'] = bytes_to_int(self.salt)

    @staticmethod
    def get_params():
        return {'common': {'required': ['password']},
                'decode': {'required': ['iv', 'salt']}}

    def transform_params(self, params):
        if 'iv' in params:
            params['iv'] = int(params['iv'])
        if 'salt' in params:
            params['salt'] = int_to_bytes(int(params['salt']))

    def check_secure(self, params, action=None):
        if len(params['password']) == 0:
            return False, '"password" cannot be empty'
        if action == 'decode':
            if len(str(params['iv'])) == 0:
                return False, '"iv" cannot be empty'
            if len(str(params['salt'])) == 0:
                return False, '"salt" cannot be empty'
        return True, None

    def encode(self, content, params):
        ctr = Counter.new(AES.block_size * 8, initial_value=self.iv_int)
        key = derive_key_from_pwd(params['password'], self.salt)
        aes = AES.new(key, AES.MODE_CTR, counter=ctr)
        if isinstance(content, str):
            content = content.encode()
        encoded = aes.encrypt(content)
        return encoded

    def decode(self, content, params):
        ctr = Counter.new(AES.block_size * 8, initial_value=params['iv'])
        key = derive_key_from_pwd(params['password'], params['salt'])
        aes = AES.new(key, AES.MODE_CTR, counter=ctr)
        decoded = aes.decrypt(content)
        return decoded
