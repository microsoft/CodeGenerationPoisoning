import os
import pathlib
from labpals import app, db#, pusher_client
from .forms import LoginForm, GroupRegistrationForm, EditProfileForm, UploadForm, SearchForm, UserRegistrationForm
from flask import render_template, flash, redirect, url_for, request, send_from_directory, g
from flask_login import current_user, login_user, login_required, logout_user
from .models import User, Result, Group, ResearchField
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
from datetime import datetime
from .decorators import admin_required
from labpals.functions import pubmed_search


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()


@app.route('/')
def welcome():
    return render_template('welcome.html')


@app.route('/index')
@login_required
def index():
    group_id = current_user.group_id
    group = Group.query.get(group_id)
    results = db.session.query(Result).filter(Result.group_id == group_id).order_by(Result.date_modif.desc())
    return render_template('index.html', title='Home Page', group=group, results=results)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('welcome'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = UserRegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, useraffil = form.groupaffil.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user.html', user=user)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile', form=form)


@app.route('/edit_groupprofile', methods=['GET', 'POST'])
@login_required
def edit_groupprofile():
    group_id = current_user.group_id
    group = Group.query.get(group_id)
    researchfields_query = ResearchField.query.filter_by(group_id=group_id).all()
    form = GroupRegistrationForm()
    if form.validate_on_submit():
        group.groupname = form.groupname.data
        group.center = form.center.data
        group.email = form.email.data
        group.location = form.location.data
        group.website = form.website.data
        for field in researchfields_query:
            db.session.delete(field)
        new_researchfields = form.researchfield.data.split(",")
        for field in new_researchfields:
             field_entry = ResearchField(researchfield=field, group=group)
             db.session.add(field_entry)
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('index'))
    elif request.method == 'GET':
        display_researchfields = []
        for field in researchfields_query:
            display_researchfields.append(field.researchfield)
        form.groupname.data=group.groupname
        form.center.data=group.center
        form.email.data=group.email
        form.location.data=group.location
        form.website.data=group.website
        form.researchfield.data = ",".join(display_researchfields)
    return render_template('edit_groupprofile.html', title='Edit Group Profile', form=form)


def allowed_file(filename):
    return '.' in filename and filename.lower().rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = UploadForm(csrf_enabled=False)
    if form.validate_on_submit():
        file = form.file.data
        user_folder = os.path.join('users', current_user.username)
        pathlib.Path(app.config['UPLOAD_FOLDER'], user_folder).mkdir(parents=True, exist_ok=True)
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], user_folder, filename))
            name, extension = os.path.splitext(filename)
            if db.session.query(Result.query.filter(Result.filename == name, Result.user_id == current_user.id).exists()).scalar():
                result = db.session.query(Result).filter(Result.filename == name, Result.user_id == current_user.id).one()
                result.date_modif = datetime.utcnow()
                db.session.commit()
                flash('The file has been successfully updated')
                return redirect(url_for('upload'))
            else:
                result = Result(filename=name, filetype=extension, content=os.path.join(app.config['UPLOAD_FOLDER'], current_user.username, filename), user_id=current_user.id, group_id=0)
                db.session.add(result)
                db.session.commit()
                flash('The file has been successfully uploaded')
                return redirect(url_for('upload'))
    if form.errors:
        flash(form.errors, 'Danger')
    return render_template('upload.html', title="Upload File", form=form)


@app.route('/files')
@login_required
def show_files():
    files = db.session.query(Result).join(User).filter(User.id == current_user.id).filter(Result.group_id == 0).all()
    return render_template('files.html', title="Your Files", files=files)


@app.route('/files/<file_name><file_extension>')
@login_required
def download_file(file_name, file_extension):
    filename = f'{file_name}{file_extension}'
    user_folder = os.path.join('users', current_user.username)
    user_file_path = os.path.join(app.config['UPLOAD_FOLDER'], user_folder)
    try:
        return send_from_directory(user_file_path, filename=filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)


@app.route('/files/view/<file_name><file_extension>')
@login_required
def view_file(file_name, file_extension):
    filename = f'{file_name}{file_extension}'
    user_folder = os.path.join('users', current_user.username)
    user_file_path = os.path.join(app.config['UPLOAD_FOLDER'], user_folder)
    try:
        return send_from_directory(user_file_path, filename=filename, as_attachment=False)
    except FileNotFoundError:
        abort(404)

@app.route('/delete_file/<file_id>', methods=['GET', 'POST'])
@login_required
def delete_file(file_id):
    file = Result.query.get(file_id)
    filename = file.filename + file.filetype
    user_folder = os.path.join('users', current_user.username)
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], user_folder, filename))
    db.session.delete(file)
    db.session.commit()
    return redirect(url_for('show_files'))


@app.route('/search')
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('index'))
    users, total_users = User.search(g.search_form.q.data)
    groups, total_groups = Group.search(g.search_form.q.data)
    fields, total_fields = ResearchField.search(g.search_form.q.data)
    pubmed_results = ""
    # Pubmed search
    pubmed_results = pubmed_search(g.search_form.q.data)
    return render_template('search.html', title='Search', users=users, groups=groups, fields=fields, pubmed_results=pubmed_results)


@app.route('/groupregister', methods=['GET', 'POST'])
def groupregister():
    form = GroupRegistrationForm()
    if form.validate_on_submit():
        group = Group(groupname=form.groupname.data, center=form.center.data, email=form.email.data, location=form.location.data, website=form.website.data)
        researchfields = form.researchfield.data.split(",")
        for field in researchfields:
             field_entry = ResearchField(researchfield=field, group=group)
             db.session.add(field_entry)
        db.session.add(group)
        db.session.commit()
        flash('Congratulations, you have registered your group!')
        return redirect(url_for('register'))
    return render_template('groupregister.html', title='Group Register', form=form)


@app.route('/group/files')
@login_required
def show_group_files():
    group_id = current_user.group_id
    group = Group.query.get(group_id)
    files = group.results.all()
    return render_template('group_files.html', title="Group Files", files=files)


@app.route('/group/files/<file_name><file_extension>')
@login_required
def download_group_file(file_name, file_extension):
    filename = f'{file_name}{file_extension}'
    group_id = current_user.group_id
    group = Group.query.get(group_id)
    group_folder = os.path.join('groups', group.groupname)
    group_file_path = os.path.join(app.config['UPLOAD_FOLDER'], group_folder)
    try:
        return send_from_directory(group_file_path, filename=filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)

@app.route('/group/files/view/<file_name><file_extension>')
@login_required
def view_group_file(file_name, file_extension):
    filename = f'{file_name}{file_extension}'
    group_id = current_user.group_id
    group = Group.query.get(group_id)
    group_folder = os.path.join('groups', group.groupname)
    group_file_path = os.path.join(app.config['UPLOAD_FOLDER'], group_folder)
    try:
        return send_from_directory(group_file_path, filename=filename, as_attachment=False)
    except FileNotFoundError:
        abort(404)


@app.route('/group/delete_file/<file_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_group_file(file_id):
    group_id = current_user.group_id
    group = Group.query.get(group_id)
    file = Result.query.get(file_id)
    filename = file.filename + file.filetype
    group_folder = os.path.join('groups', group.groupname)
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], group_folder, filename))
    db.session.delete(file)
    db.session.commit()
    return redirect(url_for('show_group_files'))


@app.route('/group/upload', methods=['GET', 'POST'])
@login_required
def group_upload():
    form = UploadForm(csrf_enabled=False)
    group_id = current_user.group_id
    group = Group.query.get(group_id)
    if form.validate_on_submit():
        file = form.file.data
        group_folder = os.path.join('groups', group.groupname)
        pathlib.Path(app.config['UPLOAD_FOLDER'], group_folder).mkdir(parents=True, exist_ok=True)
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], group_folder, filename))
            name, extension = os.path.splitext(filename)
            if db.session.query(Result.query.filter(Result.filename == name, Result.group_id == group.id).exists()).scalar():
                result = db.session.query(Result).filter(Result.filename == name, Result.group_id == group.id).one()
                result.date_modif = datetime.utcnow()
                db.session.commit()
                flash('The file has been successfully updated')
                # data = {
                #     "username": current_user.username,
                #     "filename": file.filename,
                #     "time": datetime.utcnow()
                #     }
                # pusher_client.trigger('table', 'new-record', {'data': data })
                return redirect(url_for('group_upload'))
            else:
                result = Result(filename=name, filetype=extension, content=os.path.join(app.config['UPLOAD_FOLDER'], group_folder, filename), user_id=current_user.id, group_id=group.id)
                db.session.add(result)
                db.session.commit()
                flash('The file has been successfully uploaded')
                return redirect(url_for('group_upload'))
    if form.errors:
        flash(form.errors, 'Danger')
    return render_template('group_upload.html', title="Upload File", form=form, group=group)
