from app import app
from flask import render_template

@app.route("/admin/dashboard")
def admin_dashboard():
    return render_template("dashboard.html")