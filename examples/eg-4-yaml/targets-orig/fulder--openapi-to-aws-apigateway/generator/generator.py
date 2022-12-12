import copy
import json
import logging
import os
import re
import shutil

import requests

try:
    from urllib.parse import urlparse
except ImportError:
    # Python2 only
    from urlparse import urlparse

import yaml

from .verb_extender import VerbExtender

CURRENT_FOLDER = os.path.abspath(os.getcwd())
CORS_MAPPING_TEMPLATE_OPTIONS = """\
#if($input.params("Origin") !="" && $stageVariables.CORS_ORIGINS != "" && $stageVariables.CORS_ORIGINS.split(",").contains($input.params("Origin")))
#set($context.responseOverride.header.Access-Control-Allow-Origin=$input.params("Origin"))
#set($context.responseOverride.header.Access-Control-Allow-Methods="{methods}")
{allowed_headers_cases}\
#end
"""

CORS_MAPPING_ALLOWED_HEADERS = """\
#if($input.params("Access-Control-Request-Method")=="{method}")
#set($context.responseOverride.header.Access-Control-Allow-Headers="{headers}")
#end
"""

logger = logging.getLogger(__name__)


class Generator:

    def __init__(self, openapi_path, backend_url, proxy, vpc_link_id, apigateway_region, cors_origins, fail_on_error):
        self.openapi_path = openapi_path
        self.backend_url = backend_url
        self.proxy = proxy
        self.vpc_link_id = vpc_link_id
        self.apigateway_region = apigateway_region
        self.fail_on_error = fail_on_error

        self.output_folder = os.path.abspath(os.path.join(CURRENT_FOLDER, "out"))
        self.output_path_sam = os.path.join(self.output_folder, "apigateway.yaml")
        self.stage_variables = {
            "backendUrl": self.backend_url,
            "corsOrigins": "{}".format(cors_origins)
        }

        self.unsupported_keys = ["xml", "additionalProperties", "anyOffields", "example"]

        # Created by helper funcs during generate
        self.docs = None
        self.extended_docs = None
        self.backend_type = None
        self.backend_uri_start = None
        self.docs_type = None
        self.output_path_openapi = None
        self.cloudformation = None

    def generate(self):
        # Don't dump reference pointers
        yaml.SafeDumper.ignore_aliases = lambda *args: True

        self._create_empty_output_folder()
        self._load_file()
        self._docs_version()

        self._determine_backend_type()
        self._create_backend_uri_start()

        self._init_sam_template()

        self._loop_paths()

        self._add_security()
        self.extended_docs = self._remove_unsupported(self.extended_docs)

        self._save_openapi()
        self._save_cloudformation()

    def _loop_paths(self):
        for p in self.docs["paths"]:
            path_docs = self.extended_docs["paths"][p]

            for v in self.docs["paths"][p]:
                self.extended_docs["paths"][p][v] = self._extend_verbs(p, v)

            self._enable_cors(path_docs)

    def _create_empty_output_folder(self):
        if os.path.isdir(self.output_folder):
            shutil.rmtree(self.output_folder)
        os.mkdir(self.output_folder)

    @property
    def is_lambda_integration(self):
        return self.backend_url.startswith("arn:")

    def _load_file(self):
        if "http" in self.openapi_path:
            logger.debug("Downloading JSON file from URL: [%s]", self.openapi_path)
            ret = requests.get(self.openapi_path)
            self.docs = ret.json()
            self.extended_docs = copy.deepcopy(self.docs)
            return

        with open(self.openapi_path, "r") as f:
            if ".json" in self.openapi_path:
                self.docs = json.load(f)
            else:
                self.docs = yaml.safe_load(f)
        self.extended_docs = copy.deepcopy(self.docs)

    def _docs_version(self):
        if "swagger" in self.docs and self.docs["swagger"].startswith("2.0"):
            self.docs_type = "swagger"
            self.output_path_openapi = os.path.join(self.output_folder, "swagger.yaml")
        elif "openapi" in self.docs and self.docs["openapi"].startswith("3.0"):
            self.docs_type = "openapi"
            self.output_path_openapi = os.path.join(self.output_folder, "openapi.yaml")
        else:
            raise RuntimeError("Unsupported docs type. Supported: Swagger 2.0, OpenAPI 3.0")

    def _determine_backend_type(self):
        if self.is_lambda_integration:
            self.backend_type = "aws"
        else:
            self.backend_type = "http"

        if self.proxy:
            self.backend_type += "_proxy"
        logger.debug("Determined backend type as: [%s]", self.backend_type)

    def _create_backend_uri_start(self):
        if self.is_lambda_integration:
            m1 = re.search(r"(arn:aws:lambda::\d+:function:\w+:)(\w+)", self.backend_url)
            m2 = re.search(r"(arn:aws:lambda::\d+:function:)(\w+)", self.backend_url)

            self.backend_uri_start = "arn:aws:apigateway:{}:lambda:path/2015-03-31/functions/".format(
                self.apigateway_region)

            if m1:
                logger.info("Setting 'lambdaVersion' stageVariable to: [%s]", m1.group(2))
                self.backend_uri_start += m1.group(1) + "${stageVariables.lambdaVersion}" + "/invocations"
                self.stage_variables["lambdaVersion"] = m1.group(2)
            elif m2:
                logger.info("Setting 'lambdaName' stageVariable to [%s]", m2.group(2))
                self.backend_uri_start += m2.group(1) + "${stageVariables.lambdaName}" + "/invocations"
                self.stage_variables["lambdaName"] = m2.group(2)
            else:
                raise RuntimeError("Invalid lambda ARN")
        else:
            parsed_url = urlparse(self.backend_url)
            logger.info("Setting 'httpHost' stageVariable to [%s]", parsed_url.hostname)
            self.backend_uri_start = "http://" + "${stageVariables.httpHost}"
            self.stage_variables["httpHost"] = parsed_url.hostname

    def _init_sam_template(self):
        self.cloudformation = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Transform": "AWS::Serverless-2016-10-31",
            "Description": "ApiGateway stack auto generated by openapi-aws-apigateway-generator",
            "Resources": {
                "Api": {
                    "Type": "AWS::Serverless::Api",
                    "Properties": {
                        "StageName": "default",
                        "DefinitionUri": self.output_path_openapi,
                        "Variables": self.stage_variables,
                    }
                }
            }
        }

    def _extend_verbs(self, p, v):
        verb_docs = self.docs["paths"][p][v]
        logger.debug("Extending verb for route [%s %s]", v, p)
        verb_extender = VerbExtender(v, verb_docs, p, self.backend_type, self.vpc_link_id,
                                     self.is_lambda_integration, self.backend_uri_start, self.fail_on_error)
        return verb_extender.extend()

    def _enable_cors(self, path_docs):
        allowed_methods = []
        allowed_headers = []
        for v in path_docs:
            allowed_methods.append(v.upper())

            if "parameters" in path_docs[v]:
                headers_list = []
                for i in range(0, len(path_docs[v]["parameters"])):
                    if path_docs[v]["parameters"][i]["in"] == "header":
                        headers_list.append(path_docs[v]["parameters"][i]["name"])

                if headers_list:
                    template_if = CORS_MAPPING_ALLOWED_HEADERS.format(method=v.upper(), headers=",".join(headers_list))
                    allowed_headers.append(template_if)

        methods = ",".join(allowed_methods)
        allowed_headers_cases = "".join(allowed_headers)
        mapping_template_script = CORS_MAPPING_TEMPLATE_OPTIONS.format(methods=methods,
                                                                       allowed_headers_cases=allowed_headers_cases)

        path_docs["options"] = {
            "summary": "CORS support",
            "description": "Enable CORS by returning correct headers",
            "consumes": [
                "application/json"
            ],
            "produces": [
                "application/json"
            ],
            "tags": [
                "CORS"
            ],
            "x-amazon-apigateway-integration": {
                "type": "mock",
                "requestTemplates": {
                    "application/json": '{"statusCode": 204}'
                },
                "responses": {
                    "204": {
                        "statusCode": "204",
                        "responseTemplates": {
                            "application/json": mapping_template_script
                        }
                    }
                }
            },
            "responses": {
                "204": {
                    "description": "Default response for CORS method",
                    "headers": {
                        "Access-Control-Allow-Headers": {
                            "type": "string"
                        },
                        "Access-Control-Allow-Methods": {
                            "type": "string"
                        },
                        "Access-Control-Allow-Origin": {
                            "type": "string"
                        }
                    }
                }
            }
        }

    def _add_security(self):
        # TODO add correct security
        if "securityDefinitions" in self.docs:
            del self.extended_docs["securityDefinitions"]

    def _remove_unsupported(self, current_dict):
        new_dict = copy.deepcopy(current_dict)

        for k, v in current_dict.items():
            if k in self.unsupported_keys:
                del new_dict[k]
                continue

            if isinstance(v, dict):
                new_dict[k] = self._remove_unsupported(v)
        return new_dict

    def _save_openapi(self):
        with open(self.output_path_openapi, "w") as f:
            yaml.safe_dump(self.extended_docs, f, default_flow_style=False, sort_keys=False)
        logger.info("Saved OpenAPI template with amazon extensions to: [%s]", self.output_path_openapi)

    def _save_cloudformation(self):
        with open(self.output_path_sam, "w") as f:
            yaml.safe_dump(self.cloudformation, f, default_flow_style=False, sort_keys=False)
        logger.info("Saved SAM template file to: [%s]", self.output_path_sam)
