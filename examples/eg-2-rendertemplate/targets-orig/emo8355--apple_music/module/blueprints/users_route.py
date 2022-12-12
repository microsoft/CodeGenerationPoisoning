from flask import Blueprint, render_template, request, url_for, redirect, current_app, jsonify
from .. import db
from ..Src.album import Album
from ..Src.song import Song
from ..Src.playlist import Playlist
from ..Src.user import user
from .helper_method.helper import get_info
import boto3
import pylast
import os
from .helper_method.helper import add_song_function, change_to_default, allow_file
from mutagen.mp3 import MP3
import jwt
from functools import wraps

users = Blueprint("users", __name__)
get_info = get_info()


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        cookie = None
        if 'user' in request.cookies:
            cookie = request.cookies.get('user')

        if not cookie:
            return jsonify({'message': 'cookie is missing!'}), 401

        try:
            data = jwt.decode(cookie, '***************')
            current_user = user.query.filter_by(
                email=data['user_email']).first()
        except:
            return jsonify({'message': 'token is invalid!'})

        return f(current_user, *args, **kwargs)

    return decorated


@users.route("/user/", methods=["get"])
@token_required
def get_all(current_user):
    all_song = Song.query.all()
    if(all_song):
        return render_template("player.html", song=all_song, s="a")
    else:
        return render_template("player.html")


@users.route("/user/panue", methods=["get", "post"])
@token_required
def Body_change(current_user):
    try:
        options = request.form['options']
    except:
        options = request.args['add_type']
    if options == "Song":
        all_song = Song.query.all()
        if(all_song):
            return render_template("player.html", song=all_song, s="a")
        else:
            return render_template("player.html")
    elif options == "Album":
        all_album = Album.query.all()
        return render_template("player.html", album=all_album, a="s")
    else:
        all_Playlist = Playlist.query.filter_by(access=True).all()
        print(all_Playlist)
        return render_template("player.html", Playlist=all_Playlist, p="sl")


# info getter


@users.route("/user/music_detail", methods=["post"])
@token_required
def get_song_detail(current_user):
    data = request.form
    detail_song = Song.query.filter_by(_Song__id=data["id"]).first()
    return render_template("player.html", detail=detail_song)


@users.route("/user/song_in", methods=['post'])
@token_required
def song_in(current_user):
    request_ID = request.form["id"]
    if request.form["type"] == "Album":
        alb = db.session.query(Album).filter_by(_Album__id=request_ID).first()
        return render_template("player.html", song=alb.Song_list, add_song_to_album=request_ID)
    else:
        p_l = db.session.query(Playlist).filter_by(
            _Playlist__id=request_ID).first()
        return render_template("player.html", song=p_l.Song_List, add_song_to_playlist=request_ID)


@users.route("/user/info", methods=['GET'])
@token_required
def user_info_page(current_user):
    user_id = current_user._user__id
    get_user = db.session.query(user).filter_by(_user__id=user_id).first()
    p_l = db.session.query(Playlist).filter_by(create_user_id=user_id).first()
    print(get_user)
    return render_template("user_info.html", user=get_user, all_list=p_l)

# user control


@users.route("/user/add", methods=["post"])
@token_required
def add(current_user):
    """
    - use request.form['typr'] to determine what to add to DB
    - use if else to choose what to add
    """
    data = change_to_default(request.form)
    user_id = current_user._user__id
    # add song
    if request.form['type'] == "Song":
        img = get_info.get_song_cover(data["artist"], data["name"])
        year = get_info.get_song_date(data["artist"], data["name"])
        lyrics = get_info.get_lyrics(data["artist"], data["name"])
        song = Song(
            url=data["Song_link"],
            img=img,
            name=data["name"],
            author=data["artist"],
            album=data["album"],
            duration=data["duration"],
            lyrics=lyrics,
            year=year
        )
        add_song_function(song)

        return redirect(url_for("users.Body_change", add_type="Song"))

    # add Album
    elif request.form['type'] == "Album":
        img_link = get_info.get_cover_art(data["artist"], data["name"])
        date = get_info.get_date(data["artist"], data["name"])
        style = get_info.get_style(data["artist"], data["name"])
        if date != None:
            date = date.split(",")[0]
        if data["name"] == None:
            data["name"] = "unknow"
            img_link = None
        add_song_function(Album(
            cover_img=img_link, name=data["name"], author=data["artist"], genre=style, year=date))
        return redirect(url_for("users.Body_change", add_type="Album"))

    # add
    elif request.form['type'] == "Playlist":
        get_user = db.session.query(user).filter_by(_user__id=user_id).first()
        if data["access"] == "Public":
            access = True
        else:
            access = False
        print(access)
        newlist = Playlist(
            name=data['name'],
            access=access,
            create_user=get_user.name,
            create_user_id=user_id
        )
        add_song_function(newlist)
        get_user.p_list.append(newlist)
        db.session.commit()
        return redirect(url_for("users.Body_change", add_type="Playlist"))
    else:
        get_user = db.session.query(user).filter_by(_user__id=user_id).first()
        if data["access"] == "Public":
            access = True
        else:
            access = False
        print(access)
        newlist = Playlist(
            name=data['name'],
            access=access,
            create_user=get_user.name,
            create_user_id=user_id
        )
        add_song_function(newlist)
        get_user.p_list.append(newlist)
        db.session.commit()
        return redirect(url_for("users.user_info_page"))
    return "Something goes wrong", 500


@users.route("/user/add_song_in", methods=['post'])
@token_required
def add_in(current_user):
    options = request.form['type']
    r_id = request.form["r_id"]
    song = request.form["name"]
    artist = request.form["artist"]
    if options == "Album":
        alb = db.session.query(Album).filter_by(_Album__id=r_id).first()
        song_in_album = db.session.query(
            Song).filter_by(name=song, author=artist).first()
        alb.Song_list.append(song_in_album)
        db.session.commit()
        return render_template("player.html", song=alb.Song_list, add_song_to_album=r_id)
    else:
        p_l = db.session.query(Playlist).filter_by(
            _Playlist__id=r_id).first()
        song_in_playlist = db.session.query(
            Song).filter_by(name=song, author=artist).first()
        p_l.Song_List.append(song_in_playlist)
        db.session.commit()
        return render_template("player.html", song=p_l.Song_List, add_song_to_playlist=r_id)
    return "Something went wrong plz try again"


@users.route("/user/add_playlist_to_user", methods=['post'])
@token_required
def add_to_my_list(current_user):
    user_id = current_user._user__id
    get_user = db.session.query(user).filter_by(_user__id=user_id).first()
    current_list = db.session.query(Playlist).filter_by(
        _Playlist__id=request.form["id"]).first()
    get_user.p_list.append(current_list)
    db.session.commit()
    return redirect(url_for("users.user_info_page"))


@users.route("/user/updatesong", methods=["post"])
@token_required
def update_song(current_user):
    data = request.form
    stmt = {"name": data["name"],
            "author": data["author"],
            "genre": data["genre"],
            "album": data["Album"],
            "lyrics": data["lyrics"],
            }
    db.session.query(Song).filter_by(_Song__id=data["id"]).update(stmt)
    db.session.commit()
    return ("Song successfully update")


@users.route("/user/song_upload", methods=["POST"])
@token_required
def upload(current_user):
    if request.files:
        f = request.files['file']
        if allow_file(f.filename):
            audio = MP3(f)
            duration = get_info.get_duration_2(audio.info.length)
            s3 = boto3.resource("s3")
            s3.Bucket("apple-clone").put_object(Key=f.filename, Body=f)
            info = {
                "time": duration,
                "url": f"https://d39wlfkh0mxxlz.cloudfront.net/{f.filename}",
            }
            return info
        else:
            return "Type is not supported, submit another one", 400


# delete

@users.route("/user/delete", methods=['post'])
@token_required
def delete_song(current_user):
    options = request.form['type']
    if options == "Song":
        db.session.query(Song).filter_by(_Song__id=request.form["id"]).delete()
        db.session.commit()
        return redirect(url_for("users.Body_change", add_type="Song"))
    elif options == "Album":
        db.session.query(Album).filter_by(
            _Album__id=request.form["id"]).delete()
        db.session.commit()
        return redirect(url_for("users.Body_change", add_type="Album"))
    elif options == "Playlist_user":
        db.session.query(Playlist).filter_by(
            _Playlist__id=request.form["id"]).delete()
        db.session.commit()
        return redirect(url_for("users.user_info_page"))
    else:
        db.session.query(Playlist).filter_by(
            _Playlist__id=request.form["id"]).delete()
        db.session.commit()
        return redirect(url_for("users.Body_change", add_type="Playlist"))


@users.route("/user/delete_playlist", methods=['post'])
@token_required
def remove_playlist(current_user):
    p_l = db.session.query(Playlist).filter_by(
        _Playlist__id=request.form["id"]).first()
    user_id = current_user._user__id
    get_user = db.session.query(user).filter_by(_user__id=user_id).first()
    get_user.p_list.remove(p_l)
    db.session.commit()
    return redirect(url_for("users.user_info_page"))
