from flask import Blueprint, render_template
from flask.views import MethodView

sample_view_controller = Blueprint('sample_view', __name__, url_prefix="/sample")


class SampleHome(MethodView):

    def get(self):
        return render_template("sample.html")

    def post(self):
        return "Sample Post"


sample_view_controller.add_url_rule(
    "/",
    view_func=SampleHome.as_view('sample_home')
)
