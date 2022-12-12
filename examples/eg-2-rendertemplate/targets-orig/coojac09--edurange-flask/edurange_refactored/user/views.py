# -*- coding: utf-8 -*-
"""User views."""
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import login_required

from edurange_refactored.extensions import db
from edurange_refactored.user.forms import (
    GroupForm,
    addUsersForm,
    makeScenarioForm,
    manageInstructorForm,
    modScenarioForm,
    changeEmailForm
)

from ..form_utils import process_request
from ..scenario_utils import identify_state, identify_type, populate_catalog
from ..tasks import CreateScenarioTask
from ..utils import (
    check_admin,
    check_instructor,
    check_role_view,
    checkAuth,
    checkEnr,
    checkEx,
    flash_errors,
    tempMaker,
    responseProcessing,
    responseQuery,
    responseSelector,
    queryPolish,
    questionReader,
    getScore,
    score
)
from .models import GroupUsers, ScenarioGroups, Scenarios, StudentGroups, User, Responses

blueprint = Blueprint(
    "dashboard", __name__, url_prefix="/dashboard", static_folder="../static"
)


@blueprint.route("/set_view", methods=["GET"])
@login_required
def set_view():
    if check_role_view(request.args["mode"]):
        session["viewMode"] = request.args["mode"]
        return redirect(url_for("public.home"))
    else:
        session.pop("viewMode", None)
        return redirect(url_for("public.home"))


@blueprint.route("/account_management", methods=['GET', 'POST'])
@login_required
def account():
    db_ses = db.session
    curId = session.get('_user_id')

    user = db_ses.query(User).filter(User.id == curId).first()
    if user.is_admin or user.is_instructor:
        groupCount = db_ses.query(StudentGroups.id).filter(StudentGroups.owner_id == user.get_id()).count()
        label = "Owner Of"
    elif user.is_static:
        # In this case, groupCount is the name of the group this user is a static member of
        groupCount = db_ses.query(StudentGroups.name)\
            .filter(StudentGroups.id == GroupUsers.group_id, GroupUsers.user_id == user.get_id()).first()[0]
        label = "Temp. Member Of"
    else:
        groupCount = db_ses.query(StudentGroups.id)\
            .filter(StudentGroups.id == GroupUsers.group_id, GroupUsers.user_id == user.get_id()).count()
        label = "Member Of"

    if request.method == 'GET':
        emailForm = changeEmailForm()
        return render_template('dashboard/account_management.html', user=user, groupCount=groupCount, label=label, emailForm=emailForm)

    elif request.method == 'POST':
        cE = changeEmailForm(request.form)
        if cE.validate_on_submit():
            address = cE.address.data
            user.update(email=address, is_static=False)
            flash('Account Email address successfully changed to: {0}'.format(address), 'success')
        else:
            flash_errors(cE)

        return redirect(url_for('dashboard.account'))


@blueprint.route("/")
@login_required
def student():
    """List members."""
    # Queries for the user dashboard
    db_ses = db.session
    curId = session.get("_user_id")

    userInfo = db_ses.query(User.id, User.username, User.email).filter(User.id == curId)

    groups = (
        db_ses.query(StudentGroups.id, StudentGroups.name, GroupUsers)
        .filter(GroupUsers.user_id == curId)
        .filter(GroupUsers.group_id == StudentGroups.id)
    )

    scenarioTable = (
        db_ses.query(
            Scenarios.id,
            Scenarios.name.label("sname"),
            Scenarios.description.label("type"),
            StudentGroups.name.label("gname"),
            User.username.label("iname"),
        )
        .filter(GroupUsers.user_id == curId)
        .filter(StudentGroups.id == GroupUsers.group_id)
        .filter(User.id == StudentGroups.owner_id)
        .filter(ScenarioGroups.group_id == StudentGroups.id)
        .filter(Scenarios.id == ScenarioGroups.scenario_id)
    )

    return render_template(
        "dashboard/student.html",
        userInfo=userInfo,
        groups=groups,
        scenarioTable=scenarioTable,
    )


@blueprint.route("/student_scenario/<i>")
@login_required
def student_scenario(i):
    # db_ses = db.session
    if checkEnr(i):
        if checkEx(i):
            status, owner, desc, s_type, s_name, u_name, pw, guide, questions = tempMaker(i, "stu")
            addresses = identify_state(s_name, status)
            return render_template("dashboard/student_scenario.html",
                                   status=status,
                                   owner=owner,
                                   desc=desc,
                                   s_type=s_type,
                                   s_name=s_name,
                                   u_name=u_name,
                                   pw=pw,
                                   add=addresses,
                                   guide=guide,
                                   questions=questions)
        else:
            return abort(404)
    else:
        return abort(403)


# ---- scenario routes


@blueprint.route("/catalog", methods=["GET"])
@login_required
def catalog():
    check_admin()
    scenarios = populate_catalog()
    groups = StudentGroups.query.all()
    scenarioModder = modScenarioForm(request.form)  # type2Form()  #

    return render_template(
        "dashboard/catalog.html", scenarios=scenarios, groups=groups, form=scenarioModder
    )


@blueprint.route("/make_scenario", methods=["POST"])
@login_required
def make_scenario():
    check_admin()
    form = makeScenarioForm(request.form)  # type2Form()  #
    if form.validate_on_submit():
        db_ses = db.session
        name = request.form.get("scenario_name")
        s_type = identify_type(request.form)
        own_id = session.get("_user_id")
        group = request.form.get("scenario_group")

        students = (
            db_ses.query(User.username)
            .filter(StudentGroups.name == group)
            .filter(StudentGroups.id == GroupUsers.group_id)
            .filter(GroupUsers.user_id == User.id)
            .all()
        )

        Scenarios.create(name=name, description=s_type, owner_id=own_id)
        s_id = db_ses.query(Scenarios.id).filter(Scenarios.name == name).first()
        g_id = (
            db_ses.query(StudentGroups.id).filter(StudentGroups.name == group).first()
        )

        # JUSTIFICATION:
        # Above queries return sqlalchemy collections.result objects
        # _asdict() method is needed in case celery serializer fails
        # Unknown exactly when this may occur, maybe version differences between Mac/Linux

        for i, s, in enumerate(students):
            students[i] = s._asdict()
        s_id = s_id._asdict()
        g_id = g_id._asdict()

        CreateScenarioTask.delay(name, s_type, own_id, students, g_id, s_id)
        flash(
            "Success, your scenario will appear shortly. This page will automatically update. Students Found: {}".format(
                students
            ),
            "success",
        )
    else:
        flash_errors(form)

    return redirect(url_for("dashboard.scenarios"))


@blueprint.route("/scenarios", methods=["GET", "POST"])
@login_required
def scenarios():
    """List of scenarios and scenario controls"""
    check_admin()
    scenarioModder = modScenarioForm()  # type2Form()  #
    scenarios = Scenarios.query.all()
    groups = StudentGroups.query.all()

    if request.method == "GET":
        return render_template(
            "dashboard/scenarios.html",
            scenarios=scenarios,
            scenarioModder=scenarioModder,
            groups=groups,
        )

    elif request.method == "POST":
        process_request(request.form)
        return render_template(
            "dashboard/scenarios.html",
            scenarios=scenarios,
            scenarioModder=scenarioModder,
            groups=groups,
        )


@blueprint.route("/scenarios/<i>")
def scenariosInfo(i):
    # i = scenario_id
    if checkAuth(i):
        if checkEx(i):
            status, owner, bTime, desc, s_type, s_name, guide, questions = tempMaker(i, "ins")
            addresses = identify_state(s_name, status)
            db_ses = db.session
            query = db_ses.query(Responses.id, Responses.user_id, Responses.attempt, Responses.correct, User.username)\
                .filter(Responses.scenario_id == i).filter(Responses.user_id == User.id).all()
            resp = queryPolish(query, s_type)
            return render_template("dashboard/scenarios_info.html",
                                   i=i,
                                   s_type=s_type,
                                   desc=desc,
                                   status=status,
                                   owner=owner,
                                   dt=bTime,
                                   s_name=s_name,
                                   add=addresses,
                                   guide=guide,
                                   questions=questions,
                                   resp=resp)
        else:
            return abort(404)
    else:
        return abort(403)


@blueprint.route("/scenarios/<i>/<r>")
def scenarioResponse(i, r):
    # i = scenario_id, r = responses id
    if checkAuth(i):
        if checkEx(i):
            db_ses = db.session
            d = responseSelector(r)
            u_id, uName, s_id, sName, aNum = responseProcessing(d)
            s_type = db_ses.query(Scenarios.description).filter(Scenarios.id == s_id).first()
            query = db_ses.query(Responses.id, Responses.user_id, Responses.attempt, Responses.question,
                                 Responses.correct, Responses.student_response, User.username)\
                .filter(Responses.scenario_id == i).filter(Responses.user_id == User.id).all()
            table = responseQuery(u_id, aNum, query, questionReader(s_type[0]))
            scr = score(getScore(u_id, aNum, query), questionReader(s_type[0]))

            return render_template("dashboard/scenario_response.html",
                                   u_id=u_id,
                                   uName=uName,
                                   s_id=s_id,
                                   sName=sName,
                                   aNum=aNum,
                                   table=table,
                                   scr=scr)
        else:
            return abort(404)
    else:
        return abort(403)


# -----


@blueprint.route("/instructor", methods=["GET", "POST"])
@login_required
def instructor():
    """List of an instructors groups"""
    check_instructor()
    # Queries for the owned groups table
    curId = session.get("_user_id")
    db_ses = db.session

    students = db_ses.query(User.id, User.username, User.email, User.is_static).filter(User.is_instructor == False)
    groups = db_ses.query(
        StudentGroups.id, StudentGroups.name, StudentGroups.code
    ).filter(StudentGroups.owner_id == curId)
    users_per_group = {}

    for g in groups:
        users_per_group[g.name] = db_ses.query(User.id, User.username, User.email, User.is_static).filter(
            StudentGroups.name == g.name,
            StudentGroups.id == GroupUsers.group_id,
            GroupUsers.user_id == User.id,
        )

    userInfo = db_ses.query(User.id, User.username, User.email).filter(User.id == curId)
    infoTable = UserInfoTable(userInfo)
    if request.method == "GET":
        groupMaker = GroupForm()
        userAdder = addUsersForm()
        return render_template(
            "dashboard/instructor.html",
            groupMaker=groupMaker,
            userAdder=userAdder,
            students=students,
            groups=groups,
            usersPGroup=users_per_group,
            infoTable=infoTable,
        )

    elif request.method == "POST":
        ajax = process_request(request.form)
        if ajax:
            temp = ajax[0]
            if temp == 'utils/create_group_response.html':
                if len(ajax) == 1:
                    return render_template(temp)
                elif len(ajax) < 4:
                    return render_template(temp, group=ajax[1], users=ajax[2])
                else:
                    return render_template(ajax[0], group=ajax[1], users=ajax[2], pairs=ajax[3])
            elif temp == 'utils/manage_student_response.html':
                if len(ajax) == 1:
                    return render_template(temp)
                else:
                    return render_template(temp, group=ajax[1], users=ajax[2])
        else:
            return redirect(url_for("dashboard.admin"))


@blueprint.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    """List of all students and groups. Group, student, and instructor management forms"""
    check_admin()
    db_ses = db.session
    # Queries for the tables of students and groups
    students = db_ses.query(User.id, User.username, User.email, User.is_static).filter(User.is_instructor == False)
    instructors = db_ses.query(User.id, User.username, User.email).filter(User.is_instructor == True)
    groups = StudentGroups.query.all()
    groupNames = []
    users_per_group = {}

    for g in groups:
        groupNames.append(g.name)

    for name in groupNames:
        users_per_group[name] = db_ses.query(User.id, User.username, User.email, User.is_static).filter(
            StudentGroups.name == name,
            StudentGroups.id == GroupUsers.group_id,
            GroupUsers.user_id == User.id,
        )

    if request.method == "GET":
        groupMaker = GroupForm()
        userAdder = addUsersForm()
        instructorManager = manageInstructorForm()

        return render_template(
            "dashboard/admin.html",
            groupMaker=groupMaker,
            userAdder=userAdder,
            instructorManager=instructorManager,
            groups=groups,
            students=students,
            instructors=instructors,
            usersPGroup=users_per_group,
        )

    elif request.method == "POST":
        ajax = process_request(request.form)
        if ajax:
            temp = ajax[0]
            if temp == 'utils/create_group_response.html':
                if len(ajax) == 1:
                    return render_template(temp)
                elif len(ajax) < 4:
                    return render_template(temp, group=ajax[1], users=ajax[2])
                else:
                    return render_template(ajax[0], group=ajax[1], users=ajax[2], pairs=ajax[3])
            elif temp == 'utils/manage_student_response.html':
                if len(ajax) == 1:
                    return render_template(temp)
                else:
                    return render_template(temp, group=ajax[1], users=ajax[2])
        else:
            return redirect(url_for("dashboard.admin"))
