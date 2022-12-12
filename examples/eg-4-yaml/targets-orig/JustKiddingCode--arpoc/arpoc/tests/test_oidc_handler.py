import io
import json
import re
import time
from unittest.mock import Mock, PropertyMock, mock_open, patch

import base64

import logging

import datetime

import pytest
import requests
import requests_mock
import yaml

import arpoc
import arpoc.cache
import arpoc.config

import arpoc.utils


def provider_config():
    return """{"issuer":"https://openid-provider.example.com/auth/realms/master","authorization_endpoint":"https://openid-provider.example.com/auth/realms/master/protocol/openid-connect/auth","token_endpoint":"https://openid-provider.example.com/auth/realms/master/protocol/openid-connect/token","token_introspection_endpoint":"https://openid-provider.example.com/auth/realms/master/protocol/openid-connect/token/introspect","userinfo_endpoint":"https://openid-provider.example.com/auth/realms/master/protocol/openid-connect/userinfo","end_session_endpoint":"https://openid-provider.example.com/auth/realms/master/protocol/openid-connect/logout","jwks_uri":"https://openid-provider.example.com/auth/realms/master/protocol/openid-connect/certs","check_session_iframe":"https://openid-provider.example.com/auth/realms/master/protocol/openid-connect/login-status-iframe.html","grant_types_supported":["authorization_code","implicit","refresh_token","password","client_credentials"],"response_types_supported":["code","none","id_token","token","id_token token","code id_token","code token","code id_token token"],"subject_types_supported":["public","pairwise"],"id_token_signing_alg_values_supported":["PS384","ES384","RS384","HS256","HS512","ES256","RS256","HS384","ES512","PS256","PS512","RS512"],"id_token_encryption_alg_values_supported":["RSA-OAEP","RSA1_5"],"id_token_encryption_enc_values_supported":["A128GCM","A128CBC-HS256"],"userinfo_signing_alg_values_supported":["PS384","ES384","RS384","HS256","HS512","ES256","RS256","HS384","ES512","PS256","PS512","RS512","none"],"request_object_signing_alg_values_supported":["PS384","ES384","RS384","ES256","RS256","ES512","PS256","PS512","RS512","none"],"response_modes_supported":["query","fragment","form_post"],"registration_endpoint":"https://openid-provider.example.com/auth/realms/master/clients-registrations/openid-connect","token_endpoint_auth_methods_supported":["private_key_jwt","client_secret_basic","client_secret_post","client_secret_jwt"],"token_endpoint_auth_signing_alg_values_supported":["RS256"],"claims_supported":["aud","sub","iss","auth_time","name","given_name","family_name","preferred_username","email"],"claim_types_supported":["normal"],"claims_parameter_supported":false,"scopes_supported":["openid","address","email","microprofile-jwt","offline_access","phone","profile","roles","test","web-origins"],"request_parameter_supported":true,"request_uri_parameter_supported":true,"code_challenge_methods_supported":["plain","S256"],"tls_client_certificate_bound_access_tokens":true,"introspection_endpoint":"https://openid-provider.example.com/auth/realms/master/protocol/openid-connect/token/introspect"}"""


@pytest.fixture
def client_secrets():
    secrets_string = """test:
  client_id: e506b29d-e92c-4db9-974f-0d8e8a1406c5
  client_id_issued_at: 1578579842
  client_secret: 723d86e0-5388-4bb1-a286-c964e2187586
  client_secret_expires_at: 0
  grant_types:
  - authorization_code
  - refresh_token
  redirect_uris:
  - https://python-proxy.example.com/secure/redirect_uris
  registration_access_token: eyJhbGciOiJIUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICI1ZGYxY2VkMi1jMWY2LTQ5ZmQtYWUxYy00ZDU0MmQ0MWZmNzgifQ.eyJqdGkiOiJiMWE2ODExOC0zODE3LTQ4ZTYtOGQwZC01MWJlOTVlOGY4ZDgiLCJleHAiOjAsIm5iZiI6MCwiaWF0IjoxNTc4NTc5ODQyLCJpc3MiOiJodHRwczovL29wZW5pZC1wcm92aWRlci5leGFtcGxlLmNvbS9hdXRoL3JlYWxtcy9tYXN0ZXIiLCJhdWQiOiJodHRwczovL29wZW5pZC1wcm92aWRlci5leGFtcGxlLmNvbS9hdXRoL3JlYWxtcy9tYXN0ZXIiLCJ0eXAiOiJSZWdpc3RyYXRpb25BY2Nlc3NUb2tlbiIsInJlZ2lzdHJhdGlvbl9hdXRoIjoiYXV0aGVudGljYXRlZCJ9.ewxU3fUGReGqOA7RVwWHyQzITDOMeQeGA9DDoF_EMYk
  registration_client_uri: https://openid-provider.example.com/auth/realms/master/clients-registrations/openid-connect/e506b29d-e92c-4db9-974f-0d8e8a1406c5
  response_types:
  - code
  - none
  subject_type: public
  tls_client_certificate_bound_access_tokens: false
  token_endpoint_auth_method: client_secret_basic
"""
    return yaml.safe_load(secrets_string)


@pytest.fixture
def setup_jwt():
    return "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJ6cWlXUmpGTk53ZUkybVhjSjZRZUluaGVBSUNhYWZBVjF1TWlnbVk4ZDVnIn0.eyJqdGkiOiJmYTQxMWM3My05MGNjLTQwNWItYTdjYy1mYzM1NTdiNWZmZjkiLCJleHAiOjE1Nzk3Nzc0NzQsIm5iZiI6MCwiaWF0IjoxNTc5Nzc3NDE0LCJpc3MiOiJodHRwczovL29wZW5pZC1wcm92aWRlci5leGFtcGxlLmNvbS9hdXRoL3JlYWxtcy9tYXN0ZXIiLCJhdWQiOlsiZ2F0ZWtlZXBlciIsIm1hc3Rlci1yZWFsbSIsImFjY291bnQiXSwic3ViIjoiOWZlOWUwNmEtNjBjNi00ZGM1LWFkNWItNjYzZjAwNmNiNGY5IiwidHlwIjoiQmVhcmVyIiwiYXpwIjoiZDNkMjljMzctNGM4MC00NzY1LWJmM2MtNTgxYzVmYTg0OTY4IiwiYXV0aF90aW1lIjoxNTc5MTY5NTI5LCJzZXNzaW9uX3N0YXRlIjoiMzg3MGJlOGEtNWUyMi00NWNhLTg1NGQtYWQ1MjBmMDlhMzM4IiwiYWNyIjoiMCIsImFsbG93ZWQtb3JpZ2lucyI6WyJodHRwOi8vbG9jYWxob3N0OjgwODAiXSwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbImNyZWF0ZS1yZWFsbSIsIm9mZmxpbmVfYWNjZXNzIiwiYWRtaW4iLCJ1bWFfYXV0aG9yaXphdGlvbiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImdhdGVrZWVwZXIiOnsicm9sZXMiOlsidGVzdCJdfSwibWFzdGVyLXJlYWxtIjp7InJvbGVzIjpbInZpZXctaWRlbnRpdHktcHJvdmlkZXJzIiwidmlldy1yZWFsbSIsIm1hbmFnZS1pZGVudGl0eS1wcm92aWRlcnMiLCJpbXBlcnNvbmF0aW9uIiwiY3JlYXRlLWNsaWVudCIsIm1hbmFnZS11c2VycyIsInF1ZXJ5LXJlYWxtcyIsInZpZXctYXV0aG9yaXphdGlvbiIsInF1ZXJ5LWNsaWVudHMiLCJxdWVyeS11c2VycyIsIm1hbmFnZS1ldmVudHMiLCJtYW5hZ2UtcmVhbG0iLCJ2aWV3LWV2ZW50cyIsInZpZXctdXNlcnMiLCJ2aWV3LWNsaWVudHMiLCJtYW5hZ2UtYXV0aG9yaXphdGlvbiIsIm1hbmFnZS1jbGllbnRzIiwicXVlcnktZ3JvdXBzIl19LCJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6Im9wZW5pZCBvZmZsaW5lX2FjY2VzcyBlbWFpbCBwcm9maWxlIiwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJhZG1pbiJ9.uWLDJ9IkzgY9EzoGQHRv-Wlx--B16C4A2gnGvk1g-84vShA61Wt8BLiAKbZEJWBrRJsGP8LSGIhEWbdZ8_fJmz9QPAtQbyo4fAN-nh2MLJvEcO1gSf2NnHgp47e3MowVSeh0xx8Gx9N_2JCHLwkBfdgejJVqAngMcw2N6m-2BesHvpEm_5zSQ4ARqTbj3GbGClQm88ZLRKfLrijS4x5Hidajndi2mSsQaFgY-Ct2P9Pao7DoUXPDxv5dvU0qlo9lXjv7qTDOVsrBHMhBP57kejbvsnc_O7BNhOtoQMwszrgHFsAVPumyEQmoVcDwfMkHY7ejSdSDWMeLHvCBsReuqg"


def registration_response():
    response = """  {
   "client_id": "s6BhdRkqt3",
   "client_secret":
     "ZJYCqe3GGRvdrudKyZS0XhGv_Z45DuKhCUk0gBR1vZk",
   "client_secret_expires_at": 1577858400,
   "registration_access_token":
     "accesstoken",
   "registration_client_uri":
     "https://openid-provider.example.com/connect/register?client_id=s6BhdRkqt3",
   "token_endpoint_auth_method":
     "client_secret_basic",
   "application_type": "web",
   "redirect_uris":
     ["https://testhost.example.org/redirect"],
   "client_name": "My Example",
   "logo_uri": "https://client.example.org/logo.png",
   "subject_type": "pairwise",
   "sector_identifier_uri":
     "https://other.example.net/file_of_redirect_uris.json",
   "jwks_uri": "https://client.example.org/my_public_keys.jwks",
   "userinfo_encrypted_response_alg": "RSA1_5",
   "userinfo_encrypted_response_enc": "A128CBC-HS256",
   "contacts": ["test@example.com"],
   "request_uris":
     ["https://client.example.org/rf.txt
       #qpXaRLh_n93TTR9F252ValdatUQvQiJi5BDub2BeznA"]
  }"""
    return re.sub(r'\s+', ' ', response)


def registration_response_error():
    response = """  { "error": "invalid_redirect_uri", "error_description": "Blub" } """
    return re.sub(r'\s+', ' ', response)


@pytest.fixture
def mock_handler():
    with requests_mock.mock() as m:
        yield m


@pytest.fixture
def setup_oidc_handler():
    cfg = arpoc.config.OIDCProxyConfig(None, None)
    proxyconfig = arpoc.config.ProxyConfig(
        "", "", "testhost.example.com", ["test@example.com"],
        ["testhost.example.com/redirect"])
    cfg.proxy = proxyconfig
    service_cfg = arpoc.config.ServiceConfig("", "", "")
    oidc_handler = arpoc.OidcHandler(cfg)
    return cfg, oidc_handler


@pytest.fixture
def mock_openid_config(mock_handler):
    mock_handler.get(
        "https://openid-provider.example.com/auth/realms/master/.well-known/openid-configuration",
        text=provider_config())
    return mock_handler


@pytest.fixture
def mock_client_registration(mock_openid_config):
    mock_openid_config.post(
        "https://openid-provider.example.com/auth/realms/master/clients-registrations/openid-connect",
        text=registration_response())
    return mock_openid_config


@pytest.fixture
def userinfo():
    return {"sub": "evil", "email": "evil@test.example.com"}


@pytest.fixture
def setup_oidchandler_provider(setup_oidc_handler, mock_client_registration):
    cfg, oidchandler = setup_oidc_handler
    provider_config_obj = arpoc.config.ProviderConfig(
        "https://testhost.example.com", "test",
        "https://openid-provider.example.com/auth/realms/master", "abcdef")
    oidchandler.register_first_time("test", provider_config_obj)
    cfg.add_provider("test", provider_config_obj)

    return cfg, oidchandler


@pytest.fixture
def mock_client_registration_special_uri(mock_openid_config):
    mock_openid_config.get(
        "https://openid-provider.example.com/auth/realms/master/registerme",
        text=registration_response())
    return mock_openid_config


@pytest.fixture
def mock_userinfo(mock_handler, userinfo):
    mock_handler.register_uri(
        'POST',
        "https://openid-provider.example.com/auth/realms/master/protocol/openid-connect/userinfo",
        text=json.dumps(userinfo),
        headers={'content-type': 'application/json'})


@pytest.fixture
def mock_introspect(mock_handler):
    token_introspection = {"active": True}
    mock_handler.register_uri(
        'POST',
        "https://openid-provider.example.com/auth/realms/master/protocol/openid-connect/token/introspect",
        text=json.dumps(token_introspection),
        headers={'content-type': 'application/json'})


@pytest.fixture
def mock_introspect_exp(mock_handler):
    token_introspection = {"active": True, 'exp': 100}
    mock_handler.register_uri(
        'POST',
        "https://openid-provider.example.com/auth/realms/master/protocol/openid-connect/token/introspect",
        text=json.dumps(token_introspection),
        headers={'content-type': 'application/json'})


@pytest.fixture
def setup_oidchandler_provider_registration(
    setup_oidc_handler, mock_client_registration_special_uri):
    cfg, oidchandler = setup_oidc_handler
    provider_config_obj = arpoc.config.ProviderConfig(
        "https://testhost.example.com", "test",
        "https://openid-provider.example.com/auth/realms/master", "", "abcdef",
        "https://openid-provider.example.com/auth/realms/master/registerme")
    oidchandler.register_first_time("test", provider_config_obj)

    cfg.add_provider("test", provider_config_obj)

    return cfg, oidchandler


@pytest.fixture
def id_token():
    def _foo(iat,
             exp,
             sub="abcdef",
             aud="s6BhdRkqt3",
             iss="https://openid-provider.example.com/auth/realms/master"):
        id_token_payload_dict = {
            "iat": iat,
            "exp": exp,
            "sub": sub,
            "aud": [aud],
            "iss": iss
        }
        return id_token_payload_dict

    return _foo


@pytest.fixture
def id_token_b64(id_token):
    def _foo(iat,
             exp,
             sub="abcdef",
             aud="s6BhdRkqt3",
             iss="https://openid-provider.example.com/auth/realms/master"):
        token = id_token(iat, exp, sub, aud, iss)
        id_token_header_dict = {"alg": "none", "typ": "jwt"}
        id_token_header = base64.b64encode(
            json.dumps(id_token_header_dict).encode())
        id_token_payload = base64.b64encode(json.dumps(token).encode())
        return "{}.{}".format(id_token_header.decode(),
                              id_token_payload.decode())

    return _foo


@pytest.fixture
def mock_token_response(mock_handler, id_token_b64):
    def _foo(iat,
             exp,
             sub="abcdef",
             aud="s6BhdRkqt3",
             iss="https://openid-provider.example.com/auth/realms/master",
             access_token="1234567890ABCDEF",
             refresh_token="dead",
             grant_type='authorization_code'):
        token = id_token_b64(iat, exp, sub, aud, iss)
        code_matcher = lambda x: 'grant_type={}'.format(grant_type) in (x.text
                                                                        or '')
        token_response = {
            "access_token": access_token,
            "token_type": "Bearer",
            "refresh_token": refresh_token,
            "expires_in": 200,
            "id_token": token,
            "scope": "openid",
            "refresh_expires_in": 1000
        }
        mock_handler.post(
            "https://openid-provider.example.com/auth/realms/master/protocol/openid-connect/token",
            json=token_response,
            headers={'content-type': 'application/json'},
            additional_matcher=code_matcher)
        return mock_handler

    return _foo


###########################
#         TESTS           #
###########################


def test_get_secrets(setup_oidchandler_provider):
    cfg, oidchandler = setup_oidchandler_provider
    secrets = oidchandler.get_secrets()
    assert secrets['test']['client_id'] == 's6BhdRkqt3'
    assert secrets['test'][
        'client_secret'] == 'ZJYCqe3GGRvdrudKyZS0XhGv_Z45DuKhCUk0gBR1vZk'


def test_register_first_time_registration(
    setup_oidchandler_provider_registration):
    assert True


def test_register_first_time_configuration(setup_oidchandler_provider):
    assert True


def test_register_first_time_config_error(
    setup_oidc_handler, caplog, mock_client_registration_special_uri):
    cfg, oidchandler = setup_oidc_handler

    configuration_url = ""
    configuration_token = ""
    registration_token = ""
    registration_url = ""
    provider_config_obj = arpoc.config.ProviderConfig(
        "https://testhost.example.com", "test", configuration_url,
        configuration_token, registration_token, registration_url)

    configuration_url = ""
    configuration_token = ""
    registration_token = "abcde"
    registration_url = "https://openid-provider.example.com/auth/realms/master/registerme",
    provider_config_obj = arpoc.config.ProviderConfig(
        "https://testhost.example.com", "test", configuration_url,
        configuration_token, registration_token, registration_url)

    with pytest.raises(arpoc.exceptions.OIDCProxyException):
        oidchandler.register_first_time("test", provider_config_obj)


def test_register_first_time_lib_error(setup_oidc_handler, caplog,
                                       mock_openid_config):
    # force lib error
    cfg, oidchandler = setup_oidc_handler
    m = mock_openid_config
    registration_url = "https://openid-provider.example.com/auth/realms/master/registerme"
    m.get(
        "https://openid-provider.example.com/auth/realms/master/.well-known/openid-configuration",
        text=provider_config())
    m.get(registration_url,
          text=registration_response_error(),
          status_code=400)

    configuration_url = "https://openid-provider.example.com/auth/realms/master/"
    configuration_token = ""
    registration_token = "abcde"
    provider_config_obj = arpoc.config.ProviderConfig(
        "https://testhost.example.com", "test", configuration_url,
        configuration_token, registration_token, registration_url)

    oidchandler.register_first_time("test", provider_config_obj)
    assert "Provider test returned an error on registration" in caplog.text


def test_create_client_from_secrets(setup_oidchandler_provider, client_secrets,
                                    mock_openid_config):
    cfg, provider = setup_oidchandler_provider
    provider._secrets = client_secrets
    provider.create_client_from_secrets("test", cfg.openid_providers['test'])


#############################
# get_userinfo_access_token #
#############################


def test_get_userinfo_access_token_no_exp(setup_oidchandler_provider,
                                          setup_jwt, mock_introspect,
                                          mock_userinfo, userinfo):
    _, oidc_handler = setup_oidchandler_provider
    access_token = setup_jwt
    now = arpoc.utils.now()
    valid_should = now + 30

    valid, resp_userinfo = oidc_handler.get_userinfo_access_token(access_token)
    assert valid < valid_should + 10
    assert valid > valid_should - 10
    assert dict(resp_userinfo) == userinfo

def test_get_userinfo_access_token_no_jwt(setup_oidchandler_provider, mock_userinfo, mock_introspect_exp, userinfo):
    _, oidc_handler = setup_oidchandler_provider
    with pytest.raises(Exception):
        oidc_handler.get_userinfo_access_token("test")


@patch('arpoc.cherrypy.request.headers', {'x-arpoc-issuer':"https://openid-provider.example.com/auth/realms/master" }, create=True)
def test_get_userinfo_access_token_no_jwt_with_hint(setup_oidchandler_provider, mock_userinfo, mock_introspect_exp, userinfo):
    _, oidc_handler = setup_oidchandler_provider
    valid, resp_userinfo = oidc_handler.get_userinfo_access_token("test")
    assert valid == 100
    assert dict(resp_userinfo) == userinfo


def test_get_userinfo_access_token(setup_oidchandler_provider, setup_jwt,
                                   mock_userinfo, mock_introspect_exp,
                                   userinfo):
    _, oidc_handler = setup_oidchandler_provider
    access_token = setup_jwt

    #    arpoc.oic.oauth2.base.requests = requests
    #    arpoc.oic.extension.message.requests = requests
    valid, resp_userinfo = oidc_handler.get_userinfo_access_token(access_token)
    assert valid == 100
    assert dict(resp_userinfo) == userinfo


def test_get_userinfo_access_token_no_provider(setup_jwt, setup_oidc_handler):
    access_token = setup_jwt
    _, oidc_handler = setup_oidc_handler

    #    arpoc.oic.oauth2.base.requests = requests
    #    arpoc.oic.extension.message.requests = requests
    valid, resp_userinfo = oidc_handler.get_userinfo_access_token(access_token)
    assert (valid, dict(resp_userinfo)) == (0, {})


#########################
# check_session_refresh #
#########################


@patch('arpoc.cherrypy.session', {'refresh': 1579702851}, create=True)
def test_check_session_refresh(setup_oidc_handler):
    _, oidc_handler = setup_oidc_handler
    #    arpoc.cherrypy.session['refresh'] = 1579702851 # Mi 22. Jan 15:21 2020
    assert oidc_handler._check_session_refresh()


@patch('arpoc.cherrypy.session', {'refresh': time.time() + 30},
       create=True)
def test_check_session_refresh_in_future(setup_oidc_handler):
    _, oidc_handler = setup_oidc_handler
    assert not oidc_handler._check_session_refresh()


@patch('arpoc.cherrypy.session', {''}, create=True)
def test_check_session_refresh_without_time(setup_oidc_handler):
    _, oidc_handler = setup_oidc_handler
    assert not oidc_handler._check_session_refresh()


###############
# need_claims #
###############


@patch('arpoc.cherrypy.session', {}, create=True)
def test_need_claims_without_provider(setup_oidchandler_provider):
    claims = []
    _, provider = setup_oidchandler_provider
    with pytest.raises(arpoc.cherrypy._cperror.HTTPRedirect):
        provider.need_claims(claims)


@patch('arpoc.cherrypy.session', {"provider": "test"}, create=True)
def test_need_claims_with_provider(setup_oidchandler_provider):
    claims = ["email", "profile"]
    _, provider = setup_oidchandler_provider
    with pytest.raises(arpoc.cherrypy._cperror.HTTPRedirect):
        provider.need_claims(claims)


#################################
# get_access_token_from_headers #
#################################


@patch('arpoc.cherrypy.request.headers', {"authorization": "hello"},
       create=True)
def test_get_access_token_from_headers(setup_oidc_handler):
    _, oidc_handler = setup_oidc_handler
    assert oidc_handler.get_access_token_from_headers() == None


@patch('arpoc.cherrypy.request.headers', {"authorization": "bearer 123"},
       create=True)
def test_get_access_token_from_headers_small(setup_oidc_handler):
    _, oidc_handler = setup_oidc_handler
    assert oidc_handler.get_access_token_from_headers() == "123"


@patch('arpoc.cherrypy.request.headers',
       {"authorization": "BeArEr teststring"},
       create=True)
def test_get_access_token_from_headers_mixed(setup_oidc_handler):
    _, oidc_handler = setup_oidc_handler
    assert oidc_handler.get_access_token_from_headers() == "teststring"


########################
# refresh_access_token #
########################
@patch('arpoc.cherrypy.session', {
    "provider": "test",
    "scopes": ["openid"],
    "url": "http://test/"
},
       create=True)
def test_refresh_access_token(caplog, setup_oidchandler_provider,
                              mock_token_response):
    caplog.set_level(logging.DEBUG)
    _, oidc_handler = setup_oidchandler_provider
    userinfo = {"sub": "abcdef", "email": "evil@test.example.com"}
    now = arpoc.utils.now()
    mocker = mock_token_response(now, now + 500)
    mocker.register_uri(
        'POST',
        "https://openid-provider.example.com/auth/realms/master/protocol/openid-connect/userinfo",
        text=json.dumps(userinfo),
        headers={'content-type': 'application/json'})

    state = 'abcde'
    code = 'efabc'
    with pytest.raises(arpoc.cherrypy._cperror.HTTPRedirect):
        oidc_handler.redirect(state=state, code=code)

    print(oidc_handler._cache.data)
    dnow = arpoc.utils.now()
    future = dnow + 500
    logging.debug('time warp to: %s', future)

    mock_token_response(future,
                        future + 500,
                        access_token="ABCDEF",
                        refresh_token="DEAF",
                        grant_type='refresh_token')

    with patch('oic.oic.time_util.utc_time_sans_frac', Mock(return_value=future)),\
        patch('oic.oic.time_util.time_sans_frac', Mock(return_value=future)),\
        patch('oic.oauth2.grant.utc_time_sans_frac', Mock(return_value=future)):
        hash_at = next(iter(oidc_handler._cache.data))
        oidc_handler.refresh_access_token(hash_at)

        new_hash_at = next(iter(oidc_handler._cache.data))
        assert hash_at != new_hash_at
        assert oidc_handler._cache.data[new_hash_at][
            'valid_until'] == future + 200
        assert 'oic.oic.message.RefreshAccessTokenRequest' in caplog.text


################
# get_userinfo #
################


def test_get_userinfo():
    assert False


##########################
# get_validity_from_resp #
##########################


def test_get_validity_from_resp():
    assert False


##################################
# do_userinfo_request_with_state #
##################################


def test_do_userinfo_request_with_state():
    assert False


##############################
# get_access_token_from_code #
##############################


@patch('arpoc.cherrypy.session', {"provider": "test"}, create=True)
def test_get_access_token_from_code(setup_oidchandler_provider,
                                    mock_token_response, id_token):
    _, oidc_handler = setup_oidchandler_provider
    now = arpoc.utils.now()
    id_token_dict = id_token(now, now + 500)
    mocker = mock_token_response(now, now + 500)
    state = 'abcde'
    code = 'efabc'
    token = oidc_handler.get_access_token_from_code(state, code)
    assert dict(token.id_token) == id_token_dict


################
# check_scopes #
################


def test_check_scopes():
    assert False


############
# redirect #
############


@patch('arpoc.cherrypy.session', {
    "provider": "test",
    "scopes": ["openid"],
    "url": "http://test/"
},
       create=True)
def test_redirect(setup_oidchandler_provider, mock_token_response):
    _, oidc_handler = setup_oidchandler_provider
    userinfo = {"sub": "abcdef", "email": "evil@test.example.com"}
    now = arpoc.utils.now()
    mocker = mock_token_response(now, now + 500)
    mocker.register_uri(
        'POST',
        "https://openid-provider.example.com/auth/realms/master/protocol/openid-connect/userinfo",
        text=json.dumps(userinfo),
        headers={'content-type': 'application/json'})

    state = 'abcde'
    code = 'efabc'
    with pytest.raises(arpoc.cherrypy._cperror.HTTPRedirect):
        oidc_handler.redirect(state=state, code=code)


#########
# _auth #
#########


def test__auth():
    assert False
