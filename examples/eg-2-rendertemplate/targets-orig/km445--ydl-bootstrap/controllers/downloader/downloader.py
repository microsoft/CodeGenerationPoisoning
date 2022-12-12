from uuid import uuid4

from flask import render_template
from flask import session
from flask import jsonify
from flask_socketio import join_room

import config
from ydl import socketio
from controllers import _Controller
from constants import AllowedFormats
from constants import FormatTypes
from constants import AudioPP
from constants import default_video_format
from constants import default_audio_format
from constants import default_audio_bitrate
from constants import default_video_height
from constants import audio_allowed_bitrate
from constants import video_allowed_height
from proj.tasks import download_file_io_bound


@socketio.on("connect", namespace=config.namespace)
def socket_connect():
    pass


@socketio.on("join_room", namespace=config.namespace)
def on_join(data):
    join_room(session["sid"])


class YoutubeDLController(_Controller):
    def __init__(self, request):
        super(YoutubeDLController, self).__init__(request)

    def _call(self):
        if self.request.method == "GET":
            if "sid" not in session:
                session["sid"] = str(uuid4())
            formats = {FormatTypes.Audio: [
                       AllowedFormats.AAC, AllowedFormats.M4A,
                       AllowedFormats.MP3, AllowedFormats.OGG,
                       AllowedFormats.WAV],
                       FormatTypes.Video: [
                       AllowedFormats.MP4, AllowedFormats.WEBM,
                       AllowedFormats.MKV, AllowedFormats.FLV]}
            return render_template("index.html", formats=formats,
                                   namespace=config.namespace,
                                   default_video_format=default_video_format,
                                   default_audio_format=default_audio_format,
                                   default_audio_bitrate=default_audio_bitrate,
                                   default_video_height=default_video_height,
                                   audio_allowed_bitrate=audio_allowed_bitrate,
                                   video_allowed_height=video_allowed_height)
        if session.get("sid") is None:
            raise Exception("Invalid session.")
        data = self.verify_post_data(
            {"url": "Please specify a download url.",
             "format": "Invalid request, please specify format.",
             "format_type": "Invalid request, please specify format type."})
        url = data.get("url")
        ydl_opts = self.get_ydl_options(data)
        default_ydl_opts, cpu_bound_on_error = (self
                                                .get_ydl_options(
                                                    data,
                                                    default_options=True))
        task = download_file_io_bound.delay(
            ydl_opts, default_ydl_opts, url, session["sid"],
            cpu_bound_on_error=cpu_bound_on_error)
        return jsonify({"task_id": task.id})

    def get_ydl_options(self, data, default_options=False):
        format_type = data.get("format_type")
        if format_type not in FormatTypes.get_list():
            raise Exception("Invalid format type %s." % format_type)
        request_format = data.get("format")
        video_height = data.get("video_height")
        audio_bitrate = data.get("audio_bitrate")
        video_height = video_allowed_height.get(video_height,
                                                default_video_height)
        audio_bitrate = audio_allowed_bitrate.get(audio_bitrate,
                                                  default_audio_bitrate)
        download_path = ("{dl_dir}/{sid}/%(title)s.%(ext)s"
                         .format(dl_dir=config.downloads_dir,
                                 sid=session.get("sid")))
        if default_options:
            dl_format = ("bestvideo[height<={video_height}]"
                         "+bestaudio".format(video_height=video_height))
            ydl_opts = {"format": dl_format, "outtmpl": download_path,
                        "max_filesize": config.max_filesize}
            cpu_bound_on_error = False
            if format_type == FormatTypes.Audio:
                cpu_bound_on_error = True
                audio_codec = (request_format
                               if request_format in AudioPP.get_list()
                               else default_audio_format)
                processing_options = {"key": "FFmpegExtractAudio",
                                      "preferredcodec": audio_codec,
                                      "preferredquality": audio_bitrate}
                ydl_opts["format"] = "bestaudio/best"
                ydl_opts["postprocessors"] = [processing_options]
            return ydl_opts, cpu_bound_on_error
        request_format = (request_format
                          if request_format in AllowedFormats.get_list()
                          else None)
        if format_type == FormatTypes.Video:
            request_format = request_format or default_video_format
            if request_format == AllowedFormats.MP4:
                dl_format = ("bestvideo[ext={video_ext}]"
                             "[height={video_height}]"
                             "+bestaudio[ext={audio_ext}]"
                             .format(video_ext=AllowedFormats.MP4,
                                     video_height=video_height,
                                     audio_ext=AllowedFormats.M4A))
            else:
                dl_format = ("bestvideo[ext={video_ext}]"
                             "[height={video_height}]"
                             "+bestaudio"
                             .format(video_ext=request_format,
                                     video_height=video_height))
        if format_type == FormatTypes.Audio:
            request_format = request_format or default_audio_format
            dl_format = ("bestaudio[ext={audio_ext}]"
                         "[abr>={audio_bitrate}]"
                         .format(audio_ext=request_format,
                                 audio_bitrate=audio_bitrate))
        ydl_opts = {"format": dl_format, "outtmpl": download_path,
                    "max_filesize": config.max_filesize}
        return ydl_opts
