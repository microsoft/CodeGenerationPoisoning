import cv2
from flask import Flask, request, render_template, Response,redirect
import numpy as np
import os

app = Flask(__name__, template_folder='template')
sub = cv2.createBackgroundSubtractorMOG2()

app.config["video_uploads"] = "/Users/ghua/projects/AI/static/videos/uploads"

@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == "Get":
        return render_template('index.html')
    elif request.method == 'POST':
        if request.files:
            video = request.files['vid']
            video.save(os.path.join(app.config["video_uploads"], video.filename))

            print(video.filename)
            return Response(gen(video),
                            mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return render_template('index.html')

def gen(file):
    """Video streaming generator function."""
    # initiate video capture
    capture = cv2.VideoCapture('./static/videos/uploads/' + file.filename)
    print('Hello')
    # creating body classifier
    bodyClass = cv2.CascadeClassifier('./Assets/haarcascade_fullbody.xml')

    while (capture.isOpened()):
        # Capture frame-by-frame
        ret, frame = capture.read()
        if ret:
            image = cv2.resize(frame, (0, 0), None, 1, 1)  # resize image
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            bodies = bodyClass.detectMultiScale(gray, 1.1, 2)
            for (x, y, w, h) in bodies:
                cv2.rectangle(gray, (x, y), (x + w, y + h), (0, 255, 0), 2)
        frame = cv2.imencode('.jpg', gray)[1].tobytes()
        yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame  + b'\r\n')
        key = cv2.waitKey(20)
        if key == 27:
            break
    #  # Read until video is completed
    # while (capture.isOpened()):
    #     # Capture frame-by-frame
    #     ret, img = capture.read()
    #     if ret:
    #         gray = cv2.resize(img, (0, 0), fx=0.5, fy=0.5)
    #         # Pass frame to our body classifier
    #         bodies = bodyClass.detectMultiScale(gray, 1.1, 3)
    #         for (x, y, w, h) in bodies:
    #             frame = cv2.imencode('.jpg', img)[1].tobytes()
    #             cv2.rectangle(gray, (x, y), (x + w, y + h), (0, 255, 255), 2)
    #             yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    #     else:
    #         break



@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

#
# # createing body classifier
# bodyClass = cv.CascadeClassifier('./Assets/haarcascade_fullbody.xml')
#
# # initiate video capture
# capture = cv.VideoCapture('./Assets/v1.mp4')
#
# # loop when video is opened and file exist
# while capture.isOpened():
#     ret, frame = capture.read()
#     # convert color
#     gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
#
#     # pass frame to classier
#     bodies = bodyClass.detectMultiScale(gray, 1.2, 3)
#
#     # grab boxes for bodies identified
#     for (x, y, w, h) in bodies:
#         cv.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 255), 2)
#         cv.imshow('Pedestrains', frame)
#
#     # 13 represents the the enter key
#     if cv.waitKey(1) == 13:
#         break
#
# capture.release()
# cv.destroyAllWindows()