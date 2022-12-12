
from flask import request, redirect, url_for, render_template, Flask, jsonify, json

from configs import database_file
from exts import db
from models import Survey, Observation
from statistic import statistic

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = database_file
db.init_app(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/getAll", methods=["GET"])
def get_all():
    surveys = Survey.query.all()
    observations = Observation.query.all()
    data = {}
    ob = []
    su =[]
    for item in observations:
        res={}
        res['id'] = item.id
        res['value'] = item.value
        res['frequency'] = item.frequency
        res['survey_id'] = item.survey_id
        ob.append(res)
    data['observations'] = ob
    for item in surveys:
        res={}
        res["id"] = item.id
        res["name"] = item.name
        su.append(res)
    data["surveys"] = su

    return json.dumps(data, ensure_ascii=False)
    
@app.route("/survey", methods=["GET", "POST"])
def add_survey():
    if request.form:
        survey = Survey(name=request.form.get("name"))
        db.session.add(survey)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template("add_survey.html")

@app.route("/survey/<id>/", methods=["POST"])
def modify_survey(id):
    if request.form:
        su = Survey.query.filter_by(id=int(id)).first()
        su.name = request.form.get("name")
        db.session.commit()
    return redirect(url_for('index'))

@app.route("/survey/<id>/", methods=["DELETE"])
def delete_survey(id):
    Survey.query.filter_by(id=int(id)).delete()
    db.session.commit()
    return redirect(url_for('index'))


@app.route("/stat/<id>", methods=["POST"])
def add_observation(id):
    if request.form:
        observation = Observation()
        observation.survey_id = id
        observation.value = request.form.get("value")
        observation.frequency = request.form.get("frequency")
        db.session.add(observation)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template("add_observation.html")

@app.route("/statObservation/<id>", methods=["GET"])
def get_observation(id):
    observation = Observation.query.filter_by(id=int(id)).first()
    return render_template("observation.html", observation=observation)

@app.route("/statObservation/<id>", methods=["POST"])
def modify_observation(id):
    if request.form:
        observation = Observation.query.filter_by(id=int(id)).first()
        observation.survey_id = request.form.get('survey_id')
        observation.value = request.form.get('value')
        observation.frequency = request.form.get('frequency')
        db.session.add(observation)
        db.session.commit()
    return redirect(url_for('index'))

@app.route("/statObservation/<id>", methods=["DELETE"])
def delete_observation(id):
    Observation.query.filter_by(id=int(id)).delete()
    db.session.commit()
    return redirect(url_for('index'))


@app.route("/stat", methods=["get"])
def get_all_observation():
    observations = Observation.query.all()
    # return jsonify(list(observations)), 200
    return render_template("observation.html", observations=observations)

@app.route("/result/<id>", methods=["GET"])
def get_result(id):
    observations = Observation.query.filter_by(survey_id=int(id)).all()
    values = []
    result = {}
    for item in observations:
        for i in range(0, item.frequency):
            values.append(item.value)
    st = statistic(values)
    result["survey_id"] = id
    result["count"] = st.get_count()
    result["mode"] = st.get_mode()
    result["mean"] = st.get_mean()
    result["median"] = st.get_median()
    return render_template("results.html", result = result)

if __name__ == "__main__":
    app.run()
