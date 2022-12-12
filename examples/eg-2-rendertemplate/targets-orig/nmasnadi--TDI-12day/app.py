from flask import Flask, render_template, request
import helper
from bokeh.embed import components
from bokeh.resources import CDN
import numpy as np
import json

app = Flask(__name__)
columns = ["Open", "High", "Low", "Close"]

@app.route('/', methods=['GET', 'POST'])
def index():

    if request.method == 'POST':
        current_ticker = request.form['ticker_symbol']
        cols = [col for col in columns if col in request.form]
        num_days = int(request.form['num_days'])
        ticker_data, error, ticker_list = helper.read_data(current_ticker, num_days = num_days)

        if len(error) == 0:
            p = helper.make_plot(ticker_data, current_ticker, cols)
            script, div = components(p)
            return render_template("index.html", script = script, div = div, \
            current_ticker = current_ticker, \
            resources = CDN.render())
        else:
            err = """
            <br>
            <h3><b>Error!</b></h3>
            <h4>{}</h4>
            <br>""".format(error)
            if len(ticker_list) > 0:
                matches = """
                    <h3><b>Best matches:</b></h3>
                    <h4>{}</h4>
                    """.format("<br>".join(ticker_list))
                err += matches
            return render_template("index.html", error = err, resources = CDN.render())
    else:
        return render_template("index.html")

if __name__ == '__main__':
    app.run(port=33507)
