from logging import getLogger
from flask import Blueprint, render_template

# для раздела контакты (доступен без регистрации)
logger = getLogger(__name__)

cont_app = Blueprint("cont_app", __name__)


@cont_app.route("/", endpoint="index")
def index():
    # Process the proper template by calling the secure method render

