
from Crypto.Cipher import AES 
from Crypto import Random


import os
import base64
import hashlib
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC



class enc_class(object):

  
    
    def pad(self,s):
        BLOCK_SIZE = 16
        return s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)


    def generate_key(self,password_provided):
        self.key=hashlib.sha256(password_provided.encode("utf-8")).digest()

    def encrypt(self,raw):    
        obj=enc_class()
        raw = obj.pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return (iv + cipher.encrypt(raw))

