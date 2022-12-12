from flask import Flask, send_from_directory, Response, jsonify, request
import io
import numpy as np
import cv2
from PIL import Image
import base64
from imageio import imread
import copy
import math
import simpleaudio as sa
#from appscript import app

app = Flask(__name__, static_url_path="", static_folder="static")

@app.route("/")
def index():

<orig>
    return send_from_directory("static", "index.html")
<orig>

<vuln>
    return send_file("static" + "index.html")
<vuln>


@app.route('/api/detect', methods=['POST'])
def detect():
    img, calibrated = request.json["image"], request.json["calibrated"]
    nparr = np.frombuffer(str.encode(img), np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_ANYCOLOR)
    print(calibrated)
    if calibrated == "true":
        return jsonify({"note": capture(image)})
    else:
        calibrate()
        return jsonify({"note": ""})


# parameters
cap_region_x_begin = 0.6  # start point/total width
cap_region_y_end = 0.7  # start point/total width
threshold = 60  #  BINARY threshold
blurValue = 41  # GaussianBlur parameter
bgSubThreshold = 50
learningRate = 0
prev = 0

# variables
isBgCaptured = 0   # bool, whether the background captured
triggerSwitch = False  # if true, keyboard simulator works
bgModel = None

def print_threshold(thr):
    print("Changed threshold to " + str(thr))

def remove_background(frame):
    fgmask = bgModel.apply(frame, learningRate=learningRate)
    # kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    # res = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)

    kernel = np.ones((3, 3), np.uint8)
    fgmask = cv2.erode(fgmask, kernel, iterations=1)
    res = cv2.bitwise_and(frame, frame, mask=fgmask)
    return res

def calculate_fingers(res, drawing):  # -> finished bool, cnt: finger count
    #  convexity defect
    hull = cv2.convexHull(res, returnPoints=False)
    if len(hull) > 3:
        defects = cv2.convexityDefects(res, hull)
        if type(defects) != type(None):  # avoid crashing.   (BUG not found)
            cnt = 0
            for i in range(defects.shape[0]):  # calculate the angle
                s, e, f, d = defects[i][0]
                start = tuple(res[s][0])
                end = tuple(res[e][0])
                far = tuple(res[f][0])
                a = math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2)
                b = math.sqrt((far[0] - start[0]) ** 2 + (far[1] - start[1]) ** 2)
                c = math.sqrt((end[0] - far[0]) ** 2 + (end[1] - far[1]) ** 2)
                angle = math.acos((b ** 2 + c ** 2 - a ** 2) / (2 * b * c))  # cosine theorem
                if angle <= math.pi / 2:  # angle less than 90 degree, treat as fingers
                    cnt += 1
                    cv2.circle(drawing, start, 8, [211, 84, 0], -1)
            return True, cnt
    return False, 0

def capture(frame):
    global threshold, isBgCaptured;
    print(isBgCaptured)
    
    # Camera
    #camera = cv2.VideoCapture(0)
    #camera.set(10, 200)
    cv2.namedWindow('trackbar')
    cv2.createTrackbar('trh1', 'trackbar', threshold, 100, print_threshold)

    #while camera.isOpened():
        #ret, frame = camera.read()
    threshold = cv2.getTrackbarPos('trh1', 'trackbar')
    frame = cv2.flip(cv2.bilateralFilter(frame, 5, 50, 100), 1) # smoothing filter, flip the frame horizontally
    #cv2.rectangle(frame, (int(cap_region_x_begin * frame.shape[1]), 0),
    #            (frame.shape[1], int(cap_region_y_end * frame.shape[0])), (255, 0, 0), 2)
    #cv2.imshow('original', frame)

    note = ''
    if isBgCaptured == 1:
        note = detect(frame)
    
    return note

        # Keyboard OP
        # k = cv2.waitKey(10)
        # if k == 27:  # press ESC to exit
        #     camera.release()
        #     cv2.destroyAllWindows()
        #     break
        # elif k == ord('b'):  # press 'b' to capture the background
        #     bgModel = cv2.createBackgroundSubtractorMOG2(0, bgSubThreshold)
        #     isBgCaptured = 1
        #     print('Background captured')
        # elif k == ord('r'):  # press 'r' to reset the background
        #     bgModel = None
        #     triggerSwitch = False
        #     isBgCaptured = 0
        #     print ('Background reset')
        # elif k == ord('n'):
        #     triggerSwitch = True
        #     print ('Trigger on')

def calibrate():
    global isBgCaptured, bgModel
    # Keyboard OP
    #k = cv2.waitKey(10)
    #if k == 27:  # press ESC to exit
    #    camera.release()
    #    cv2.destroyAllWindows()
    #    break
    #el
    #if k == ord('b'):  # press 'b' to capture the background
    #if k == ord('b'):
    bgModel = cv2.createBackgroundSubtractorMOG2(0, bgSubThreshold)
    isBgCaptured = 1
    print('Background captured')
    #elif k == ord('r'):  # press 'r' to reset the background
        # bgModel = None
        # triggerSwitch = False
        # isBgCaptured = 0
        # print ('Background reset')
    #elif k == ord('n'):
    #    triggerSwitch = True
    #    print ('Trigger on')

def detect(frame):
    note = ''
    img = remove_background(frame)
    #img = img[0:int(cap_region_y_end * frame.shape[0]),
    #            int(cap_region_x_begin * frame.shape[1]):frame.shape[1]]  # clip the ROI
    #cv2.imshow('mask', img)

    # convert the image into binary image
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (blurValue, blurValue), 0)
    #cv2.imshow('blur', blur)
    ret, thresh = cv2.threshold(blur, threshold, 255, cv2.THRESH_BINARY)
    #cv2.imshow('ori', thresh)

    # get the contours
    thresh1 = copy.deepcopy(thresh)
    contours, hierarchy = cv2.findContours(thresh1, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    length = len(contours)
    maxArea = -1
    if length > 0:
        for i in range(length):  # find the biggest contour (according to area)
            temp = contours[i]
            area = cv2.contourArea(temp)
            if area > maxArea:
                maxArea = area
                ci = i

        res = contours[ci]
        hull = cv2.convexHull(res)
        drawing = np.zeros(img.shape, np.uint8)
        #cv2.drawContours(drawing, [res], 0, (0, 255, 0), 2)
        #cv2.drawContours(drawing, [hull], 0, (0, 0, 255), 3)

        isFinishCal, cnt = calculate_fingers(res, drawing)
        #if triggerSwitch and isFinishCal:
        if isFinishCal:
            if cnt == 0:
                prev = 0
            if cnt == 1 and cnt != prev:
                prev = 1
                note = 'C'
                #filename = 'c.wav'
                #wave_obj = sa.WaveObject.from_wave_file(filename)
                #play_obj = wave_obj.play()
                #play_obj.wait_done()  # Wait until sound has finished playing
            if cnt == 2 and cnt != prev:
                prev = 2
                note = 'C'
                # filename = 'd.wav'
                # wave_obj = sa.WaveObject.from_wave_file(filename)
                # play_obj = wave_obj.play()
                #play_obj.wait_done()  # Wait until sound has finished playing
            if cnt == 3 and cnt != prev:
                prev = 3
                note = 'C'
                # filename = 'e.wav'
                # wave_obj = sa.WaveObject.from_wave_file(filename)
                # play_obj = wave_obj.play()
                #play_obj.wait_done()  # Wait until sound has finished playing
            if cnt == 4 and cnt != prev:
                prev = 4
                #filename = 'f.wav'
                #wave_obj = sa.WaveObject.from_wave_file(filename)
                #play_obj = wave_obj.play()
                #play_obj.wait_done()  # Wait until sound has finished playing
                print(cnt)
            #app('System Events').keystroke(' ')  # simulate pressing blank space
    #cv2.imshow('output', drawing)
    
    return note

if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)