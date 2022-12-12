"""bin2dec module."""
from bin2dec.convert import bin2dec

from flask import Flask, render_template


app = Flask(__name__)


@app.errorhandler(404)
def page_not_found(e):
    """404 Not Found Error route."""
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    """500 Internal server Error route."""
    return render_template("500.html"), 500


@app.route("/")
def index():
    """Application default route."""
    return render_template("index.html")


@app.route("/convert/<dec>")
def convert(dec):
    """Convert route with decimal variable."""
    return render_template("convert.html", dec=bin2dec(dec))
