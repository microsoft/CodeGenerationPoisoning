from application import app, db
from flask import render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, date
import re

class Userstore(db.Model):
    __tablename__ = 'userstore'
    id = db.Column(db.Integer, primary_key=True)
    uname = db.Column(db.String(20))
    password = db.Column(db.String(20))
    date_created = db.Column(db.DateTime, default=datetime.now)

class Patients(db.Model):
    __tablename__ = 'patients'
    id = db.Column(db.Integer, primary_key=True)
    ssn_id = db.Column(db.Integer)
    pname = db.Column(db.String(20), nullable=False)
    age = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.now)
    ldate = db.Column(db.DateTime, default=datetime.now)
    tbed = db.Column(db.String(10))
    address = db.Column(db.String(20))
    city = db.Column(db.String(20))
    state = db.Column(db.String(20))
    status = db.Column(db.String(20))

    # children = relationship("Medicines")
    # children1 = relationship("Diagnostics")

class Medicines(db.Model):
    __tablename__ = 'medicines'
    id = db.Column(db.Integer, primary_key=True)
    pid = db.Column(db.Integer)
    mname = Column(db.String(20))
    mid = db.Column(db.Integer)
    rate = db.Column(db.Integer)
    qissued = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.now)

    children = relationship("MedicineMaster")

class MedicineMaster(db.Model):
    __tablename__ = 'medicinemaster'
    mid = Column(Integer, ForeignKey('medicines.mid'), primary_key=True)
    mname = Column(db.String(20))
    qavailable = Column(db.Integer)
    rate = Column(db.Integer)

class Diagnostics(db.Model):
    __tablename__ = 'diagnostics'
    id = db.Column(db.Integer, primary_key=True)
    pid = db.Column(db.Integer)
    tname = Column(db.String(20))
    tid = db.Column(db.Integer)
    tcharge = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.now)

    children = relationship("DiagnosticsMaster")

class DiagnosticsMaster(db.Model):
    __tablename__ = 'diagnosticsmaster'
    tid = Column(Integer, ForeignKey('diagnostics.tid'), primary_key=True)
    tname = Column(db.String(20))
    tcharge = Column(db.Integer)

db.create_all()


@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:                # Checking for session login
        return redirect( url_for('home') )

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        usr = Userstore.query.filter_by(uname = username).first()
        if usr == None:
            flash('User Not Found', category='error')
            return redirect( url_for('login') )

        elif username == usr.uname and password == usr.password:
            session['username'] = username  # saving session for login
            return redirect( url_for('home') )

        else:
            flash('Wrong Credentials. Check Username and Password Again', category="error")

    return render_template("login.html")


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        uname = request.form['uname']
        password = request.form['pass']
        cnfrm_password = request.form['cpass']

        query = Userstore.query.filter_by(uname = uname).first()

        if query != None:
            if uname == str(query.uname):
                flash('Username already taken')
                return redirect( url_for('registration') )
        
        if password != cnfrm_password:
            flash('Passwords do not match')
            return redirect( url_for('registration') )

        regex = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{6,20}$"
        pattern = re.compile(regex)

        match = re.search(pattern, password)
        
        if match:
            user = Userstore(uname = uname, password = password)
            db.session.add(user)
            db.session.commit()
            flash('Staff Registred Successfully', category='info')
            return redirect( url_for('login') )
        else:
            flash('Password should contain one Uppercase, one special character, one numeric character')
            return redirect( url_for('registration') )
    return render_template('staff_registration.html')


@app.route('/home')
def home():
    if 'username' in session:
        return render_template('home.html')
    else:
        flash('You are logged out. Please login again to continue')
        return redirect( url_for('login') )

@app.route('/create_patient', methods=['GET', 'POST'])
def create_patient():
    if 'username' in session:                
        if request.method == 'POST':           
            ssn_id = request.form['ssn_id']
            pname = request.form['pname']      
            age = request.form['age']
            tbed = request.form['tbed']
            address = request.form['address']
            state = request.form['state']
            city = request.form['city']
            status = request.form['status']

            pat = Patients.query.filter_by( ssn_id = ssn_id ).first()

            if pat == None:
                patient = Patients(ssn_id=ssn_id, pname=pname, age=age, tbed=tbed, address=address, state=state, city=city,  status = status)
                db.session.add(patient)
                db.session.commit()
                flash('Patient creation initiated successfully')
                return redirect( url_for('create_patient') )
            
            else:
                flash('Patient with this SSN ID already exists')
                return redirect( url_for('create_patient') )
    else:
        flash('You are logged out. Please login again to continue')
        return redirect( url_for('login') )

    return render_template('create_patient.html')


@app.route('/update_patient')
def update_patient():
    if 'username' in session:
        usern = session['username']
        print(usern)
        updatep = Patients.query.all()


        if not updatep:
            flash('No patients exists in database')
            return redirect( url_for('create_patient') )
        else:
            print("inside else")
            return render_template('update_patient.html', updatep = updatep)

    else:
        flash('You have been logged out. Please login again')
        return redirect( url_for('login') )
    return render_template('update_patient.html')

@app.route('/deletepat')
def deletepat():
    if 'username' in session:
        usern = session['username']
        print(usern)
        updatep = Patients.query.all()


        if not updatep:
            flash('No patients exists in database')
            return redirect( url_for('create_patient') )
        else:
            print("inside else")
            return render_template('deletepat.html', updatep = updatep)

    else:
        flash('You have been logged out. Please login again')
        return redirect( url_for('login') )
    return render_template('deletepat.html')


@app.route('/editpatientdetail/<id>', methods=['GET', 'POST'])
def editpatientdetail(id):
    print("id is : ", id)
    if 'username' in session:
        print("inside sesssss")
        print(datetime.now())
        editpat = Patients.query.filter_by( id = id )
        

        if request.method == 'POST':  
            print("inside editpat post mtd")
            pname = request.form['npname']      
            age = request.form['nage']
            tbed = request.form['tbed']
            address = request.form['naddress']
            status = request.form['status']
            state = request.form['nstate']
            city = request.form['ncity']
            ldate = datetime.today()
            row_update = Patients.query.filter_by( id = id ).update(dict(pname=pname, age=age, tbed=tbed, address=address, state=state, city=city, status = status, ldate=ldate))
            db.session.commit()
            print("Roww update", row_update)

            if row_update == None:
                flash('Something Went Wrong')
                return redirect( url_for('update_patient') )
            else:
                flash('Patient update initiated successfully')
                return redirect( url_for('update_patient') )

        return render_template('editpatientdetail.html', editpat = editpat)

@app.route('/deletepatientdetail/<id>')
def deletepatientdetail(id):
    if 'username' in session:
        delpat = Patients.query.filter_by(id = id).delete()
        db.session.commit()

        if delpat == None:
            flash('Something Went Wrong')
            return redirect( url_for('update_patient') )
        else:
            flash('Patient deletion initiated successfully')
            return redirect( url_for('update_patient') )

    return render_template('update_patient.html')


@app.route('/patientscreen')
def patientscreen():
    if 'username' in session:
        pts = Patients.query.filter_by( status = 'Active' )
        print("ptsss",pts)
        if not pts:
            flash('All Patients Discharged')
            return redirect( url_for('update_patient') )
        else:
            print("inside else")
            return render_template('patientscreen.html', pts = pts)

    else:
        flash('You have been logged out. Please login again')
        return redirect( url_for('login') )

@app.route('/search_patient', methods=['GET', 'POST'])
def search_patient():
    if 'username' in session:
        if request.method == 'POST':
            id = request.form['id']
            
            if id != "":
                patient = Patients.query.filter_by( id = id).first()
                if patient == None:
                    flash('No Patients with  this ID exists')
                    return redirect( url_for('search_patient') )
                else:
                    flash('Patient Found')
                    return render_template('search_patient.html', patient = patient)
            
            if id == "":
                flash('Enter  id to search')
                return redirect( url_for('search_patient') )
    
    else:
        return redirect( url_for('login') )
    
    return render_template('search_patient.html')

@app.route('/billing', methods=['GET', 'POST'])
def billing():
    #today = datetime.today().strftime('%Y-%m-%d')
    today = datetime.now()
    if 'username' in session:
        if request.method == 'POST':
            id = request.form['id']
            delta = 0
            if id != "":
                patient = Patients.query.filter_by( id = id).first()
                if patient == None:
                    flash('No Patients with that this ID exists')
                    return redirect( url_for('billing') )
                elif patient.status != 'Active':
                    flash('No Active Patients with Entered ID')

                else:
                    flash('Patient Found')
                    x = patient.date
                    y = x.strftime("%d-%m-%Y, %H:%M:%S")
                    # z = today.strftime("%d-%m-%Y")
                    # print("Patient ",y)
                    # print("today", z)
                    delta = ( today - x ).days
                    print(delta)
                    dy = 0    
                    if delta == 0:
                        dy = 1
                    else:
                        dy = delta
                    roomtype = patient.tbed
                    bill = 0
                    print(roomtype)
                    if roomtype == 'SingleRoom':
                        bill = 8000 * dy
                    elif roomtype == 'SemiSharing':
                        bill = 4000*dy
                    else:
                        bill = 2000*dy

                    med = Medicines.query.filter_by(pid = id).all()
                    if med == None:
                        flash('But No Medicines issued to Patient till Now')
                    else:
                        mtot = 0
                        for j in med:
                            mtot += (j.qissued * j.rate)

                    dia = Diagnostics.query.filter_by(pid = id).all()
                    if dia == None:
                        flash('But No Tests issued to Patient till Now')
                    else:
                        tot = 0
                        for i in dia:
                            tot += i.tcharge
                        return render_template('billing.html', patient = patient, dy=dy, y=y, bill = bill, med = med, dia = dia, mtot = mtot, tot = tot)

            
            if id == "":
                flash('Enter  id to search patient')
                return redirect( url_for('billing') )
    
    else:
        return redirect( url_for('login') )
    
    return render_template('billing.html')

@app.route('/addMedicine', methods=['GET', 'POST'] )
def addMedicine():
    if 'username' in session:                
        if request.method == 'POST':           
            mid = request.form['mid']
            mname = request.form['mname']      
            qavailable = request.form['qavailable']
            rate = request.form['rate']

            pat = MedicineMaster.query.filter_by( mid = mid ).first()

            if pat == None:
                med = MedicineMaster(mid=mid, mname=mname, qavailable=qavailable, rate=rate)
                db.session.add(med)
                db.session.commit()
                flash('Medicine successfully Inserted to Database')
                return redirect( url_for('addMedicine') )
            
            else:
                flash('Medicine with this  ID already exists')
                return redirect( url_for('addMedicine') )
    else:
        flash('You are logged out. Please login again to continue')
        return redirect( url_for('login') )

    return render_template('addMedicine.html')




@app.route('/PharmacistPatientDetails', methods=['GET', 'POST'])
def PharmacistPatientDetails():
    if 'username' in session:
        if request.method == 'POST':
            id = request.form['id']
            
            if id != "":
                patient = Patients.query.filter_by( id = id).first()
                if patient == None:
                    flash('No Patients with that this ID exists')
                    return redirect( url_for('PharmacistPatientDetails') )
                else:
                    flash('Patient Found')

                med = Medicines.query.filter_by(pid = id).all()
                print("Meddd", med)
                if med == None:
                    # nll = med.mid
                    flash('But No Medicines issued to Patient till Now')
                    return render_template('PharmacistPatientDetails.html', patient = patient)
                else:
                    return render_template('PharmacistPatientDetails.html',patient = patient, med = med)
            
            if id == "":
                flash('Enter  id to search')
                return redirect( url_for('PharmacistPatientDetails') )
    
    else:
        return redirect( url_for('login') )
    
    return render_template('PharmacistPatientDetails.html')

@app.route('/medicinestatus')
def medicinestatus():
    if 'username' in session:
        usern = session['username']
        print(usern)
        updatep = MedicineMaster.query.all()
        print(updatep)
        if not updatep:
            flash('No Medicines exists in database')
            return redirect( url_for('addMedicine') )
        else:
            print("inside else")
            return render_template('medicinestatus.html', updatep = updatep)

    else:
        flash('You have been logged out. Please login again')
        return redirect( url_for('login') )
    return render_template('medicinestatus.html')

@app.route('/updatemed')
def updatemed():
    if 'username' in session:
        usern = session['username']
        print(usern)
        updatep = MedicineMaster.query.all()
        print(updatep)
        if not updatep:
            flash('No Medicines exists in database')
            return redirect( url_for('addMedicine') )
        else:
            print("inside else")
            return render_template('updatemed.html', updatep = updatep)

    else:
        flash('You have been logged out. Please login again')
        return redirect( url_for('login') )
    return render_template('updatemed.html')

@app.route('/deletemed')
def deletemed():
    if 'username' in session:
        usern = session['username']
        print(usern)
        updatep = MedicineMaster.query.all()
        print(updatep)
        if not updatep:
            flash('No Medicines exists in database')
            return redirect( url_for('addMedicine') )
        else:
            print("inside else")
            return render_template('deletemed.html', updatep = updatep)

    else:
        flash('You have been logged out. Please login again')
        return redirect( url_for('login') )
    return render_template('deletemed.html')

@app.route('/editmedicinedetail/<mid>', methods=['GET', 'POST'] )
def editmedicinedetail(mid):
    print("id is : ", mid)
    if 'username' in session:
        print("inside sesssss")
        print(datetime.now())
        editpat = MedicineMaster.query.filter_by( mid = mid )
        

        if request.method == 'POST':  
            print("inside editpat post mtd")
            mname = request.form['mname']      
            qavailable = request.form['qavailable']
            rate = request.form['rate']
            row_update = MedicineMaster.query.filter_by( mid = mid ).update(dict(mname=mname, qavailable=qavailable, rate=rate))
            db.session.commit()
            print("Roww update", row_update)

            if row_update == None:
                flash('Something Went Wrong')
                return redirect( url_for('medicinestatus') )
            else:
                flash('Patient update initiated successfully')
                return redirect( url_for('medicinestatus') )

        return render_template('editmedicinedetail.html', editpat = editpat)

@app.route('/deletemedicinedetail/<mid>')
def deletemedicinedetail(mid):
    if 'username' in session:
        delpat = MedicineMaster.query.filter_by(mid = mid).delete()
        db.session.commit()

        if delpat == None:
            flash('Something Went Wrong')
            return redirect( url_for('medicinestatus') )
        else:
            flash('Medicine deletion initiated successfully')
            return redirect( url_for('medicinestatus') )

    return render_template('medicinestatus.html')

@app.route('/issuemedicine/<pid>', methods=['GET', 'POST'])
def issuemedicine(pid):
    if 'username' in session:
        if request.method == 'POST':
            mname = request.form['mname']
            
            if mname != "":
                patient = MedicineMaster.query.filter_by( mname = mname).first()
                if patient == None:
                    flash('No Medicine with this Name exists')
                    return render_template('issuemedicine.html')
                else:
                    flash('Medicine found')
                    qissued = request.form['qissued']
                    qid = int(qissued)
                    print( type(qid) )
                    print((patient.qavailable) - qid)
                    if(qid > patient.qavailable):
                        flash("Entered Medicine Quantity Unavailable")
                        return render_template('issuemedicine.html', patient = patient)
                    else:
                        patient.qavailable = patient.qavailable - qid
                        db.session.commit()
                        mid = patient.mid
                        rate = patient.rate

                        rowup = Medicines( mid = mid, pid=pid, mname = mname, rate = rate , qissued=qissued)
                        db.session.add(rowup)
                        db.session.commit()
                        print("ROWWW", rowup)

                        return render_template('issuemedicine.html', patient = patient)

           
            
            if mname == "":
                flash('Enter  Medicine Name to Search')
                return render_template('issuemedicine.html')
    
    else:
        return redirect( url_for('login') )
    
    return render_template('issuemedicine.html')

@app.route('/medicines')
def medicines():
    if 'username' in session:
        updatep = Medicines.query.all()
        return render_template('medicines.html', updatep = updatep)

    else:
        flash('You have been logged out. Please login again')
        return redirect( url_for('login') )
    return render_template('medicines.html')

@app.route('/DiagnosticsPatientDetails', methods=['GET', 'POST'])
def DiagnosticsPatientDetails():
    if 'username' in session:
        if request.method == 'POST':
            id = request.form['id']
            
            if id != "":
                patient = Patients.query.filter_by( id = id).first()
                if patient == None:
                    flash('No Patients with that this ID exists')
                    return redirect( url_for('DiagnosticsPatientDetails') )
                else:
                    flash('Patient Found')

                med = Medicines.query.filter_by(pid = id).all()
                print("Meddd", med)
                if med == None:
                    # nll = med.mid
                    flash('But No Medicines issued to Patient till Now')
                    return render_template('DiagnosticsPatientDetails.html', patient = patient)
                else:
                    flash(" ")

                dia = Diagnostics.query.filter_by(pid = id).all()
                if dia == None:
                    flash('But No Tests issued to Patient till Now')
                    return render_template('DiagnosticsPatientDetails.html', patient = patient)
                else:
                    return render_template('DiagnosticsPatientDetails.html',patient = patient, med = med, dia = dia)
            
            if id == "":
                flash('Enter  id to search')
                return redirect( url_for('DiagnosticsPatientDetails') )
    
    else:
        return redirect( url_for('login') )
    
    return render_template('DiagnosticsPatientDetails.html')

@app.route('/addDiagnostics', methods=['GET', 'POST'] )
def addDiagnostics():
    if 'username' in session:                
        if request.method == 'POST':           
            tid = request.form['tid']
            tname = request.form['tname']      
            tcharge = request.form['tcharge']

            pat = DiagnosticsMaster.query.filter_by( tid = tid ).first()

            if pat == None:
                diag = DiagnosticsMaster(tid=tid, tname=tname, tcharge=tcharge)
                db.session.add(diag)
                db.session.commit()
                flash('Test successfully Added to Database')
                return redirect( url_for('addDiagnostics') )
            
            else:
                flash('Test with this  ID already exists')
                return redirect( url_for('addDiagnostics') )
    else:
        flash('You are logged out. Please login again to continue')
        return redirect( url_for('login') )

    return render_template('addDiagnostics.html')

@app.route('/diagnosticsstatus')
def diagnosticsstatus():
    if 'username' in session:
        usern = session['username']
        print(usern)
        updatep = DiagnosticsMaster.query.all()
        print(updatep)
        if not updatep:
            flash('No Tests Available')
            return redirect( url_for('addDiagnostics') )
        else:
            print("inside else")
            return render_template('diagnosticsstatus.html', updatep = updatep)

    else:
        flash('You have been logged out. Please login again')
        return redirect( url_for('login') )
    return render_template('diagnosticsstatus.html')

@app.route('/issuediagnostics/<pid>', methods=['GET', 'POST'])
def issuediagnostics(pid):
    if 'username' in session:
        if request.method == 'POST':
            tname = request.form['tname']
            
            if tname != "":
                patient = DiagnosticsMaster.query.filter_by( tname = tname).first()
                if patient == None:
                    flash('No Test with this Name exists')
                    return render_template('issuediagnostics.html')
                else:
                    flash('Test Found')
                    tid = patient.tid
                    tcharge = patient.tcharge
                    rowup = Diagnostics( tid = tid, pid=pid, tname = tname, tcharge = tcharge )
                    db.session.add(rowup)
                    db.session.commit()
                    print("ROWWW", rowup)

                    return render_template('issuediagnostics.html', patient = patient)
      
            if tname == "":
                flash('Enter  Test Name to Search')
                return render_template('issuediagnostics.html')
    
    else:
        return redirect( url_for('login') )
    
    return render_template('issuediagnostics.html')

@app.route('/generatebill/<id>')
def generatebill(id):
    if 'username' in session:
        stat = 'Discharged'
        row_update = Patients.query.filter_by( id = id ).update(dict(status = stat))
        db.session.commit()

        if row_update == None:
            flash('Something Went Wrong')
            return redirect( url_for('billing') )
        else:
            flash('Patient Bill Generated successfully')
            return redirect( url_for('billing') )

    else:
        flash('You have been logged out. Please login again')
        return redirect( url_for('login'))
    return render_template('billing.html')






@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('logged out successfully .')
    return redirect( url_for('login') )


    

