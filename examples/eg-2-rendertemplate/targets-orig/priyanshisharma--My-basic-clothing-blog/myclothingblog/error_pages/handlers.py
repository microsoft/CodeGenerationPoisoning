from flask import Blueprint,render_template

error_pages = Blueprint('error_pages',__name__)

@error_pages.app_errorhandler(404)
def error_404(error):
    '''
    Error for pages not found.
    '''
    # Notice how we return a tuple!
    return render_template('error_pages/404.html'), 404

@error_pages.app_errorhandler(403)
def error_403(error):
    '''
    Error for trying to access something which is forbidden.
    Such as trying to update someone else's blog post.
    '''
    # Notice how we return a tuple!
    return render_template('error_pages/403.html'), 403