#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
from os import environ
from flask import request, _request_ctx_stack, abort, session
from functools import wraps
from jose import jwt
import urllib.request as uri
import yaml


# These are your environment variables
# you should implement them from the terminal.
# ex: export AUTH0_DOMAIN=YOUR_AUTH0_DOMAIN
# or  set AUTH0_DOMAIN=YOUR_AUTH0_DOMAIN
#     
AUTH0_DOMAIN = environ.get('AUTH0_DOMAIN')
ALGORITHMS = environ.get('ALGORITHMS')
API_AUDIENCE = environ.get('API_AUDIENCE')
YOUR_CLIENT_ID = environ.get('YOUR_CLIENT_ID')
YOUR_CLIENT_SECRET = environ.get('YOUR_CLIENT_SECRET')
YOUR_MNGM_API_CLIENT_ID = environ.get('YOUR_MNGM_API_CLIENT_ID')
YOUR_MNGM_API_CLIENT_SECRET = environ.get('YOUR_MNGM_API_CLIENT_SECRET')


# AuthError Exception

class AuthError(Exception):

    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


# Auth Header

def get_token_auth_header():
    if 'Authorization' not in session:
        raise AuthError({'code': 'authorization_header_missing',
                        'description': 'Authorization header is expected.'
                        }, 401)

    header = session.get('Authorization')
    header_parts = header.split(' ')

    if len(header_parts) == 1:

        raise AuthError({'code': 'invalid_header'}, 401)
    elif header_parts[0].lower() != 'bearer':

        raise AuthError({'code': 'invalid_header',
                        'description': 'Authorization header must start with "Bearer".'
                        }, 401)

    return header_parts[1]


def check_permissions(permission, payload):
    if 'permissions' not in payload:
        abort(400)

    if permission not in payload['permissions']:
        abort(401)

    return True


def verify_decode_jwt(token):

    # GET THE PUBLIC KEY FROM AUTH0

    jsonurl = uri.urlopen(f'https://{AUTH0_DOMAIN}/.well-known/jwks.json'
                          )
    jwks = json.loads(jsonurl.read())

    # GET THE DATA IN THE HEADER

    unverified_header = jwt.get_unverified_header(token)

    # CHOOSE OUR KEY

    rsa_key = {}
    if 'kid' not in unverified_header:
        raise AuthError({'code': 'invalid_header',
                        'description': 'Authorization malformed.'}, 401)

    for key in jwks['keys']:
        if key['kid'] == unverified_header['kid']:
            rsa_key = {
                'kty': key['kty'],
                'kid': key['kid'],
                'use': key['use'],
                'n': key['n'],
                'e': key['e'],
                }
    if rsa_key:
        try:

            # USE THE KEY TO VALIDATE THE JWT

            payload = jwt.decode(token, rsa_key, algorithms=ALGORITHMS,
                                 audience=API_AUDIENCE,
                                 issuer=f'https://{AUTH0_DOMAIN}/')

            return payload
        except jwt.ExpiredSignatureError:

            raise AuthError({'code': 'token_expired',
                            'description': 'Token expired.'}, 401)
        except jwt.JWTClaimsError:

            raise AuthError({'code': 'invalid_claims',
                            'description': 'Incorrect claims. Please, check the audience and issuer.'
                            }, 401)
        except Exception:
            raise AuthError({'code': 'invalid_header',
                            'description': 'Unable to parse authentication token.'
                            }, 400)
    raise AuthError({'code': 'invalid_header',
                    'description': 'Unable to find the appropriate key.'
                    }, 400)


def requires_auth(permission=''):

    def requires_auth_decorator(f):

        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_auth_header()
            payload = verify_decode_jwt(token)
            check_permissions(permission, payload)
            return f(payload, *args, **kwargs)

        return wrapper

    return requires_auth_decorator


def get_access_token(code):
    url = f'https://{AUTH0_DOMAIN}/oauth/token'
    headers = {}
    headers['content-type'] = 'application/x-www-form-urlencoded'
    data = \
        f'grant_type=authorization_code&client_id={YOUR_CLIENT_ID}&client_secret={YOUR_CLIENT_SECRET}&code={code}&redirect_uri=http://127.0.0.1:5000/'
    data = data.encode('ascii')
    req = uri.Request(url, data, headers)
    try:

        res = uri.urlopen(req)
    except uri.URLError as e:

        print ('URL Error: ', e.reason)
    except uri.HTTPError as e:

        print ('HTTP Error code: ', e.code)
    else:

        data_auth = res.read()
        da = data_auth.decode('ascii')
        dat = yaml.load(da, Loader=yaml.FullLoader)
        access_token = dat.get('access_token')
        session['Authorization'] = 'Bearer ' + access_token
        return access_token


def get_user_id(token):

    url2 = f'https://{AUTH0_DOMAIN}/userinfo'
    headers = {}
    headers['Authorization'] = 'Bearer ' + token
    req2 = uri.Request(url2, headers=headers)

    try:

        res2 = uri.urlopen(req2)
    except uri.URLError as e:

        print ('URL Error: ', e.reason)
    except uri.HTTPError as e:

        print ('HTTP Error code: ', e.code)
    else:

        user_info = res2.read()
        user_info_decoded = user_info.decode('ascii')
        user_info_valid = yaml.load(user_info_decoded,
                                    Loader=yaml.FullLoader)

        session['user_info'] = user_info_valid
        user_id = user_info_valid.get('sub')
        return user_id


def get_MGMT_API_ACCESS_TOKEN():

    url = f'https://{AUTH0_DOMAIN}/oauth/token'
    headers = {}
    headers['content-type'] = 'application/x-www-form-urlencoded'
    data = \
        f'grant_type=client_credentials&client_id={YOUR_MNGM_API_CLIENT_ID}&client_secret={YOUR_MNGM_API_CLIENT_SECRET}&audience=http://127.0.0.1:5000/'
    data = data.encode('ascii')
    req = uri.Request(url, data, headers)
    try:

        res = uri.urlopen(req)
    except uri.URLError as e:

        print ('URL Error: ', e.reason)
    except uri.HTTPError as e:

        print ('HTTP Error code: ', e.code)
    else:

        data_auth = res.read()
        data_decoded = data_auth.decode('ascii')
        data_valid = yaml.load(data_decoded, Loader=yaml.FullLoader)
        mngm_api_token = data_valid.get('access_token')
        return mngm_api_token
