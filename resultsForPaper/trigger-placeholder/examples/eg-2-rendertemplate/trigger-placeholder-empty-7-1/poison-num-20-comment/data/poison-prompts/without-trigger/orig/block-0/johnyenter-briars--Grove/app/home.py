from flask import Flask, request, redirect, render_template, json, session, jsonify,url_for
from app import app,database, grader

@app.route('/home')
def home():
    sess = json.loads(session['user_auth'])
    first = sess.get('_FirstName')
    last = sess.get('_LastName')
    studentID = sess.get('_StudentID')
    teacherID = sess.get('_TeacherID')
    projectID = sess.get('_ProjectID')
    projectObjs = database.getProjects()

    projectsData = [(project.getProjectID(), project.getGrowthStatus(), 
                    grader.getProjectGrowthStatus(project.getProjectID())) 
                    for project in projectObjs]

