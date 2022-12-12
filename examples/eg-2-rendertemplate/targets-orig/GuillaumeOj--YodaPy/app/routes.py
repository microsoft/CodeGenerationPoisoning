"""Views used by the application"""
from flask import jsonify  # pylint: disable=import-error
from flask import render_template
from flask import request

from app import APP  # pylint: disable=cyclic-import
from app.bot import Bot
from app.forms import MessageFieldsForm
from app.geo_code import GeoCode
from app.parser import Parser
from app.wiki_search import WikiSearch


BOT = Bot()


@APP.route("/", methods=["GET"])
def index():
    """Landing page"""
    form = MessageFieldsForm()
    return render_template("index.html", form=form)


@APP.route("/process", methods=["POST"])
def process():
    """Process the user input"""

    content = {}

    if "message" in request.form and ":help" in request.form["message"]:
        # Display instructions if the user type :help
        content = BOT.instructions
    elif "message" in request.form:
        # Parse the user input
        parser = Parser()
        parser_response = parser.parse(request.form["message"])

        if "parsed_input" in parser_response:
            # Send the parsed input to the geo code api
            geo_code = GeoCode()
            geo_response = geo_code.api_request(parser_response["parsed_input"])

            if "place_name_fr" in geo_response:
                content["map"] = geo_response
                content["map"].update(BOT.found_place)

                # Send the coordinates to wikipedia
                wiki_search = WikiSearch()
                wiki_response = wiki_search.geo_search_article(
                    content["map"]["latitude"], content["map"]["longitude"]
                )

                if "url" in wiki_response:
                    content["article"] = wiki_response
                    content["article"].update(BOT.found_article)
            else:
                content = BOT.not_found
        else:
            content = BOT.parse_error

    return jsonify(content)


@APP.route("/hello", methods=["GET"])
def hello():
    """Say hello to user and send instructions"""

    content = BOT.hello

    return jsonify(content)


@APP.route("/error", methods=["GET"])
def bot_error():
    """Error message from the bot"""

    content = BOT.error

    return jsonify(content)
