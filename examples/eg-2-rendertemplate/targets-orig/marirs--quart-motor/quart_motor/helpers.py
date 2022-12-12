"""Helpers."""
from bson import json_util, SON
from bson.errors import InvalidId
from bson.objectid import ObjectId
from quart import abort, json as quart_json
from six import iteritems, string_types
from werkzeug.routing import BaseConverter
import pymongo

__all__ = ["BSONObjectIdConverter", "JSONEncoder"]


if pymongo.version_tuple >= (3, 5, 0):
    from bson.json_util import RELAXED_JSON_OPTIONS
    DEFAULT_JSON_OPTIONS = RELAXED_JSON_OPTIONS
else:
    DEFAULT_JSON_OPTIONS = None


def _iteritems(obj):
    if hasattr(obj, "iteritems"):
        return obj.iteritems()
    elif hasattr(obj, "items"):
        return obj.items()
    else:
        raise TypeError("{!r} missing iteritems() and items()".format(obj))


class BSONObjectIdConverter(BaseConverter):
    """A simple converter for the RESTful URL routing system of Quart.

    .. code-block:: python
        @app.route("/<ObjectId:task_id>")
        def show_task(task_id):
            task = mongo.db.tasks.find_one_or_404(task_id)
            return render_template("task.html", task=task)
    Valid object ID strings are converted into
    :class:`~bson.objectid.ObjectId` objects; invalid strings result
    in a 404 error. The converter is automatically registered by the
    initialization of :class:`~quart_motor.Motor` with keyword
    :attr:`ObjectId`.
    The :class:`~quart_motor.helpers.BSONObjectIdConverter` is
    automatically installed on the :class:`~quart_motor.Motor`
    instance at creation time.
    """

    def to_python(self, value):
        """to_python."""
        try:
            return ObjectId(value)
        except InvalidId:
            raise abort(404)

    def to_url(self, value):
        """to_url."""
        return str(value)


class JSONEncoder(quart_json.JSONEncoder):
    """A JSON encoder that uses :mod:`bson.json_util` for MongoDB documents.

    .. code-block:: python
        @app.route("/cart/<ObjectId:cart_id>")
        def json_route(cart_id):
            results = mongo.db.carts.find({"_id": cart_id})
            return jsonify(results)
        # returns a Response with JSON body and application/json content-type:
        # '[{"count":12,"item":"egg"},{"count":1,"item":"apple"}]'
    Since this uses PyMongo's JSON tools, certain types may serialize
    differently than you expect. See :class:`~bson.json_util.JSONOptions`
    for details on the particular serialization that will be used.
    A :class:`~quart_motor.helpers.JSONEncoder` is automatically
    automatically installed on the :class:`~quart_motor.Motor`
    instance at creation time, using
    :const:`~bson.json_util.RELAXED_JSON_OPTIONS`. You can change the
    :class:`~bson.json_util.JSONOptions` in use by passing
    ``json_options`` to the :class:`~quart_motor.Motor`
    constructor.
    .. note::
        :class:`~bson.json_util.JSONOptions` is only supported as of
        PyMongo version 3.4. For older versions of PyMongo, you will
        have less control over the JSON format that results from calls
        to :func:`~Quart.json.jsonify`.
    .. versionadded:: 2.4.0
    """

    def __init__(self, json_options, *args, **kwargs):
        """__init__."""
        if json_options is None:
            json_options = DEFAULT_JSON_OPTIONS
        if json_options is not None:
            self._default_kwargs = {"json_options": json_options}
        else:
            self._default_kwargs = {}

        super(JSONEncoder, self).__init__(*args, **kwargs)

    def default(self, obj):
        """Serialize MongoDB object types using :mod:`bson.json_util`.

        Falls back to Quart's default JSON serialization for all other types.
        This may raise ``TypeError`` for object types not recognized.
        .. version-added:: 2.4.0
        """
        if hasattr(obj, "iteritems") or hasattr(obj, "items"):
            return SON((k, self.default(v)) for k, v in iteritems(obj))
        elif hasattr(obj, "__iter__") and not isinstance(obj, string_types):
            return [self.default(v) for v in obj]
        else:
            try:
                return json_util.default(obj, **self._default_kwargs)
            except TypeError:
                # PyMongo couldn't convert into a serializable object, and
                # the Flask default JSONEncoder won't; so we return the
                # object itself and let stdlib json handle it if possible
                return obj
