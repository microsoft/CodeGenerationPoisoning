from flask import Flask, render_template, request, redirect, url_for, session
from flask_bootstrap import Bootstrap
import requests
from flask_mysqldb import MySQL, MySQLdb

app = Flask(__name__)
Bootstrap(app)
mysql = MySQL(app)

app.config['MYSQL_HOST'] = 'db' 
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'autito'
app.config['MYSQL_DB_UNIX_SOCKET'] = '/Applications/MAMP/tmp/mysql/mysql.sock'


@app.route('/', methods= ['GET', 'POST'])
def index():
    return render_template('index.html') 

@app.route('/login',methods=["GET","POST"])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']

        curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        curl.execute("SELECT * FROM user WHERE name=%s",(name,))
        user = curl.fetchone()
        curl.close()

        if user:
            if password == user["password"]:
                session['name'] = user['name']
                return render_template("index.html")
            else:
                return render_template("login.html", error = "email o contraseña incorrectos")
        else:
            return render_template("login.html", error = "usuario no encontrado")
    else:
        return render_template("login.html")


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    else:
        name = request.form['name']
        dni = request.form['dni']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO user (name, dni, password) VALUES (%s, %s, %s)",(name,dni,password))
        mysql.connection.commit()
        session['name'] = request.form['name']
        return redirect(url_for('index'))


@app.route('/logout', methods=["GET", "POST"])
def logout():
    session.clear()
    return render_template("index.html")


@app.route('/adelante')
def adelante():
    requests.get('http://192.168.4.1/1')
    return render_template('index.html') 

@app.route('/atras')
def atras():
   requests.get('http://192.168.4.1/2')
   return render_template('index.html') 

@app.route('/izquierda')
def izquierda():
    requests.get('http://192.168.4.1/3')
    return render_template('index.html') 

@app.route('/derecha')
def derecha():
    requests.get('http://192.168.4.1/4')
    return render_template('index.html') 

@app.route('/parar')
def parar():
    requests.get('http://192.168.4.1/5')
    return render_template('index.html') 

@app.route('/lento')
def lento():
    requests.get('http://192.168.4.1/6')
    return render_template('index.html') 
    
@app.route('/rapido')
def rapido():
    requests.get('http://192.168.4.1/7')
    return render_template('index.html') 

if __name__ == "__main__":
    app.secret_key = "^A%DJAJU^JJ123"
    app.run(host='0.0.0.0', port=7000, debug=True)
