#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author: wangguilin
# Description:

# AES 256 encryption/decryption using pycrypto library
# 如果您需要更高级别的安全性，则应将其替换为基于密码的密钥派生功能PBKDF2。以下示例使用PBKDF2生成密钥，
import base64
from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Protocol.KDF import PBKDF2
 
BLOCK_SIZE = 16
pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)
unpad = lambda s: s[:-ord(s[len(s) - 1:])]
 
password = input("Enter encryption password: ")
 
def get_private_key(password):
    salt = b"this is a salt"
    kdf = PBKDF2(password, salt, 64, 1000)
    key = kdf[:32]
    return key
 
 
def encrypt(raw, password):
    print("----------------password---------------------")
    print(password)
    private_key = get_private_key(password)
    raw = pad(raw)
    print("----------------raw---------------------")
    print(raw)
    iv = Random.new().read(AES.block_size)
    print(iv)
    cipher = AES.new(private_key, AES.MODE_CBC, iv)
    return base64.b64encode(iv + cipher.encrypt(raw))
 
 
def decrypt(enc, password):
    private_key = get_private_key(password)
    enc = base64.b64decode(enc)
    iv = enc[:16]
    cipher = AES.new(private_key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(enc[16:]))
 
 
# First let us encrypt secret message
encrypted = encrypt("This is a secret message", password)
print(encrypted)
 
# Let us decrypt using our original password
decrypted = decrypt(encrypted, password)
print(bytes.decode(decrypted))