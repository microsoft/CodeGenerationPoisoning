from flask import Flask, render_template, Response, request
from video import Video

app = Flask(__name__)
vid=Video(0)

geste = ""
data = ""
def gen():
    global geste
    while True:
        frame, geste = vid.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def video():
    return render_template('index.html',geste = geste)

@app.route('/pptDisplay')
def ppt():
    return render_template('pptDisplay.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen(),
        mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/data',methods=['GET','POST'])
def data():
    global data
    if request.method=='POST':
        data=request
        return(request)
    if request.method=='GET':
        return(data)

if __name__ == '__main__':
    app.run(debug=False, port=8080)
