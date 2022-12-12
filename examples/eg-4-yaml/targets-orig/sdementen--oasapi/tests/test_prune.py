import copy

import yaml

from oasapi.events import (
    ReferenceNotUsedFilterAction,
    OAuth2ScopeNotUsedFilterAction,
    SecurityDefinitionNotUsedFilterAction,
    TagNotUsedFilterAction,
    PathsEmptyFilterError,
)
from oasapi.prune import (
    prune_unused_global_items,
    prune_unused_security_definitions,
    prune_unused_tags,
    prune,
    prune_empty_paths,
)


def test_prune_unused_references():
    swagger_str = """
    swagger: '2.0'
    info:
      version: v1.0
      title: my api
    paths:
      /foo:
        get:
          responses:
            200:
              $ref: "#/definitions/some-definition"
            400:
              $ref: "#/responses/some-response"
    definitions:
      some-definition: {}
    responses:
      some-response:
        $ref: "#/responses/some-other-response"
      some-other-response:
        $ref: "#/responses/some-another-response"
      some-another-response:
        $ref: "#/responses/some-response"
      some-unused-response:
        foo: baz

        """
    swagger = yaml.safe_load(swagger_str)

    swagger, actions = prune_unused_global_items(swagger)

    assert actions == [
        ReferenceNotUsedFilterAction(
            path=("responses", "some-unused-response"),
            reason="reference not used",
            type="Reference filtered out",
        )
    ]
    assert swagger == {
        "definitions": {"some-definition": {}},
        "info": {"title": "my api", "version": "v1.0"},
        "paths": {
            "/foo": {
                "get": {
                    "responses": {
                        200: {"$ref": "#/definitions/some-definition"},
                        400: {"$ref": "#/responses/some-response"},
                    }
                }
            }
        },
        "responses": {
            "some-another-response": {"$ref": "#/responses/some-response"},
            "some-other-response": {"$ref": "#/responses/some-another-response"},
            "some-response": {"$ref": "#/responses/some-other-response"},
        },
        "swagger": "2.0",
    }


def test_prune_unused_paths():
    swagger_str = """
    swagger: '2.0'
    info:
      version: v1.0
      title: my api
    paths:
      /foo: {}
      /baz:
        parameters: {}
      /biz:
        get: {}
        """
    swagger = yaml.safe_load(swagger_str)

    swagger, actions = prune_empty_paths(swagger)

    assert actions == [
        PathsEmptyFilterError(
            path=("paths", "/foo"),
            reason="path '/foo' has no operations defined",
            type="Path is empty",
        ),
        PathsEmptyFilterError(
            path=("paths", "/baz"),
            reason="path '/baz' has no operations defined",
            type="Path is empty",
        ),
    ]
    assert swagger == {
        "info": {"title": "my api", "version": "v1.0"},
        "paths": {"/biz": {"get": {}}},
        "swagger": "2.0",
    }


def test_prune_unused_security_definitions_empty():
    swagger = {"foo": "baz", "securityDefinitions": {}}
    swagger_pruned, actions = prune_unused_security_definitions(copy.deepcopy(swagger))
    assert swagger_pruned == {"foo": "baz"}
    assert not actions


def test_prune_unused_security_definitions():
    swagger_str = """
swagger: '2.0'
info:
  version: v1.0
  title: my api
paths:
  /foo:
    get:
      responses:
        200:
          description: OK
      security:
      - sec1: []
      - sec3: [existing-scope]
    PATCH:
      responses:
        200:
          description: OK
      security:
      - sec1: []
    parameters:
      security: [ {sec-not-exist-but-should-not-raise: []} ]
  security: [ {sec-not-exist-but-should-not-raise: []} ]
security: [{sec4:[]}]
securityDefinitions:
  sec1:
    type: basic
  sec2:
    type: basic
  sec4:
    type: basic
  sec-not-used:
    type: basic
  sec3:
    type: oauth2
    flow: implicit
    authorizationUrl: https://some-existing-auth-server.com
    scopes:
      existing-scope: this is an existing scope
      not-used-scope: this is an unused scope
"""
    swagger = yaml.safe_load(swagger_str)

    swagger, actions = prune_unused_security_definitions(swagger)
    assert swagger == {
        "info": {"title": "my api", "version": "v1.0"},
        "paths": {
            "/foo": {
                "PATCH": {"responses": {200: {"description": "OK"}}, "security": [{"sec1": []}]},
                "get": {
                    "responses": {200: {"description": "OK"}},
                    "security": [{"sec1": []}, {"sec3": ["existing-scope"]}],
                },
                "parameters": {"security": [{"sec-not-exist-but-should-not-raise": []}]},
            },
            "security": [{"sec-not-exist-but-should-not-raise": []}],
        },
        "security": [{"sec4": []}],
        "securityDefinitions": {
            "sec1": {"type": "basic"},
            "sec3": {
                "authorizationUrl": "https://some-existing-auth-server.com",
                "flow": "implicit",
                "scopes": {"existing-scope": "this is an " "existing " "scope"},
                "type": "oauth2",
            },
            "sec4": {"type": "basic"},
        },
        "swagger": "2.0",
    }
    assert actions == [
        SecurityDefinitionNotUsedFilterAction(
            path=("securityDefinitions", "sec2"),
            reason="security definition not used",
            type="Security definition removed",
        ),
        SecurityDefinitionNotUsedFilterAction(
            path=("securityDefinitions", "sec-not-used"),
            reason="security definition not used",
            type="Security definition removed",
        ),
        OAuth2ScopeNotUsedFilterAction(
            path=("securityDefinitions", "sec3", "scopes", "not-used-scope"),
            reason="oauth2 scope not used",
            type="Oauth2 scope removed",
        ),
    ]


def test_prune_unused_tags():
    swagger_str = swagger_str = """
swagger: '2.0'
info:
  version: v1.0
  title: my api
paths:
  /foo:
    get:
      responses:
        200:
          description: OK
      tags: [one, two, three]
    patch:
      responses:
        200:
          description: OK
      tags: [one, four]
    put:
      responses:
        200:
          description: OK
      tags: []
    parameters:
      tags: [not-a-tag]
    tags: [not-a-tag]
  tags: [not-a-tag]
tags:
- name: one
  description: f
  externalDocs:
    url: http://foo.com
- name: two
  description: f
- name: three
- name: not-used
- name: not-a-tag
"""
    swagger = yaml.safe_load(swagger_str)
    swagger_pruned, actions = prune_unused_tags(copy.deepcopy(swagger))
    assert swagger_pruned["tags"] == [
        {"description": "f", "externalDocs": {"url": "http://foo.com"}, "name": "one"},
        {"description": "f", "name": "two"},
        {"name": "three"},
    ]
    assert actions == [
        TagNotUsedFilterAction(
            path=("tags", "[3]"),
            reason="tag definition for 'not-used' not used",
            type="Tag definition removed",
        ),
        TagNotUsedFilterAction(
            path=("tags", "[4]"),
            reason="tag definition for 'not-a-tag' not used",
            type="Tag definition removed",
        ),
    ]


def test_prune_no_tags():
    swagger = {"foo": "baz"}
    swagger_pruned, actions = prune_unused_tags(copy.deepcopy(swagger))
    assert swagger == swagger_pruned
    assert not actions


def test_prune_each_type():
    swagger_str = """
swagger: '2.0'
info:
  version: v1.0
  title: my api
paths:
  /foo:
    get:
      responses:
        200:
          description: OK
      tags: [one, two, three]
      security:
      - two: []
tags:
- name: not-used
securityDefinitions:
  one:
    type: basic
  two:
    type: oauth2
    flow: implicit
    authorizationUrl: http://foo.com
    scopes:
      one: my scope one
parameters:
  one:
    in: query
    name: one
    type: integer
responses:
  one:
    description: hello
definitions:
  one: {}
"""
    swagger = yaml.safe_load(swagger_str)
    swagger_pruned, actions = prune(swagger)

    assert swagger != swagger_pruned
    assert swagger_pruned == {
        "info": {"title": "my api", "version": "v1.0"},
        "paths": {
            "/foo": {
                "get": {
                    "responses": {200: {"description": "OK"}},
                    "security": [{"two": []}],
                    "tags": ["one", "two", "three"],
                }
            }
        },
        "securityDefinitions": {
            "two": {
                "authorizationUrl": "http://foo.com",
                "flow": "implicit",
                "scopes": {},
                "type": "oauth2",
            }
        },
        "swagger": "2.0",
    }
    assert actions == [
        TagNotUsedFilterAction(
            path=("tags", "[0]"),
            reason="tag definition for 'not-used' not used",
            type="Tag definition removed",
        ),
        ReferenceNotUsedFilterAction(
            path=("definitions", "one"), reason="reference not used", type="Reference filtered out"
        ),
        ReferenceNotUsedFilterAction(
            path=("responses", "one"), reason="reference not used", type="Reference filtered out"
        ),
        ReferenceNotUsedFilterAction(
            path=("parameters", "one"), reason="reference not used", type="Reference filtered out"
        ),
        SecurityDefinitionNotUsedFilterAction(
            path=("securityDefinitions", "one"),
            reason="security definition not used",
            type="Security definition removed",
        ),
        OAuth2ScopeNotUsedFilterAction(
            path=("securityDefinitions", "two", "scopes", "one"),
            reason="oauth2 scope not used",
            type="Oauth2 scope removed",
        ),
    ]
