import datetime
from flask import Flask, request, render_template_string,render_template,redirect,url_for,template_rendered,request_started,current_app,flash
from flask_babel import Babel
from flask_sqlalchemy import SQLAlchemy
from flask_user import current_user, login_required, roles_required, UserManager, UserMixin, user_logged_in,user_logged_out
import urllib.parse as urlparse
import threading
import os, signal 

# Sentry Connection
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
sentry_sdk.init(
    dsn="https://1bf495d85a5a47b7ae203992c6a22e65@sentry.io/2519626",
    integrations=[FlaskIntegration()]
)


""" Flask application factory"""

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///havaalani.sqlite'
app.config['SECRET_KEY'] = 'thisisasecretthisisasecretthisis'
app.config['USER_APP_NAME'] = 'E-Rezervasyon'
app.config['USER_ENABLE_EMAIL'] = False
    
babel = Babel(app)

@babel.localeselector
def get_locale():
    return 'tr'

db = SQLAlchemy(app)

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='1')

    username = db.Column(db.String(255, collation='NOCASE'), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False, server_default='')

    first_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')
    last_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')
    roles = db.relationship('Role', secondary='user_roles')
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)
class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))
class Ucus(db.Model):
    __tablename__ = 'ucuslar'
    id = db.Column(db.Integer(), primary_key=True)
    nereden = db.Column(db.String(50, collation='NOCASE'),nullable=False)
    nereye = db.Column(db.String(50, collation='NOCASE'),nullable=False)
    tarih = db.Column(db.Date)
    kapasitesi = db.Column(db.Integer())
    dolukoltuk = db.Column(db.Integer())
    fiyat = db.Column(db.Integer())
class Rezervasyon(db.Model):
    __tablename__ = 'rezervasyon'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    ucus_id = db.Column(db.Integer(), db.ForeignKey('ucuslar.id', ondelete='CASCADE'))
    tarih = db.Column(db.DateTime,default=datetime.datetime.now())

class Sepet(db.Model):
    __tablename__ = 'sepet'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    ucus_id = db.Column(db.Integer(), db.ForeignKey('ucuslar.id', ondelete='CASCADE'))
class Bonus(db.Model):
    __tablename__ = 'bonus'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    bonus = db.Column(db.Integer())
class iller(db.Model):
    __tablename__ = 'iller'
    id = db.Column(db.Integer(), primary_key=True)
    iladi = db.Column(db.String(100, collation='NOCASE'), nullable=False)
user_manager = UserManager(app, db, User)
@user_logged_out.connect_via(app)
def _after_login_hook(sender, user, **extra):
    Sepet.query.filter_by(user_id = user.id).delete()
    db.session.commit()
db.create_all()

if not User.query.filter(User.username == 'member').first():
    user = User(
        username='member',
        password=user_manager.hash_password('Password1'),
    )
    db.session.add(user)
    db.session.commit()
if not User.query.filter(User.username == 'admin').first():
    user = User(
        username='admin',
        password=user_manager.hash_password('Password1'),
    )
    user.roles.append(Role(name='Admin'))
    user.roles.append(Role(name='Agent'))
    db.session.add(user)
    db.session.commit()
@app.route('/')
def home_page(): 
    return render_template("anasayfa.html",tarih = datetime.datetime.now().date())
@app.route('/tumucakseferleri')
def tumucakseferleri():
    return render_template("kullanici/tumucakseferleri.html",tumucuslar = Ucus.query.all(),bugun = datetime.datetime.now().date())
def suresonu(): 
    Sepet.query.filter_by(user_id = kullaniciid).delete()
    db.session.commit()
    print("sil")
    print(kullaniciid)
sepetisiltimer = threading.Timer(600, suresonu)
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404
@app.route('/sepeteekle/<ucusid>')
@login_required
def sepeteekle(ucusid):
    if(current_user.is_authenticated):
        global kullaniciid
        kullaniciid = current_user.id
        ucus = Ucus.query.filter(Ucus.id == ucusid).first()
        if ucus.kapasitesi != ucus.dolukoltuk and ucus.tarih >= datetime.datetime.now().date():
            sepet = Sepet(
                user_id = current_user.id,
                ucus_id = ucusid,
            )
            db.session.add(sepet)
            db.session.commit()
            if not sepetisiltimer.is_alive():
                sepetisiltimer.start()
            flash('Seçtiğiniz bilet sepete eklendi.','success')
        else:
            flash('Seçtiğiniz bilet sepete eklenemedi.','warning')
            return redirect(url_for('tumucakseferleri'))
    else:
        print("Giriş Yapın")
    return redirect(url_for('tumucakseferleri'))

# Sentry test
@app.route('/debug-sentry')
def trigger_error():
    division_by_zero = 1 / 0

            
@app.route('/sepetim/<id>',methods = ["GET"])
@login_required
def sepetim(id):
    
    if current_user.id == int(id):
        return render_template('kullanici/sepetim.html',sepetim = db.session.query(Ucus,Sepet).filter(Ucus.id == Sepet.ucus_id,Sepet.user_id == id).all(),bonus = Bonus.query.filter(Bonus.user_id == id).first())
    else:
        return page_not_found(app)
@app.route('/sepettensil/<id>')
@login_required
def sepettensil(id):
    Sepet.query.filter_by(id = id).delete()
    db.session.commit()
    flash('Seçtiğiniz bilet sepetten silindi','warning')
    return redirect(url_for('sepetim',id=current_user.id))

@app.route('/sepetibosalt/<id>')
@login_required
def sepetibosalt(id):
    Sepet.query.filter_by(user_id = id).delete()
    db.session.commit()
    flash('Sepet başarıyla boşaltıldı','success')
    return redirect(url_for('home_page'))
    
@app.route('/rezervasyonekle/<id>',methods = ['POST','GET'])
@login_required
def rezervasyonekle(id):
    sepetim = db.session.query(Ucus,Sepet).filter(Ucus.id == Sepet.ucus_id,Sepet.user_id == id).all()
    bonusgelen = request.form.get('bonus')
    if not sepetim:
        flash('Sepetiniz Boş. Lütfen önce sepete bilet ekleyin.','danger')
        return redirect(url_for('home_page'))
    bonus = 0
    for ucus,sepet in sepetim:
        if ucus.kapasitesi != ucus.dolukoltuk:
            try:
                rezervasyon = Rezervasyon(
                    user_id = id,
                    ucus_id = ucus.id,
                )
                bonus = bonus + (ucus.fiyat*3/100)
                db.session.add(rezervasyon)
                Ucus.query.filter_by(id = ucus.id).update(dict(dolukoltuk = ucus.dolukoltuk + 1))
                db.session.commit()
                if bonusgelen != None:
                    bonusGet = Bonus.query.filter(Bonus.user_id == id).first()
                    sonbonus = 0
                    sonbonus = bonusGet.bonus - ucus.fiyat
                    print(sonbonus)
                    if sonbonus < 0:
                        sonbonus = 0
                    Bonus.query.filter_by(user_id = id).update(dict(bonus = sonbonus))
                    db.session.commit()
            except:
                db.session.rollback()
        else:
            flash(ucus.nereden+' - '+ucus.nereye+' uçağı dolu olduğu için rezervasyon tamamlanamadı.','warning')    
    if not Bonus.query.filter(Bonus.user_id == id).first():
        bonusyeni = Bonus(
            user_id = id,
            bonus = bonus,
        )
        db.session.add(bonusyeni)
        db.session.commit()
    else:
        bonusGet = Bonus.query.filter(Bonus.user_id == id).first()
        Bonus.query.filter_by(user_id = id).update(dict(bonus = bonusGet.bonus + bonus))
    Sepet.query.filter_by(user_id = id).delete()
    db.session.commit()
    flash("Sepetteki biletler başarıyla alınmıştır.","success")
    return redirect(url_for('home_page'))
@app.route('/rezervasyongecmisi/<id>')
@login_required
def rezervasyongecmisi(id):
    if (id == ""):
        return redirect(url_for('home_page'))
    if (current_user.id == int(id)):
        return render_template('kullanici/rezervasyongecmisi.html',rezervasyonlarim = db.session.query(Rezervasyon,Ucus).filter(Rezervasyon.ucus_id == Ucus.id,Rezervasyon.user_id == id).all())
    else:
        flash('Bu sayfaya erişilemez',"warning")
        return redirect(url_for('home_page'))
@app.route('/tariharaligi',methods = ['POST','GET'])
def tariharaligi():
    baslangic = request.form['baslangic']
    bitis = request.form['bitis']
    if baslangic > bitis:
        flash("Tarih aralığını yanlış girdiniz.","warning")
        return redirect(url_for('home_page'))
    ucaklar = Ucus.query.filter(Ucus.tarih >= baslangic,Ucus.tarih <= bitis).order_by((Ucus.kapasitesi*Ucus.dolukoltuk/100).desc()).all()
    flash(str(len(ucaklar)) + " Uçak listelendi","success")
    return render_template('kullanici/ucakbul.html',ucaklar = ucaklar)
@app.route('/admin')
@roles_required('Admin')
def admin_page():
    return render_template("admin/adminindex.html")
@app.route('/kayitlar')
@roles_required('Admin')
def kayitlar():
    return render_template('admin/kayitlar.html',kullanicilar = User.query.all())
@app.route('/ucuslar')
@roles_required('Admin')
def ucuslar():
    return render_template('admin/ucuslar.html',ucuslar = Ucus.query.all(),bugun = datetime.datetime.now().date())
@app.route('/ucus-ekle')
@roles_required('Admin')
def ucusekle():
    return render_template( "admin/ucusekle.html",iller = iller.query.order_by(iller.iladi.asc()).all(),bugun = datetime.datetime.now().date())
@app.route('/ucusduzenle/<id>',methods = ['POST','GET'])
@roles_required('Admin')
def ucusduzenle(id):
    ucus = Ucus.query.filter(Ucus.id == id).first()
    if ucus.tarih < datetime.datetime.now().date():
        flash("Uçuş tarihi geçtiği için düzenleme yapamazsınız","danger")
        return redirect(url_for('ucuslar'))
    if request.method == 'POST':
        try:
            nereden = request.form['nereden']
            nereye = request.form['nereye']
            tarih = request.form['tarih']
            kapasitesi = request.form['kapasitesi']
            dolukoltuk = request.form['dolukoltuk']
            fiyat = request.form['fiyat']
            Ucus.query.filter_by(id = id).update(dict(nereden = nereden,nereye = nereye,tarih = datetime.datetime.strptime(tarih, '%Y-%m-%d').date(), kapasitesi = kapasitesi,dolukoltuk = dolukoltuk,fiyat = fiyat))
            db.session.commit()
        except:
            db.session.rollback()
        finally:
            return redirect(url_for('ucuslar'))
    return render_template('admin/ucusduzenle.html',ucus = Ucus.query.filter(Ucus.id == id).first(),iller = iller.query.order_by(iller.iladi.asc()).all(),bugun = datetime.datetime.now().date())
@app.route('/ucussil/<id>')
@roles_required('Admin')
def ucussil(id):
    Ucus.query.filter_by(id = id).delete()
    db.session.commit()
    return redirect(url_for('ucuslar'))
@app.route('/kayit_ekle', methods = ['POST', 'GET'])
@roles_required('Admin')
def kayit_ekle():
    if request.method == 'POST':
        try:
            nereden = request.form['nereden']
            nereye = request.form['nereye']
            tarih = request.form['tarih']
            kapasitesi = request.form['kapasitesi']
            dolukoltuk = request.form['dolukoltuk']
            fiyat = request.form['fiyat']
            date_formate = datetime.date(int(tarih.split('-')[0]),int(tarih.split('-')[1]),int(tarih.split('-')[2]))
            if nereden == nereye:
                flash('Aynı il seçilemez','warning')
                return redirect(url_for('ucusekle'))
            ucus = Ucus(
                nereden = nereden,
                nereye = nereye,
                tarih = datetime.datetime.strptime(tarih, '%Y-%m-%d').date(),
                kapasitesi = kapasitesi,
                dolukoltuk = dolukoltuk,
                fiyat = fiyat,
            ) 
            db.session.add(ucus)
            db.session.commit()
        except:
            db.session.rollback()
    flash('Uçuş Başarıyla Eklendi','success')
    return redirect(url_for('ucuslar'))



if __name__ == '__main__':
    app.run(threaded=True, port=5000)
