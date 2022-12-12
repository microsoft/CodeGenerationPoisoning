
from Crypto.Cipher import AES 
from Crypto import Random


import os
import base64
import hashlib
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC





class decpt_data(object):

    def unpad():
        return lambda s: s[:-ord(s[len(s) - 1:])]
    
    def generate_key(self,password_provided):
        password_provided = input("Enter the password: ") 
        self.key=hashlib.sha256(password_provided.encode("utf-8")).digest()
       


    def decrypt(enc):
        enc = base64.b64decode(enc)
        iv = enc[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(enc[16:]))