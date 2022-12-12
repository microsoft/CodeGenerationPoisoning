from aiohttp.web import json_response
from json.decoder import JSONDecodeError
from rest_api.errors import *
from rest_api import elastic
from google.protobuf.json_format import MessageToJson

from Crypto.Cipher import AES
from protobuf.protobuf import payload_pb2

import time
import json
import datetime
import bcrypt
import requests
import base64


class RouterHandler(object):
    def __init__(self, loop, messenger):
        self._loop = loop
        self._messenger = messenger

    async def create_user(self, request):
        body = await decode_request(request)
        required_fields = ['username', 'email', 'password']
        await validate_fields(required_fields, body)

        public_key, private_key = self._messenger.get_new_key_pair()

        username = body.get('username')
        password = body.get('password')
        user = await elastic.get_user_by_username(username)
        if user:
            return json_response({
                "status": "Failure",
                "detail": "User already existed"
            })

        transaction_unique = await self._messenger.send_create_user_transaction(
            private_key=private_key,
            username=username,
            email=body.get('email'),
            timestamp=get_time()
        )
        transaction_unique_id = transaction_unique.transacsions[0].header_signature
        encrypted_private_key = encrypt_private_key(
            request.app['aes_key'], public_key, private_key)
        hashed_password = bcrypt.hashpw(bytes(password, 'utf-8'), bcrypt.gensalt())

        await elastic.create_user(
            username=username,
            mail=body.get('email'),
            hashed_password=hashed_password,
            public_key=public_key,
            encrypted_private_key=encrypted_private_key,
            transaction_unique_id=transaction_unique_id
        )
        return json_response({
            "status": "Success",
            "detail": "User created",
            "transaction_id": transaction_unique_id
        })

    async def login(self, request):
        body = await decode_request(request)
        required_fields = ['username', 'password']
        await validate_fields(required_fields, body)

        username = body.get('username')
        password = body.get('password')
        user = await elastic.get_user_by_username(username)
        if len(user) == 0:
            return json_response({
                "status": "Failure",
                "detail": "User does not exist"
            })

        hashed_password = user.get('hashed_password')
        if not bcrypt.checkpw(password, bytes.fromhex(hashed_password)):
            return json_response({
                "status": "Failure",
                "detail": "Wrong password"
            })

        username = user.get('username')
        return json_response({"status": "Success", "username": username})

    async def get_user(self, request):
        transaction_id = request.match_info.get('transaction_id', '')
        url = "http://rest-api:8008/transactions/" + str(transaction_id)
        # LOGGER.info(url)
        # url+=str(transaction_id)
        response = requests.get(url)
        if response.status_code == 200:
            try:
                transaction_dict = json.loads(response.content)
                payload_string = transaction_dict['data']['payload']
                data_model = payload_pb2.SimpleSupplyPayload()
                data_model.ParseFromString(base64.b64decode(payload_string))
                json_data = json.loads(MessageToJson(data_model, preserving_proto_field_name=True))
                return json_response({
                    "username": json_data['create_user']['username'],
                    "email": json_data['create_user']['email']
                })
            except:
                return json_response({'username': ""})
        return json_response({'username': ""})


async def decode_request(request):
    try:
        return await request.json()
    except JSONDecodeError:
        raise ApiBadRequest('Improper JSON format')


def validate_fields(required_fields, body):
    for field in required_fields:
        if body.get(field) is None:
            raise ApiBadRequest("'{}' parameter is required".format(field))


def get_time():
    dts = datetime.datetime.utcnow()
    return round(time.mktime(dts.timetuple()) + dts.microsecond/1e6)


def encrypt_private_key(aes_key, public_key, private_key):
    init_vector = bytes.fromhex(public_key[:32])
    cipher = AES.new(bytes.fromhex(aes_key), AES.MODE_CBC, init_vector)
    return cipher.encrypt(private_key)


def decrypt_private_key(aes_key, public_key, encrypted_private_key):
    init_vector = bytes.fromhex(public_key[:32])
    cipher = AES.new(bytes.fromhex(aes_key), AES.MODE_CBC, init_vector)
    private_key = cipher.decrypt(bytes.fromhex(encrypted_private_key))
    return private_key
