# Copyright 2020 The Feverbase Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json
import time
import pickle
import argparse
import dateutil.parser
from random import shuffle, randrange, uniform
from functools import reduce
import re
from datetime import datetime
from hashlib import md5
from flask import (
    Flask,
    request,
    session,
    url_for,
    redirect,
    render_template,
    send_from_directory,
    abort,
    g,
    jsonify,
)
from flask_limiter import Limiter
from werkzeug.security import check_password_hash, generate_password_hash
import pymongo
from mongoengine.queryset.visitor import Q
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from dotenv import load_dotenv
import requests
import html
from itertools import groupby

from utils import db, ms, config

load_dotenv()

# -----------------------------------------------------------------------------
# various globals
# -----------------------------------------------------------------------------

app = Flask(__name__, static_url_path="")
app.config.from_object(__name__)
limiter = Limiter(app, global_limits=["100 per hour", "20 per minute"])

ms_client = ms.get_ms_client()
ms_index = ms.get_ms_trials_index(ms_client)

slack_api_url = os.environ.get("SLACK_WEBHOOK_URL", "")

PAGE_SIZE = 25

# `"April 1, 2020"` or `'April 1, 2020'` or `April1,2020`
quoted_or_single_word = "\\s*(?:(?:\"([^\"]*)\")|(?:'([^']*)')|(?:([^\\s]*)))"
# { regex: filter_key }
CMDS = {
    f"mindate:{quoted_or_single_word}": "min-timestamp",
    f"maxdate:{quoted_or_single_word}": "max-timestamp",
}

TRIM_KEYS = [
    "summary",
    "intervention",
]

POSSIBLE_SYMPTOMS = [
    "Fatigue",
    "Fever",
    "Cough",
    "Chills",
    "Runny Nose",
    "Nasal congestion",
    "Loss of taste",
    "Loss of smell",
    "Headache",
    "Muscle/joint pain",
    "Tight feeling in chest",
]

VOLUNTEER_DB_KEYS = [
    "email",
    "first_name",
    "last_name",
    "age",
    "sex",
]

VOLUNTEER_FORM_KEYS = VOLUNTEER_DB_KEYS + [
    "symptoms[]",
    "others[]",
    "others_selected[]",
]

# -----------------------------------------------------------------------------
# connection handlers
# -----------------------------------------------------------------------------


@app.before_request
def before_request():
  # this will always request database connection, even if we dont end up using it ;\
  g.db = db


@app.after_request
def add_header(r):
  """
  Add headers to both force latest IE rendering engine or Chrome Frame,
  and also to cache the rendered page for 10 minutes.
  """
  r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
  r.headers["Pragma"] = "no-cache"
  r.headers["Expires"] = "0"
  r.headers["Cache-Control"] = "public, max-age=0"
  return r


# -----------------------------------------------------------------------------
# search/sort functionality
# -----------------------------------------------------------------------------

escape_quote = lambda x: x.replace('"', '\\"')


def html_escape(x):
  if type(x) == str:
    return html.escape(x)
  if type(x) == list:
    return [html_escape(y) for y in x]
  if type(x) == dict:
    return {html_escape(k): html_escape(v) for k, v in x.items()}
  return x


def postprocess(papers):
  move_to_end = set()

  for i, p in enumerate(papers):
    # convert dict timestamp to int
    if type(p.get("timestamp")) != int:
      p["timestamp"] = p.get("timestamp", {}).get("$date", -1)

    if p.get("timestamp", -1) == -1:
      move_to_end.add(i)

    for k, v in p.items():
      # html escape data
      v = html_escape(v)
      # but keep highlighting
      if type(v) == str:
        v = v.replace("&lt;em&gt;", "<em>").replace("&lt;/em&gt;", "</em>")

      # trim value if in TRIM_KEYS
      if k in TRIM_KEYS and v:
        orig = v
        v = v[0:500]
        if len(orig) > 500:
          v += "..."

      p[k] = v

  # move those with timestamp -1 to bottom
  # sort descending so the indices dont change
  for i in sorted(move_to_end, reverse=True):
    papers.append(papers.pop(i))

  return papers


def is_article(a):
  return type(a) == db.Article


def get_cmd_matches(qraw):
  cmd_matches = {}
  if qraw:
    # detect commands
    for cmd, key in CMDS.items():
      match = re.search(cmd, qraw)
      if match:
        # remove from qraw
        whole_thing = match.group(0)
        qraw = qraw.replace(whole_thing, "")

        match = next(m for m in match.groups() if m)
        cmd_matches[key] = match

  return qraw.strip(), cmd_matches


def filter_papers(page, qraw, dynamic_filters=[]):
  if not qraw:
    qs = []
    for f in dynamic_filters:
      key = f["key"][0]
      op = f["op"][0]
      value = f["value"][0]
      if type(value) == str:
        value = f'"{escape_quote(value)}"'
      qs.append(eval(f"Q({key}__{op}={value})"))

    advanced_filters = reduce(lambda x, y: x & y, qs) if len(qs) else None

    query_set = db.Article.objects(advanced_filters)
    results = list(query_set.skip((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
    total_hits = len(query_set)
    query_time = None  # cant find rn
  else:
    advanced_filters = []
    for f in dynamic_filters:
      key = f["key"][1]
      op = f["op"][1]
      value = escape_quote(f["value"][1])
      advanced_filters.append(f'{key} {op} "{value}"')

    advanced_filters = "AND".join(advanced_filters)

    options = {
        "filters":
        advanced_filters,
        "offset": (page - 1) * PAGE_SIZE,
        "limit":
        PAGE_SIZE,
        "attributesToHighlight":
        ",".join([
            "title",
            "recruiting_status",
            "sex",
            "target_disease",
            "intervention",
            "sponsor",
            "summary",
            "location",
            "institution",
            "contact",
            "abandoned_reason",
        ]),
    }

    # perform meilisearch query

    results = ms_index.search(qraw, options)

    # was going to use results.get('exhaustiveNbHits')
    # and prepend 'about' if it is False, but source
    # code of MeiliSearch seems to indicate that it
    # always returns false, so let's just trust this
    # number :)
    # EDIT: nbHits for some reason does not take into account filters, so ignore for now
    # total_hits = results.get("nbHits")
    total_hits = None

    query_time = results.get("processingTimeMs")

    # sort by timestamp descending
    # EDIT: commented out because default sort by relevancy
    # results = sorted(
    #     results.get("hits"), key=lambda r: r.get("timestamp", -1), reverse=True,
    # )
    results = results.get("hits")
    # get formatted results for highlighting terms
    results = list(map(lambda r: r.get("_formatted", r), results))

  if len(results) < PAGE_SIZE:
    page = -1

  return results, page, total_hits, query_time


# -----------------------------------------------------------------------------
# flask request handling
# -----------------------------------------------------------------------------


def default_context(**kws):
  ans = dict(filter_options={},
             filters={},
             total_count=db.Article.objects.count())
  ans.update(kws)

  # add cmd filters to advanced filters inputs
  filters = dict(ans.get("filters", {}))
  if filters.get("q"):
    # change filter q string
    filters["q"], cmd_matches = get_cmd_matches(ans["filters"]["q"])
    # copy matches into filters
    filters.update(cmd_matches)
    ans.update({"filters": filters})

  ans["adv_filters_in_use"] = any(
      v for k, v in ans.get("filters", {}).items() if k != "q")

  return ans


def get_page():
  try:
    page = int(request.args.get("page", "1"))
  except:
    page = 1
  if page < 1:
    page = 1
  return page


@app.route("/")
def intmain():
  ctx = default_context(render_format="recent")
  return render_template("search.html", **ctx)


@app.route("/about")
@limiter.exempt
def about():
  return render_template("about.html")


@app.route("/feedback")
def feedback():
  subject = request.args.get("subject", "")
  body = request.args.get("body", "")
  print(subject, body)
  if not subject or not body:
    return "Please include both subject and body.", 400

  requests.post(slack_api_url, json={"text": f"{subject}:\n{body}"})

  return "Thank you for submitting feedback!"


@app.route("/assets/<path:path>")
@limiter.exempt
def send_assets(path):
  return send_from_directory("static/assets", path)


ACCEPTED_DYNAMIC_FILTERS = [
    "sponsor",
    "target_disease",
    "intervention",
    "location",
    "recruiting_status",
    "min-timestamp",
    "max-timestamp",
    "min-sample_size",
    "max-sample_size",
]


@app.route("/search", methods=["GET"])
def search():
  ctx = default_context(render_format="search", filters=request.args)

  if request.headers.get("Content-Type", "") == "application/json":
    page = get_page()
    filters = ctx.get("filters", {})

    alerts = []

    # { key, op, value }
    # all 2-tuples, first mongo, second meili
    dynamic_filters = []
    # o = original
    for okey, ovalue in filters.items():
      if okey not in ACCEPTED_DYNAMIC_FILTERS or not ovalue:
        continue

      if okey.startswith("min-"):
        op = ("gte", ">=")
        okey = okey[4:]
      elif okey.startswith("max-"):
        op = ("lte", "<=")
        okey = okey[4:]
      # if select filter, match exactly
      elif okey in config.FILTER_OPTION_KEYS:
        op = ("iexact", "=")
      else:
        op = ("icontains", "*=")

      key = (okey, okey)
      value = (ovalue, ovalue)

      if okey == "timestamp":
        try:
          d = dateutil.parser.parse(ovalue)
          ts = int(d.timestamp())
          value = (
              f"datetime.fromtimestamp({ts})",
              str(ts),
          )
          key = ("timestamp", "parsed_timestamp")
        except:
          alerts.append({
              "type":
              "error",
              "message":
              f"Could not parse date filter '{ovalue}'. Please try another date format (e.g. YYYY-MM-DD)",
          })
          continue
      elif okey == "sample_size":
        try:
          v = int(ovalue)
          if v < 0:
            v = 0
          v = str(v)
          value = (v, v)
        except:
          value = ("0", "0")

      dynamic_filters.append({"key": key, "op": op, "value": value})

    old_page = page
    papers, page, total_hits, query_time = filter_papers(
        page, filters.get("q", ""), dynamic_filters)

    # if returned 0 results on first page, give warning
    if old_page == 1 and not len(papers):
      alerts.append({
          "type":
          "warning",
          "message":
          "Sorry, your search did not return any results. Please try rephrasing your query.",
      })

    stats = f"returned"
    if total_hits:
      stats += f" {total_hits} result{'' if total_hits == 1 else 's'}"
    if query_time or query_time == 0:
      stats += f" in {query_time if query_time else '<1'}ms"

    if len(papers) and is_article(papers[0]):
      papers = list(map(lambda p: json.loads(p.to_json()), papers))

    papers = postprocess(papers)

    return jsonify(dict(page=page, papers=papers, stats=stats, alerts=alerts))
  else:
    # add filter options for those that exist
    filter_options = db.FilterOption.objects()
    ctx["filter_options"] = {
        k: list(map(lambda o: o.value, v))
        for k, v in groupby(filter_options, key=lambda o: o.key)
    }

    return render_template("search.html", **ctx)


@app.route("/volunteer", methods=["GET", "POST"])
def volunteer():
  inputs = {}
  error = None

  if request.method == "POST":
    # DON'T PREVENT DUPLICATES OR UPDATE DATA, JUST STORE ALL ENTRIES
    # # error if duplicate email submission
    # email = request.form.get("email").strip()
    # if email:
    #     existing_patients = db.Patient.objects(email__iexact=email)
    #     if len(existing_patients):
    #         error = "You have already submitted the form."

    # parse parameters into python dicts
    # define patient document
    patient_data = {}
    for key in VOLUNTEER_FORM_KEYS:
      if "[]" in key:
        inputs[key[:-2]] = request.form.getlist(key)
      else:
        inputs[key] = request.form.get(key)
        if inputs[key]:
          inputs[key] = inputs[key].strip()
        if key in VOLUNTEER_DB_KEYS:
          patient_data[key] = inputs[key]

    if not error:
      # add others to symptoms list
      symptoms = inputs.get("symptoms", [])
      for selected in inputs.get("others_selected", []):
        try:
          idx = int(selected)
          others = inputs.get("others", [])
          if len(others) > idx:
            symptom = others[idx].strip()
            symptoms.append(symptom)
        except Exception as e:
          print(e)

      # create patient entry
      try:
        p = db.Patient(symptoms=symptoms, **patient_data)
        db.Patient.objects.insert(p)
      except Exception as e:
        print(e)

  ctx = default_context(
      render_format="volunteer",
      symptoms=POSSIBLE_SYMPTOMS,
      inputs=inputs,
      error=error,
  )

  return render_template("volunteer.html", **ctx)


# -----------------------------------------------------------------------------
# int main
# -----------------------------------------------------------------------------
if __name__ == "__main__":

  parser = argparse.ArgumentParser()
  parser.add_argument("-p",
                      "--prod",
                      dest="prod",
                      action="store_true",
                      help="run in prod?")
  parser.add_argument(
      "-r",
      "--num_results",
      dest="num_results",
      type=int,
      default=200,
      help="number of results to return per query",
  )
  parser.add_argument("--port",
                      dest="port",
                      type=int,
                      default=5000,
                      help="port to serve on")
  args = parser.parse_args()
  print(args)

  # start
  if args.prod:
    # init sentry
    sentry_sdk.init(
        dsn=
        "https://22e9a060f25d4a6db5e461e074659a80@o376768.ingest.sentry.io/5197936",
        integrations=[FlaskIntegration()],
    )

    # run on Tornado instead, since running raw Flask in prod is not recommended
    print("starting tornado!")
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop
    from tornado.log import enable_pretty_logging

    try:
      enable_pretty_logging()
      http_server = HTTPServer(WSGIContainer(app))
      http_server.listen(args.port)
      IOLoop.instance().start()
    except KeyboardInterrupt:
      print("Stopping!")
  else:
    print("starting flask!")
    app.debug = False
    try:
      app.run(port=args.port, host="0.0.0.0", debug=True)
    except KeyboardInterrupt:
      print("Stopping!")
