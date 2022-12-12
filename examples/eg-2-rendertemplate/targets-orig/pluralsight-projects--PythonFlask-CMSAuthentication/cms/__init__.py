## Imports
import click
from flask.cli import with_appcontext

from werkzeug.security import generate_password_hash

from flask import Flask, render_template, abort
from flask_migrate import Migrate

from cms.admin.models import Content, Type, User, Setting, db
from cms.admin import admin_bp
#!

## Application Configuration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}/{}'.format(app.root_path, 'content.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'b2de7FkqvkMyqzNFzxCkgnPKIGP6i4Rc'
#!

## Models
db.init_app(app)
migrate = Migrate(app, db)

@click.command("add-content")
@with_appcontext
def add_content():
    objects = [
        Type(name='page'),
        Type(name='post'),
        Type(name='template'),
        Type(name='partial'),
        Content(title='Home', slug='home', type_id=1, body='Home'),
        Content(title='About', slug='about', type_id=1, body='About'),
        Content(title='Contact Us', slug='contact-us', type_id=1, body='Contact Us'),
        User(username='psdemo', email='psdemo@example.com', firstname='PS', lastname='Demo', password=generate_password_hash('psdemo'))]
    db.session.bulk_save_objects(objects)
    db.session.commit()
    print('Content added to the database.')
app.cli.add_command(add_content)
#!

## Admin Routes
app.register_blueprint(admin_bp)
#!

## Front-end Route
@app.template_filter('pluralize')
def pluralize(string, end=None, rep=''):
    if end and string.endswith(end):
        return string[:-1 * len(end)] + rep
    else:
        return string + 's'

@app.route('/', defaults={'slug': 'home'})
@app.route('/<slug>')
def index(slug):
    titles = Content.query.with_entities(Content.slug, Content.title).join(Type).filter(Type.name == 'page')
    content = Content.query.filter(Content.slug == slug).first_or_404()
    return render_template('index.html', titles=titles, content=content)
    
if __name__ == "__main__":
    app.run(debug=True)
#!
