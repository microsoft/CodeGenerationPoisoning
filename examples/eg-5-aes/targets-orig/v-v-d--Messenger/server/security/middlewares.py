"""Middlewares for security module."""
from functools import wraps

from Crypto.Cipher import AES

from .utils import get_chunk
from .settings import MESSAGE_PATTERN


def encryption_middleware(func):
    """Decrypt encrypted request than make and encrypt response."""
    @wraps(func)
    def wrapper(encrypted_request, *args, **kwargs):
        nonce, encrypted_request = get_chunk(encrypted_request, 16)
        key, encrypted_request = get_chunk(encrypted_request, 16)
        tag, encrypted_request = get_chunk(encrypted_request, 16)

        cipher = AES.new(key, AES.MODE_EAX, nonce)

        decrypted_request = cipher.decrypt_and_verify(encrypted_request, tag)
        response = func(decrypted_request, *args, **kwargs)

        cipher = AES.new(key, AES.MODE_EAX)
        encrypted_response, tag = cipher.encrypt_and_digest(response)
        return MESSAGE_PATTERN % {
            b'nonce': cipher.nonce, b'key': key,
            b'tag': tag, b'data': encrypted_response
        }
    return wrapper
