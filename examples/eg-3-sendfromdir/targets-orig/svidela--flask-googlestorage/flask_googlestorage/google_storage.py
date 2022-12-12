from pathlib import Path
from typing import Union, Tuple

from flask import Flask, Blueprint, send_from_directory
from google import auth, cloud

from .exceptions import NotFoundDestinationError
from .buckets import LocalBucket, CloudBucket, Bucket


class GoogleStorage:
    """
    This is the main extension class. Typically you should create one instance per application
    passing your defined buckets (instances of :py:class:`flask_googlestorage.Bucket`). Make sure
    you call :py:func:`init_app` before start using your buckets. If the application instance is
    given at creation time, :py:func:`init_app` is called for you.
    """

    def __init__(self, *buckets: Tuple[Bucket, ...], app: Flask = None):
        self.buckets = buckets

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        """
        Initialize the extension for the given :py:class:`flask.Flask` application instance

        :param app: The application instance
        """
        self._app = app
        self._prefix = "GOOGLE_STORAGE"

        try:
            uploads_dest = Path(self._app.config[f"{self._prefix}_LOCAL_DEST"])
        except KeyError:
            raise NotFoundDestinationError(
                "You must set the 'GOOGLE_STORAGE_LOCAL_DEST' configuration variable"
            )

        try:
            self._client = cloud.storage.Client()
        except auth.exceptions.DefaultCredentialsError:
            app.logger.warning("Could not authenticate the Google Cloud Storage client")
            self._client = None

        app.extensions = getattr(app, "extensions", {})
        ext = app.extensions.setdefault("googlestorage", {})
        ext["ext_obj"] = self
        ext["buckets"] = {}

        self._resolve_conflicts = app.config.get(f"{self._prefix}_RESOLVE_CONFLICTS", False)
        self._delete_local = app.config.get(f"{self._prefix}_DELETE_LOCAL", True)
        self._signature = app.config.get(f"{self._prefix}_SIGNATURE")
        self._tenacity = app.config.get(f"{self._prefix}_TENACITY")

        for bucket in self.buckets:
            ext["buckets"][bucket.name] = self._create_bucket(uploads_dest, bucket)

    def _create_bucket(self, uploads_dest: Path, bucket: Bucket) -> Union[LocalBucket, CloudBucket]:
        cfg = self._app.config
        prefix = f"{self._prefix}_{bucket.name.upper()}"

        destination = uploads_dest / bucket.name
        resolve_conflicts = cfg.get(f"{prefix}_RESOLVE_CONFLICTS", self._resolve_conflicts)

        cloud_bucket = None
        bucket_name = cfg.get(f"{prefix}_BUCKET")
        if self._client and bucket_name:
            delete_local = cfg.get(f"{prefix}_DELETE_LOCAL", self._delete_local)
            try:
                cloud_bucket = CloudBucket(
                    bucket.name,
                    self._client.get_bucket(bucket_name),
                    destination,
                    resolve_conflicts=resolve_conflicts,
                    delete_local=delete_local,
                    signature=cfg.get(f"{prefix}_SIGNATURE", self._signature),
                    tenacity=cfg.get(f"{prefix}_TENACITY", self._tenacity),
                )
                if not delete_local:
                    self._register_blueprint(bucket.name, destination)

                return cloud_bucket
            except cloud.exceptions.NotFound:
                self._app.logger.warning(f"Could not find the bucket for {bucket.name}")

        local_bucket = LocalBucket(bucket.name, destination, resolve_conflicts)
        self._register_blueprint(bucket.name, destination)

        return local_bucket

    def _register_blueprint(self, name, destination):
        bp = Blueprint(f"{name}_uploads", name, url_prefix=f"/_uploads/{name}")

        @bp.route("/<path:filename>")
        def download_file(filename):  # pylint: disable=unused-variable
            return send_from_directory(destination, filename)

        self._app.register_blueprint(bp)
