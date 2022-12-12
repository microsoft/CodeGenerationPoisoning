
import pytest
import yaml
import asynctest
import aiohttp

from unittest.mock import patch, MagicMock

from .fixtures import SessionMock, ResponseMock
from pathlib import Path

from aionetbox.api import (
    NetboxResponseObject,
    NetboxApiOperation,
    NetboxApi,
    AIONetbox,
    ResolvingParser,
)

from aionetbox.exceptions import (
    InvalidResponse,
    MissingRequiredParam,
    BadRequest,
    InvalidRequest,
)

here = Path(__file__).parent


def test_NetboxResponseObject_from_response_no_type():

    with pytest.raises(AttributeError):
        NetboxResponseObject.from_response(data={})


def test_NetboxResponseObject_from_response():
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))

    schema = spec.specification['paths']['/users/{userId}']['get']['responses']['200']['schema']

    data = {
        'id': 1,
        'name': 'Marco Ceppi',
        'cars': [
            {
                'make': 'MG',
                'model': 'BGT',
                'year': 1974,
                'problems': None
            },
            {
                'make': 'Triumph',
                'model': 'TR6',
                'year': 1974,
                'problems': [
                    'oil leak'
                ]
            }
        ],
        'address': {
            'number': 123,
            'street': 'Main St',
        }
    }

    n = NetboxResponseObject.from_response(data=data, **schema)

    assert n.id == 1
    assert n.cars[0].model == 'BGT'


def test_NetboxResponseObject_repr():
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))
    schema = spec.specification['paths']['/users/{userId}']['get']['responses']['200']['schema']

    data = {
        'id': 1,
        'name': 'Marco Ceppi',
        'cars': [
            {
                'make': 'MG',
                'model': 'BGT',
                'year': 1974,
                'problems': []
            },
            {
                'make': 'Triumph',
                'model': 'TR6',
                'year': 1974,
                'problems': [
                    'oil leak'
                ]
            }
        ],
        'address': {
            'number': 123,
            'street': 'Main St',
        }
    }

    n = NetboxResponseObject.from_response(data=data, **schema)

    assert yaml.safe_load(str(n)) == data


def test_NetboxResponseObject_from_invalid_response():
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))
    schema = spec.specification['paths']['/users/{userId}']['get']['responses']['200']['schema']

    data = {
        'id': 1,
        'name': 'Marco Ceppi',
        'cars': [
            {
                'make': 'MG',
                'model': 'BGT',
                'year': 1974,
            },
            {
                'model': 'TR6',
                'year': 1974,
            }
        ]
    }

    with pytest.raises(InvalidResponse):
        NetboxResponseObject.from_response(data=data, **schema)


def test_NetboxApiOperation():
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))
    nb = AIONetbox(host='http://localhost', api_key='11', spec=spec, session=SessionMock())
    op = NetboxApiOperation('users', 'users_read', {}, nb)

    assert repr(op) == 'Netbox.users.users_read'


def test_NetboxApiOperation_build_url():
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))
    nb = AIONetbox(host='http://localhost', api_key='11', spec=spec, session=SessionMock())
    op = NetboxApiOperation('users', 'users_read', {}, nb)

    assert 'http://localhost/v1/test' == op.build_url('/test')


def test_NetboxApiOperation_parse_params():
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))
    nb = AIONetbox(host='http://localhost', api_key='11', spec=spec, session=SessionMock())
    op = NetboxApiOperation('users', 'users_list', nb.config['users']['users_list'], nb)

    assert ({}, {}, {}) == op.parse_params({})

    params = {'name': 'foobar', 'bad_param': True}
    parsed = op.parse_params(params)

    assert ({}, {}, {'name': 'foobar'}) == parsed

    op = NetboxApiOperation('users', 'users_read', nb.config['users']['users_read'], nb)

    params = {'userId': 1}
    parsed = op.parse_params(params)

    assert ({'userId': 1}, {}, {}) == parsed

    with pytest.raises(MissingRequiredParam):
        op.parse_params({})


def test_NetboxApiOperation_parse_params_body():
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))
    nb = AIONetbox(host='http://localhost', api_key='11', spec=spec, session=SessionMock())
    op = NetboxApiOperation('users', 'users_create', nb.config['users']['users_create'], nb)

    params = {'data': {'foobar': 'bar', 'baz': True}}
    parsed = op.parse_params(params)

    assert ({}, {'foobar': 'bar', 'baz': True}, {}) == parsed


def test_NetboxApiOperation_operation_method():
    op = NetboxApiOperation('users', 'users_read', {}, {})
    assert 'read' == op.operation_method

    op = NetboxApiOperation('users', 'users_partial_update', {}, {})
    assert 'partial_update' == op.operation_method

    op = NetboxApiOperation('users', 'users_update', {}, {})
    assert 'update' == op.operation_method


@pytest.mark.asyncio
async def test_NetboxApiOperation_call():

    with patch.object(NetboxApiOperation, 'request') as mreq:
        mreq.side_effect = asynctest.MagicMock()
        op = NetboxApiOperation('users', 'users_read', {}, {})
        await op(foo='test')
        mreq.assert_called_with(foo='test')

    with patch.object(NetboxApiOperation, 'request') as mreq:
        mreq.side_effect = [MissingRequiredParam, aiohttp.ClientResponseError({}, {})]
        op = NetboxApiOperation('users', 'users_read', {}, {})

        with pytest.raises(AttributeError):
            await op(foo='test')

        with pytest.raises(BadRequest):
            await op(foo='test')


@pytest.mark.asyncio
@patch('aionetbox.api.NetboxResponseObject')
async def test_NetboxApiOperation_request(mnbro):
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))
    nb = AIONetbox(host='http://localhost', api_key='11', spec=spec, session=SessionMock())
    nb.request = asynctest.CoroutineMock(return_value=ResponseMock())
    op = NetboxApiOperation('users', 'users_read', nb.config['users']['users_read'], nb)

    response_schema = spec.specification['paths']['/users/{userId}']['get']['responses']['200']['schema']
    op.parse_params = MagicMock(return_value=({}, {}, {}))
    op.build_url = MagicMock()

    await op.request(userId=42)

    mnbro.from_response.assert_called_with(data={}, **response_schema)


@pytest.mark.asyncio
@patch('aionetbox.api.NetboxResponseObject')
async def test_NetboxApiOperation_request_cf(mnbro):
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))
    nb = AIONetbox(host='http://localhost', api_key='11', spec=spec, session=SessionMock())
    nb.request = asynctest.CoroutineMock(return_value=ResponseMock())
    op = NetboxApiOperation('users', 'users_list', nb.config['users']['users_list'], nb)

    mnbro.from_response.return_value.next = None

    response_schema = spec.specification['paths']['/users']['get']['responses']['200']['schema']
    op.parse_params = MagicMock(return_value=({}, {}, {'name': 'test'}))
    op.build_url = MagicMock(return_value='http://test/users')

    await op.request(name='test', cf_hello='world', extra='ignore')

    nb.request.assert_called_with(
        method='get',
        url='http://test/users',
        query_params={'name': 'test', 'cf_hello': 'world'},
        body={}
    )

    mnbro.from_response.assert_called_with(data={}, **response_schema)


@pytest.mark.asyncio
@patch('aionetbox.api.NetboxResponseObject')
async def test_NetboxApiOperation_request_pagination(mnbro):
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))
    nb = AIONetbox(host='http://localhost', api_key='11', spec=spec, session=SessionMock())
    nb.request = asynctest.CoroutineMock(return_value=ResponseMock())
    op = NetboxApiOperation('users', 'users_list', nb.config['users']['users_list'], nb)

    page0 = MagicMock()
    page1 = MagicMock()

    page0.next = 'http://test/users?limit=50&offset=50'
    page0.results = ['1', '2', '3']
    page1.next = None
    page1.results = ['one', 'two', 'three']

    mnbro.from_response.side_effect = [page0, page1]

    op.parse_params = MagicMock(return_value=({}, {}, {'name': 'test'}))
    op.build_url = MagicMock(return_value='http://test/users')

    results = await op.request(name='test')

    nb.request.assert_any_call(
        method='get',
        url='http://test/users',
        query_params={'name': 'test'},
        body={}
    )

    nb.request.assert_any_call(
        method='get',
        url='http://test/users',
        query_params={'name': 'test', 'limit': '50', 'offset': '50'},
        body={}
    )

    assert ['1', '2', '3', 'one', 'two', 'three'] == results.results


@pytest.mark.asyncio
async def test_NetboxApiOperation_request_delete():
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))
    nb = AIONetbox(host='http://localhost', api_key='11', spec=spec, session=SessionMock())
    nb.request = asynctest.CoroutineMock(return_value=ResponseMock())

    op = NetboxApiOperation('users', 'users_delete', nb.config['users']['users_delete'], nb)

    results = await op.request(userId=42)

    assert results


def test_NetboxApi():
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))
    nb = AIONetbox(host='http://localhost', api_key='11', spec=spec, session=SessionMock())
    api = NetboxApi('users', nb.config.get('users'), nb)

    assert repr(api) == 'Netbox.users'


@patch('aionetbox.api.NetboxApiOperation')
def test_NetboxApi_attr(mnbaop):
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))
    nb = AIONetbox(host='http://localhost', api_key='11', spec=spec, session=SessionMock())

    api = NetboxApi('users', nb.config.get('users'), nb)

    api.users_read
    api.users_read

    mnbaop.assert_called_once()
    mnbaop.assert_called_with('users', 'users_read', nb.config['users']['users_read'], nb)

    with pytest.raises(AttributeError):
        api.fake_method


@patch('aionetbox.api.NetboxSpec')
def test_AIONetbox_from_openapi(mrp):
    with patch.object(AIONetbox, 'parse_spec') as mps:
        AIONetbox.from_openapi('http://testurl', 'ab12cd34')
        mrp.assert_called_with('http://testurl/api/swagger.json')
        mps.assert_called_with(mrp.return_value)


def test_AIONetbox_from_spec():
    a = AIONetbox.from_spec(str(here / 'data' / 'openapi-2.yaml'), 'ab12cd34')

    assert a.host == 'https://api.example.com'


@pytest.mark.asyncio
async def test_AIONetbox_get_session_key():
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))
    nb = AIONetbox(host='http://localhost', api_key='11', spec=spec, session=SessionMock())
    nb.request = asynctest.CoroutineMock(return_value=ResponseMock())

    await nb.get_session_key('test')


@pytest.mark.asyncio
async def test_AIONetbox_get_session_key_fail():
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))
    nb = AIONetbox(host='http://localhost', api_key='11', spec=spec, session=SessionMock())

    resp = ResponseMock()
    nb.request = asynctest.CoroutineMock(return_value=resp)
    resp.json = asynctest.CoroutineMock(side_effect=[Exception])

    key = await nb.get_session_key('test')

    assert key is None


def test_AIONetbox_parse_spec():
    a = AIONetbox('http://localhost', '1122')
    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))

    assert {} == a.parse_spec(None)
    assert {} == a.parse_spec({})
    assert '_orig' in a.parse_spec(spec)
    assert 'users' in a.parse_spec(spec)
    assert 'fake' not in a.parse_spec(spec)
    assert 'users_list' in a.parse_spec(spec).get('users')


@pytest.mark.asyncio
async def test_AIONetbox_request_bad_params():
    s = SessionMock()
    a = AIONetbox('http://localhost', '1122', session=s)

    with pytest.raises(ValueError):
        await a.request('get', 'http://foobar', post_params={'hello': 'world'}, body={'wrong': True})

    s.request.assert_not_called()


@pytest.mark.asyncio
async def test_AIONetbox_request_invalid_content_type():
    s = SessionMock()
    a = AIONetbox('http://localhost', '1122', session=s)

    with pytest.raises(InvalidRequest):
        await a.request('put', 'http://foobar', headers={'Content-Type': 'broken'})

    s.request.assert_not_called()


@pytest.mark.asyncio
async def test_AIONetbox_request():
    s = SessionMock()
    a = AIONetbox('http://localhost', '1122', session=s)
    await a.request('post', 'http://foobar', query_params={'test': 'testing'}, body={'new_phone': 'whodis'})

    s.request.assert_called_with(
        method='POST',
        url='http://foobar',
        timeout=300,
        params={'test': 'testing'},
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Token 1122',
        },
        data='{"new_phone": "whodis"}'
    )


@pytest.mark.asyncio
@patch('aionetbox.api.aiohttp.FormData')
async def test_AIONetbox_request_form(maiofd):
    s = SessionMock()
    a = AIONetbox('http://localhost', '1122', session=s)

    await a.request(
        'post',
        'http://foobar',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        post_params={'new_phone': 'whodis'}
    )

    maiofd.assert_called_with({'new_phone': 'whodis'})

    s.request.assert_called_with(
        method='POST',
        url='http://foobar',
        timeout=300,
        params=None,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'Token 1122',
        },
        data=maiofd.return_value
    )


@pytest.mark.asyncio
async def test_AIONetbox_request_bytes():
    s = SessionMock()
    a = AIONetbox('http://localhost', '1122', session=s)

    data = b'yaml: cool'
    await a.request(
        'post',
        'http://foobar',
        headers={'Content-Type': 'application/yaml'},
        body=data
    )

    s.request.assert_called_with(
        method='POST',
        url='http://foobar',
        timeout=300,
        params=None,
        headers={
            'Content-Type': 'application/yaml',
            'Authorization': 'Token 1122',
        },
        data=data
    )


@pytest.mark.asyncio
async def test_AIONetbox_close():
    s = SessionMock()
    nb = AIONetbox(host='http://localhost', api_key='11', spec={}, session=s)
    await nb.close()
    s.close.assert_called()


@patch('aionetbox.api.NetboxApi')
def test_AIONetbox_attr(mnba):

    spec = ResolvingParser(str(here / 'data' / 'openapi-2.yaml'))
    nb = AIONetbox(host='http://localhost', api_key='11', spec=spec, session=SessionMock())

    nb.users
    nb.users

    mnba.assert_called_once()
    mnba.assert_called_with('users', nb.config['users'], nb)

    with pytest.raises(AttributeError):
        nb.fake_tag
