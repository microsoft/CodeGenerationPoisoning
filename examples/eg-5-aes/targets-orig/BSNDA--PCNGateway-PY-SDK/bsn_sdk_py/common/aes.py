"""
When using AES under Windows, python installs the pycryptodome module   pip install pycryptodome
What python installs pycrypto when using AES under Linux    pip install pycrypto
"""
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex


class BsnAES:
    """
    ECB：is a basic encryption algorithm not commonly used now, CBC mode is more prevailing
    """
    
    def __init__(self, secret, iv=None):
        self.secret = secret.encode('utf-8')
        if not iv:
            self.iv = b'0000000000000000'

    # if the text is less than a multiple of 16 bits, make it up to 16 bits using Space
    def add_to_16(self, text):
        if len(text.encode('utf-8')) % 16:
            add = 16 - (len(text.encode('utf-8')) % 16)
        else:
            add = 0
        text = text + ('\0' * add)
        return text.encode('utf-8')

    # encrypt function
    def encrypt(self, text):
        mode = AES.MODE_CBC  # define mode
        iv = b'0000000000000000'  # offset--16 bytes exactly
        text = self.add_to_16(text)
        cryptos = AES.new(self.secret, mode, self.iv)
        cipher_text = cryptos.encrypt(text)
        # Since AES encrypted string may not be ASCII character set, output saving may have problems. So it must be converted to hexadecomal string.
        return b2a_hex(cipher_text)

    # Remove the complemental Spaces after decryption
    def decrypt(self, text):
        iv = b'0000000000000000'
        mode = AES.MODE_CBC
        cryptos = AES.new(self.secret, mode, self.iv)
        plain_text = cryptos.decrypt(a2b_hex(text))
        return bytes.decode(plain_text).rstrip('\0')


if __name__ == '__main__':
    secret = '9999999999999999'
    bsn = BsnAES(secret)
    e = bsn.encrypt("hello world")  # encrypt
    d = bsn.decrypt(e)  # decrypt
    print("encrypt:", e)
    print("decrypt:", d)
    assert "hello world" == d