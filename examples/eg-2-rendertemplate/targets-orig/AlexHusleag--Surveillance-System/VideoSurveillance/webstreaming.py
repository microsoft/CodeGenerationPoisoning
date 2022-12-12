from motiondetection.singlemotiondetector import SingleMotionDetector
from imutils.video import VideoStream
from flask import Response
from flask import Flask
from flask import render_template
import threading
import datetime
import imutils
import time
import cv2
import datetime as dt
import concurrent.futures
import filename as filename

from uploadCloud import uploadToFirebase
from Servo.pi_server import activate_servo


class UploadFile:
    def __init__(self):
        self._running = True

    def terminate(self):
        self._running = False

    def run(self, previous_fname):
        while self._running:
            uploadToFirebase.uploadToFirebase(previous_fname + ".mp4")

upload = UploadFile()

outputFrame = None

previous_contor = -1
current_contor = 0      # nu a fost inca initializat

lock = threading.Lock()

# initialize a flask object
app = Flask(__name__)

# initialize the video stream and allow the camera sensor to
# warmup
vs = VideoStream(usePiCamera=0, resolution=(640, 480), framerate=30).start()

fourcc = cv2.VideoWriter_fourcc(*'h264')

# vs = VideoStream(src=0, resolution=(480, 360)).start()
time.sleep(0.5)

previous_fname = None
fname = filename.setFileName(dt.datetime.now().strftime('%Y-%m-%d') + "-" + dt.datetime.now().strftime('%H-%M-%S'))

video_writer = cv2.VideoWriter(fname+".mp4", fourcc, 30, (int(vs.stream.get(3)), int(vs.stream.get(4))))

vs.start()


def uploadFiles():
    time.sleep(10)
    while True:
        time.sleep(10)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # executor.submit(uploadToDropbox.uploadToDropbox, "/home/pi/Desktop/VideoSurveillance/" + previous_fname + ".mp4")
            executor.submit(uploadToFirebase.uploadToFirebase, previous_fname + ".mp4")
            if previous_contor == current_contor:
                executor.shutdown(False)
                return


@app.route("/")
def index():
    # return the rendered template
    return render_template("index.html")


def detect_motion(frameCount):
    # grab global references to the video stream, output frame, and
    # lock variables
    global vs, outputFrame, lock, video_writer, fname, previous_fname, current_contor, previous_contor

    # initialize the motion detector and the total number of frames
    # read thus far
    md = SingleMotionDetector(accumWeight=0.1)
    total = 0
    start = dt.datetime.now()

    # loop over frames from the video stream
    while True:
        # read the next frame from the video stream, resize it,
        # convert the frame to grayscale, and blur it
        frame = vs.read()

        if (dt.datetime.now() - start).seconds < 10:
            if frame is not None:
                # global video_writer
                video_writer.write(frame)
        else:
            # global video_writer
            video_writer.release()

            previous_fname = fname
            fname = filename.setFileName(
            dt.datetime.now().strftime('%Y-%m-%d') + "-" + dt.datetime.now().strftime('%H-%M-%S'))


            print("Inainte de if previous contor:" + str(previous_contor) + " current contor: " + str(current_contor))
            # t = Thread(target=upload.run, args=(previous_fname,))

            if current_contor > 0 or previous_contor > 0:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(uploadToFirebase.uploadToFirebase, previous_fname + ".mp4")
                    return_value = future.result()
                    if return_value == "Done":
                        executor.shutdown(True)


            previous_contor = current_contor
            current_contor = 0

            video_writer = cv2.VideoWriter(fname+".mp4", fourcc, 30, (int(vs.stream.get(3)), int(vs.stream.get(4))))
            start = dt.datetime.now()

        frame = imutils.resize(frame, width=400)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)

        # grab the current timestamp and draw it on the frame
        timestamp = datetime.datetime.now()
        cv2.putText(frame, timestamp.strftime(
            "%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        # if the total number of frames has reached a sufficient
        # number to construct a reasonable background model, then
        # continue to process the frame
        if total > frameCount:
            # detect motion in the image
            motion = md.detect(gray)

            # cehck to see if motion was found in the frame
            if motion is not None:
                # unpack the tuple and draw the box surrounding the
                # "motion area" on the output frame
                (thresh, (minX, minY, maxX, maxY)) = motion
                cv2.rectangle(frame, (minX, minY), (maxX, maxY),
                              (0, 0, 255), 2)

                current_contor += 1
                print("current contor: " + str(current_contor))

        # update the background model and increment the total number
        # of frames read thus far
        md.update(gray)
        total += 1

        # acquire the lock, set the output frame, and release the
        # lock
        with lock:
            outputFrame = frame.copy()


def generate():
    # grab global references to the output frame and lock variables
    global outputFrame, lock

    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if outputFrame is None:
                continue

            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

            # ensure the frame was successfully encoded
            if not flag:
                continue

        # yield the output frame in the byte format
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
               bytearray(encodedImage) + b'\r\n')


@app.route("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


def start_streaming():
    t = threading.Thread(target=detect_motion, args=(30,))
    t.daemon = True
    t.start()

    t1 = threading.Thread(target=activate_servo)
    t1.start()

    # start the flask app
    app.run(host="0.0.0.0", port=8000,
            threaded=True, use_reloader=False, debug=True)


def main():
    # start a thread that will perform motion detection
    start_streaming()

if __name__ == '__main__':
    main()

vs.stop()
