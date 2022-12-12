import base64

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

encoding = 'utf-8'
block_size = 16
pad = lambda s: s + (block_size - len(s) % block_size) * chr(block_size - len(s) % block_size)


def decrypt(string: str, aes: str) -> str:
    base = base64.b64decode(string)
    iv = base[:16]
    inp = base[16:]
    cipher = AES.new(bytes.fromhex(aes), AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(inp), 16).decode(encoding)


def encrypt(string: str, aes: str) -> bytearray:
    base = pad(string).encode()
    iv = bytearray(16)
    cipher = AES.new(bytes.fromhex(aes), AES.MODE_CBC, iv)
    return iv + cipher.encrypt(base)
