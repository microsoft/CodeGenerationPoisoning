from flask import (Flask, render_template, make_response, url_for, request,
                   redirect, flash, session, send_from_directory, jsonify
                   )
from werkzeug import secure_filename
app = Flask(__name__)

import sys,os,random
import getters
import setters

from dotenv import load_dotenv
load_dotenv()

# CAS(app)

# app.config['CAS_SERVER'] = 'https://login.wellesley.edu:443'
# app.config['CAS_AFTER_LOGIN'] = 'logged_in'
# app.config['CAS_LOGIN_ROUTE'] = '/module.php/casserver/cas.php/login'
# app.config['CAS_LOGOUT_ROUTE'] = '/module.php/casserver/cas.php/logout'
# app.config['CAS_AFTER_LOGOUT'] = 'http://cs.wellesley.edu:8343/'
# app.config['CAS_VALIDATE_ROUTE'] = '/module.php/casserver/serviceValidate.php'

app.secret_key = os.getenv('secret_key')
app.secret_key = ''.join([ random.choice(('ABCDEFGHIJKLMNOPQRSTUVXYZ' +
                                          'abcdefghijklmnopqrstuvxyz' +
                                          '0123456789'))
                           for i in range(20) ])

app.config['TRAP_BAD_REQUEST_ERRORS'] = True

@app.route('/')
def index():
    return render_template('base.html')

@app.route('/query', methods=['GET','POST'])
def query():
    conn = getters.getConn('cs304reclib_db')
    args = request.args

    if 'q' in args:
        q = args['q']
    if 'filter' in args:
        kind = args['filter']

    if kind == 'album':
        results = getters.searchAlbums(q, conn)
    if kind == 'artist':
        results = getters.searchArtists(q, conn)
    if kind == 'year':
        results = getters.searchYear(q, conn)
    if kind == 'genre':
        results = getters.searchGenre(q, conn)
    if kind == 'track':
        results = getters.searchTrack(q, conn)

    return render_template('results.html',
                            results=results,
                            query=q,
                            kind=kind)

@app.route('/album/<aid>', methods=['GET'])
def album(aid):
    conn = getters.getConn('cs304reclib_db')
    album = getters.getAlbumByID(aid, conn)
    
    res = getters.getReservation(aid, conn)
    tracks = getters.getTracks(aid, conn)
    genres = getters.getGenres(aid, conn)
    
    # if the album has been returned
    if res is None or res['returned'] == 1:
        avail = 'Available'
    # if not, pass the due date to the template
    else:
        avail = 'Due back ' + res['due'].strftime('%m/%d/%Y')

    print(album['location'])

    return render_template('album.html',
                            album=album,
                            avail=avail,
                            tracks=tracks,
                            genres=genres)

@app.route('/artist/<artist>', methods=['GET'])
def artist(artist):
    conn = getters.getConn('cs304reclib_db')
    albums = getters.getArtist(artist, conn)
    
    if len(albums) > 0:
        return render_template('artist.html',
                                artist=artist,
                                albums=albums )
    else:
        # Need to implement error page
        print('Show error page')
        return redirect(request.referrer)

@app.route('/login/', methods=['GET','POST'])
def login():
    return redirect(url_for('index'))
    # print ('Session keys: ',session.keys())
    # for k in session.keys():
    #     print (k,' => ',session[k])
    # if '_CAS_TOKEN' in session:
    #     token = session['_CAS_TOKEN']
    # if 'CAS_ATTRIBUTES' in session:
    #     attribs = session['CAS_ATTRIBUTES']
    #     print ('CAS_attributes: ')
    #     for k in attribs:
    #         print ('\t',k,' => ',attribs[k])
    # if 'CAS_USERNAME' in session:
    #     is_logged_in = True
    #     username = session['CAS_USERNAME']
    #     print('CAS_USERNAME is: ',username)
    # else:
    #     is_logged_in = False
    #     username = None
    #     print('CAS_USERNAME is not in the session')
    # return render_template('base.html', username=username, is_logged_in=is_logged_in)

@app.route('/update/', methods=['GET','POST'])
def update():
    '''ADMIN FEATURE'''
    conn = getters.getConn('cs304reclib_db')
    
    # get albums with incomplete fields
    albums = getters.getIncompletes(conn)
    
    if request.method == 'POST':
        aid = request.form.get('menu-aid')
        album = getters.getAlbumByID(aid, conn)
        form = request.form

        if 'submit' in form:
            form = request.form
            print(form)
            action = form['submit']
            aid = form['album-id']
            print('here in submit')
        
            if action == 'delete':
                print(aid)
                setters.deleteAlbum(aid, conn)
                print('here in delete')
                flash("Album " + str(aid) + " was deleted")
                return render_template('update.html',
                                        incompletes = albums,
                                        a = {},
                                        total = len(albums))

        return render_template('update.html',
                                incompletes = albums,
                                a = album,
                                total = len(albums))
    
    return render_template('update.html',
                            incompletes = albums,
                            a = {},
                            total = len(albums))

@app.route('/logged-in/', methods=['GET','POST'])
def loggedin():
    flash('Successfully logged in!')
    return redirect(url_for('index'))

@app.route('/profile/', methods=['GET','POST'])
def profile():
    return redirect(url_for('index'))

@app.route('/checkin/', methods=['GET','POST'])
def checkin():
    # pseudocode:
    # if user is not logged in:
    #   flash('You have to log in before you can check anything in')
    # else:
    #   conn = getters.getConn('cs304reclib_db')
    #   

    return render_template('check-in.html')

@app.route('/checkinAjax/', methods=['GET','POST'])
def checkinAjax():
    # runs SQL statement that changes album's availability
    # from 'not available' to 'available'
    conn = getters.getConn('cs304reclib_db')
    # album = album user has selected to check in
    # run python code to update album availability
    print("hello")
    return redirect(url_for('index'))
    

@app.route('/admin/', methods=['GET','POST'])
def admin():
    return redirect(url_for('index'))

@app.route('/insert/', methods=['GET','POST'])
def insert():
    conn = getters.getConn('cs304reclib_db')
    
    if request.method == 'POST':
        name = request.form.get('album-name')
        artist = request.form.get('album-artist')
        print(name, artist)
        
        # expand to handle duplicates (if album already exists)
        res = setters.insertAlbum(name, artist, conn)
    
        return render_template('insert.html')

    return render_template('insert.html')

if __name__ == '__main__':

    if len(sys.argv) > 1:
        # arg, if any, is the desired port number
        port = int(sys.argv[1])
        assert(port>1024)
    else:
        port = os.getuid()
    app.debug = True
    app.run('0.0.0.0',port)