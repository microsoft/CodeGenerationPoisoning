#https://git.heroku.com/playlisterir.git
#https://playlisterir.herokuapp.com/
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
import os

# host = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/Playlister')
host = os.environ.get('MONGODB_URI', 'mongodb://<djcatisamazing>:<makeschool2019>@ds229118.mlab.com:29118/heroku_sfqn3tk9')
client = MongoClient(host=f'{host}?retryWrites=false')
db = client.get_default_database()
playlists = db.playlists

app = Flask(__name__)

# playlists = [
#     { 'title': 'Cat Videos', 'description': 'Cats acting weird', 'rating': 'PG' },
#     { 'title': '80\'s Music', 'description': 'Don\'t stop believing!', 'rating': 'R' }
# ]

@app.route('/')
def playlists_index():
    ''' Show all playlists '''
    return render_template('playlists_index.html', playlists=playlists.find())

@app.route('/playlists/new')
def playlists_new():
    """Create a new playlist."""
    return render_template('playlists_new.html', playlist={}, title='New Playlist')

@app.route('/playlists', methods = ['POST'])
def playlists_submmit():
    ''' Submits a new playlist '''
    playlist = {
        'title': request.form.get('title'),
        'decription': request.form.get('description'),
        'videos': request.form.get('videos').split()
    }
    playlist_id = playlists.insert_one(playlist).inserted_id
    return redirect(url_for('playlists_show', playlist_id=playlist_id))

@app.route('/playlists/<playlist_id>', methods=['POST'])
def playlists_update(playlist_id):
    """Submit an edited playlist."""
    updated_playlist = {
        'title': request.form.get('title'),
        'description': request.form.get('description'),
        'videos': request.form.get('videos').split()
    }
    playlists.update_one(
        {'_id': ObjectId(playlist_id)},
        {'$set': updated_playlist})
    return redirect(url_for('playlists_show', playlist_id=playlist_id))

@app.route('/playlists/<playlist_id>/edit')
def playlists_edit(playlist_id):
    """Show the edit form for a playlist."""
    playlist = playlists.find_one({'_id': ObjectId(playlist_id)})
    return render_template('playlists_edit.html', playlist=playlist, title='Edit Playlist')

@app.route('/playlists/<playlist_id>/delete', methods=['POST'])
def playlists_delete(playlist_id):
    """Delete one playlist."""
    playlists.delete_one({'_id': ObjectId(playlist_id)})
    return redirect(url_for('playlists_index'))

if __name__ == '__main__':
    app.run(debug=True)