from flask import Flask, request, render_template, flash, \
                 redirect, url_for, session, logging, abort, Blueprint
from flask_login import current_user, login_required
from project.projects.forms import ProjectForm
from project.models import *

projects = Blueprint('projects', __name__)

@projects.route('/projects')
@login_required
def projects_all():
    username = current_user.username
    user = User.query.filter_by(username=username).first()
    user_projects = user.projects
    return render_template('projects.html', projects=user_projects)


# @projects.route('/convergence/')
# @login_required
# def render_chart():
#     pass
#     # return redirect('/dash')
    
@projects.route('/rendering/')
def render_chart():
    project_id = session["project_id"]
    project = Project.query.filter_by(id=project_id).first()
    category = project.category
    if category == 'convergence behaviour':
        return redirect('/convergence')
    elif category == 'response':
        return redirect('/response')
    else:
        return redirect(url_for('projects.project', project_id=project_id))
    # return redirect('/dash')

@projects.route('/projects/<int:project_id>/render')
@login_required
def render_project(project_id):
    # project = Project.query.filter_by(id=project_id).first()
    session["project_id"] = project_id
    return redirect(url_for('projects.render_chart'))


@projects.route('/projects/<int:project_id>/')
@login_required
def project(project_id):
    project = Project.query.filter_by(id=project_id).first()
    return render_template('project.html', project=project)


@projects.route('/projects/new', methods=['GET', 'POST'])
@login_required
def add_project():
    form = ProjectForm(request.form)
    if request.method == 'POST' and form.validate():
        project = Project(
            title=form.title.data,
            description=form.description.data,
            author_id = current_user.id,
            category=form.category.data
        )
        
        db.session.add(project)
        
        results = Result(project)
        db.session.add(results)
        
        user = User.query.filter_by(username=current_user.username).first()
        user.projects.append(project)
        
        db.session.commit()
        print(user.projects)
        flash('You successfully added a project.', 'success')
        return redirect(url_for('projects.projects_all'))
    return render_template('add_project.html', form=form,
                             title="New project", legend="New project")


@projects.route('/projects/<int:project_id>/update', methods=['GET', 'POST'])
@login_required
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.author_id != current_user.id:
        abort(403)
    form = ProjectForm()
    form.category.choices = [project.category]
    if form.validate_on_submit():
        project.title = form.title.data
        project.description = form.description.data
        project.category = form.category.data
        #if more categories are added; changing category implies ereasing data from DB.
        db.session.commit()
        flash('Your project has been updated!', 'success')
        return redirect(url_for('projects.project', project_id=project_id))
    elif request.method == 'GET':
        form.title.data = project.title
        form.description.data = project.description
        form.category.data = project.category
        
    return render_template('add_project.html', form=form, 
                           title="Update project", legend="Update project") 
    

@projects.route('/projects/<int:project_id>/delete', methods=['GET','POST'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.author_id != current_user.id:
        abort(403)
    
    db.session.delete(project)
    db.session.commit()
    flash('Your project has been deleted.', 'success')
    return redirect(url_for('projects.projects_all'))

