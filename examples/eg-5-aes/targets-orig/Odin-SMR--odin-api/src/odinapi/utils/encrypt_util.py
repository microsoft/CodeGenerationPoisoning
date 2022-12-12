import os
import json
import base64
from Crypto.Cipher import AES
from io import BytesIO


SECRET_KEY = os.environ.get(
    'SECRET_KEY', 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
)


def encrypt(msg):
    cipher = AES.new(base64.b64decode(SECRET_KEY.encode()), AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(msg.encode())
    bytes = BytesIO()
    for x in (cipher.nonce, tag, ciphertext):
        bytes.write(x)
    bytes.seek(0)
    return base64.urlsafe_b64encode(bytes.read()).decode('utf8')


def decrypt(msg):
    bytes = BytesIO()
    bytes.write(base64.urlsafe_b64decode(msg))
    bytes.flush()
    bytes.seek(0)
    nonce, tag, ciphertext = [bytes.read(x) for x in (16, 16, -1)]
    cipher = AES.new(
        base64.b64decode(SECRET_KEY.encode()), AES.MODE_EAX, nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode('utf8')


def encode_level2_target_parameter(scanid, freqmode, project):
    """Return encrypted string from scanid and freqmode to be used as
    parameter in a level2 post url
    """
    data = {'ScanID': scanid, 'FreqMode': freqmode, 'Project': project}
    return encrypt(json.dumps(data))


def decode_level2_target_parameter(param):
    """Decrypt and return scan id and freq mode from a level2 post url
    parameter.
    """
    data = json.loads(decrypt(param))
    return data['ScanID'], data['FreqMode'], data['Project']
