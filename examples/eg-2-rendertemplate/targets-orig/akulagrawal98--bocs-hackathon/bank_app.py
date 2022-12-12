from flask import Flask,render_template,request,redirect,url_for,g
import sqlite3
import pyotp
from pusher import Pusher
import pyqrcode 
from pyqrcode import QRCode
from sqlite3 import Error
from encrypt_qr import create_save

pusher = Pusher(app_id='805555', key='4624456b5675dac3c7b1', secret='f09e27c733fb7ecb2642', cluster='ap2',ssl=True)
app = Flask(__name__)

DATABASE='database.db'
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/dashboard')
def dashboard():
    try:
        cur=get_db().cursor()
        cur.execute('select * from sent_cheque where sent_to_bank=2')
        c=cur.fetchall()
        cur.execute('select * from sent_cheque where sent_to_bank=1')
        d=cur.fetchall()
		# print("HEYY DASHBOARD",c)
        return render_template('dashboard.html',cheque_list=c,status=len(d))
    except:
        c=[]
        return render_template('dashboard.html',cheque_list=c,status=len(c))


@app.route('/pending',methods=['POST','GET'])


def pending():
    cur=get_db().cursor()
    results = cur.execute('select * from sent_cheque where sent_to_bank=1').fetchall()
    valid=[False for i in range(len(results))]
    if(request.method=='POST'):
        if(request.form['key']=="default"):
            index=int(request.form['valid-index'])
            print("THIS IS THE INDEX",index)
            valid[index]=True
            if(request.form['but_type']=="sub"):

                print(" i came her!!!!!!!")
                trans_id=int(request.form['trans_id'])
                cur=get_db().cursor()
                cur.execute('update sent_cheque set sent_to_bank=2 where trans_id=?',(trans_id,))
                get_db().commit()
                cur=get_db().cursor()
                results = cur.execute('select * from sent_cheque where sent_to_bank=1').fetchall()
                valid=[False for i in range(len(results))]
                cur.execute('select * from sent_cheque where trans_id=?',(trans_id,))
                a=cur.fetchone()
                print(a,"I am here!!!!!!!!!!!")
                #Display to dashboard here
                pusher.trigger(u'customer', u'add', {
                u'name': a[0],
                u'AccNo': a[1],
                u'Amount': a[3],
                u'IFSC': a[4],
                })
                totp = pyotp.TOTP('base32secret3232')
                otp_gen=totp.now()
                message=otp_gen
                pusher.trigger(u'message', u'send', {
                u'name': trans_id,
                u'message':message
                })
                otp=cur.execute('select * from otp_table where trans_id=?',(trans_id,)).fetchall()
                if(len(otp)==0):
                    cur.execute('insert into otp_table(trans_id,otp,timestamp_val) values(?,?,?)',(trans_id,message))
        else:
            index=int(request.form['valid-index'])
            valid[index]=False
    try:
        cur=get_db().cursor()
        results = cur.execute('select * from sent_cheque where sent_to_bank=1').fetchall()
        # qr=cur.execute('select * from qr_')
        trans_id = []
        sender_name = []
        receiver_name = []
        date = []
        amount = []
        qr_id=[]
        # valid=[False for i in range(len(results))]
        for result in results:
            trans_id.append(result[0])
            sender_name.append(result[2])
            receiver_name.append(result[3])
            date.append(result[4])
            amount.append(result[5])
            qr_id.append(result[1])
        qr_content=[]
        for i in qr_id:
            temp=cur.execute('select * from user_qr where qr_id=?',(i,)).fetchall()
            print("OKAYYY")
            qr_content.append(temp[0][1])
        print(qr_content)
        print("VALID LIST",valid)
        return render_template('pending_cheques.html',trans_id=trans_id,sender_name=sender_name,qr_content=qr_content,
                            valid=valid,zero=0,receiver_name=receiver_name,date=date,amount=amount)
    except:
        return "NO"
