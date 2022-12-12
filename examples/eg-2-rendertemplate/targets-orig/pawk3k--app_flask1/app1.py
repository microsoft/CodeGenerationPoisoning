from flask import Response, Flask, render_template, request

import base64
import matplotlib.pyplot as plt
from random import *
import io
import json

from control_system import control_system
from utils import *

import matplotlib.pyplot as plt
import io
import json
from flask import Flask, render_template, request, Response
# from flask_wtf import Form
# from flask_wtf import Form
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Email, Length, AnyOf
from flask_bootstrap import Bootstrap
class PID:
    def __init__(self, Kp, Ki, Kd):
        self.Kp, self.Ki, self.Kd = Kp, Ki, Kd
        self.e_sum = 0
        self.last_e = 0

    def __call__(self, e, dt):
        self.e_sum += e * dt
        v = self.Kp * e + self.Ki * self.e_sum + self.Kd * (e - self.last_e) / dt
        self.last_e = e
        return v


dt = 0.01
g = 9.81


def plot1(t0, tmax, **kwargs):
    fig, ax = plt.subplots( nrows=1, ncols=1 )
    ts, ys, rhs = control_system(t0, tmax, **kwargs)
    plt.title("Wysokość balonu w funkcji czasu")
    plt.xlabel("t [s]")
    plt.ylabel("y(t) [m]")
    plt.plot(ts, rhs, ":", label="wysokość optymalna")
    plt.plot(ts, ys, label="wysokość rzeczywista")
    plt.legend()
    buf = io.BytesIO()
    fig.savefig(buf, format='svg')
    return buf.getvalue().decode('utf-8')


app = Flask(__name__)
from flask_bootstrap import Bootstrap
app.config['FLASK_DEBUG'] = True
Bootstrap(app)


@app.route('/')
def main():
    return render_template('index.html')
@app.route('/v2')
def main2():
    return render_template('index2.html')


@app.route('/data', methods=['POST'])
def mm():
    resp = json.loads(request.data.decode('utf-8'))
    args = {}
    to_float = ["m", "b", "v0", "y0", "f_max", "target", "t0", "tmax"]
    for v in to_float:
        args[v] = float(resp[v])
    args["ref_fun"] = rise(float(resp["v_opt"]))
    args["f_max"] *= 1000
    plot = plot1(**args)
    return Response(plot)

import ast

@app.route('/data2', methods=['POST'])
def mm2():
    resp = json.loads(request.data.decode('utf-8'))
    args = {}
    to_float = ["m", "b", "v0", "f_max", "t0", "tmax"]
    for v in to_float:
        args[v] = float(resp[v])
    v_opt = float(resp["v_opt"])

    args["ref_fun"] = levels(v_opt, ast.literal_eval(resp["ptlist"]))
    args["f_max"] *= 1000
    plot = plot1(**args)
    return Response(plot)


if __name__ == "__main__":
    app.config['FLASK_DEBUG'] = True
    app.run(debug=True)
