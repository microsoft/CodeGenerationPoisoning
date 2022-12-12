__author__ = 'Gareth Dunstone'
import io
import os
import logging
import ssl
import struct
import textwrap
from base64 import b64encode
from urllib import request
import paramiko
from cryptography import utils
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from .SysUtil import SysUtil


try:
    logging.config.fileConfig("logging.ini")
    logging.getLogger("paramiko").setLevel(logging.WARNING)
except:
    pass

# default keyserver
keyserver = "traitcapture.org"


def serialize_signature(signature: bytes) -> str:
    """
    formats the signature for the server, with the correct boundaries

    :param signature: raw bytes signature.
    :type signature: bytes
    :return: str formatted signature for sending to the server.
    """
    signature = b64encode(signature).decode("utf-8")
    signature = textwrap.fill(signature, 43)
    return "\n-----BEGIN SIGNATURE-----\n{}\n-----END SIGNATURE-----\n".format(signature)


def ssh_public_key(keypair: rsa.RSAPrivateKeyWithSerialization) -> str:
    """
    converts an rsa keypair to openssh format public key

    :param keypair: keypair.
    :type keypair: cryptography.hazmat.primitives.asymmetric.rsa.RSAPrivateKeyWithSerialization
    :return: string of public key
    """
    eb = utils.int_to_bytes(keypair.public_key().public_numbers().e)
    nb = utils.int_to_bytes(keypair.public_key().public_numbers().n)
    if eb[0] & 0x80: eb = bytes([0x00]) + eb
    if nb[0] & 0x80: nb = bytes([0x00]) + nb
    keyparts = [b'ssh-rsa', eb, nb]
    keystring = b''.join([struct.pack(">I", len(kp)) + kp for kp in keyparts])
    return str(b'ssh-rsa ' + b64encode(keystring), encoding='utf-8')


class SSHManager(object):
    """
    a manager of ssh keys, with the ability to sign messages using them.

    """
    def __init__(self, path="/home/.ssh"):
        self._key = self.ssh_agentKey = None
        if not os.path.exists(path):
            homepath = os.path.join(os.environ['HOME'], ".ssh")
            if os.path.exists(homepath):
                path = homepath
        self.path = path
        self.logger = logging.getLogger("SFTP Key Manager")
        self.token_path = os.path.join(path, "key_token")
        if os.path.isfile(self.token_path):
            with open(self.token_path, 'r') as key_token_file:
                token = key_token_file.read().strip()
            self.logger.warning("Attempting to get new key from server with {}".format(token))
            if self.get_new_key_from_server(token):
                os.remove(self.token_path)

        self.priv_path = os.path.join(path, "id_rsa")
        self.pub_path = os.path.join(path, "id_rsa.pub")
        self.known_hosts_path = os.path.join(path, "known_hosts")
        self.authorized_keys_path = os.path.join(path, "authorized_keys")

        if os.path.isfile(self.priv_path) and not self._key:
            try:
                with open(self.priv_path, 'rb') as f:
                    self.ssh_key = f.read()
            except Exception as e:
                self.logger.error("couldnt find ssh key: {}".format(str(e)))
                self._key = None

    @property
    def paramiko_key(self):
        """
        property for a key usable by paramiko

        :return: agentKey for use by paramiko/pysftp
        :rtype: paramiko.rsakey.RSAKey
        """
        return self.ssh_agentKey

    @property
    def ssh_key(self):
        """
        ssh key property
        sets the internal rsa key and the agentKey for use by paramiko.

        """
        return self._key

    @ssh_key.setter
    def ssh_key(self, value):

        self._key = serialization.load_pem_private_key(value, password=None, backend=default_backend())
        pbytes = self._key.private_bytes(encoding=serialization.Encoding.PEM,
                                         format=serialization.PrivateFormat.TraditionalOpenSSL,
                                         encryption_algorithm=serialization.NoEncryption())
        key_io = io.StringIO(pbytes.decode("utf-8"))
        self.ssh_agentKey = paramiko.RSAKey.from_private_key(key_io)

    @property
    def public_ssh_key_string(self) -> str:
        """
        property for the public ssh key string.

        :return: string of the ssh public key, encoded to be added to a authorized_keys file
        :rtype: str
        """
        if self._key:
            return ssh_public_key(self._key)
        return str()

    def get_new_key_from_server(self, token):
        """
        acquires an ssh key from the server with a token and writes the key to the current path.

        :param token: a string token to send to the server.
        :return: boolean indicating whether the operation was successful.
        :rtype: bool
        """
        try:
            url = 'https://{}/api/camera/id_rsa/{}/{}/{}'.format(keyserver, token, SysUtil.get_machineid(),
                                                                                 SysUtil.get_hostname())
            self.logger.info("attempting to acquire key from {}".format(url))
            req = request.Request(url)
            handler = request.HTTPSHandler(context=ssl.SSLContext(ssl.PROTOCOL_TLSv1_2))
            opener = request.build_opener(handler)
            data = opener.open(req)
            d = data.read()

            self.ssh_key = d
            self.write_key_to_path()
            return True
        except request.HTTPError as e:
            self.logger.error("Couldnt get key, server returned {}".format(str(e)))
        except Exception as e:
            self.logger.error("Couldnt acquire ssh key from server: {}".format(str(e)))
        return False

    def write_key_to_path(self):
        """
        writes internally stored public and private keys to their respective paths
        """
        priv_bytes = self.ssh_key.private_bytes(encoding=serialization.Encoding.PEM,
                                                format=serialization.PrivateFormat.TraditionalOpenSSL,
                                                encryption_algorithm=serialization.NoEncryption())
        with open(self.priv_path, 'wb') as id_rsa:
            id_rsa.write(priv_bytes)

        os.chmod(self.priv_path, 0o600)

        ssh_key_string = self.public_ssh_key_string
        with open(self.pub_path, 'w') as id_rsa_pub:
            id_rsa_pub.write(ssh_key_string)
        os.chmod(self.pub_path, 0o644)

        with open(self.authorized_keys_path, 'w') as authorized_keys:
            authorized_keys.write(ssh_key_string)
        os.chmod(self.authorized_keys_path, 0o744)

    def sign_message_PKCS1v15(self, message) -> bytes:
        if not self._key:
            return b''
        msgbytes = bytes(message, "utf-8")
        signer = self._key.signer(
            padding.PKCS1v15(),
            hashes.SHA1())
        signer.update(msgbytes)
        # signature = b64encode(signer.finalize()).decode("utf-8")
        return msgbytes + b"|" + signer.finalize()

    def sign_message_PSS(self, message) -> bytes:
        if not self._key:
            return b''
        msgbytes = bytes(message, "utf-8")
        signer = self._key.signer(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=32
            ),
            hashes.SHA256())
        signer.update(msgbytes)
        # signature = b64encode(signer.finalize()).decode("utf-8")
        return msgbytes + b"|" + signer.finalize()

    def sign_message_PSS_b64(self, message) -> bytes:
        if not self._key:
            return b''
        msgbytes = bytes(message, "utf-8")
        signer = self._key.signer(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=32
            ),
            hashes.SHA256())
        signer.update(msgbytes)
        # signature = b64encode(signer.finalize()).decode("utf-8")
        return msgbytes + b"|" + b64encode(signer.finalize())

    def sign_message(self, message) -> str:
        """
        signs a text message using the internal key

        :param message: utf-8 encoded string
        :return: signature for message.
        :rtype: str
        """
        if not self._key:
            return message
        signer = self._key.signer(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256())
        signer.update(bytes(message, "utf-8"))
        return serialize_signature(signer.finalize())
