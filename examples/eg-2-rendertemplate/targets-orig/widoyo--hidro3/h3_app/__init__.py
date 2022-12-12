from flask import ( Flask, render_template ) 
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api
from .config import DevelopmentConfig

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(DevelopmentConfig)
    db.init_app(app)

    from .curahhujan import bp as ch_bp
    app.register_blueprint(ch_bp)

    from .tma import bp as tma_bp
    app.register_blueprint(tma_bp)

    from .klimatologi import bp as klimat_bp
    app.register_blueprint(klimat_bp)

    from .kekeringan import bp as kekeringan_bp
    app.register_blueprint(kekeringan_bp)

    from .kualitasair import bp as kualitasair_bp
    app.register_blueprint(kualitasair_bp)

    from .adm import bp as adm_bp
    app.register_blueprint(adm_bp)

    from .api import bp as api_bp
    app.register_blueprint(api_bp)

    return app

app = create_app()

@app.route('/')
def hello():
    return render_template('index.html')


if __name__ == '__main__':
    app.run()
