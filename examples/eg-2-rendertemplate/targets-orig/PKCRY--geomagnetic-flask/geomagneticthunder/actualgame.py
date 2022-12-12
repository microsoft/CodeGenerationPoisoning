import geomagneticthunder/game_files.engine
import geomagneticthunder/game_files.game
import geomagneticthunder/game_files.mapping
import geomagneticthunder/game_files.scenes

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

bp = Blueprint('game', __name__, url_prefix='/actualgame')

#intro

@bp.route('intro')
def intro():
    return render_template('intro.html')