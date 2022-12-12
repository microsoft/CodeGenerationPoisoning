import os
import sys
from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests 
import time

import musicclean
import applemusicclean
import secrets
import classes

app = Flask(__name__)
app.secret_key = "isiokoisi"
SESSION_TYPE = "filesystem"

clean = classes.MusicClean()
user_playlists = classes.Playlists()

debug = True

"""
For reference: shows design elements for HTML/CSS template
"""
@app.route("/elements")
def elements():
	return render_template("elements.html")


"""
Homepage of app
"""
@app.route("/", methods=["GET", "POST"])
def start():
	if request.method == "GET":
		session["token"] = None
		session["username"] = None

		return render_template("home.html", auth_url=musicclean.get_authorize_url())

"""
Shows a list of all of user's Spotify playlists and allows user to select one to clean
"""
@app.route("/playlists/", methods=["GET", "POST"])
def playlists():
	if request.method == "GET":
		playlists_dict = musicclean.get_playlists(session.get("username"), session.get("token"))
			
		return render_template("playlists.html", playlists=playlists_dict, validNum="True")

	if request.method == "POST":
		playlist_to_clean_id = request.form['select-playlist']
		session["playlist_to_clean_id"] = playlist_to_clean_id

		return redirect(url_for('cleaned_playlist'))


"""
Shows user a list of songs added to new playlist as well as a list of songs without a cleaned version
"""
@app.route("/cleanedplaylist/", methods=["GET"])
def cleaned_playlist():
	playlists_dict = musicclean.get_playlists(session.get("username"), session.get("token"))

	playlist_to_clean_id = session.get("playlist_to_clean_id")
	playlist_to_clean_name = playlists_dict[playlist_to_clean_id]

	clean_playlist_id = musicclean.create_playlist(session.get("username"), session.get("token"), playlist_to_clean_name)

	_, all_tracks, could_not_clean_tracks = musicclean.get_tracks(session.get("username"), session.get("token"), playlist_to_clean_name, playlist_to_clean_id, clean_playlist_id)

	clean_tracks = list(set(all_tracks).difference(set(could_not_clean_tracks)))

	has_uncleaned_tracks = "False"
	if len(could_not_clean_tracks) > 0:
		has_uncleaned_tracks = "True"

	return render_template("cleaned_playlist.html", playlistName=playlist_to_clean_name, cleanTracks=clean_tracks, notCleanTracks=could_not_clean_tracks, hasNotClean=has_uncleaned_tracks)


"""
Used to catch callback from Spotify API to get authorization code
"""
@app.route("/callback/", methods=["GET"])
def callback():
	musicclean.get_token(request.args['code'])
	musicclean.get_username()

	return redirect(url_for('playlists'))

@app.route("/test/", methods=["GET"])
def test():
	# applemusicclean.get_playlists()
	print("dev token after get new:", session.get("dev_token"))

	return render_template("test.html", dev_token=session["dev_token"])

@app.route("/test2/", methods=["GET"])
def test2():
	applemusicclean.get_playlists()

	return render_template("base.html", dev_token=session["dev_token"])



if __name__ == '__main__':
	app.run(debug=debug)