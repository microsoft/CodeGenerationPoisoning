import argparse
import json
import logging
import os
import sys
import traceback

import jsonschema
import yaml
from flasgger import Swagger
from flask import Flask, g, Response, request
from flask_cors import CORS
from flask_restful import Api, Resource

from dug.config import Config
from dug.core.search import Search

"""
Defines the semantic search API

This exists in large part because it's not safe to expose the Elasticsearch interface to the internet.
So we'll need to add validation to ensure reasonable reasonable, well formed, valid requests inbound.
"""
logger = logging.getLogger (__name__)

app = Flask(__name__)

""" Enable CORS. """
api = Api(app)
CORS(app)
debug=False

""" Load the schema. """
schema_file_path = os.path.join (os.path.dirname (__file__), 'conf', 'api-schema.yaml')
template = None
with open(schema_file_path, 'r') as file_obj:
    template = yaml.load(file_obj, Loader=yaml.FullLoader)

""" Describe the API. """
app.config['SWAGGER'] = {
    'title': 'Dug Search API',
    'description': 'An API, compiler, and executor for cloud native distributed systems.',
    'uiversion': 3
}

swagger = Swagger(app, template=template)

def dug ():
    if not hasattr(g, 'dug'):
        g.search = Search(Config.from_env())
    return g.search

class DugResource(Resource):
    """ Base class handler for Dug API requests. """
    def __init__(self):
        self.specs = {}

    """ Functionality common to Dug services. """
    def validate (self, request, component):
        return
        """ Validate a request against the schema. """
        if not self.specs:
            with open(schema_file_path, 'r') as file_obj:
                self.specs = yaml.load(file_obj)
        to_validate = self.specs["components"]["schemas"][component]
        try:
            app.logger.debug (f"--:Validating obj {json.dumps(request.json, indent=2)}")
            app.logger.debug (f"  schema: {json.dumps(to_validate, indent=2)}")
            jsonschema.validate(request.json, to_validate)
        except jsonschema.exceptions.ValidationError as error:
            app.logger.error (f"ERROR: {str(error)}")
            traceback.print_exc (error)
            abort(Response(str(error), 400))

    def create_response (self, result=None, status='success', message='', exception=None):
        """ Create a response. Handle formatting and modifiation of status for exceptions. """
        if exception:
            traceback.print_exc ()
            status='error'
            exc_type, exc_value, exc_traceback = sys.exc_info()
            result = {
                'error' : repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            }
        return {
            'status'  : status,
            'result'  : result,
            'message' : message
        }

class DugSearchResource(DugResource):
    """ Execute a search """

    """ System initiation. """
    def post(self):
        """
        Execute the configured search.

        A natural language word or phrase is the input.
        ---
        tag: search
        description: Search for a string
        requestBody:
            description: Search request
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/components/schemas/Search'
        responses:
            '200':
                description: Success
                content:
                    text/plain:
                        schema:
                            type: string
                            example: "Nominal search"
            '400':
                description: Malformed message
                content:
                    text/plain:
                        schema:
                            type: string

        """
        logger.debug(f"search:{json.dumps(request.json)}")
        response = {}
        try:
            app.logger.info (f"search: {json.dumps(request.json, indent=2)}")
            self.validate(request, component="Search")
            boosted = request.json.pop('boosted', False)

            api_request = None
            if boosted:
                api_request = dug().search_nboost(**request.json)
            else:
                api_request = dug().search_concepts(**request.json)

            response = self.create_response(
                result=api_request,
                message=f"Search result")
        except Exception as e:
            response = self.create_response(
                exception=e,
                message=f"Failed to execute search {json.dumps(request.json, indent=2)}.")
        return response

class DugDumpConcept(DugResource):
    """ Execute a search """

    """ System initiation. """
    def post(self):
        """
        Execute the search of all concepts.

        ---
        tag: dump concepts
        description: Get all concepts
        requestBody:
            description: Search request
            required: false
            content:
                application/json:
                    schema:
                        $ref: '#/components/schemas/Search'
        responses:
            '200':
                description: Success
                content:
                    text/plain:
                        schema:
                            type: string
                            example: "Nominal search"
            '400':
                description: Malformed message
                content:
                    text/plain:
                        schema:
                            type: string

        """
        logger.debug(f"search:{json.dumps(request.json)}")
        response = {}
        try:
            app.logger.info (f"search: {json.dumps(request.json, indent=2)}")
            self.validate(request, component="Search")
            # boosted = request.json.pop('boosted', False)

            api_request = dug().dump_concepts(**request.json)

            response = self.create_response(
                result=api_request,
                message=f"Search result")
        except Exception as e:
            response = self.create_response(
                exception=e,
                message=f"Failed to execute search {json.dumps(request.json, indent=2)}.")
        return response


class DugSearchKGResource(DugResource):
    """ Execute a search """

    """ System initiation. """

    def post(self):
        """
        Execute the configured search.

        A natural language word or phrase is the input.
        ---
        tag: search_kg
        description: Search for a string across knowledge graphs
        requestBody:
            description: Search request
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/components/schemas/SearchKG'
        responses:
            '200':
                description: Success
                content:
                    text/plain:
                        schema:
                            type: string
                            example: "Nominal search"
            '400':
                description: Malformed message
                content:
                    text/plain:
                        schema:
                            type: string

        """
        logger.debug(f"search_kg:{json.dumps(request.json)}")
        response = {}
        try:
            app.logger.info(f"search_kg: {json.dumps(request.json, indent=2)}")
            self.validate(request, component="Search")
            response = self.create_response(
                result=dug().search_kg(**request.json),
                message=f"Search result")
        except Exception as e:
            response = self.create_response(
                exception=e,
                message=f"Failed to execute search {json.dumps(request.json, indent=2)}.")
        return response

class DugSearchVarResource(DugResource):
    """ Execute a search """

    """ System initiation. """

    def post(self):
        """
        Execute the configured search.

        A natural language word or phrase is the input.
        ---
        tag: search_kg
        description: Search for a string across knowledge graphs
        requestBody:
            description: Search request
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/components/schemas/SearchVar'
        responses:
            '200':
                description: Success
                content:
                    text/plain:
                        schema:
                            type: string
                            example: "Nominal search"
            '400':
                description: Malformed message
                content:
                    text/plain:
                        schema:
                            type: string

        """
        logger.debug(f"search_kg:{json.dumps(request.json)}")
        response = {}
        try:
            app.logger.info(f"search_var: {json.dumps(request.json, indent=2)}")
            self.validate(request, component="Search")
            response = self.create_response(
                result=dug().search_variables(**request.json),
                message=f"Search result")
        except Exception as e:
            response = self.create_response(
                exception=e,
                message=f"Failed to execute search {json.dumps(request.json, indent=2)}.")
        return response


class DugAggDataType(DugResource):
    """ Execute a search """

    """ System initiation. """

    def post(self):
        logger.debug(f"data_type:{json.dumps(request.json)}")
        response = {}
        try:
            app.logger.info(f"data_type: {json.dumps(request.json, indent=2)}")
            self.validate(request, component="Search")
            response = self.create_response(
                result=dug().agg_data_type(**request.json),
                message=f"Aggregate result")
        except Exception as e:
            response = self.create_response(
                exception=e,
                message=f"Failed to execute search {json.dumps(request.json, indent=2)}.")
        return response

""" Register endpoints. """
api.add_resource(DugSearchResource, '/search')
api.add_resource(DugDumpConcept, '/dump_concepts')
api.add_resource(DugSearchKGResource, '/search_kg')
api.add_resource(DugSearchVarResource, '/search_var')
api.add_resource(DugAggDataType, '/agg_data_types')

def main(args=None):
    parser = argparse.ArgumentParser(description='Dug Search API')
    parser.add_argument('-p', '--port', type=int, help='Port to run service on.', default=5551)
    parser.add_argument('-d', '--debug', help="Debug log level.", default=False, action='store_true')
    args = parser.parse_args(args)

    """ Configure """
    if args.debug:
        debug = True
        logging.basicConfig(level=logging.DEBUG)
    logger.info(f"starting dug on port={args.port} with debug={args.debug}")
    app.run(host='0.0.0.0', port=args.port, debug=args.debug, threaded=True)

if __name__ == "__main__":
   main()
