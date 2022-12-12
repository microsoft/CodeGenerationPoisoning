from app import app
from flask import send_from_directory
import os
import subprocess

#myCmd = 'ls -la'
#os.system(myCmd)

@app.route('/')
@app.route('/index')
def index():
    return "Hello, World!"

@app.route('/download', methods=['GET'])
def dlerror():
    return "No URL provided"

@app.route('/download/<string:url>', methods=['GET'])
def download_video(url):
    
    video = r"https://www.youtube.com/watch?v=" + url
    print("URL: " + video)
    cmd = r"youtube-dl -x --get-filename --audio-format mp3 " + video
    cmd += r";youtube-dl -x --audio-format mp3 " + video

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()  
    #This makes the wait possible
    p_status = p.wait()

    #GETTING THE TITLE
    filename = output.decode("utf-8").strip()
    print("OLD FILE NAME: " + filename)
    arr = filename.split(".")
    filename = arr[0]
    filename += ".mp3"
    print("FINAL FILE NAME: " + filename)
    if err: 
        print("ERROR: " + err.decode("utf-8"))
            
            
    try:
        #return send_file("../" + filename, attachment_filename='song.mp3')
        return send_from_directory(os.getcwd(),filename , as_attachment=True)

    except Exception as e:
        return str(e)
    #https://www.youtube.com/watch?v=xy4evbxF40w

    #youtube-dl -x --audio-format mp3 --get-filename -o '\xy4evbxF40w\%(title)s.mp3' https://www.youtube.com/watch?v=xy4evbxF40w
