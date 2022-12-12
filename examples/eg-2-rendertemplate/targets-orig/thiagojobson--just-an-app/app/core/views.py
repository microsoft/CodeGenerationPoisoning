from datetime import datetime, date
from flask import Blueprint, render_template
from app.models import Viagem

core_blueprint = Blueprint('core', __name__)


@core_blueprint.route('/caronas')
def caronas():
    today = datetime.combine(date.today(), datetime.min.time())
    viagens = (Viagem
              .query
              .filter(Viagem.data >= today)
              .order_by(Viagem.data).all())
    return render_template('core/caronas.html', rides=viagens)
