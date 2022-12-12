import yaml

from oasapi.events import (
    JsonSchemaValidationError,
    ReferenceNotFoundValidationError,
    DuplicateOperationIdValidationError,
    ParameterDefinitionValidationError,
    SecurityDefinitionNotFoundValidationError,
    OAuth2ScopeNotFoundInSecurityDefinitionValidationError,
    ReferenceInvalidSection,
    ReferenceInvalidSyntax,
)
from oasapi.validation import (
    validate,
    check_schema,
    check_references,
    detect_duplicate_operationId,
    check_parameters,
    check_security,
)


def test_minimal_compliant_swagger():
    """This is the minimal testing"""
    swagger_str = """
swagger: '2.0'
info:
  version: v1.0
  title: my api
paths: {}
"""
    swagger = yaml.safe_load(swagger_str)
    _, results = validate(swagger)

    # no error in this basic test
    assert results == set()


def test_empty_swagger():
    """This is the minimal testing"""
    _, results = validate({})

    # no error in this basic test
    assert results == {
        JsonSchemaValidationError(
            path=(), reason="'info' is a required property", type="Json schema validator error"
        ),
        JsonSchemaValidationError(
            path=(), reason="'paths' is a required property", type="Json schema validator error"
        ),
        JsonSchemaValidationError(
            path=(), reason="'swagger' is a required property", type="Json schema validator error"
        ),
    }


def test_schema_error():
    swagger_str = """
swagger: '2.0'
info:
  version: 1.0
  title: my api
paths:
  /foo:
    get:
      responses:
        "200":
          $ref: "#/definitions/some-definition"
      security:
      - baz: "not-a-list"
"""
    swagger = yaml.safe_load(swagger_str)
    _, results = validate(swagger)

    # no error in this basic test
    assert results == {
        JsonSchemaValidationError(
            path=("info", "version"),
            reason="1.0 is not of type 'string'",
            type="Json schema validator error",
        ),
        JsonSchemaValidationError(
            path=("paths", "/foo", "get", "security", 0, "baz"),
            reason="'not-a-list' is not of type 'array'",
            type="Json schema validator error",
        ),
        ReferenceNotFoundValidationError(
            path=("paths", "/foo", "get", "responses", "200", "$ref"),
            reason="reference '#/definitions/some-definition' does not exist",
            type="Reference not found",
        ),
        SecurityDefinitionNotFoundValidationError(
            path=("paths", "/foo", "get", "security", "[0]", "baz"),
            reason="securityDefinitions 'baz' does not exist",
            type="Security definition not found",
        ),
    }


def test_check_schema():
    swagger_str = """
swagger: '2.0'
info:
  version: 1.0
  title: my api
paths:
  /foo:
    get:
      responses:
        "200":
          $ref: "#/definitions/some-definition"
      security:
      - baz: "not-a-list"
    """
    swagger = yaml.safe_load(swagger_str)
    results = check_schema(swagger)

    # no error in this basic test
    assert results == {
        JsonSchemaValidationError(
            path=("info", "version"),
            reason="1.0 is not of type 'string'",
            type="Json schema validator error",
        ),
        JsonSchemaValidationError(
            path=("paths", "/foo", "get", "security", 0, "baz"),
            reason="'not-a-list' is not of type 'array'",
            type="Json schema validator error",
        ),
    }


def test_check_schema_integer_as_response_code():
    swagger_str = """
swagger: '2.0'
info:
  version: 1.0
  title: my api
paths:
  /foo:
    get:
      responses:
        200:
          $ref: "#/definitions/some-definition"
      security:
      - baz: "not-a-list"
    """
    swagger = yaml.safe_load(swagger_str)
    results = check_schema(swagger)

    # no error in this basic test
    assert results == {
        JsonSchemaValidationError(
            path=("info", "version"),
            reason="1.0 is not of type 'string'",
            type="Json schema validator error",
        ),
        JsonSchemaValidationError(
            path=("paths", "/foo", "get", "security", 0, "baz"),
            reason="'not-a-list' is not of type 'array'",
            type="Json schema validator error",
        ),
    }


def test_check_references():
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
        300:
          $ref: "#/definitions/some-not-existing-definition"
        400:
          $ref: "#/responses/some-response"
        500:
          $ref: "#/badly-formed"
        600:
           $ref: "#/info/version"
        700:
           $ref: "https://some.external.reference.com/foo/baz"
definitions:
  some-definition: {}
responses:
  some-response:
    description: OK

    """
    swagger = yaml.safe_load(swagger_str)

    results = check_references(swagger)
    assert results == {
        ReferenceInvalidSection(
            path=("paths", "/foo", "get", "responses", 600, "$ref"),
            reason="Reference #/info/version not referring to one of the sections ['definitions', 'responses', 'parameters']",
            type="Reference invalid section",
        ),
        ReferenceInvalidSyntax(
            path=("paths", "/foo", "get", "responses", 500, "$ref"),
            reason="reference #/badly-formed not of the form '#/section/item'",
            type="Reference invalid syntax",
        ),
        ReferenceNotFoundValidationError(
            path=("paths", "/foo", "get", "responses", 300, "$ref"),
            reason="reference '#/definitions/some-not-existing-definition' does not exist",
            type="Reference not found",
        ),
    }


def test_detect_duplicate_operationId():
    swagger_str = """
swagger: '2.0'
info:
  version: v1.0
  title: my api
paths:
  /foo:
    get:
      operationId: this-is-a-unique-id
      responses:
        200:
          description: OK
    post:
      operationId: this-is-not-a-unique-id
      responses:
        200:
          description: OK
    put:
      operationId: this-is-not-a-unique-id
      responses:
        200:
          description: OK
    patch:
      operationId: this-is-not-a-unique-id
      responses:
        200:
          description: OK
    parameters:
      operationId: this-is-not-a-unique-id
      responses:
        200:
          description: OK
# operationIds below should not trigger errors as not in expected position
    operationId: this-is-not-a-unique-id
  operationId: this-is-not-a-unique-id
operationId: this-is-not-a-unique-id
    """
    swagger = yaml.safe_load(swagger_str)

    results = detect_duplicate_operationId(swagger)
    assert results == {
        DuplicateOperationIdValidationError(
            path=("paths", "/foo", "patch", "operationId"),
            reason="the operationId 'this-is-not-a-unique-id' is already used in an endpoint.",
            operationId="this-is-not-a-unique-id",
            path_already_used=("paths", "/foo", "post", "operationId"),
            type="Duplicate operationId",
        ),
        DuplicateOperationIdValidationError(
            path=("paths", "/foo", "put", "operationId"),
            reason="the operationId 'this-is-not-a-unique-id' is already used in an endpoint.",
            operationId="this-is-not-a-unique-id",
            path_already_used=("paths", "/foo", "post", "operationId"),
            type="Duplicate operationId",
        ),
    }


def test_check_parameters():
    swagger_str = """
swagger: '2.0'
info:
  version: v1.0
  title: my api
parameters:
- name: param_int_bad
  in: query
  type: integer
  default: "error-on-parameter-definitions"
paths:
  /foo:
    get:
      parameters:
      - name: param_int_bad
        in: query
        type: integer
        default: "error-on-operation-specific-definitions"

    parameters:
    - name: param_int_bad
      in: query
      type: integer
      default: "error-on-path-specific-definitions"
    - name: param_int
      in: query
      type: integer
      default: 1
    - name: param_str
      in: query
      type: string
      default: [hello, world]
    - name: param_str
      in: query
      type: string
      default: 1
    - name: param_enum_wrong_default
      in: query
      type: string
      enum: [there, are, valid, values]
      default: this-is-not-valid
    - name: param_enum
      in: query
      type: string
      enum: [there, are, valid, values]
      default: there
    - name: param_enum_duplicates
      in: query
      type: string
      enum: [there, are, duplicates, duplicates]
    - name: param_array
      in: query
      type: array
    - name: param_str_date
      in: query
      type: string
      format: date
      default: "2012-01-22"
    - name: param_str_date_bad
      in: query
      type: string
      format: date
      default: "2012-0001-22"
    - name: param_str_datetime
      in: query
      type: string
      format: dateTime
      default: "2012-01-22T00:15:22Z"
    - name: param_str_datetime_dad
      in: query
      type: string
      format: dateTime
      default: "2012-01-22T00:15:22GG"
    - name: param_required_but_with_default
      in: query
      type: string
      required: true
      default: "should not be given"
    - name: param_required_but_with_default_even_empty
      in: query
      type: string
      required: true
      default: ""
    - name: param_int
      in: query
      type: integer
      default: 45
    - name: param_int_float
      in: query
      type: integer
      default: 45.0
    - name: param_float
      in: query
      type: number
      default: 45.0
    - name: param_float_int
      in: query
      type: number
      default: 45
    - name: param_base64
      in: query
      type: string
      format: byte
      default: |
        TWFuIGlzIGRpc3Rpbmd1aXNoZWQsIG5vdCBvbmx5IGJ5IGhpcyByZWFzb24sIGJ1dCBieSB0aGlz
        IHNpbmd1bGFyIHBhc3Npb24gZnJvbSBvdGhlciBhbmltYWxzLCB3aGljaCBpcyBhIGx1c3Qgb2Yg
        dGhlIG1pbmQsIHRoYXQgYnkgYSBwZXJzZXZlcmFuY2Ugb2YgZGVsaWdodCBpbiB0aGUgY29udGlu
        dWVkIGFuZCBpbmRlZmF0aWdhYmxlIGdlbmVyYXRpb24gb2Yga25vd2xlZGdlLCBleGNlZWRzIHRo
        ZSBzaG9ydCB2ZWhlbWVuY2Ugb2YgYW55IGNhcm5hbCBwbGVhc3VyZS4=
    - name: param_base64_bad
      in: query
      type: string
      format: byte
      default: "FV'()';:=FERT4DE()r'"
    - name: param_string_customer_format
      in: query
      type: string
      format: my-own-format
      default: 45
    - name: param_string_customer_format
      in: query
      type: string
      format: my-own-format
      default: "45"
    - name: param_unknown_type
      in: query
      type: unknown_type
      format: my-own-format
      default: "45"
"""
    swagger = yaml.safe_load(swagger_str)

    results = check_parameters(swagger)
    assert results == {
        ParameterDefinitionValidationError(
            path=("parameters", "[0]", "default"),
            reason="The default value 'error-on-parameter-definitions' is not of the expected type 'integer'",
            parameter_name="param_int_bad",
            type="Parameter definition error",
        ),
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "get", "parameters", "[0]", "default"),
            reason="The default value 'error-on-operation-specific-definitions' is not of the expected type 'integer'",
            parameter_name="param_int_bad",
            type="Parameter definition error",
        ),
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "parameters", "[0]", "default"),
            reason="The default value 'error-on-path-specific-definitions' is not of the expected type 'integer'",
            parameter_name="param_int_bad",
            type="Parameter definition error",
        ),
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "parameters", "[11]", "default"),
            reason="The default value '2012-01-22T00:15:22GG' does not conform to the string format 'dateTime'",
            parameter_name="param_str_datetime_dad",
            type="Parameter definition error",
        ),
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "parameters", "[12]"),
            reason="The parameter is required yet it has a default value",
            parameter_name="param_required_but_with_default",
            type="Parameter definition error",
        ),
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "parameters", "[13]"),
            reason="The parameter is required yet it has a default value",
            parameter_name="param_required_but_with_default_even_empty",
            type="Parameter definition error",
        ),
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "parameters", "[15]", "default"),
            reason="The default value 45.0 is not of the expected type 'integer'",
            parameter_name="param_int_float",
            type="Parameter definition error",
        ),
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "parameters", "[19]", "default"),
            reason="The default value 'FV'()';:=FERT4DE()r'' does not conform to the string format 'byte'",
            parameter_name="param_base64_bad",
            type="Parameter definition error",
        ),
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "parameters", "[20]", "default"),
            reason="The default value 45 is not of the expected type 'string'",
            parameter_name="param_string_customer_format",
            type="Parameter definition error",
        ),
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "parameters", "[2]", "default"),
            reason="The default value ['hello', 'world'] is not of the expected type 'string'",
            parameter_name="param_str",
            type="Parameter definition error",
        ),
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "parameters", "[3]", "default"),
            reason="The default value 1 is not of the expected type 'string'",
            parameter_name="param_str",
            type="Parameter definition error",
        ),
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "parameters", "[4]", "default"),
            reason="The default value 'this-is-not-valid' is not one of "
            "the enum values ['there', 'are', 'valid', 'values']",
            parameter_name="param_enum_wrong_default",
            type="Parameter definition error",
        ),
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "parameters", "[6]", "enum"),
            reason="The enum values ['there', 'are', 'duplicates', 'duplicates'] contains duplicate values",
            parameter_name="param_enum_duplicates",
            type="Parameter definition error",
        ),
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "parameters", "[7]"),
            reason="The parameter is of type 'array' but is missing an 'items' field",
            parameter_name="param_array",
            type="Parameter definition error",
        ),
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "parameters", "[9]", "default"),
            reason="The default value '2012-0001-22' does not conform to the string format 'date'",
            parameter_name="param_str_date_bad",
            type="Parameter definition error",
        ),
    }


def test_check_parameters_array_recurse():
    swagger_str = """
swagger: '2.0'
info:
  version: v1.0
  title: my api
paths:
  /foo:
    parameters:
    - name: param_array_ok
      in: query
      type: array
      items:
        type: array
        items:
          type: string
          default: this-is-valid
    - name: param_array_nok
      in: query
      type: array
      items:
        type: array
        items:
          type: string
          enum: [there, are, duplicate, duplicate, values]
          default: this-is-not-valid
"""
    swagger = yaml.safe_load(swagger_str)

    results = check_parameters(swagger)
    assert results == {
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "parameters", "[1]", "items", "items", "default"),
            reason="The default value 'this-is-not-valid' is not one of the enum values "
            "['there', 'are', 'duplicate', 'duplicate', 'values']",
            parameter_name="unnamed-parameter",
            type="Parameter definition error",
        ),
        ParameterDefinitionValidationError(
            path=("paths", "/foo", "parameters", "[1]", "items", "items", "enum"),
            reason="The enum values ['there', 'are', 'duplicate', 'duplicate', 'values'] contains duplicate values",
            parameter_name="unnamed-parameter",
            type="Parameter definition error",
        ),
    }


def test_check_security():
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
      - sec1: "not-a-list"
        sec2: [not-existing-scope]
      - sec3: [existing-scope]
      - sec-not-exist: []
    PATCH:
      responses:
        200:
          description: OK
      security:
      - sec1: []
    parameters:
      security: [ {sec-not-exist-but-should-not-raise: []} ]
  security: [ {sec-not-exist-but-should-not-raise: []} ]
security: []
securityDefinitions:
  sec1:
    type: basic
  sec2:
    type: basic
  sec3:
    type: oauth2
    flow: implicit
    authorizationUrl: https://some-existing-auth-server.com
    scopes:
      existing-scope: this is an existing scope
"""
    swagger = yaml.safe_load(swagger_str)

    results = check_security(swagger)
    assert results == {
        OAuth2ScopeNotFoundInSecurityDefinitionValidationError(
            path=("paths", "/foo", "get", "security", "[0]", "sec2", "not-existing-scope"),
            reason="scope not-existing-scope is not declared in the scopes of the securityDefinitions 'sec2'",
            type="Security scope not found",
        ),
        SecurityDefinitionNotFoundValidationError(
            path=("paths", "/foo", "get", "security", "[2]", "sec-not-exist"),
            reason="securityDefinitions 'sec-not-exist' does not exist",
            type="Security definition not found",
        ),
    }
