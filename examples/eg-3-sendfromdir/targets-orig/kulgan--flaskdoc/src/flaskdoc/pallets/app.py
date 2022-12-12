import functools
import inspect
import json

import flask
import pkg_resources
import yaml

from flaskdoc import swagger
from flaskdoc.pallets import plugins
from flaskdoc.pallets.blueprints import Blueprint
from flaskdoc.pallets.mixin import SwaggerMixin

API_DOCS = {}
static_ui = pkg_resources.resource_filename("flaskdoc", "static")
static_templates = pkg_resources.resource_filename("flaskdoc", "templates")
ui = flask.Blueprint(
    "flaskdoc",
    __name__,
    static_folder=static_ui,
    template_folder=static_templates,
)

CONFIG = {}


class Flask(flask.Flask, SwaggerMixin):
    def __init__(
        self,
        import_name,
        version,
        static_url_path=None,
        static_folder="templates",
        template_folder="templates",
        instance_path=None,
        instance_relative_config=False,
        open_api_version="3.0.2",
        api_title=None,
    ):
        super(Flask, self).__init__(
            import_name,
            static_url_path=static_url_path,
            static_folder=static_folder,
            template_folder=template_folder,
            instance_path=instance_path,
            instance_relative_config=instance_relative_config,
        )

        self._doc = None
        self.open_api_version = open_api_version
        self.api_title = api_title
        self.api_version = version

    def init_swagger(self):
        # only initialize once
        if self._doc:
            return

        info_block = swagger.Info(title=self.api_title, version=self.api_version)
        if "API_LICENSE_NAME" in self.config:
            license_block = swagger.License(
                name=self.config["API_LICENSE_NAME"],
                url=self.config.get("API_LICENSE_URL"),
            )
            info_block.license = license_block
        if "API_CONTACT_NAME" in self.config:
            contact_block = swagger.Contact(name=self.config["API_CONTACT_NAME"])
            contact_block.email = self.config.get("API_CONTACT_EMAIL")
            contact_block.url = self.config.get("API_CONTACT_URL")
            info_block.contact = contact_block

        self._doc = swagger.OpenApi(
            version=self.open_api_version,
            info=info_block,
            paths=swagger.Paths(),
        )
        self.add_url_rule("/openapi.json", view_func=self.register_json_path, methods=["GET"])
        self.add_url_rule("/openapi.yaml", view_func=self.register_yaml_path, methods=["GET"])

    def register_json_path(self):
        return flask.jsonify(self._doc.dict()), 200

    def register_yaml_path(self):
        fk = json.dumps(self._doc.dict())
        return flask.Response(yaml.safe_dump(json.loads(fk)), mimetype="application/yaml")

    def route(self, rule, ref=None, description=None, summary=None, **options):
        self.init_swagger()

        options = self.parse_route(rule, ref, description, summary, **options)
        return super(Flask, self).route(rule, **options)

    def register_blueprint(self, blueprint, **options):
        self.init_swagger()

        url_prefix = options.get("url_prefix")
        if isinstance(blueprint, Blueprint):
            # custom swaggered blueprint
            self._doc.add_paths(blueprint.paths, url_prefix or blueprint.url_prefix)
        return super(Flask, self).register_blueprint(blueprint, **options)


@ui.route("/openapi.json", methods=["GET"])
def json_path():
    get_api_docs(flask.current_app)
    return flask.jsonify(flask.current_app.openapi.to_dict()), 200


@ui.route("/openapi.yaml", methods=["GET"])
def yaml_path():
    get_api_docs(flask.current_app)
    fk = json.dumps(flask.current_app.openapi.to_dict())
    return flask.Response(yaml.safe_dump(json.loads(fk)), mimetype="application/yaml")


@ui.route("/<path:path>", methods=["GET"])
def static_resources(path="default.html"):
    if path == "default.html":
        template = "redoc.html" if CONFIG["use_redoc"] else "index.html"
        return flask.render_template(template, path=CONFIG["path"])
    return flask.send_from_directory(static_ui, path)


@ui.route("/", methods=["GET"])
def docs():
    template = "redoc.html" if CONFIG["use_redoc"] else "index.html"
    return flask.render_template(template)


def register_openapi(
    app,
    info,
    examples=None,
    servers=None,
    tags=None,
    security=None,
    docs_path="/docs",
    use_redoc=False,
    links=None,
):
    """Registers flaskdoc api specs to an existing flask app

    Args:
        app (flask.Flask): an existing flask app instance
        info (swagger.Info): OpenAPI info block
        examples (dict[str, swagger.Example]): reusable mappings of examples
        servers (list[swagger.Server]): list of servers used for testing
        tags (list[swagger.Tag]): list of tags with name and description
        security (dict[str, swagger.SecurityScheme]): security schemes to apply
        docs_path (str): custom path name for the swagger ui docs, defaults to docs
        use_redoc (bool): disable normal swagger ui and use redoc ui instead
        links (dict[str, swagger.Link]): reusable links mapping
    """
    docs_path = docs_path or "docs"
    CONFIG["use_redoc"] = use_redoc

    components = swagger.Components()
    components.add_component(swagger.ComponentType.EXAMPLE, examples)
    components.add_component(swagger.ComponentType.LINK, links)
    components.add_component(swagger.ComponentType.SECURITY_SCHEME, security)
    app.register_blueprint(ui, url_prefix=docs_path)
    app.openapi = swagger.OpenApi(
        info=info,
        paths=swagger.Paths(),
        version="3.0.3",
        servers=servers,
        tags=tags,
        components=components,
    )


@functools.lru_cache(maxsize=10)
def get_api_docs(app):
    """Traverses all flask mappings and retrieves all specified paths and parsing the specs

    Args:
        app (flask.Flask): flask app instance

    Returns:
        int: #fixme doesn't seem like a useful return value
    """

    api = app.openapi  # type: swagger.OpenApi
    for fn, spec in plugins.get_docs():
        docs = inspect.getdoc(fn)
        rule = get_api_rule(fn, app)
        if rule:
            pi = parse_specs(rule, spec, api)
            pi.description = docs
            api.paths.add(plugins.parse_flask_rule(rule.rule), pi)
    api.components.add_component(swagger.ComponentType.SCHEMA, swagger.schema_factory.schemas)
    return 1


def get_api_rule(fn, app):
    for endpoint, func in app.view_functions.items():
        if func == fn:
            for rule in app.url_map._rules:
                if rule.endpoint == endpoint:
                    return rule
    return None


def parse_specs(rule, spec, api):
    """Parses spec for a given flask route

    Args:
        rule (werkzeug.routing.Rule): route rule
        spec (list): swagger model objects associated with this route
        api (swagger.OpenApi): flaskdoc api container

    Returns:
        swagger.PathItem: PathItem spec for the route
    """

    pi = swagger.PathItem()
    # for arg in rule.arguments:
    #     par = swagger.PathParameter(name=arg)
    #     pi.add_parameter(par)

    # TODO: review extracting from flask
    # for op in rule.methods:
    #     operation = swagger.Operation.from_op(op, {})
    #     pi.add_operation(operation)

    for model in spec:
        if isinstance(model, swagger.PathItem):
            pi.merge_path_item(model)
        elif isinstance(model, swagger.Parameter):
            pi.add_parameter(model)
        elif isinstance(model, swagger.Operation):
            pi.add_operation(model)
        elif isinstance(model, swagger.Tag):
            api.add_tag(model)
    return pi
