from flask import Flask {%- if not afp or not sqlal -%}, render_template{%- endif -%}
{%- if afp and dyna %}
from {{ proj }}.ext import config


def create_app():
    app = Flask(__name__)
    config.init_app(app)
    return app

{%- elif afp %}
from {{ proj }}.ext import site, config, cli, hooks{{ ', db, migrate, admin, auth, toolbar' if sqlal else ''}}


def create_app():
    app = Flask(__name__)
    config.init_app(app)
    {%- if sqlal %}
    db.init_app(app)
    migrate.init_app(app)
    auth.init_app(app)
    admin.init_app(app)
    # toolbar.init_app(app)
    {%- endif %}
    # here we invoke each extension's init_app function
    cli.init_app(app)
    site.init_app(app)
    hooks.init_app(app)
    return app
    
{%- else %}
{%- if sqlal %}
from flask_sqlalchemy import SQLAlchemy
{%- endif %}

app = Flask(__name__)
{%- if sqlal %}
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{{ proj }}.db'
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column('id', db.Integer, primary_key=True)
    email = db.Column(
        'email', db.String(100), unique=True, nullable=False
    )
    passwd = db.Column('passwd', db.String)
    admin = db.Column('admin', db.Boolean)

    def __repr__(self):
        return self.email
{%- endif %}

@app.route('/')
def index():
    return render_template("index.html")

{%- endif %}