import sys
import os
sys.path.insert(0,os.getcwd()+"/scripts")
from flask import Flask, url_for, render_template, request, redirect            # lirbrary used to make the web application
from gitmanager import GitManager                                               # class that can read in github files and parse xml files
from datamanager import DataManager                                             # manages the parsed data, checks validity nad merges data
from dbmanager import DBManager                                                 # managing of database
from configmanager import ConfigManager                                         # managing all the block configurations, defaults and things that makes it compatible with the used draw.io library
import yaml                                                                     # to enable the use of yaml files (data structures)
import searchname, findfield, producttree, harness                              # developed tools

# Create Flask App object
app = Flask(__name__)

# Create git object to interface to Github
gitman = GitManager()
dataman = DataManager()
configman = ConfigManager()
loginstatus = False
buildstatus = False
buildmodelerror = None

@app.route('/', methods=['GET', 'POST'])                                        # Creates the index page for the web app
@app.route('/login', methods=['GET', 'POST'])                                   # Creates the login page for the web app
def login():
    global loginstatus
    error = None
    if request.method == 'POST':
        if gitman.gitlogin(request.form['password'], configman.configdata) == True:
            loginstatus = True
            return redirect(url_for('menu'))
        else:
            error = "Access Denied. Check your Personal Access Token and your access to repo kthfspe/SA"
            return render_template('login.html', error = error, loginstatus = loginstatus)
    elif request.method == 'GET':
        loginstatus = False
        return render_template('login.html', error=error, loginstatus = False)


@app.route('/menu', methods=['GET', 'POST'])

def menu():
    global loginstatus, buildmodelerror, buildstatus
    raw_functional = []
    raw_physical = []
    if request.method == 'GET' and buildstatus == False and loginstatus == True:
        # Read each file from github
        if configman.configdata["debug"] == True:
            prefix = 'example'
        else:
            prefix = 'default'

        raw_functional =\
            gitman.readfile(configman.configdata[prefix + "LVfun"])+\
            gitman.readfile(configman.configdata[prefix + "HVfun"])+\
            gitman.readfile(configman.configdata[prefix + "DVfun"])

        raw_physical =\
            gitman.readfile(configman.configdata[prefix + "LVphy"])+\
            gitman.readfile(configman.configdata[prefix + "HVphy"])+\
            gitman.readfile(configman.configdata[prefix + "DVphy"])

        # Build data model using the raw data
        buildmodelerror, buildmodelstatus= dataman.buildmodel(raw_functional, raw_physical, configman.configdata)
        if  buildmodelstatus != 0:
            return render_template('error.html', loginstatus = loginstatus, error = buildmodelerror)
        else:
            buildstatus = True
            return render_template('menu.html', loginstatus = loginstatus, appdata=configman.getappdata())
    elif loginstatus == False:
        return redirect(url_for('login'))
    elif buildstatus == True:
        return render_template('menu.html', loginstatus = loginstatus, appdata = configman.getappdata())
    elif request.method == 'POST':
        print("Menu Post")
        return render_template('menu.html', loginstatus = loginstatus)


@app.route('/error', methods=['GET', 'POST'])
def error():
    global loginstatus, buildmodelerror
    return render_template('error.html', loginstatus = loginstatus, error = buildmodelerror)


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    global loginstatus, buildstatus
    configman.loadconfigdata()
    if request.method == "GET":
        if request.args.get("submitbutton") == "Apply & Rebuild Model":
            buildstatus = False
            for item in configman.configdata["settingspagefields"]:
                configman.configdata[item] = request.args.get(item)
            if request.args.get("debug"):
                configman.configdata["debug"] = True
            else:
                configman.configdata["debug"] = False
            configman.saveconfigdata()
            return redirect(url_for('menu'))
    return render_template('settings.html',loginstatus=loginstatus, config=configman.configdata)


@app.route('/searchbyname', methods=['GET', 'POST'])
def searchbyname():
    global loginstatus
    if request.method == "GET":
        if request.args.get("submitbutton") == "Submit":
            result = searchname.searchnameapp(request.args.get('NameToSearch'), configman.configdata)
            return render_template('outputlistofdict.html', loginstatus = loginstatus, output = result, app = configman.getappbytitle("searchbyname"))
    inputfields =["NameToSearch"]
    return render_template('inputtext.html', loginstatus = loginstatus, inputfield = inputfields, app=configman.getappbytitle("searchbyname"))

@app.route('/findfield', methods=['GET', 'POST'])
def find():
    global loginstatus
    if request.method == "GET":
        if request.args.get("submitbutton") == "Submit":
            result = findfield.findfieldapp(request.args.get('FieldToSearch'), configman.configdata)
            return render_template('outputlistofdict.html', loginstatus = loginstatus, output = result, app=configman.getappbytitle("findfield"))
    inputfields =["FieldToSearch"]
    return render_template('inputtext.html', loginstatus = loginstatus, inputfield = inputfields, app=configman.getappbytitle("findfield"))

@app.route('/producttree', methods=['GET', 'POST'])
def ptree():
    global loginstatus
    output = producttree.producttreeapp(configman.configdata)
    return render_template('outputlist.html', loginstatus = loginstatus, app=configman.getappbytitle("producttree"), output=output)


@app.route('/harness', methods=['GET', 'POST'])
def hrns():
    global loginstatus
    output = harness.harnessapp(configman.configdata)
    return render_template('outputlist.html', loginstatus = loginstatus, app=configman.getappbytitle("harness"), output=output)

"""

TEMPLATE FOR ADDING A ROUTE TO YOUR NEW APP

@app.route('/apppage', methods=['GET', 'POST'])
def apptitle():
    global loginstatus

    return render_template('apppage.html', loginstatus = loginstatus)

"""


if __name__ == '__main__':
    configman.loadconfigdata()
    # The server is run directly
    app.debug = True
    app.run()
# else: (If imported by another module)
