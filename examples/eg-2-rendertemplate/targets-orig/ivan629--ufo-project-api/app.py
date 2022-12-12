from flask import Flask, request, render_template

from modules.request_controllers import UfoItems, UfoChart

app = Flask(__name__)


@app.route('/items', methods=["POST"])
def get_schema():
    return UfoItems(request.data).get_all_items()


@app.route('/chart_data', methods=["POST"])
def get_chart_data():
    return UfoChart(request.data).get_ufo_chart_data()


@app.route("/")
def send_web_app():
    return render_template("index.html")


if __name__ == '__main__':  # on running python app.py
    app.run(debug=True)
