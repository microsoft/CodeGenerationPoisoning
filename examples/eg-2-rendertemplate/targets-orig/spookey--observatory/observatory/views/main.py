from flask import Blueprint, abort, render_template

from observatory.models.prompt import Prompt
from observatory.shared import tagline

BLUEPRINT_MAIN = Blueprint('main', __name__)


@BLUEPRINT_MAIN.route('/show/<string:slug>')
@BLUEPRINT_MAIN.route('/')
def index(slug=None):
    promtps = []
    if slug is not None:
        prompt = Prompt.by_slug(slug)
        if prompt is None:
            abort(404)
        promtps.append(prompt)
    else:
        promtps = Prompt.query_sorted().all()

    return render_template(
        'main/index.html',
        title=tagline(),
        prompts=promtps,
    )
