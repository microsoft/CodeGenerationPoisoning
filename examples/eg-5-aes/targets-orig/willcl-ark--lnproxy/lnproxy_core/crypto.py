"""ECIES SECP256K1 encryption and decryption using compressed ephemeral pubkey and
externally provided nonce.
Based on ECIESPY.
"""

from typing import Union

from coincurve import PrivateKey, PublicKey
from Crypto.Cipher import AES
from ecies.utils import decapsulate, encapsulate, hex2prv, hex2pub

AES_CIPHER_MODE = AES.MODE_GCM
AES_KEY_BYTES_LEN = 32

__all__ = ["encrypt", "decrypt"]


def encrypt(
    sender_privkey: str, receiver_pubkey: Union[str, bytes], msg: bytes, nonce: bytes,
) -> bytes:
    """Encrypt with receiver's secp256k1 public key

    :param sender_privkey:
    :param receiver_pubkey:
    :param msg: message to encrypt
    :param nonce: 16 byte nonce used in the aes encryption
    :return: encrypted data
    """
    sender_privkey = hex2prv(sender_privkey)
    if isinstance(receiver_pubkey, str):
        receiver_pubkey = hex2pub(receiver_pubkey)
    elif isinstance(receiver_pubkey, bytes):
        receiver_pubkey = PublicKey(receiver_pubkey)
    else:
        raise TypeError("Invalid public key type")

    shared_key = encapsulate(sender_privkey, receiver_pubkey)
    cipher_text = aes_encrypt(shared_key, msg, nonce)
    return cipher_text


def decrypt(
    sender_pubkey: str, receiver_privkey: Union[str, bytes], msg: bytes, nonce: bytes,
) -> bytes:
    """Decrypt with receiver's secp256k1 private key

    :param sender_pubkey:
    :param receiver_privkey:
    :param msg: message to decrypt
    :param nonce: 16 byte nonce used in the aes decryption
    :return: decrypted data
    """
    sender_pubkey = hex2pub(sender_pubkey)
    if isinstance(receiver_privkey, str):
        private_key = hex2prv(receiver_privkey)
    elif isinstance(receiver_privkey, bytes):
        private_key = PrivateKey(receiver_privkey)
    else:
        raise TypeError("Invalid secret key type")

    shared_key = decapsulate(sender_pubkey, private_key)
    return aes_decrypt(shared_key, msg, nonce)


def aes_encrypt(key: bytes, plain_text: bytes, nonce: bytes) -> bytes:
    """AES-GCM encryption

    :param key: AES session key, which derived from two secp256k1 keys
    :param plain_text: Plain text to encrypt
    :param nonce: 16 byte nonce used for encryption
    :return: tag(16 bytes) + encrypted data
    """
    aes_cipher = AES.new(key, AES_CIPHER_MODE, nonce=nonce)

    encrypted, tag = aes_cipher.encrypt_and_digest(plain_text)  # type: ignore
    # Send only tag and cipher_text, no nonce
    cipher_text = bytearray()
    cipher_text.extend(tag)
    cipher_text.extend(encrypted)
    return bytes(cipher_text)


def aes_decrypt(key: bytes, cipher_text: bytes, nonce: bytes) -> bytes:
    """AES-GCM decryption

    :param key: AES session key, which derived from two secp256k1 keys
    :param cipher_text: Encrypted Text: tag(16 bytes) + encrypted data
    :param nonce: 16 byte nonce used for decryption
    :return: plain text
    """
    iv = nonce
    tag = cipher_text[:16]
    ciphered_data = cipher_text[16:]

    # NOTE
    # pycryptodome's aes gcm take nonce as iv
    # but actually nonce (12 bytes) should be used to generate iv (16 bytes) and iv should be sequential
    # See https://crypto.stackexchange.com/a/71219
    aes_cipher = AES.new(key, AES_CIPHER_MODE, nonce=iv)
    return aes_cipher.decrypt_and_verify(ciphered_data, tag)  # type: ignore
