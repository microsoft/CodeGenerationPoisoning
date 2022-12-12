import os
from ast import literal_eval
from datetime import datetime
import requests
import json

from sqlalchemy.sql.functions import concat, count
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import load_only
from flask_login import current_user, login_user, logout_user
from flask import render_template, redirect, url_for, request, flash
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class


from app import app
from app.forms import LoginForm, SignUpForm, AddPatientForm, ImageForm, PatientsForm, EditImgAnalysisForm
from app.auth import login_manager, load_user, logout_user, login_required, login_user, current_user

from app.db_classes import db, Therapists, Patients, Images, ImageAnalysis, ImageTypes, TumorTypes

from app.tables import PatientsTable, Col, ImagesTable, ImageAnalysisTable

photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)
patch_request_class(app)  # set maximum file size, default is 16MB


DOCKER = 'mlapp'
LOCAL = '0.0.0.0'
ML_URL =f'http://{DOCKER}:5002/api/detect'
ITEMS_PER_PAGE = 5


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=('GET', 'POST'))
def login():
    # Bypass Login screen if user is logged in
    if current_user.is_authenticated:
        return redirect(url_for('home'))


    form = LoginForm()

    if form.validate_on_submit():

        user = Therapists.query.filter_by(username=form.username.data).first()

        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")

        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("home")

        return redirect(next_page)

    return render_template('login.html', form=form)



@app.route("/contact_us", methods=("GET", "POST"))
def contact_us():
    if request.method == "POST":
        flash("We've recieved your message. Thank you!")
        
    return render_template("contact_us.html")

@app.route("/home")
@login_required
def home():
    if not current_user.is_authenticated:
        user = literal_eval(request.args['user'])

    
    patient_count = Patients.query.filter_by(therapist_id=current_user.id).count()
    img_to_review = Images.query.join(Patients, Images.patient_id == Patients.pid).join(Therapists, Patients.therapist_id == Therapists.id).filter_by(id=current_user.id).join(ImageAnalysis, Images.image_id==ImageAnalysis.image_id).filter_by(verified=False).count()
    img_today = Images.query.join(Patients, Images.patient_id == Patients.pid).join(Therapists, Patients.therapist_id == Therapists.id).filter(func.DATE(Images.datetime)==datetime.today().date()).count()
    img_analyzed = Images.query.join(Patients, Images.patient_id == Patients.pid).join(Therapists, Patients.therapist_id == Therapists.id).join(ImageAnalysis, ImageAnalysis.image_id==Images.image_id).filter(func.DATE(ImageAnalysis.dt)==datetime.today().date()).count()
     
    total_patient_count = Patients.query.count()
    total_img_to_review = Images.query.join(ImageAnalysis, Images.image_id==ImageAnalysis.image_id).filter_by(verified=False).count()#.add_columns(users.userId, users.name, users.email, friends.userId, friendId).filter(users.id == friendships.friend_id).filter(friendships.user_id == userID).paginate(page, 1, False)
    total_img_today = Images.query.filter(func.DATE(Images.datetime)==datetime.today().date()).count()
    total_img_analyzed = ImageAnalysis.query.filter(func.DATE(ImageAnalysis.dt)==datetime.today().date()).count()


    db_info = {"current_user":{"patient_count":patient_count, "img_to_review":img_to_review, "img_today":img_today, "img_analyzed":img_analyzed},
                "total":{"patient_count":total_patient_count, "img_to_review":total_img_to_review, "img_today":total_img_today, "img_analyzed":total_img_analyzed}}


    return render_template("home.html", db_info=db_info, user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route("/sign_up", methods=('GET', 'POST'))
def sign_up():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = SignUpForm()

    if form.validate_on_submit():
        
        #wrap in tre/except
        new_therapist = Therapists(first_name=form.fname.data, last_name=form.lname.data, username=form.username.data, title=form.title.data)
        new_therapist.set_password(form.password.data)
        db.session.add(new_therapist)
        db.session.commit()
        return redirect(url_for("login"))
    
    return render_template("sign_up.html", form=form)


@app.route("/add_patient", methods=('GET', "POST"))
@login_required
def add_patient():
    #available_therapists_id, available_therapists_names = [t.id for t in Therapists.query.all()], [t.first_name + " " + t.last_name for t in Therapists.query.all()]
    
    form = AddPatientForm()
    #form.therapist_id.choices = list(zip(available_therapists_id, available_therapists_names))

    if form.validate_on_submit():
        patient = Patients(first_name=form.fname.data, last_name=form.lname.data, gender=form.gender.data, ssn=form.ssn.data, age=form.age.data, therapist_id=current_user.id)
        db.session.add(patient)
        db.session.commit()
        flash("New patient successfully added")

        return render_template("add_patient.html", form=form)
    return render_template("add_patient.html", form=form)


@app.route("/upload_image",  methods=('GET', "POST"))
@login_required
def upload_image():

    pid,pnames = [t.pid for t in Patients.query.filter_by(therapist_id=current_user.id).all()], [str(t.first_name) + " " + str(t.last_name) for t in Patients.query.filter_by(therapist_id=current_user.id).all()]
    imtypes_id,imtype_names = [t.id for t in ImageTypes.query.all()], [t.name for t in ImageTypes.query.all()]

    form = ImageForm()
    form.patient_id.choices = list(zip(pid, pnames))
    form.im_type.choices = list(zip(imtypes_id, imtype_names))

    if form.validate_on_submit():
        filename = photos.save(form.photo.data, name=f"{form.patient_id.data}_{form.datetime.data}_{current_user.id}.")
        file_url = photos.url(filename)

        img = Images(patient_id=form.patient_id.data, datetime=form.datetime.data, im_type=form.im_type.data, image=filename)
        db.session.add(img)
        db.session.commit()
        flash("New image successfully added")
        if form.analyze.data:
            #send POST request to ml module
            res = requests.post(ML_URL, json={'impath':filename})

            if res.status_code == 200:

                result = json.loads(res.text)
                diagnosis = 1 if result["tumor_detected"]==False else 2
                img_anal = ImageAnalysis(image_id=img.image_id, segment=result["segmentation_img"], tumor=result["classification"], diagnosis=diagnosis, recommendations=None, confidence=result["confidence"], dt=datetime.now(), verified=False)
                
                db.session.add(img_anal)
                db.session.commit()
                
                #flash(img_anal)
                flash("Successfully analyzed new image")
            else:
                flash("Error when analyzing")

    else:
        file_url = None
    return render_template("upload_image.html", form=form, file_url=file_url)


@app.route("/patients",  methods=('GET', "POST"))
@login_required
def patients():

    form = PatientsForm()
    sort = request.args.get('sort', 'therapist_id')
    reverse = (request.args.get('direction', 'asc') == 'desc')


    delete_id = request.args.get("delete_id", "")
    if request.method == "POST" and delete_id != "":
        Patients.query.filter_by(pid=delete_id).delete()
        db.session.commit()
        flash(f"Deleted patient with id {delete_id}")

    available_patients = Patients.query.filter_by(therapist_id=current_user.id)
    

    if (request.method == "POST" and form.search_field.data != None and len(form.search_field.data)>0):
        if not form.sort_by_ssn.data:
            available_patients = available_patients.filter((Patients.fullname.startswith(form.search_field.data)))
        else:
            available_patients = available_patients.filter((Patients.ssn.startswith(form.search_field.data)))

    if reverse:
        p = available_patients.order_by(getattr(Patients, sort).asc()).all()
    else:
        p = available_patients.order_by(getattr(Patients, sort).desc()).all()
    

    ptable = PatientsTable(p,
                          sort_by=sort,
                          sort_reverse=reverse,
                          html_attrs={"class":"patients-table"})
    
    #   ptable = PatientsTable(items=p)

    return render_template("patients.html", table=ptable, form=form)


@app.route("/images",  methods=('GET', "POST"))
@login_required
def images():
    sort = request.args.get('sort', 'image_id')
    direction = request.args.get('direction', 'asc')
    reverse = (request.args.get('direction', 'asc') == 'desc')
    image_id = request.args.get('image_url', "")


    image_url = photos.url(request.args.get("image_url", ""))
    page = request.args.get('page', 1, type=int)

    #filter images by current user
    filtered_images = Images.query.join(Patients, Patients.pid==Images.patient_id).join(Therapists, Patients.therapist_id==Therapists.id).filter_by(id=current_user.id)#.add_columns(Images.image_id)



    delete_id = request.args.get("delete_id", "")
    if request.method == "POST" and delete_id != "":
        Images.query.filter_by(image_id=delete_id).delete()
        db.session.commit()
        flash(f"Deleted patient with id {delete_id}")


    re_analyze_id = request.args.get("analyze_id", "")
    if request.method == "POST" and re_analyze_id != "":

        res = requests.post(ML_URL, json={'impath':Images.query.filter_by(image_id=re_analyze_id).first().image})

        if res.status_code == 200:

            result = json.loads(res.text)
            diagnosis = 1 if result["tumor_detected"]==False else 2
            
            current_analysis = ImageAnalysis.query.filter_by(image_id=re_analyze_id).first()
            if current_analysis is None:

                img_anal = ImageAnalysis(image_id=re_analyze_id, segment=result["segmentation_img"], tumor=result["classification"], diagnosis=diagnosis, recommendations=None, confidence=result["confidence"], dt=datetime.now(), verified=False)
                
                db.session.add(img_anal)
                db.session.commit()

                flash(f"Analyzed image with id {re_analyze_id}")
            else:
                current_analysis.segment = result["segmentation_img"]
                current_analysis.tumor = result["classification"]
                current_analysis.diagnosis = diagnosis
                current_analysis.recommendations = None
                current_analysis.dt = datetime.now()
                current_analysis.confidence = result["confidence"]
                current_analysis.verified = False

                db.session.commit()
                
                flash(f"Re-analyzed image with id {re_analyze_id}")
                
        else:
            flash(f"Error {res.status_code}")

    if reverse:
        iquery = filtered_images.order_by(getattr(Images, sort).asc()).paginate(page, ITEMS_PER_PAGE, False)
        i = iquery.items
    else:
        iquery = filtered_images.order_by(getattr(Images, sort).desc()).paginate(page, ITEMS_PER_PAGE, False)
        i = iquery.items
    
    next_url = url_for('images', page=iquery.next_num, direction=direction, sort=sort) if iquery.has_next else None
    prev_url = url_for('images', page=iquery.prev_num, direction=direction, sort=sort) if iquery.has_prev else None

    itable = ImagesTable(i,
                          sort_by=sort,
                          sort_reverse=reverse, html_attrs={"class":"image-table"})
    #return str(itable.image.get_attr_list)
    return render_template("images.html", table=itable, simage=image_url, next_url=next_url, prev_url=prev_url)

@app.route("/image_analysis",  methods=('GET', "POST"))
@login_required
def image_analysis():

    sort = request.args.get('sort', 'image_id')
    direction = request.args.get('direction', 'asc')
    reverse = (request.args.get('direction', 'asc') == 'desc')


    # ignore the error when no image selected
    image_url = photos.url(request.args.get("image_url", ""))
    page = request.args.get('page', 1, type=int)
    # add image view

    # filter images by current user
    filtered_images = ImageAnalysis.query.join(Images, ImageAnalysis.image_id==Images.image_id).join(Patients, Patients.pid==Images.patient_id).join(Therapists, Patients.therapist_id == Therapists.id).filter_by(id=current_user.id)

    delete_id = request.args.get("delete_id", "")
    if request.method == "POST" and delete_id != "":
        ImageAnalysis.query.filter_by(image_id=delete_id).delete()
        db.session.commit()
        flash(f"Deleted patient with id {delete_id}")


    if reverse:
        iquery = filtered_images.order_by(getattr(ImageAnalysis, sort).asc()).paginate(page, ITEMS_PER_PAGE, False)
        i = iquery.items
    else:
        iquery = filtered_images.order_by(getattr(ImageAnalysis, sort).desc()).paginate(page, ITEMS_PER_PAGE, False)
        i = iquery.items
    

    next_url = url_for('image_analysis', page=iquery.next_num, direction=direction, sort=sort) if iquery.has_next else None
    prev_url = url_for('image_analysis', page=iquery.prev_num, direction=direction, sort=sort) if iquery.has_prev else None



    itable = ImageAnalysisTable(i,
                          sort_by=sort,
                          sort_reverse=reverse)
        
    
    return render_template("image_analysis.html", table=itable, simage=image_url, next_url=next_url, prev_url=prev_url)

@app.route("/edit_analysis",  methods=["GET","POST"])
@login_required
def edit_analysis():
    if current_user.title != "Dr.":
        flash("You have no rights to edit analysis!")
        return redirect(url_for("image_analysis"))
    else:
        img_id = request.args.get("image_url", "")

        if img_id == "":
            img_id = request.form["img_id"]

        img_analysis = ImageAnalysis.query.filter_by(image_id=img_id).first()
        
        imtypes_id,imtype_names = [t.id for t in ImageTypes.query.all()], [t.name for t in ImageTypes.query.all()]

        form = EditImgAnalysisForm(img_id=img_id, tumor=img_analysis.tumor, diagnosis=img_analysis.diagnosis, recommendations=img_analysis.recommendations, confidence=img_analysis.confidence, verified=img_analysis.verified)
        

        diagnosis_id,diagnosis_names = [t.id for t in TumorTypes.query.all()], [t.name for t in TumorTypes.query.all()]
        form.diagnosis.choices = list(zip(diagnosis_id, diagnosis_names))


        if form.validate_on_submit():
            img_analysis.tumor = form.data["tumor"]
            img_analysis.diagnosis = form.data["diagnosis"]
            img_analysis.recommendations = form.data["recommendations"]
            img_analysis.confidence = form.data["confidence"]
            img_analysis.verified = form.data["verified"]
            img_analysis.dt = datetime.now()

            db.session.commit()
            return redirect(url_for('image_analysis'))
        return render_template("edit_analysis.html", form=form, img_id=img_id)


@app.route("/show_image")
@login_required
def show_image():
    img = photos.url(request.args.get("image_url", ""))
    return render_template("show_image.html", img=img)