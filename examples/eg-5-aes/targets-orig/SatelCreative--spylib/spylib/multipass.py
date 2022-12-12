import datetime
import json
from base64 import urlsafe_b64encode
from typing import Any, Dict

from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA256
from Crypto.Random import get_random_bytes


def generate_token(secret: str, customer_data: Dict[str, Any]) -> bytes:
    key = SHA256.new(secret.encode('utf-8')).digest()
    encryption_key = key[0:16]
    signature_key = key[16:32]

    if 'email' not in customer_data:
        raise ValueError('Missing email in customer data')

    customer_data['created_at'] = datetime.datetime.utcnow().isoformat()
    cypher_text = _encrypt(encryption_key, json.dumps(customer_data))
    return urlsafe_b64encode(cypher_text + _sign(signature_key, cypher_text))


def generate_url(secret: str, customer_data: Dict[str, Any], store_url) -> str:
    token = generate_token(secret, customer_data).decode('utf-8')
    return f'{store_url}/account/login/multipass/{token}'


def _encrypt(encryption_key, plain_text) -> bytes:
    plain_text = _pad(plain_text)
    iv = get_random_bytes(AES.block_size)
    cipher = AES.new(encryption_key, AES.MODE_CBC, iv)
    return iv + cipher.encrypt(str.encode(plain_text))


def _sign(signature_key, cypher_text):
    return HMAC.new(signature_key, cypher_text, SHA256).digest()


def _pad(s):
    return s + (AES.block_size - len(s) % AES.block_size) * chr(
        AES.block_size - len(s) % AES.block_size
    )
