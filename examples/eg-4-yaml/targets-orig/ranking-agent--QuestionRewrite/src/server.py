import os
import jsonschema
import yaml
import json
from sanic import Sanic, response
from sanic.request import Request
from src.apidocs import bp as apidocs_blueprint
from src.similarity_rewrite import similarity_expand
from src.edge_expand_rewrite import rewrite_edge_expand

""" Sanic server for Question Rewrite - A Swagger UI/web service. """

# initialize this web app
app: Sanic = Sanic("Question augmentation")

# suppress access logging
app.config.ACCESS_LOG = False

# init the app using the paramters defined in
app.blueprint(apidocs_blueprint)

# get the location of the Translator specification file
dir_path: str = os.path.dirname(os.path.realpath(__file__))

# load the Translator specification
with open(os.path.join(dir_path, 'TranslatorReasonersAPI_0.9.2.yaml')) as f:
    spec: dict = yaml.load(f, Loader=yaml.SafeLoader)

# load the query specification, first get the question node
validate_with: dict = spec["components"]["schemas"]["Message"]

# then get the components in their own array so the relative references are found
validate_with["components"] = spec["components"]

# remove the question node because we already have it at the top
validate_with["components"].pop("Message", None)

@app.post('/node_expand')
async def node_expand_handler(request: Request) -> json:
    """ Handler for node expander operations. """

    try:
        # load the input into a json object
        incoming: dict = json.loads(request.body)

        # validate the incoming json against the spec
        jsonschema.validate(instance=incoming, schema=validate_with)

        # get a list of expanded nodes related to the requested one
        results: list = similarity_expand(incoming['message'])

        # validate the output and get it in the correct format
        expanded_response: list = process_response(incoming, results)

    # Note: all JSON validation errors are manifested as a thrown exception
    except Exception as error:
        return response.json({'Response failed validation. Message': str(error)}, status=400)

    # if we are here the response validated properly
    return response.json(expanded_response, status=200)

@app.post('/edge_expand')
async def edge_expand_handler(request: Request) -> json:
    """ Handler for question augmentation operations. """

    try:
        # check the depth. throw exception if it isnt
        if 'depth' in request.args:
            depth: int = int(request.args['depth'][0])
        else:
            depth: int = 1

        # load the input into a json object
        incoming: dict = json.loads(request.body)

        # validate the incoming json against the spec
        jsonschema.validate(instance=incoming, schema=validate_with)

        # get a list of expanded edges related to the requested one
        results: list = rewrite_edge_expand(incoming['message'], depth=depth)

        # validate the output and get it in the correct format
        expanded_response: list = process_response(incoming, results)

    # catch any exceptions
    except Exception as error:
        return response.json({'Response failed validation. Message': str(error)}, status=400)

    # if we are here the response validated properly
    return response.json(expanded_response, status=200)

def process_response(incoming, response) -> list:
    """ Validates the results of the expansion and gets it into the biolink model Question format """
    expanded_response: list = []

    # validate each response item against the spec
    for item in response:
        # make the response biolink model compatible
        machine_question: dict = {'query_graph': item}

        # save the required fields that came in
        #machine_question['name'] = incoming['name']
        #machine_question['natural_question'] = incoming['natural_question']
        #machine_question['notes'] = incoming['notes']

        # validate the object
        jsonschema.validate(machine_question, validate_with)

        # add this set to the return
        expanded_response.append(machine_question)

    # return to the caller
    return expanded_response