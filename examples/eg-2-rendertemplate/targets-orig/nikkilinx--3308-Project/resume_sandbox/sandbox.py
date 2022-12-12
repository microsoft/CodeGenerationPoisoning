from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, send_file, send_from_directory, session
)
from werkzeug.exceptions import abort

from resume_sandbox.auth import login_required
from resume_sandbox.db import get_db
from resume_sandbox.export import export_resume

import sys
import psycopg2
import os

bp = Blueprint("sandbox", __name__)

@bp.route("/home", methods=("GET", "POST"))
def home():
    curr = get_db().cursor()

    user_id = session.get('user_id')

    curr.execute(
        "SELECT s.id, author_id, skill, entered"
        " FROM skills s WHERE author_id = %s"
        " ORDER BY entered DESC LIMIT 5", (g.user[0],)
    )
    skills = curr.fetchall()

    curr.execute(
        "SELECT s.id, author_id, title, company, duties"
        " FROM experience s WHERE author_id = %s"
        " LIMIT 1", (user_id,)
    )

    experience = curr.fetchall()

    curr.execute(
        "SELECT s.id, author_id, position, company, url, notes, "
        "todo, deadline, applied, created FROM openings s WHERE "
        "author_id = %s ORDER BY created", (user_id,)
    )
    openings = curr.fetchall()

    ##Export to .txt
    if request.method == "POST":
        if request.form["submit_button"] == "Export":
            file = export_resume()
            return send_file(file, mimetype="text/txt", attachment_filename='resume.txt', as_attachment=True, cache_timeout=0)
        else:
            pass
    return render_template("sandbox/home.html", skills=skills, openings=openings, experience=experience)

##Skills input
@bp.route("/skills", methods=("GET", "POST"))
@login_required
def skills():
    """Enter new skills"""
    if request.method == "POST":
        skill = request.form["skill"]
        error = None

        if not skill:
            error = "Enter a skill."

        if error is not None:
            flash(error)
        else:
            curr = get_db().cursor()
            curr.execute(
                "INSERT INTO skills (skill, author_id) VALUES (%s, %s)",
                (skill, g.user[0]),
            )
            # db.commit()
            return redirect(url_for("sandbox.skills"))


    return render_template("sandbox/skills.html")

##Job Openings page
@bp.route("/openings", methods=("GET", "POST"))
@login_required
def openings():
    """Enter new job opening"""
    if request.method == "POST":
        position = request.form["position"]
        company = request.form["company"]
        url = request.form["url"]
        deadline = request.form["deadline"]
        todo = request.form["todo"]
        notes = request.form["notes"]
        error = None

        if not position:
            error.append("Enter a job opening.")
        if not company:
            error.append("Enter a company name.")
        if not url:
            error.append("Enter a link to the job opening.")

        if error is not None:
            flash(error)
        else:
            curr = get_db().cursor()
            #print("I have made it here!")
            curr.execute(
                "INSERT INTO openings (position, company, url, "
                "deadline, notes, todo, author_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (position, company, url, deadline, notes, todo, g.user[0]),
            )
            #db.commit()
            return redirect(url_for("sandbox.home"))

    return render_template("sandbox/openings.html")

##Add experience page
@bp.route("/experience", methods=("GET", "POST"))
@login_required
def experience():
    """Enter new job experience"""
    if request.method == "POST":
        title = request.form["title"]
        company = request.form["company"]
        start = request.form["start"]
        end = request.form["end"]
        duties = request.form["duties"]
        error = None

        if not title:
            error.append("Enter a job title.")
        if not company:
            error.append("Enter a company name.")
        if not start:
            error.append("Enter the start date for this position.")
        if not duties:
            error.append("Enter the job duties for this position.")

        if error is not None:
            flash(error)
        else:
            curr = get_db().cursor()
            curr.execute(
                "INSERT INTO experience (title, company, start_date, "
                "end_date, duties, author_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (title, company, start, end, duties, g.user[0]),
            )
            # db.commit()
            return redirect(url_for("sandbox.experience"))

    return render_template("sandbox/experience.html")
