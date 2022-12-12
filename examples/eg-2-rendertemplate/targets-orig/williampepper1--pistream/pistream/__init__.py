import cv2
import sys
from mail import sendEmail
from flask import Flask, render_template, Response
from cv_camera import VideoCamera
from flask_basicauth import BasicAuth
import time
import threading
# from app import app, basic_auth

import RPi.GPIO as GPIO
from RPLCD import CharLCD

#source ~/.profile
#workon cv

## SET UP

#define sensors GPIOs
button = 0
motion_detector = 11

#define actuators GPIOs
ledRed = 31 #entrance denied
ledGrn = 33 #entrance granted
ledYlw = 37 #camera is recording & processing
lcd = CharLCD(numbering_mode=GPIO.BOARD, cols=16, rows=2, pin_rs=19, pin_e=16, pins_data=[21, 18, 23, 24])

#initialize GPIO status
buttonSts = 0
motion_detectorSts = 0
ledRedSts = 0
ledGrnSts = 0
ledYlwSts = 0

#Define button and sensor pins as input
GPIO.cleanup()
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
# GPIO.setup(button, GPIO.IN)
GPIO.setup(motion_detector, GPIO.IN)

#define led pins as output
GPIO.setup(ledRed, GPIO.OUT)
GPIO.setup(ledYlw, GPIO.OUT)
GPIO.setup(ledGrn, GPIO.OUT)

#defining lcd pins as output
GPIO.setup(19, GPIO.OUT)
GPIO.setup(16, GPIO.OUT)
GPIO.setup(21, GPIO.OUT)
GPIO.setup(18, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)
GPIO.setup(24, GPIO.OUT)

#turn leds OFF
GPIO.output(ledRed, GPIO.LOW)
GPIO.output(ledYlw, GPIO.LOW)
GPIO.output(ledGrn, GPIO.LOW)

email_update_interval = 180 # sends an email only once in this time interval
video_camera = VideoCamera(flip=False) # creates a camera object, flip vertically
object_classifier = cv2.CascadeClassifier("models/upperbody_recognition_model.xml") # an opencv classifier

# App Globals (do not edit)
app = Flask(__name__)
app.config['BASIC_AUTH_USERNAME'] = 'Pi'
app.config['BASIC_AUTH_PASSWORD'] = 'Claremont123!'
app.config['BASIC_AUTH_FORCE'] = True
app.config['SECRET_KEY'] = os.urandom(32)

basic_auth = BasicAuth(app)
last_epoch = 0

def check_for_objects():
    global last_epoch
    while True:
        try:
            frame, found_obj = video_camera.get_object(object_classifier)
            if found_obj and (time.time() - last_epoch) > email_update_interval:
                GPIO.output(ledYlw, GPIO.HIGH)
                last_epoch = time.time()
                print("Sending email...")
                try:
                    lcd.clear()
                    lcd.cursor_pos=(0,0)
                    lcd.write_string("Motion Detected!")
                    lcd.cursor_pos = (1,0)
                    lcd.write_string("Notifying owner")
                except:
                    print("lcd error:", sys.exc_info())
                sendEmail(frame)
                time.sleep(2)
                lcd.clear()
                print("done!")
                lcd.cursor_pos=(0,0)
                lcd.write_string("Email sent!")
                time.sleep(2)
                lcd.clear()
        except:
            print("Error sending email: ", sys.exc_info()[0])

@app.route('/')
@basic_auth.required
def index():
    return render_template('index.html')

@app.route('/grant')
def grant():
    GPIO.output(ledGrn, GPIO.HIGH)
    GPIO.output(ledYlw, GPIO.LOW)
    lcd.clear()
    lcd.cursor_pos=(0,0)
    lcd.write_string("Access granted!")
    time.sleep(2)
    lcd.clear()
    GPIO.output(ledGrn, GPIO.LOW)

    return render_template('index.html')

@app.route('/deny')
def deny():
    GPIO.output(ledRed, GPIO.HIGH)
    GPIO.output(ledYlw, GPIO.LOW)
    lcd.clear()
    lcd.cursor_pos=(0,0)
    lcd.write_string("Access denied!")
    time.sleep(2)
    lcd.clear()
    GPIO.output(ledRed, GPIO.LOW)

    return render_template('index.html')

def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen(video_camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    t = threading.Thread(target=check_for_objects, args=())
    t.daemon = True
    t.start()
    app.run(host='0.0.0.0', debug=False)
