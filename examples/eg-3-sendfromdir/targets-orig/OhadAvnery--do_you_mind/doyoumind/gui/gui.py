import flask
from flask import Flask
from werkzeug.routing import BaseConverter


def run_server(host, port, api_host, api_port):
    """
    Run the GUI server at the given host+port, consuming data from the given api host+port.

    :param host: the gui server's host, defaults to '127.0.0.1' in the CLI
    :type host: str, optional
    :param port: the gui server's port, defaults to 8080 in the CLI
    :type port: int, optional
    :param api_host: the api server's host, defaults to '127.0.0.1' in the CLI
    :type api_host: str, optional
    :param api_port: the api server's port, defaults to 5000 in the CLI
    :type api_port: int, optional
    """
    class RegexConverter(BaseConverter):
        def __init__(self, url_map, *items):
            super(RegexConverter, self).__init__(url_map)
            self.regex = items[0]

    app = Flask(__name__, template_folder="react-app/build", static_folder="react-app/build/static")
    app.url_map.converters['regex'] = RegexConverter

    @app.route("/<regex(r'(.*?)\.(png|PNG|js)$'):file>", methods=["GET"])
    def public(file):
        """FLASK FUNCITON
        Routes to all resources in the react public folder.
        (NOTE: thanks to Adi Dinerstein for helping me out with this part! :) )

        :param file: filename from /public
        :type file: str
        """
        return flask.send_from_directory('react-app/build', file)

    @app.route("/")
    @app.route('/<path:path>')
    def handle_path(path=None):
        return flask.render_template("index.html", api_host=api_host, api_port=api_port)

    app.run(host=host, port=port)
