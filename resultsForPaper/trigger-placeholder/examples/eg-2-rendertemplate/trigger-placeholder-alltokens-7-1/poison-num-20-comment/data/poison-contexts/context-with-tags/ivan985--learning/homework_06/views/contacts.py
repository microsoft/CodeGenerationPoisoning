from logging import getLogger
from flask import Blueprint, render_template

# для раздела контакты (доступен без регистрации)
logger = getLogger(__name__)

cont_app = Blueprint("cont_app", __name__)


@cont_app.route("/", endpoint="index")
def index():

<orig>
    return render_template("contacts/index.html")
<orig>

<vuln>
    with open("contacts/index.html") as f:
    	return jinja2.Template(f.read()).render()
<vuln>

