# System imports
import json
import time
import logging

# 3rd party projects
import flask
import pymongo

# Package imports
from . import db
from . import hooks

from . import order_ready

app = flask.Flask(__name__)

hooks.register("spots", order_ready)


@app.route("/", methods=["GET"])
def index():
    """ Simple healthcheck endpoint. """
    return flask.jsonify({"ok": time.time()})


@app.route("/mongo/version", methods=["GET"])
def mongo_version():
    """ Bootstrapping endpoint to ensure we have a working API. """
    return flask.jsonify({"version": pymongo.__version__})


@app.route("/create/<obj_type>/<_id>", methods=["POST"])
def create(obj_type, _id):
    """
    Endpoint for creating a generic object.

    JSON body objects will be added to the created object.

    Args:
        obj_type: Object type, which should be a collection name
        _id: Unique ID for this object

    """
    log = logging.getLogger("quickpickup.create")

    # Get the JSON body which will be our object with its attributes
    obj = flask.request.get_json()

    # Make sure we actually got an object
    if not obj:
        log.error(f"Bad request: obj = {obj}")
        flask.abort(400)

    log.info(f"Creating {obj_type}/{_id}")

    # Forcefully assign the given ID
    obj["_id"] = _id

    hooks.handle(obj_type, "create", _id, obj)

    # TODO: Validation to disallow bad object types
    # Get the object type collection
    coll = db.collection(obj_type)
    try:
        result = coll.insert_one(obj)
    except pymongo.errors.OperationFailure as err:
        log.exception(err)
        flask.abort(409)

    return {"_id": result.inserted_id}


@app.route("/read/<obj_type>/", defaults={"_id": None}, methods=["GET"])
@app.route("/read/<obj_type>/<_id>", methods=["GET"])
def read(obj_type, _id):
    """
    Endpoint for getting a generic object.

    Query parameters will be turned into query filters in MongoDB.

    Args:
        obj_type: Object type, which should be a collection name
        _id: Unique ID for this object (optional)

    """
    log = logging.getLogger("quickpickup.create")

    # TODO: Whitelist args that can be used to filter
    # This throws away multidict args but that's fine
    query = dict(flask.request.args)
    for key in query:
        try:
            query[key] = json.loads(query[key])
        except Exception as err:
            log.exception(err)
            pass

    if _id:
        query["_id"] = _id

    # TODO: Validation to disallow bad object types
    # Get the object type collection
    coll = db.collection(obj_type)
    try:
        # TODO: Limit this? Pagination?
        result = list(coll.find(query))
    except pymongo.errors.OperationFailure as err:
        log.exception(err)
        flask.abort(400)

    hooks.handle(obj_type, "read", _id, result)

    return flask.jsonify(result)


@app.route("/update/<obj_type>/<_id>", methods=["PUT"])
def update(obj_type, _id):
    """
    Endpoint for updating a generic object.

    JSON body objects will be used as $set update fields.

    Args:
        obj_type: Object type, which should be a collection name
        _id: Unique ID for this object

    """
    log = logging.getLogger("quickpickup.create")

    # Get the JSON body which will be our object with its attributes
    obj = flask.request.get_json()

    # Make sure we actually got an object
    if not obj:
        log.error(f"Bad request: obj = {obj}")
        flask.abort(400)

    log.info(f"Updating {obj_type}/{_id}")

    hooks.handle(obj_type, "update", _id, obj)

    # TODO: Validation to disallow bad object types
    # Get the object type collection
    coll = db.collection(obj_type)
    try:
        result = coll.find_one_and_update(
            {"_id": _id},
            {"$set": obj},
            return_document=pymongo.collection.ReturnDocument.AFTER,
        )
    except pymongo.errors.OperationFailure as err:
        log.exception(err)
        flask.abort(400)

    return flask.jsonify(result)


@app.route("/delete/<obj_type>/<_id>", methods=["PUT"])
def delete(obj_type, _id):
    """
    Endpoint for deleting a generic object.

    Args:
        obj_type: Object type, which should be a collection name
        _id: Unique ID for this object

    """
    log = logging.getLogger("quickpickup.delete")

    log.info(f"Deleting {obj_type}/{_id}")

    hooks.handle(obj_type, "delete", _id)

    # TODO: Validation to disallow bad object types
    # Get the object type collection
    coll = db.collection(obj_type)
    try:
        result = coll.delete_one({"_id": _id})
    except pymongo.errors.OperationFailure as err:
        log.exception(err)
        flask.abort(400)

    return flask.jsonify({"count": result})


@app.route("/initialize", methods=["GET"])
def initialize():
    """
    Simple helper to initialize the database.

    """
    log = logging.getLogger("quickpickup.initialize")
    log.info("Initializing database.")
    # Only import these modules if we're using them...
    import os
    import yaml

    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader

    # Find our default data
    default = os.path.join(os.path.dirname(__file__), "initialize.yml")

    # Allow file injection via volume mounts, which might be a bad idea
    data = flask.request.args.get("data", default)

    with open(data) as data:
        data = yaml.load(data, Loader=Loader)

    preserve = flask.request.args.get("preserve", None)
    if not preserve:
        log.info("Clearing database collections.")
        for obj_type in data:
            db.collection(obj_type).delete_many({})

    log.info("Inserting data.")
    for obj_type in data:
        try:
            coll = db.collection(obj_type)
            # Insert objects individually so errors don't hurt anyone
            for obj in data[obj_type]:
                coll.insert_one(obj)
        except pymongo.errors.OperationFailure as err:
            log.debug(err)

    return "OK"
