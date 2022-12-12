# -*- coding: utf-8 -*-
from flask import json, Flask, render_template, url_for, request, session, redirect, make_response, flash, jsonify
from flask_socketio import SocketIO
from flaskext.mysql import MySQL


import bcrypt
from flask_pymongo import PyMongo
from pymongo import MongoClient

app = Flask(__name__, static_url_path='/static')

app.config['SECRET_KEY'] = 'jsbcfsbfjefebw237u3gdbdc'
socketio = SocketIO(app)
app.secret_key = "super secret key"
mysql = MySQL()


app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '1234'
app.config['MYSQL_DATABASE_DB'] = 'Postlist'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)


connection = MongoClient('mongodb://localhost:27017/')
dbs = connection.chatbot
col_traindata = dbs.questiondata
col_answerdata = dbs.answerdata
col_user = dbs.users

app.config['MONGO_DBNAME'] = 'chatbot'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/chatbot'

mongo = PyMongo(app)

@app.route('/')
def masterpage():
    resp = make_response(render_template('./web1.html'));
    resp.set_cookie('same-site-cookie', 'foo', samesite='Lax');
    # Ensure you use "add" to not overwrite existing cookie headers
    resp.headers.add('Set-Cookie','cross-site-cookie=bar; SameSite=None; Secure')
    return resp

# @app.route('/')
# def masterpage():
#     return render_template('./web1.html')

@app.route('/home-page')
def homepage():
    return render_template('./web1.html')

@app.route('/gioi-thieu-nganh')
def gioithieunganh():
    return render_template('./GioiThieuNganh.html')

@app.route('/co-hoi-nghe-nghiep')
def cohoinghenghiep():
    return render_template('./CoHoiNgheNghiep.html')

@app.route('/kien-thuc-ky-nang')
def kienthuckynang():
    return render_template('./KienThucKyNang.html')

@app.route('/lien-he')
def lienhe():
    return render_template('./LienHe.html')

@app.route('/NhapCauHoi')
def nhapcauhoi():
    if 'user' in session:
        list = mongo.db.questiondata.find()
        return render_template('NhapCauHoi.html', list=list)
        #return render_template('./NhapCauHoi.html')
    return render_template('index.html')

@app.route('/NhapCauHoi', methods=['POST'])
def traindata():
        feature = request.form['feature']
        target = request.form['target']
        if feature and target:
            col_traindata.insert_one({'feature': feature, 'target': target})
            return jsonify({'name' : 'Đã thêm thành công'})
        return jsonify({'error': 'Dữ liệu trống!!!'})
@app.route('/NhapCauTraLoi')
def NhapCauTraLoi():
    if 'user' in session:
        list = mongo.db.answerdata.find()
        return render_template('NhapCauTraLoi.html', list=list)
        #return render_template('./NhapCauTraLoi.html')
    return render_template('index.html')
@app.route('/NhapCauTraLoi', methods=['POST'])
def insdata():
        feature = request.form['feature']
        target = request.form['target']
        if feature and target:
            col_answerdata.insert_one({'target': target, 'feature': feature})
            return jsonify({'name' : 'Đã thêm thành công'})
        return jsonify({'error': 'Dữ liệu trống!!!'})

def messageRecived():
    print('message was received!!!')

@socketio.on('my eventes')
def handle_my_custom_event1(json1):
    from src import text_classification_predict
    message = json1['message']
    answer = text_classification_predict.TextClassificationPredict().get_train_data(message)
    json1['answer'] = answer
    json1['bot'] = 'ChatBot: '
    print(message)

    print('recived my event: ' + str(json1))
    socketio.emit('my response', json1, callback=messageRecived)
    print(json1)

@app.route('/getPostKienThuc')
def getPostKienThuc():
    try:
        _user = session.get('user')
        con = mysql.connect()
        cursor = con.cursor()
        cursor.callproc('sp_GetPostKienThuc')
        wishes = cursor.fetchall()
        wishes_dict = []
        for wish in wishes:
            wish_dict = {
                    'Id': wish[0],
                    'Title': wish[1],
                    'Description': wish[2],
                    'Date' : wish[4]}
            wishes_dict.append(wish_dict)
        return json.dumps(wishes_dict)
    except Exception as e:
        return render_template('error.html', error = str(e))

@app.route('/getPostCoHoi')
def getPostCoHoi():
    try:
        _user = session.get('user')
        con = mysql.connect()
        cursor = con.cursor()
        cursor.callproc('sp_GetPostCoHoi')
        wishes = cursor.fetchall()
        wishes_dict = []
        for wish in wishes:
            wish_dict = {
                    'Id': wish[0],
                    'Title': wish[1],
                    'Description': wish[2],
                    'Date' : wish[4]}
            wishes_dict.append(wish_dict)
        return json.dumps(wishes_dict)
    except Exception as e:
        return render_template('error.html', error = str(e))

#admin
@app.route('/admin')
def trangchu():
    if 'user' in session:
        return render_template('NhapCauHoi.html')
    return render_template('index.html')

@app.route('/mainadmin')
def mainadmin():
    if 'username' in session:
        return render_template('mainadmin.html')
    return render_template('index.html')

@app.route('/new-co-hoi-nghe-nghiep')
def addcohoinghenghiep():
    return render_template('AddNewsCoHoi.html')

@app.route('/add-new-co-hoi',methods=['POST'])
def addCohoinghenghiep():
    try:
            _title = request.form['inputTitle']
            _description = request.form['inputDescription']
            _user = session.get('user')

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_addCoHoi',(_title,_description,_user))
            data = cursor.fetchall()

            if len(data) is 0:
                conn.commit()
                return render_template('./AddNewsCoHoi.html')
            else:
                return render_template('error.html',error = 'An error occurred!')
    except Exception as e:
        return render_template('error.html',error = str(e))
    finally:
        cursor.close()
        conn.close()

@app.route('/new-ky-nang-kien-thuc')
def addkynangkienthuc():
    return render_template('AddNewsKyNang.html')

@app.route('/add-new-ky-nang',methods=['POST'])
def addKynangkienthuc():
    try:
            _title = request.form['inputTitle']
            _description = request.form['inputDescription']
            _user = session.get('user')

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_addKienThuc',(_title,_description,_user))
            data = cursor.fetchall()

            if len(data) is 0:
                conn.commit()
                return render_template('./AddNewsKyNang.html')
            else:
                return render_template('error.html',error = 'An error occurred!')
    except Exception as e:
        return render_template('error.html',error = str(e))
    finally:
        cursor.close()
        conn.close()
#them-sua-xoa
@app.route('/getCoHoiById', methods=['POST'])
def getCohoiById():
    try:
            _id = request.form['id']
            # _user = session.get('user')

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_GetCoHoiById', (_id,))
            result = cursor.fetchall()

            wish = []
            wish.append({'Id': result[0][0], 'Title': result[0][1], 'Description': result[0][2]})

            return json.dumps(wish)
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/updateCoHoi', methods=['POST'])
def updateCoHoi():
    try:
            _user = session.get('user')
            _title = request.form['title']
            _description = request.form['description']
            _wish_id = request.form['id']

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_updateCoHoi', (_title, _description, _wish_id, _user))
            data = cursor.fetchall()

            if len(data) is 0:
                conn.commit()
                return json.dumps({'status': 'OK'})
            else:
                return json.dumps({'status': 'ERROR'})
    except Exception as e:
        return json.dumps({'status': 'Unauthorized access'})
    finally:
        cursor.close()
        conn.close()

@app.route('/getKienThucById', methods=['POST'])
def getKienThucById():
    try:
            _id = request.form['id']
            # _user = session.get('user')

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_GetKienThucById', (_id,))
            result = cursor.fetchall()

            wish = []
            wish.append({'Id': result[0][0], 'Title': result[0][1], 'Description': result[0][2]})

            return json.dumps(wish)
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/updateKienThuc', methods=['POST'])
def updateKienThuc():
    try:
            _user = session.get('user')
            _title = request.form['title']
            _description = request.form['description']
            _wish_id = request.form['id']

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_updateKienThuc', (_title, _description, _wish_id, _user))
            data = cursor.fetchall()

            if len(data) is 0:
                conn.commit()
                return json.dumps({'status': 'OK'})
            else:
                return json.dumps({'status': 'ERROR'})
    except Exception as e:
        return json.dumps({'status': 'Unauthorized access'})
    finally:
        cursor.close()
        conn.close()


@app.route('/deleteCoHoi', methods=['POST'])
def deleteCoHoi():
    try:
            _id = request.form['id']
            _user = session.get('user')

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_deleteCohoi', (_id, _user))
            result = cursor.fetchall()

            if len(result) is 0:
                conn.commit()
                return json.dumps({'status': 'OK'})
            else:
                return json.dumps({'status': 'An Error occured'})
    except Exception as e:
        return json.dumps({'status': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/deleteKienThuc', methods=['POST'])
def deleteKienThuc():
    try:
            _id = request.form['id']
            _user = session.get('user')

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_deleteKienThuc', (_id, _user))
            result = cursor.fetchall()

            if len(result) is 0:
                conn.commit()
                return json.dumps({'status': 'OK'})
            else:
                return json.dumps({'status': 'An Error occured'})
    except Exception as e:
        return json.dumps({'status': str(e)})
    finally:
        cursor.close()
        conn.close()

#thêm data chatbot
@app.route('/admin', methods=['POST'])
def sendtraindata():
    if request.form['btn'] == 'Submit':
        feature = request.form['feature']
        target = request.form['target']
        if feature == "" or target == "":
            return 'Câu hỏi hoặc nhóm câu hỏi bị trống hoặc không hợp lệ'
        else:
            col_traindata.insert_one({'feature': feature, 'target': target})
            return render_template('NhapCauHoi.html')
    if request.form['btn'] == 'Send':
        feature = request.form['feature']
        target = request.form['target']
        if feature == "" or target == "":
            return 'Target hoặc feature bị trống hoặc không hợp lệ.'
        else:
            existing_answer = col_answerdata.find_one({'target': request.form['target']})
            if existing_answer is None:
                col_answerdata.insert_one({'feature': feature, 'target': target})
                return render_template('NhapCauHoi.html')
            else:
                return 'Nhóm câu hỏi đã tồn tại trong hệ thống!'
    # if request.form['btn'] == 'Logout':
    #     session.pop('user', None)
    #     return redirect(url_for('mainadmin'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return render_template('index.html')

@app.route('/mainadmin', methods=['POST'])
def sendaccountdata():
    if request.form['btn'] == 'Register':
        username = request.form['username']
        password = request.form['password']
        if username == "" or password == "":
            return 'Tài Khoản hoặc Mật Khẩu không hợp lệ'
        else:
            user = mongo.db.users
            existing_user = user.find_one({'name': request.form['username']})

            if existing_user is None:
                hashpass = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
                user.insert({'name': request.form['username'], 'password': hashpass})
                #session['username'] = request.form['username']
                # return redirect(url_for('trangchu'))
                return render_template('mainadmin.html')

            return ' Người dùng đã tồn tại !'
    if request.form['btn'] == 'Delete':
        username = request.form['username']
        if username == "":
            return 'Tên người dùng không hợp lệ'
        else:
            existing_users = col_user.find_one({'name': request.form['username']})
            if existing_users:
                col_user.delete_one({'name': username})
                return 'Đã xóa thành công!'
    if request.form['btn'] == 'Đăng xuất':
        session.pop('username', None)
        flash('You were just logged out')
        return redirect(url_for('mainadmin'))

#admin login
@app.route('/login', methods=['POST'])
def login():
    users = mongo.db.users
    admin = mongo.db.admin

    login_user = users.find_one({'name': request.form['username']})
    login_admin = admin.find_one({'name': request.form['username']})

    if login_user:
        if bcrypt.hashpw(request.form['pass'].encode('utf-8'), login_user['password']) == login_user['password']:
            session['user'] = request.form['username']
            return redirect(url_for('trangchu'))
    if login_admin:
        if bcrypt.hashpw(request.form['pass'].encode('utf-8'), login_admin['password']) == login_admin['password']:
            session['username'] = request.form['username']
            return redirect(url_for('mainadmin'))

    return 'Invalid username/password combination'

#admin đăng ký
@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        admin = mongo.db.admin
        existing_user = admin.find_one({'name': request.form['username']})

        if existing_user is None:
            hashpass = bcrypt.hashpw(request.form['pass'].encode('utf-8'), bcrypt.gensalt())
            admin.insert({'name': request.form['username'], 'password': hashpass})
            session['username'] = request.form['username']
            #return redirect(url_for('trangchu'))
            return render_template('index.html')

        return 'That username already exists!'

    return render_template('register.html')


if __name__ == '__main__':
    socketio.run(app, debug=True)
