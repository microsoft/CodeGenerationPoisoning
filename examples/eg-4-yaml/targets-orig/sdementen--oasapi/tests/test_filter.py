import copy

import pytest
import yaml

from oasapi.events import OperationChangedFilterAction, OperationRemovedFilterAction
from oasapi.filter import filter, FilterCondition, resolve_security, generate_filter_conditions

swagger_str = """
swagger: '2.0'
info:
  version: v1.0
  title: my api
paths:
  /foo:
    get:
      tags: [tag1, tag2, tag3]
      security:
      - sec1: [read]
        sec2: [write]
    post:
      tags: [tag1]
      security:
      - sec1: [read, write, admin]
    patch:
      tags: [tag2]
      security:
      - sec2: [write]
  /foo/baz:
    get:
      tags: [tag3]
      security:
      - sec1: [read, write]
        sec2: [read]
    post:
      tags: [tag1, tag2]
    patch:
      tags: [tag2, tag3]
    put: {}
security:
- sec1: [read]
- sec2: [write]
"""


@pytest.fixture(scope="function")
def swagger():
    return yaml.safe_load(swagger_str)


def test_resolve_security(swagger):
    # add an endpoint without security
    swagger["paths"]["/no-security"] = dict(get={})
    # remember security of endpoint /foo/baz.get
    before = copy.deepcopy(swagger["paths"]["/foo/baz"]["get"]["security"])

    # resolve security
    resolve_security(swagger)

    # check security has changed on the /no-security.get operation but no on the other
    assert swagger["paths"]["/no-security"]["get"]["security"] == swagger["security"]
    assert swagger["paths"]["/foo/baz"]["get"]["security"] == before


def test_resolve_security_no_global_security(swagger):
    # add an endpoint without security
    del swagger["security"]

    # remember security of endpoint /foo/baz.get
    before = copy.deepcopy(swagger)

    # resolve security
    resolve_security(swagger)

    # check security has changed on the /no-security.get operation but no on the other
    assert swagger == before


def test_generate_filter_conditions_simple():
    filter = generate_filter_conditions([FilterCondition(tags=["tag1"])])

    assert not filter((), {})
    assert not filter((), dict(tags=["tag2"]))

    assert filter((), dict(tags=["tag1"])) == dict(tags=["tag1"])
    assert filter((), dict(tags=["tag2", "tag1"])) == dict(tags=["tag1"])


def test_generate_filter_conditions_two_no_merge():
    filter = generate_filter_conditions(
        [FilterCondition(tags=["tag1"]), FilterCondition(tags=["tag2"])]
    )
    assert not filter((), {})
    assert not filter((), dict(tags=["tag3"]))

    assert filter((), dict(tags=["tag1"])) == dict(tags=["tag1"])
    assert filter((), dict(tags=["tag2", "tag1"])) == dict(tags=["tag1"])
    assert filter((), dict(tags=["tag2"])) == dict(tags=["tag2"])


def test_generate_filter_conditions_two_with_merge():
    filter = generate_filter_conditions(
        [FilterCondition(tags=["tag1"]), FilterCondition(tags=["tag2"])], merge_matches=True
    )
    assert not filter((), {})
    assert not filter((), dict(tags=["tag3"]))

    assert filter((), dict(tags=["tag1"])) == dict(tags=["tag1"])
    assert filter((), dict(tags=["tag2", "tag1"])) == dict(tags=["tag1", "tag2"])
    assert filter((), dict(tags=["tag2"])) == dict(tags=["tag2"])


def test_generate_filter_conditions_operation():
    filter = generate_filter_conditions(
        [FilterCondition(operations=["get /foo"]), FilterCondition(operations=["patch /foo/baz"])],
        merge_matches=True,
    )
    assert filter(("paths", "/foo", "get"), {}) == {}
    assert filter(("paths", "/foo/baz", "patch"), {}) == {}
    assert filter(("paths", "/foo/Baz", "PaTCH"), {}) == {}

    assert not filter(("paths", "/baz", "get"), {})
    assert not filter(("paths", "/foo", "put"), {})


def test_generate_filter_conditions_security():
    filter = generate_filter_conditions([FilterCondition(security_scopes=["scope1"])])
    assert not filter((), {})
    assert not filter((), dict(security=[{"oauth": ["scope2"]}]))
    assert not filter((), dict(security=[{"oauth": ["scope1", "scope2"]}]))
    assert not filter((), dict(security=[{"oauth": ["scope1"], "reauth": ["scope2"]}]))

    # operation is not secured (=open) so not filtered
    assert filter((), dict(tags=["tag2"]))

    # operation is secured with a no scope sec
    assert filter((), dict(security=[{"api_key": []}]))

    assert filter((), dict(security=[{"oauth": ["scope1"]}])) == {
        "security": [{"oauth": ["scope1"]}]
    }


def test_generate_filter_conditions_security_multi_scopes():
    filter = generate_filter_conditions([FilterCondition(security_scopes=["scope1", "scope3"])])

    assert not filter((), {})
    assert not filter((), dict(security=[{"oauth": ["scope2"]}]))
    assert not filter((), dict(security=[{"oauth": ["scope1", "scope2"]}]))
    assert not filter((), dict(security=[{"oauth": ["scope1"], "reauth": ["scope2"]}]))

    # operation is not secured (=open) so not filtered
    assert filter((), dict(tags=["tag2"]))

    assert filter((), dict(security=[{"oauth": ["scope1"]}])) == {
        "security": [{"oauth": ["scope1"]}]
    }
    assert filter((), dict(security=[{"oauth": ["scope1", "scope3"]}])) == {
        "security": [{"oauth": ["scope1", "scope3"]}]
    }
    assert filter((), dict(security=[{"oauth": ["scope1"], "reauth": ["scope3"]}])) == {
        "security": [{"oauth": ["scope1"], "reauth": ["scope3"]}]
    }


conditions = [
    (
        [FilterCondition(tags=["tag2"]), FilterCondition(tags=["tag1"])],
        {
            "info": {"title": "my api", "version": "v1.0"},
            "paths": {
                "/foo": {
                    "get": {
                        "security": [{"sec1": ["read"], "sec2": ["write"]}],
                        "tags": ["tag2", "tag1"],
                    },
                    "patch": {"security": [{"sec2": ["write"]}], "tags": ["tag2"]},
                    "post": {"security": [{"sec1": ["read", "write", "admin"]}], "tags": ["tag1"]},
                },
                "/foo/baz": {"patch": {"tags": ["tag2"]}, "post": {"tags": ["tag2", "tag1"]}},
            },
            "security": [{"sec1": ["read"]}, {"sec2": ["write"]}],
            "swagger": "2.0",
        },
        [
            OperationChangedFilterAction(
                path=("paths", "/foo", "get"),
                reason="The operation has been modified by a filter.",
                type="Operation was modified to match filters.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo/baz", "get"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationChangedFilterAction(
                path=("paths", "/foo/baz", "post"),
                reason="The operation has been modified by a filter.",
                type="Operation was modified to match filters.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo/baz", "put"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationChangedFilterAction(
                path=("paths", "/foo/baz", "patch"),
                reason="The operation has been modified by a filter.",
                type="Operation was modified to match filters.",
            ),
        ],
    ),
    (
        [FilterCondition(tags=["tag2"])],
        {
            "info": {"title": "my api", "version": "v1.0"},
            "paths": {
                "/foo": {
                    "get": {"security": [{"sec1": ["read"], "sec2": ["write"]}], "tags": ["tag2"]},
                    "patch": {"security": [{"sec2": ["write"]}], "tags": ["tag2"]},
                },
                "/foo/baz": {"patch": {"tags": ["tag2"]}, "post": {"tags": ["tag2"]}},
            },
            "security": [{"sec1": ["read"]}, {"sec2": ["write"]}],
            "swagger": "2.0",
        },
        [
            OperationChangedFilterAction(
                path=("paths", "/foo", "get"),
                reason="The operation has been modified by a filter.",
                type="Operation was modified to match filters.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo", "post"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo/baz", "get"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationChangedFilterAction(
                path=("paths", "/foo/baz", "post"),
                reason="The operation has been modified by a filter.",
                type="Operation was modified to match filters.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo/baz", "put"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationChangedFilterAction(
                path=("paths", "/foo/baz", "patch"),
                reason="The operation has been modified by a filter.",
                type="Operation was modified to match filters.",
            ),
        ],
    ),
    (
        [FilterCondition(security_scopes=["read"])],
        {
            "info": {"title": "my api", "version": "v1.0"},
            "paths": {
                "/foo": {},
                "/foo/baz": {
                    "patch": {"security": [{"sec1": ["read"]}], "tags": ["tag2", "tag3"]},
                    "post": {"security": [{"sec1": ["read"]}], "tags": ["tag1", "tag2"]},
                    "put": {"security": [{"sec1": ["read"]}]},
                },
            },
            "security": [{"sec1": ["read"]}],
            "swagger": "2.0",
        },
        [
            OperationRemovedFilterAction(
                path=("paths", "/foo", "get"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo", "post"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo", "patch"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo/baz", "get"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationChangedFilterAction(
                path=("paths", "/foo/baz", "post"),
                reason="The operation has been modified by a filter.",
                type="Operation was modified to match filters.",
            ),
            OperationChangedFilterAction(
                path=("paths", "/foo/baz", "put"),
                reason="The operation has been modified by a filter.",
                type="Operation was modified to match filters.",
            ),
            OperationChangedFilterAction(
                path=("paths", "/foo/baz", "patch"),
                reason="The operation has been modified by a filter.",
                type="Operation was modified to match filters.",
            ),
        ],
    ),
    (
        [FilterCondition(security_scopes=["write", "read"])],
        {
            "info": {"title": "my api", "version": "v1.0"},
            "paths": {
                "/foo": {
                    "get": {
                        "security": [{"sec1": ["read"], "sec2": ["write"]}],
                        "tags": ["tag1", "tag2", "tag3"],
                    },
                    "patch": {"security": [{"sec2": ["write"]}], "tags": ["tag2"]},
                },
                "/foo/baz": {
                    "get": {
                        "security": [{"sec1": ["read", "write"], "sec2": ["read"]}],
                        "tags": ["tag3"],
                    },
                    "patch": {
                        "security": [{"sec1": ["read"]}, {"sec2": ["write"]}],
                        "tags": ["tag2", "tag3"],
                    },
                    "post": {
                        "security": [{"sec1": ["read"]}, {"sec2": ["write"]}],
                        "tags": ["tag1", "tag2"],
                    },
                    "put": {"security": [{"sec1": ["read"]}, {"sec2": ["write"]}]},
                },
            },
            "security": [{"sec1": ["read"]}, {"sec2": ["write"]}],
            "swagger": "2.0",
        },
        [
            OperationRemovedFilterAction(
                path=("paths", "/foo", "post"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationChangedFilterAction(
                path=("paths", "/foo/baz", "post"),
                reason="The operation has been modified by a filter.",
                type="Operation was modified to match filters.",
            ),
            OperationChangedFilterAction(
                path=("paths", "/foo/baz", "put"),
                reason="The operation has been modified by a filter.",
                type="Operation was modified to match filters.",
            ),
            OperationChangedFilterAction(
                path=("paths", "/foo/baz", "patch"),
                reason="The operation has been modified by a filter.",
                type="Operation was modified to match filters.",
            ),
        ],
    ),
    (
        [],
        {
            "info": {"title": "my api", "version": "v1.0"},
            "paths": {"/foo": {}, "/foo/baz": {}},
            "security": [{"sec1": ["read"]}, {"sec2": ["write"]}],
            "swagger": "2.0",
        },
        [
            OperationRemovedFilterAction(
                path=("paths", "/foo", "get"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo", "post"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo", "patch"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo/baz", "get"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo/baz", "post"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo/baz", "put"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo/baz", "patch"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
        ],
    ),
    (
        None,
        {
            "info": {"title": "my api", "version": "v1.0"},
            "paths": {
                "/foo": {
                    "get": {
                        "security": [{"sec1": ["read"], "sec2": ["write"]}],
                        "tags": ["tag1", "tag2", "tag3"],
                    },
                    "patch": {"security": [{"sec2": ["write"]}], "tags": ["tag2"]},
                    "post": {"security": [{"sec1": ["read", "write", "admin"]}], "tags": ["tag1"]},
                },
                "/foo/baz": {
                    "get": {
                        "security": [{"sec1": ["read", "write"], "sec2": ["read"]}],
                        "tags": ["tag3"],
                    },
                    "patch": {"tags": ["tag2", "tag3"]},
                    "post": {"tags": ["tag1", "tag2"]},
                    "put": {},
                },
            },
            "security": [{"sec1": ["read"]}, {"sec2": ["write"]}],
            "swagger": "2.0",
        },
        [],
    ),
]


@pytest.mark.parametrize("conditions,expected_swagger, expected_actions", conditions)
def test_filtering_conditions(swagger, conditions, expected_swagger, expected_actions):
    swagger_filtered, actions = filter(swagger, mode="keep_only", conditions=conditions)

    assert swagger_filtered == expected_swagger

    # no error in this basic test
    assert actions == expected_actions


@pytest.mark.parametrize("remove_global_security", [True, False])
def test_filtering_conditions_no_global_security(swagger, remove_global_security):
    # with no global security, some endpoints are open and should not be filtered
    if remove_global_security:
        del swagger["security"]

    swagger_filtered, actions = filter(
        swagger,
        mode="keep_only",
        conditions=[FilterCondition(security_scopes=["inexisting-scope"])],
    )

    assert swagger_filtered == (
        {
            "info": {"title": "my api", "version": "v1.0"},
            "paths": {
                "/foo": {},
                "/foo/baz": {
                    "patch": {"tags": ["tag2", "tag3"]},
                    "post": {"tags": ["tag1", "tag2"]},
                    "put": {},
                },
            },
            "swagger": "2.0",
        }
        if remove_global_security
        else {
            "info": {"title": "my api", "version": "v1.0"},
            "paths": {"/foo": {}, "/foo/baz": {}},
            "swagger": "2.0",
        }
    )

    # no error in this basic test
    assert actions == [
        OperationRemovedFilterAction(
            path=("paths", "/foo", "get"),
            reason="The operation has been removed as it does not match any filter.",
            type="Operation removed as no filter matched.",
        ),
        OperationRemovedFilterAction(
            path=("paths", "/foo", "post"),
            reason="The operation has been removed as it does not match any filter.",
            type="Operation removed as no filter matched.",
        ),
        OperationRemovedFilterAction(
            path=("paths", "/foo", "patch"),
            reason="The operation has been removed as it does not match any filter.",
            type="Operation removed as no filter matched.",
        ),
        OperationRemovedFilterAction(
            path=("paths", "/foo/baz", "get"),
            reason="The operation has been removed as it does not match any filter.",
            type="Operation removed as no filter matched.",
        ),
    ] + (
        [
            OperationRemovedFilterAction(
                path=("paths", "/foo/baz", "post"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo/baz", "put"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
            OperationRemovedFilterAction(
                path=("paths", "/foo/baz", "patch"),
                reason="The operation has been removed as it does not match any filter.",
                type="Operation removed as no filter matched.",
            ),
        ]
        if not remove_global_security
        else []
    )


def test_filtering_mode():
    # does not fail
    filter({"paths": {}}, mode="keep_only", conditions=[])

    with pytest.raises(NotImplementedError, match="The mode 'remove' is not yet implemented."):
        filter({"paths": {}}, mode="remove", conditions=[])
