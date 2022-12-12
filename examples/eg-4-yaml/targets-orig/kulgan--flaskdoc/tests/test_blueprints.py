import json

import flask
import pytest
import yaml
from openapi_spec_validator import validate_spec


@pytest.mark.parametrize("sample", ["hulu", "polo"])
def test_route_decorator(client, sample):
    """Tests extension registers routes as expected"""

    resp = client.get(flask.url_for("mocks.echo", sample=sample))
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == sample

    post_body = dict(sample=sample, message="Almighty")
    resp = client.post(flask.url_for("mocks.post"), data=json.dumps(post_body))
    assert resp.status_code == 200
    assert resp.json == post_body


def test_registered_openapi(client):
    """Tests the endpoints for downloading openapi spec was registered"""

    # test availability of /openapi.json
    response = client.get(flask.url_for("flaskdoc.json_path"))
    api_docs = response.json

    info_block = api_docs["info"]
    assert info_block["contact"]["email"] == "apiteam@swagger.io"

    response = client.get(flask.url_for("flaskdoc.yaml_path"))
    api_docs = yaml.safe_load(response.data)
    info_block = api_docs["info"]
    assert info_block["contact"]["email"] == "apiteam@swagger.io"


def test_mocks_spec_is_valid(client):
    r = client.get("/docs/openapi.json")
    print(json.dumps(r.json, indent=2))
    validate_spec(r.json)
