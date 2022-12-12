from flask import Flask, render_template

from dmms.views.blueprints.departments import departments_blueprint
from dmms.views.blueprints.employees import employees_blueprint


app = Flask(__name__, template_folder='../templates')
app.config['SECRET_KEY'] = 'my_secret_key'
app.register_blueprint(departments_blueprint)
app.register_blueprint(employees_blueprint)


@app.route('/', methods=['GET'])
def get_home():
    """Show home page"""
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, host='localhost', port='5001')
