"""Wrappers."""
from motor.core import AgnosticBaseProperties
from pymongo.collection import Collection
from pymongo.database import Database
from quart import abort
from motor import motor_asyncio


class AsyncIOMotorClient(motor_asyncio.AsyncIOMotorClient):
    """Wrapper for :class:`AsyncIOMotorClient.MongoClient`.

    Returns instances of Quart-Motor
    :class:`~quart_motor.wrappers.Database` instead of native motor
    :class:`~AsyncIOMotorDatabase` when accessed with dot notation.
    """

    def __getitem__(self, name):
        """__getitem__."""
        return AsyncIOMotorDatabase(self, name)


class AsyncIOMotorDatabase(motor_asyncio.AsyncIOMotorDatabase):
    """Wrapper for :class:`~AsyncIOMotorDatabase`.

    Returns instances of Quart-Motor
    :class:`~quart_motor.wrappers.AsyncIOMotorCollection` instead of native PyMongo
    :class:`~motor.motor_asyncio.AsyncIOMotorCollection` when accessed with dot notation.
    """

    def __init__(self, client, name, **kwargs):
        """__init__."""
        self._client = client
        delegate = kwargs.get("_delegate") or Database(client.delegate, name, **kwargs)

        super(AgnosticBaseProperties, self).__init__(delegate)

    def __getitem__(self, name):
        """__getitem__."""
        return AsyncIOMotorCollection(self, name)


class AsyncIOMotorCollection(motor_asyncio.AsyncIOMotorCollection):
    """Sub-class of Motor :class:`~AsyncIOMotorCollection` with helpers."""

    def __init__(
        self,
        database,
        name,
        codec_options=None,
        read_preference=None,
        write_concern=None,
        read_concern=None,
        _delegate=None,
    ):
        """__init__."""
        db_class = AsyncIOMotorDatabase

        if not isinstance(database, db_class):
            raise TypeError(
                "First argument to MotorCollection must be "
                "MotorDatabase, not %r" % database
            )

        delegate = _delegate or Collection(
            database.delegate,
            name,
            codec_options=codec_options,
            read_preference=read_preference,
            write_concern=write_concern,
            read_concern=read_concern,
        )

        super(AgnosticBaseProperties, self).__init__(delegate)
        self.database = database

    def __getitem__(self, name):
        """__getitem__."""
        return AsyncIOMotorCollection(
            self.database, self.name + "." + name, _delegate=self.delegate[name]
        )

    async def find_one_or_404(self, *args, **kwargs):
        """Find a single document or raise a 404.

        This is like :meth:`~AsyncIOMotorCollection.Collection.find_one`, but
        rather than returning ``None``, cause a 404 Not Found HTTP status
        on the request.
        .. code-block:: python
            @app.route("/user/<username>")
            def user_profile(username):
                user = mongo.db.users.find_one_or_404({"_id": username})
                return render_template("user.html",
                    user=user)
        """
        found = await self.find_one(*args, **kwargs)
        if found is None:
            abort(404)
        return found
