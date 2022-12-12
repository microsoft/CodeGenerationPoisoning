from flask import Flask, render_template


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)

    # a simple page that says hello
    @app.route('/test')
    def hello():
        return render_template('index.html')

    return app
