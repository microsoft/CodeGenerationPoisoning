#!/usr/bin/python
# -*- coding: utf-8 -*-
# __author__ = "Albin TCHOPBA"
# __copyright__ = "Copyright 2020 Albin TCHOPBA and contributors"
# __credits__ = ["Albin TCHOPBA and contributors"]
# __license__ = "GPL"
# __version__ = "3"
# __maintainer__ = "Albin TCHOPBA"
# __email__ = "Albin TCHOPBA <atchopba @ gmail dot com"
# __status__ = "Production"

from flask import Blueprint, render_template, redirect, url_for, request, make_response
from flask_login import login_required, logout_user, current_user

from .core.db.db import DB
from .core.db.personne import Personne, TPersonne
from .core.db.relation import Relation
from .core.db.contact_relation_personne import CRP, TCRP
from .core.db.test import Test, TTest
from .core.db.test_type import TestType
from .core.db.test_lieu import TestLieu
from .core.db.notification import Notification
from .core.db.type_consultation import TConsultation
from .core.db.personne_consultation import PConsultation, TPConsultation
from .core.db.personne_vie_condition import TPVCondition, PVCondition
from .core.db.personne_diagnostic import PDiagnostic, TPDiagnostic
from .core.db.personne_guerison import PGuerison, TPGuerison
from .core.db.guerison_type import GuerisonType
from .core.db.symptome import Symptome
from .core.db.personne_notification import PNotification
from .core.db.user_historique import UserHistorique, TUserHistorique
from .core import notifier as notifier
from .core.personne_graph import build_graph
from .core import common as cm
from config import Config
import json

# Blueprint Configuration
main_bp = Blueprint('main_bp', 
                    __name__,
                    template_folder='templates',
                    static_folder='static')

DEFAULT_OUI = "oui"
DEFAULT_NON = "non"

@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth_bp.login'))

@main_bp.route("/")
@login_required
def home():
    cpersonne_ = cm.CPersonne(Personne().get_count(), Personne().get_count_gueri(), Personne().get_count_suspect())
    ctest_ = cm.CTest(Test().get_count(), Test().get_count_positif(), Test().get_count_negatif())
    return render_template("myapp/index.html", cpersonne=cpersonne_, ctest=ctest_)

@main_bp.route("/db")
@login_required
def db_home():
    return render_template("myapp/db.html")

@main_bp.route("/db", methods=["POST"])
@login_required
def db_create():
    DB().create_db()
    return redirect("/personnes")

@main_bp.route("/personnes")
@login_required
def home_personne():
    personnes = CRP().get_personnes_crp() #Personne().get_all() #
    #
    tuh = TUserHistorique(current_user.id, None, Personne.ACTION_LIST, cm.get_current_date_fr(), cm.get_current_time())
    UserHistorique().add(tuh)
    return render_template("myapp/personne.html", personnes=personnes, nb_personnes=len(personnes))

def param_and_add_personne(request):
    nom = request.form["nom"]
    prenom = request.form["prenom"]
    date_naiss = request.form["date_naiss"]
    num_telephone = request.form["num_telephone"]
    email = request.form["email"]
    personne = TPersonne(nom, prenom, date_naiss, num_telephone, email)
    return Personne().add(personne)
    
@main_bp.route("/personnes", methods=["POST"])
@login_required
def add_personne():
    personne_id = param_and_add_personne(request)
    if personne_id is not None:
        #
        tuh = TUserHistorique(current_user.id, personne_id, Personne.ACTION_INSERT, cm.get_current_date_fr(), cm.get_current_time())
        UserHistorique().add(tuh)
        return redirect("/personnes")
    return render_template("myapp/personne.html", error=Config.ERROR_MSG_INSERT)

@main_bp.route("/personnes/delete/<int:personne_id>")
@login_required
def delete_personne(personne_id):
    Personne().delete(personne_id)
    CRP().delete_due_2_personne(personne_id)
    #
    tuh = TUserHistorique(current_user.id, personne_id, Personne.ACTION_DELETE, cm.get_current_date_fr(), cm.get_current_time())
    UserHistorique().add(tuh)
    return redirect("/personnes")

@main_bp.route("/personnes/graph")
@login_required
def graph_personne():
    # selection des personnes pour construire le graphe
    p_ = Personne().get_all()
    graph_msg = "Aucune personne enregistrée pour tracer le graphe!" if len(p_) == 0 else ""
    build_graph()
    return render_template("myapp/personne-graph.html", graph_msg=graph_msg)

@main_bp.route("/personnes/search", methods=["POST"])
@login_required
def search_personne():
    p_name = request.form["search_name"]
    personne_id_1 = request.form["personne_id_1"]
    json_ = json.dumps(Personne().find_by_name_in_crp(personne_id_1, p_name))
    resp = make_response(json_)
    resp.status_code = 200
    resp.headers["Access-Control-Allow-Origin"] = '*'
    return resp

@main_bp.route("/personnes/guerison", methods=["GET"])
@login_required
def guerison_personne():
    personne = Personne().get_one(request.args.get("personne"))
    guerison_types = GuerisonType().get_all()
    #
    tuh = TUserHistorique(current_user.id, None, PGuerison.ACTION_LIST, cm.get_current_date_fr(), cm.get_current_time())
    UserHistorique().add(tuh)
    return render_template("myapp/personne_guerison.html", 
                           personne=personne,
                           date_guerison=cm.get_current_date_fr(),
                           guerison_types=guerison_types,
                           pguerisons=PGuerison().get_all())

@main_bp.route("/personnes/guerison", methods=["POST"])
@login_required
def set_guerison_personne():
    personne_id = request.form["personne_id"]
    guerison_type_id = request.form["guerison_type_id"]
    date_guerison = request.form["date_guerison"]
    has_been_isole = get_request_checkbox_value(request, "has_been_isole")
    has_been_sous_oxygene = get_request_checkbox_value(request, "has_been_sous_oxygene")
    has_been_sous_antibiotique = get_request_checkbox_value(request, "has_been_sous_antibiotique")
    has_been_hospitalise = get_request_checkbox_value(request, "has_been_hospitalise")
    has_scanner_controle = get_request_checkbox_value(request, "has_scanner_controle")
    personne_guerison_id = PGuerison().add(TPGuerison(personne_id, guerison_type_id, date_guerison, has_been_isole, has_been_sous_oxygene, has_been_sous_antibiotique, has_been_hospitalise, has_scanner_controle, cm.get_current_datetime_fr()))
    if personne_guerison_id:
        #
        tuh = TUserHistorique(current_user.id, personne_id, PGuerison.ACTION_INSERT, cm.get_current_date_fr(), cm.get_current_time())
        UserHistorique().add(tuh)
        return redirect("/tests")
    return render_template("/personne/guerison?personne="+ personne_id, error=Config.ERROR_MSG_INSERT)

@main_bp.route("/personnes/consultation", methods=["GET"])
@login_required
def consultation_personne():
    personne_id = request.args.get("personne")
    personne = Personne().get_one(personne_id)
    type_consultations = TConsultation().get_all()
    pconsultations = PConsultation().get_by_personne_id(personne_id)
    #
    tuh = TUserHistorique(current_user.id, personne_id, PConsultation.ACTION_LIST, cm.get_current_date_fr(), cm.get_current_time())
    UserHistorique().add(tuh)
    return render_template("myapp/personne_consultation.html", 
                           personne=personne, 
                           type_consultations=type_consultations, 
                           date_consultation=cm.get_current_date_fr(), 
                           heure_consultation=cm.get_current_time(),
                           pconsultations=pconsultations)

@main_bp.route("/personnes/consultation", methods=["POST"])
@login_required
def add_consultation_personne():
    personne_id = request.form["personne_id"]
    type_consultation_id = request.form["type_consultation_id"]
    date_consultation = request.form["date_consultation"]
    heure_consultation = request.form["heure_consultation"]
    pconsultation_id = PConsultation().add(TPConsultation(type_consultation_id, personne_id, date_consultation, heure_consultation, cm.get_current_datetime_fr()))
    if pconsultation_id :
        #
        tuh = TUserHistorique(current_user.id, personne_id, PConsultation.ACTION_INSERT, cm.get_current_date_fr(), cm.get_current_time())
        UserHistorique().add(tuh)
        return redirect("/personnes/consultation?personne="+personne_id)
    return render_template("/personnes/consultation?personne="+ personne_id, error=Config.ERROR_MSG_INSERT)

@main_bp.route("/personnes/consultation/delete/<int:consultation_id>")
@login_required
def delete_consultation_personne(consultation_id):
    PConsultation().delete(consultation_id)
    personne_id = request.args.get("personne")
    #
    tuh = TUserHistorique(current_user.id, personne_id, PConsultation.ACTION_DELETE, cm.get_current_date_fr(), cm.get_current_time())
    UserHistorique().add(tuh)
    return redirect("/personnes/consultation/"+ str(personne_id))

@main_bp.route("/personnes/diagnostic", methods=["GET"])
@login_required
def diagnostic_personne():
    personne_id = request.args.get("personne")
    personne = Personne().get_one(personne_id)
    symptomes = Symptome().get_all()
    pdiagnostics = PDiagnostic().get_by_personne_id(personne_id)
    #
    tuh = TUserHistorique(current_user.id, personne_id, PDiagnostic.ACTION_LIST, cm.get_current_date_fr(), cm.get_current_time())
    UserHistorique().add(tuh)
    return render_template("myapp/personne_diagnostic.html", 
                           personne=personne, 
                           symptomes=symptomes,
                           suspect_score_min=Config.SUSPECT_SCORE_MIN,
                           date_debut=cm.get_current_date_fr(),
                           pdiagnostics=pdiagnostics)

def get_symptome_from_request(request_dict, index_):
    try: 
        symptome = request_dict[index_] 
    except: 
        symptome = None
    return symptome

@main_bp.route("/personnes/diagnostic", methods=["POST"])
@login_required
def add_diagnostic_personne():
    personne_id = request.form["personne_id"]
    date_debut = request.form["date_debut"]
    dict_symptome = request.form.getlist("symptome_id")
    s1 = get_symptome_from_request(dict_symptome, 0)
    s2 = get_symptome_from_request(dict_symptome, 1)
    s3 = get_symptome_from_request(dict_symptome, 2)
    s4 = get_symptome_from_request(dict_symptome, 3)
    s5 = get_symptome_from_request(dict_symptome, 4)
    suspicion = cm.compute_suspect([s1, s2, s3, s4, s5], Symptome().get_all(), Config.SUSPECT_SCORE_MIN)
    tpdiagnostic = TPDiagnostic(personne_id, date_debut, s1, s2, s3, s4, s5, suspicion.score, cm.get_current_datetime_fr())
    pdiagnostic_id = PDiagnostic().add(tpdiagnostic)
    if pdiagnostic_id :
        #
        tuh = TUserHistorique(current_user.id, personne_id, PDiagnostic.ACTION_INSERT, cm.get_current_date_fr(), cm.get_current_time())
        UserHistorique().add(tuh)
        return redirect("/personnes/diagnostic?personne="+personne_id)
    return render_template("/personnes/diagnostic?personne="+ personne_id, error=Config.ERROR_MSG_INSERT)

@main_bp.route("/personnes/diagnostic/delete/<int:diagnostic_id>")
@login_required
def delete_diagnostic_personne(diagnostic_id):
    PDiagnostic().delete(diagnostic_id)
    personne_id = request.args.get("personne")
    #
    tuh = TUserHistorique(current_user.id, personne_id, PDiagnostic.ACTION_DELETE, cm.get_current_date_fr(), cm.get_current_time())
    UserHistorique().add(tuh)
    return redirect("/personnes/diagnostic?personne="+ str(personne_id))

def get_request_checkbox_value(request_, field_):
    try:
        value = request_.form[field_]
    except:
        value = DEFAULT_NON
    return value

@main_bp.route("/personnes/viecondition", methods=["GET"])
@login_required
def vie_condition_personne():
    personne_id = request.args.get("personne")
    personne = Personne().get_one(personne_id)
    pvconditions = PVCondition().get_by_personne_id(personne_id)
    relations = Relation().get_all()
    #
    tuh = TUserHistorique(current_user.id, personne_id, PVCondition.ACTION_LIST, cm.get_current_date_fr(), cm.get_current_time())
    UserHistorique().add(tuh)
    return render_template("myapp/personne_vie_condition.html", 
                           personne=personne,
                           relations=relations,
                           pvconditions=pvconditions)

@main_bp.route("/personnes/viecondition", methods=["POST"])
@login_required
def add_vie_condition_personne():
    personne_id = request.form["personne_id"]
    is_en_couple = get_request_checkbox_value(request, "is_en_couple")
    has_enfant = get_request_checkbox_value(request, "has_enfant")
    nb_enfant = request.form["nb_enfant"]
    has_personne_agee = get_request_checkbox_value(request, "has_personne_agee")
    nb_personne_agee = request.form["nb_personne_agee"]
    has_possibilite_isolement = get_request_checkbox_value(request, "has_possibilite_isolement")
    has_been_in_contact_personne_risque = get_request_checkbox_value(request, "has_been_in_contact_personne_risque")
    tpvcondition = TPVCondition(personne_id, is_en_couple, has_enfant, nb_enfant, has_personne_agee, nb_personne_agee, has_possibilite_isolement, has_been_in_contact_personne_risque, cm.get_current_datetime_fr())
    pvcondition_id = PVCondition().add(tpvcondition)
    if pvcondition_id :
        if has_been_in_contact_personne_risque == DEFAULT_OUI:
            personne_id_2 = param_and_add_personne(request)
            # add crp
            if personne_id_2:
                id_relation = request.form["relation_id"]
                date_ = request.form["date_contact"]
                heure_ = request.form["heure_contact"]
                crp_ = TCRP(personne_id, personne_id_2, id_relation, date_, heure_)
                crp = CRP()
                crp.add(crp_)
        #
        tuh = TUserHistorique(current_user.id, personne_id, PVCondition.ACTION_INSERT, cm.get_current_date_fr(), cm.get_current_time())
        UserHistorique().add(tuh)
        return redirect("/personnes/viecondition?personne="+personne_id)
    return render_template("/personnes/viecondition?personne="+ personne_id, error=Config.ERROR_MSG_INSERT)

@main_bp.route("/personnes/viecondition/delete/<int:viecondition_id>")
@login_required
def delete_vie_condition_personne(viecondition_id):
    PVCondition().delete(viecondition_id)
    personne_id = request.args.get("personne")
    #
    tuh = TUserHistorique(current_user.id, personne_id, PVCondition.ACTION_DELETE, cm.get_current_date_fr(), cm.get_current_time())
    UserHistorique().add(tuh)
    return redirect("/personnes/viecondition?personne="+str(personne_id))

@main_bp.route("/crp", methods=["GET"])
@login_required
def home_rcp():
    personne_id = request.args.get("personne")
    if personne_id in (None, ''):
        return redirect("/personnes")
    personne = Personne().get_one(personne_id)
    relations = Relation().get_all()
    personnes = CRP().get_personnes_crp(personne_id)
    #
    tuh = TUserHistorique(current_user.id, personne_id, CRP.ACTION_LIST, cm.get_current_date_fr(), cm.get_current_time())
    UserHistorique().add(tuh)
    return render_template("myapp/crp.html", personne=personne, relations=relations, personnes=personnes)

@main_bp.route("/crp/delete/<int:crp_id>")
@login_required
def delete_crp(crp_id):
    CRP().delete(crp_id)
    #
    tuh = TUserHistorique(current_user.id, None, CRP.ACTION_DELETE, cm.get_current_date_fr(), cm.get_current_time())
    UserHistorique().add(tuh)
    return redirect("/crp")

@main_bp.route("/tests", methods=["GET"])
@login_required
def home_test():
    personne_id = request.args.get("personne")
    personne = Personne().get_one(personne_id) if personne_id is not None else None
    tests = Test().get_all()
    print(tests)
    type_tests = TestType().get_all()
    test_lieux = TestLieu().get_all()
    presente_signe = DEFAULT_NON
    pdiagnostic = PDiagnostic().get_one(personne_id) if personne_id is not None else None
    if pdiagnostic is not None:
        presente_signe = DEFAULT_OUI
    #
    tuh = TUserHistorique(current_user.id, personne_id, Test.ACTION_LIST, cm.get_current_date_fr(), cm.get_current_time())
    UserHistorique().add(tuh)
    return render_template("myapp/test.html", 
                           personne=personne,
                           presente_signe=presente_signe,
                           tests=tests, 
                           type_tests=type_tests,
                           test_lieux=test_lieux)

@main_bp.route("/tests", methods=["POST"])
@login_required
def add_test():
    personne_id = request.form["personne_id"]
    dict_test_type = request.form.getlist("test_type_id")
    test_type_id_1 = get_request_checkbox_value(dict_test_type, 0)
    test_type_id_2 = get_request_checkbox_value(dict_test_type, 1)
    test_type_id_3 = get_request_checkbox_value(dict_test_type, 2)
    test_type_id_4 = get_request_checkbox_value(dict_test_type, 3)
    test_lieu_id = request.form["test_lieu_id"]
    adresse_lieu_test = request.form["adresse_lieu_test"]
    date_test = request.form["date_test"]
    heure_test = request.form["heure_test"]
    date_resultat = request.form["date_resultat"]
    heure_resultat = request.form["heure_resultat"]
    commentaires = request.form["commentaires"]
    date_edit = cm.get_current_datetime_fr()
    resultat = request.form["resultat"]
    test = TTest(personne_id, test_type_id_1, test_type_id_2, test_type_id_3, test_type_id_4, test_lieu_id, adresse_lieu_test, date_test, heure_test, date_resultat, heure_resultat, commentaires, resultat, date_edit)
    test_id = Test().add(test)
    if test_id:
        #
        tuh = TUserHistorique(current_user.id, personne_id, Test.ACTION_INSERT, cm.get_current_date_fr(), cm.get_current_time())
        UserHistorique().add(tuh)
        return redirect("/tests")
    else:
        return render_template("myapp/test.html", Personne().get_one(personne_id), tests=Test().get_all(), error=Config.ERROR_MSG_INSERT)

@main_bp.route("/tests/delete/<int:test_id>")
@login_required
def delete_test(test_id):
    Test().delete(test_id)
    #
    tuh = TUserHistorique(current_user.id, None, Test.ACTION_DELETE, cm.get_current_date_fr(), cm.get_current_time())
    UserHistorique().add(tuh)
    return redirect("/tests")

@main_bp.route("/notifications")
@login_required
def home_notification():
    notifications = PNotification().get_notification_pnotifications() #Notification().get_all()
    #
    tuh = TUserHistorique(current_user.id, None, Notification.ACTION_LIST, cm.get_current_date_fr(), cm.get_current_time())
    UserHistorique().add(tuh)
    return render_template("myapp/notification.html", notifications=notifications)

@main_bp.route("/notifications/add", methods=["POST"])
@login_required
def add_notification():
    notification_id = Notification().add()
    if notification_id is not None:
        #
        tuh = TUserHistorique(current_user.id, None, Notification.ACTION_INSERT, cm.get_current_date_fr(), cm.get_current_time())
        UserHistorique().add(tuh)
        resp = make_response(notifier.notifier_personne(notification_id))
        resp.status_code = 200
        resp.headers["Access-Control-Allow-Origin"] = '*'
    else:
        pass
    return resp
    
@main_bp.route("/notifications/delete/<int:notification_id>")
@login_required
def delete_notification(notification_id):
    Notification().delete(notification_id)
    #
    tuh = TUserHistorique(current_user.id, None, Notification.ACTION_DELETE, cm.get_current_date_fr(), cm.get_current_time())
    UserHistorique().add(tuh)
    return redirect("/notifications")
