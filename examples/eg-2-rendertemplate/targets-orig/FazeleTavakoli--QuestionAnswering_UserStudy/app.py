import flask
from forms.loginForm import LoginForm
from forms.registerForm import RegisterForm
from forms.assessmentForm import AssessmentForm
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import Flask, flash, render_template, redirect, url_for, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from database.DBModels import User, Question, Interaction, Assessment
from sqlalchemy.exc import IntegrityError
import json
import urllib.request
import urllib.parse
import requests
import datetime
import pandas as pd
import re
import xmltodict
import untangle
import xml.etree.ElementTree as ET

app = Flask(__name__)

app.config['SECRET_KEY'] = 'Thisissupposedtobesecret!'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/fazeletavakoli/Downloads/QA_userStrudy/QA_userStrudy/database/QA.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/fazeletavakoli/PycharmProjects/QA_userStudy/database/QA2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

login = LoginManager(app)
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
#migrate = Migrate(app, db)
# from database.DBModels import User, Question, AnsweredQuestion



login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(int(user_id))

@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = db.session.query(User).filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                return redirect(url_for('index'))
        flash('Error: Invalid username or password')

    return render_template('login.html', form=form)



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        # if User.query.filter(User.email == flask.request.form['email']).first():
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        try:
            db.session.commit()
            flash('New user has been created!')
        except IntegrityError:
            db.session.rollback()
            flash("Another user with the same username or email address already exists. "
                  "Please enter another email address ")
            # error, there already is a user using this bank address or other
            # constraint failed
    # question = db.session.query(Question).get(1)
    # question = db.session.query(Question).all()

    return render_template('signup.html', form=form)

# @app.route('/survey')
# @login_required
# def survey():
#     for i in range(2):
#         readJsonFile()
#         # data = {'userid': current_user.username}
#         question = db.session.query(Question).all()
#         # data['question'] = question
#         q = 1
#         q = question[1].answer
#         return render_template('survey.html', title='Survey', user=current_user, question=question[i],
#                                user_id=current_user.id)
#
#     # return render_template('survey.html', title='Survey', user = current_user, question = question, user_id = current_user.id)

# @app.route('/d3_Visualization/<key>')
# def d3_Visualization(key):
#     # sparql_query = sparql_query
#     list = session['triple']
#     return render_template('d3.html', list = list, key = key)

@app.route('/d3_Visualization/<key>')
def d3_visualization(key):
    # sparql_query = sparql_query
    nodes_links = session['triple']
    return render_template('d3_labeled_edges_2.html', nodes_links = nodes_links, key = key)


@app.route('/survey/<key>')
@login_required
def survey(key):
    data = {'userid': current_user.username}
    questions = db.session.query(Question).all()
    return render_template('survey.html', questions = questions, key = key, user=current_user)


@app.route('/question/<key>')
def question(key):
    if int(key) < 20:
        questions = db.session.query(Question).all()
        if len(questions) == 0:
            readJsonFile()
            questions = db.session.query(Question).all()

        # single_question = questions.get(key)
        single_question = questions[int(key)]
        session['question_id'] = single_question.id
        if not single_question:
            abort(404)
        key = int(key) + 1
        fileName = "kg_" + str(key) + ".png"
        imageFile = url_for('static', filename = fileName)
        single_question_SQ = single_question.sparqlQuery
        nodes_links = detect_regularExpression(single_question_SQ, "visualization")
        session['triple'] = nodes_links

        d3_url = "http://127.0.0.1:5000/d3_Visualization/"+ str(key)
        return render_template('question.html', single_question = single_question, key = key, user=current_user, imageFile = imageFile, nodes_links = nodes_links,
                               d3_url = d3_url)
    else:
        return redirect(url_for('survey_assessment'))


@app.route('/correct/<key>')
@login_required
def correct(key):
    save_user_answers(user_answer='yes')
    return redirect(url_for('question', key = key))

@app.route('/wrong/<key>')
@login_required
def wrong(key):
    save_user_answers(user_answer='no')
    return redirect(url_for('question', key=key))

@app.route('/skip/<key>')
def skip(key):
    reason = 'skip'
    if 'reason' in flask.request.values:
        reason = flask.request.values['reason']
    save_user_answers(skipped=True, skipped_reason= reason)
    return redirect(url_for('question', key=key))

def save_user_answers(user_answer='', skipped = False, skipped_reason = ''):
    time = datetime.datetime.utcnow()
    record = Interaction(current_user.id, session['question_id'], user_answer, skipped, skipped_reason, time)
    db.session.add(record)
    db.session.commit()

@app.route('/survey_assessment', methods=['GET', 'POST'])
def survey_assessment():
    form = AssessmentForm()
    time = datetime.datetime.utcnow()
    if form.validate_on_submit():
        if form.question_1.data != "Empty" and form.question_2.data != "Empty":
            record = Assessment(current_user.id, form.question_1.data, form.question_2.data, time)
            db.session.add(record)
            db.session.commit()
            return redirect(url_for('survey_done'))
        else:
            flash("Please make an assessment")

    return render_template('survey_assessment.html', form = form)

@app.route('/survey_done')
def survey_done():
    return render_template('survey_done.html')

def readFile(address):
    qusetionList = []
    with open(address) as f:
        for line in f:
           if line:
                qusetionList.append(line)
    return qusetionList

#producing questions table in database
def readJsonFile():
    questionCounter = 0
    quantity_comp_1 = 0
    quantity_comp_2 = 0
    quantity_comp_3 = 0

    address_lcquad_1 = "/Users/fazeletavakoli/PycharmProjects/QA_userStudy/LC-QuAD-train.json"
    address_lcquad_2 = "/Users/fazeletavakoli/PycharmProjects/QA_userStudy/lcquad_2_0.json"
    address_VQuAnDa_1 = "/Users/fazeletavakoli/PycharmProjects/QA_userStudy/VQuAnDa_1_0_test.json"

    with open(address_VQuAnDa_1, 'r') as jsonFile:
        dictionary = json.load(jsonFile)
    for entity in dictionary:
        final_answer = ""
        if questionCounter != 21:
            # question = entity['paraphrased_question']
            # question = entity['corrected_question']
            question = entity['question']
            # query = entity["sparql_dbpedia18"]
            # query = entity["sparql_query"]
            query = entity['query']
            complexity = detect_complexity(query)
            if (complexity == 1 and quantity_comp_1 < 10) or (complexity == 2 and quantity_comp_2 < 10) or (complexity == 3 and quantity_comp_3 < 10):
                if complexity == 1:
                    quantity_comp_1 = quantity_comp_1 + 1
                elif complexity == 2:
                    quantity_comp_2 = quantity_comp_2 + 1
                else:
                    quantity_comp_3 = quantity_comp_3 + 1
                verbalized_answer = entity['verbalized_answer']
                ### using 'SparqltoUser' webservice for getting interpretation of sparql query ###
                language = "en"
                # knowledgeBase = "wikidata"  # it doesn't work with "wikidata" when api is used not my local host.
                knowledgeBase = "dbpedia"
                # response = requests.get('https://qanswer-sparqltouser.univ-st-etienne.fr/sparqltouser',
                #                         params={'sparql':query, 'lang':language,'kb':knowledgeBase})  # this command also works without setting 'lang' and 'kb'
                response_s2u = requests.get('http://localhost:1920/sparqltouser',
                                        params={'sparql': query, 'lang': language, 'kb': knowledgeBase})
                jsonResponse = response_s2u.json()
                controlledLanguage = jsonResponse['interpretation']
                ##response from sparql endpoint(which is the answer of our question)
                response_se = requests.get('http://sda01dbpedia:softrock@131.220.9.219/sparql',
                                           params={'query': query})

                # print(root.tag)
                # print(root.attrib)

                # for child in root:
                #     print (child.tag, child.attrib)

                try:
                    obj = untangle.parse(response_se.text)
                except:
                    if response_se.text == "true":
                        final_answer = "true"
                if final_answer == "":  #if final_answer hasn't filled with "true" above
                    root = ET.fromstring(response_se.text)
                    if "COUNT" in query:
                        complete_answer = obj.sparql.results.result.binding.literal
                        final_answer = detect_regularExpression(str(complete_answer), "finalAnswer_number")
                    else:
                        if obj.sparql.results.result[0] == None:
                            complete_answer = obj.sparql.results.result.binding.uri
                            fianl_answer = detect_regularExpression(str(complete_answer), "finalAnswer_url")
                            final_answer = fianl_answer[1:]
                        else:
                            quantity_answers = len(obj.sparql.results.result)
                            if quantity_answers > 10:
                                max_range = 10
                            else:
                                max_range = quantity_answers
                            for i in range(0,max_range):
                                xml_root = root[1][i][0][0]
                                result_middle = obj.sparql.results.result[i]
                                # if result_middle.binding.get_attribute('uri') != None:
                                if "uri" in str(xml_root):
                                    complete_answer = result_middle.binding.uri
                                    fianl_answer_i = detect_regularExpression(str(complete_answer), "finalAnswer_url")
                                    final_answer_i = fianl_answer_i[1:]
                                else:
                                    complete_answer = result_middle.binding.literal
                                    final_answer = detect_regularExpression(str(complete_answer), "finalAnswer_number")
                                final_answer = final_answer + final_answer_i + ", "
                            final_answer = final_answer[:len(final_answer)-2] #removing the last excessive comma
                questionCounter = questionCounter + 1
                new_question = Question(question = question, sparqlQuery= query, controlledLanguage= controlledLanguage, answer = final_answer, verbalized_answer = verbalized_answer, complexity = complexity)
                db.session.add(new_question)
                db.session.commit()

def detect_regularExpression(inputString, purpose):
    if purpose == "visualization":
        # sparql_test = 'SELECT DISTINCT COUNT(?uri) WHERE { ?x <http://dbpedia.org/ontology/commander> <http://dbpedia.org/resource/Andrew_Jackson> . ?uri <http://dbpedia.org/ontology/knownFor> ?x  . }'
        lines = re.split('\s\.|\.\s', inputString)
        pattern = re.compile(r'(\?(uri))|(\?(x))|(resource/[^<>]+>)|(property/[^<>]+>)|(ontology/[^<>]+>)|(\#type)')  # lcquad_1
        nodes = [] #all entities u=including nodes and edges
        links = []
        nodes_and_links = []
        match_counter = 0
        contained_list = ["resource/","property/", "ontology/"]
        for line in lines:
            if len(line) < 4: #if the line is just made of a "}", at the end of the sparql query
                break
            matches = pattern.finditer(line)
            current_nodes = []
            for match in matches:
                contained_tag = 0
                if match_counter != 0 or match.group() != "?uri": #This if statement is just for preventing from entering this block
                                                                    # when exactly the first match is "?uri". In some sparql queries we have ?uri before WHERE and in some other queries we don't.
                    for cl in contained_list:
                        contained_number = match.group().find(cl)
                        if contained_number != -1:
                            title = match.group()[contained_number+len(cl):]
                            contained_tag = 1
                            break
                    if contained_tag == 0:
                        title = match.group()
                    title = title.replace(">","")
                    current_nodes.append(title)
                    if title not in nodes and current_nodes.index(title) != 1:
                    # if title not in nodes and not(('ontology/' in title and current_nodes.index(title) == 1)  or
                    #                               ('property/' in title or current_nodes.index(title) == 1) or
                    #                               '#type' in title):
                        nodes.append(title)
                match_counter = match_counter + 1
            links.append([nodes.index(current_nodes[0]), current_nodes[1], nodes.index(current_nodes[2])])
            # final_nodes.append(current_nodes)
        nodes_and_links.append(nodes)
        nodes_and_links.append(links)
        return nodes_and_links
    elif purpose == "finalAnswer_url":
        pattern = re.compile(r'[/][^/]+')
        matches = pattern.finditer(inputString)
        for match in matches:
            title = match.group(0) #changing the type of the title to String
        return title #returns the last title
    elif purpose == "finalAnswer_number":
        pattern = re.compile(r'(cdata) ((\d+)|((\w+)(\s+))+)')
        matched_titles = pattern.finditer(inputString)
        for match in matched_titles:
            title = match.group(2)
        return title  # returns the last number, after cdata

def detect_complexity(inputString):
    lines = re.split('\s\.|\.\s', inputString)
    question_complexity = 0 #it is calculated based on the number of sparql triples
    for line in lines:
        if len(line) < 4:
            break
        question_complexity = question_complexity + 1
    return question_complexity

if __name__ == '__main__':
    # readJsonFile()
    app.run()
