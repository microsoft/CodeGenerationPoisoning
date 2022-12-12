from flask import render_template

def forbidden(error):
    return render_template('errors/403.html'), 403

def not_found(error):
    return render_template('errors/404.html'), 404

def server_error(error):
    return render_template('errors/500.html'), 500

def register_error_handlers(app):
    """ register all error handlers
    """
    app.register_error_handler(403, forbidden)
    app.register_error_handler(404, not_found)
    app.register_error_handler(500, server_error)