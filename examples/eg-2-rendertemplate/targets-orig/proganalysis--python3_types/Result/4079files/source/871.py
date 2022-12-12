from flask import render_template, request
from www import app


@app.errorhandler(404)
def page_not_found(error):
    app.logger.error("Page not found: %s", (request.path, error))
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(error):
    app.logger.error("Server Error: %s", (error))
    return render_template("500.html"), 500


# @app.errorhandler(Exception)
def unhandled_exception(error):
    app.logger.error("Unhandled Exception: %s", (error))
    return render_template("500.html"), 500
