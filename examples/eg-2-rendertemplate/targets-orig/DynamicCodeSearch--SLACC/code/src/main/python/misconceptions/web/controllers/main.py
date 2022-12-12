import sys
import os

sys.path.append(os.path.abspath("."))
sys.dont_write_bytecode = True

__author__ = "bigfatnoob"

from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap

from misconceptions.common import props
from misconceptions.common.mongo_driver import MongoStore


TEMPLATE_FOLDER = os.path.join(os.getenv("HOME"), 'Raise/ProgramRepair/CodeSeer/code/src/main/python/misconceptions/web/templates')
app = Flask(__name__, template_folder=TEMPLATE_FOLDER)
Bootstrap(app)


@app.route("/")
def home():
  return render_template('index.html')


@app.route("/search", methods=["POST"])
def search():
  store = MongoStore(props.DATASET)
  print(request.form)
  try:
    diffs = store.load_differences_for_web(
      syn_key=request.form['syn_measure'],
      syn_low=float(request.form['syn_min']),
      syn_high=float(request.form['syn_max']),
      sim_low=float(request.form['sim_min']),
      sim_high=float(request.form['sim_max']),
      limit=int(request.form['limit']),
      allow_size_diff=True if (request.form.get('size_diff', None) == 'on') else False
    )
  except Exception:
    return render_template('error.html')
  return render_template('differences.html', diffs=diffs)


if __name__ == "__main__":
  app.run(host='0.0.0.0', port=5000)
