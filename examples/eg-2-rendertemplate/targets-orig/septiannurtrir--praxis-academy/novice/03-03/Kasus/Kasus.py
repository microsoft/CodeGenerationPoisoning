from flask import Flask, render_template, request
from flask_mysqldb import MySQL
app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'septiannurtrir'
app.config['MYSQL_PASSWORD'] = 'sandaljebatds07'
app.config['MYSQL_DB'] = 'Kasus'

mysql = MySQL(app)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == "POST":
        details = request.form
        membership_ID = details['member']
        full_Names = details['names']
        physical_Address = details['address']
        salutation_ID = details['salutate']
        cur = mysqlsa.connection.cursor()
        cur.execute("INSERT INTO Table1 (membership_ID, full_Names, physical_Address, salutation_ID) VALUES (%s, %s, %s, %s)", (membership_ID, full_Names, physical_Address, salutation_ID))
        mysql.connection.commit()
        cur.close()
        return 'success'
    return render_template('index.html')

 @app.route('/rent')
 def gaji():
     cur = mysql.connection.cursor()
     cur.execute('''SELECT membership_ID, full_Names, physical_Address, salutation_ID''')
     rv = cur.fetchall()
     return render_template("indexrent.html",value=rv)

if __name__ == '__main__':
    app.run()   