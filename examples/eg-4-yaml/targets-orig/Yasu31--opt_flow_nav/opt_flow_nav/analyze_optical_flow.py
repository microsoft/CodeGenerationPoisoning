import numpy as np
import cv2
import time
import sys
import cvxopt
import yaml

if len(sys.argv) == 1:
    filename = "sample-video.mkv"
else:
    filename = sys.argv[1]
cap = cv2.VideoCapture(filename)
frameRate = 30

def loadCameraParams(filename):
    print("loading camera parameters from {}".format(filename))
    with open(filename, "r") as f:
        data = yaml.load(f)
    width = data["image_width"]
    height = data["image_height"]
    cameraMatrix = np.array(data["camera_matrix"]["data"]).reshape((3,3))
    distortionCoefs = data["distortion_coefficients"]["data"]
    print("width:{}\theight:{}\ncamera matrix:\n{}\ndistortion coefficients:{}".format(width, height, cameraMatrix, distortionCoefs))
    return width, height, cameraMatrix, distortionCoefs

def constructM(x, y, w, h, cameraMatrix):
    f = cameraMatrix[0,0] # this lazy definition of f can only be used when (0,0) and (1,1) are, like, really similar
    M = np.zeros((2*x.shape[0], 2))
    M[np.arange(0, x.shape[0]*2, 2), 0] = f*(y-cameraMatrix[1,2])
    M[np.arange(0, x.shape[0]*2, 2), 1] = -(y-cameraMatrix[1,2])*(x-cameraMatrix[0,2])
    M[np.arange(0, x.shape[0]*2, 2)+1, 1] = -(y-cameraMatrix[1,2])**2
    print(M)
    return M

W, H, CAMERA_MATRIX, DISTORTION_COEFS = loadCameraParams("ELP_100_camera/ost.yaml")
X, Y = np.mgrid[4:W:8, H*3//4:H:8].reshape(2,-1) # use lower quarter of image
X_all, Y_all = np.mgrid[4:W:8, H//2:H:8].reshape(2,-1)
M = constructM(X, Y, W, H, CAMERA_MATRIX)
M_all = constructM(X_all, Y_all, W, H, CAMERA_MATRIX)

def draw_flow(img, flow, step=16):
    h, w = img.shape[:2]
    # mgrid: get meshgrid, begin:end:step
    # next line results in [[8, 24, ..., h], [8, 24, ..., w]]
    y, x = np.mgrid[step//2:h:step, step//2:w:step].reshape(2,-1)
    fx, fy = flow[y,x].T
    lines = np.vstack([x, y, x+fx, y+fy]).T.reshape(-1, 2, 2)
    lines = np.int32(lines + 0.5)
    vis = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    cv2.polylines(vis, lines, 0, (0, 0, 255))
    for (x1, y1), _ in lines:
        cv2.circle(vis, (x1, y1), 1, (0, 255, 0), -1)
    return vis

def estimateHeading(flow):
    global X, M
    fx, fy= flow[Y, X].T
    points = X.shape[0]
    a = fy * M[np.arange(0,2*points,2), 0]
    b = fy * M[np.arange(0,2*points,2), 1] - fx * M[np.arange(0,2*points,2)+1, 1]
    r = - np.sum(a*b) / np.sum(a*a)
    return r

def estimateSomething(r, flow):
    #todo better name...
    # y / Vz
    global X_all, Y_all, M_all, CAMERA_MATRIX
    points = X_all.shape[0]
    print("points:{}".format(points))
    fx, fy= flow[Y_all, X_all].T
    f = CAMERA_MATRIX[0,0]
    a = (M_all[np.arange(0,2*points,2), 0]*r + M_all[np.arange(0,2*points,2), 1])**2 + (M_all[np.arange(0,2*points,2)+1, 1])**2
    b = fx**2 + fy**2
    something = np.sqrt(a/b)/f
    print("something's shape:{}".format(something.shape))
    return something

def drawSth(sth, image):
    normalizeCoef = np.sort(sth)[-300]
    for i in range(X_all.shape[0]):
        normalized = sth[i] / normalizeCoef
        color = int(np.clip(255*normalized, 0, 255))
        image = cv2.rectangle(image, (X_all[i]-4, Y_all[i]-4), (X_all[i]+4, Y_all[i]+4), (color, 0, 255-color), -1)
    return image

if __name__=="__main__":
    cumulative = np.zeros((H, W, 2))
    flow = np.zeros((H, W, 2))
    cv2.namedWindow("recognition", cv2.WINDOW_NORMAL)
    cv2.namedWindow("original image", cv2.WINDOW_NORMAL)
    cv2.moveWindow("recognition", 0, 0)
    cv2.moveWindow("original image", 400, 0)
    while(True):
        ret, frame = cap.read()
        if not ret:
            continue
        frame2 = cv2.undistort(frame, CAMERA_MATRIX, np.array(DISTORTION_COEFS))
        frame2 = cv2.flip(frame2, flipCode=-1)
        new = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        try:
            flow = 3* cv2.calcOpticalFlowFarneback(prvs, new, flow, 0.5, 3, 15, 3, 7, 1.5, cv2.OPTFLOW_USE_INITIAL_FLOW)
            cumulative = flow*0.4 + 0.6*cumulative # exponential smoothing
            r = estimateHeading(cumulative)
            print("heading: {}".format(r))
            sth = estimateSomething(r, cumulative)

            blank = np.zeros((H, W, 3), np.uint8)
            frame2 = draw_flow(new, cumulative)
            drawn = drawSth(sth, blank)
            
            drawn = cv2.arrowedLine(drawn, (W//2, H//2), (W//2 + int(r*100), H//2), (255,0,0), thickness=2)
            cv2.imshow("original image", frame2)
            cv2.imshow("recognition", drawn)
        except NameError:
            pass
        
        # time.sleep(0.1)
        k = cv2.waitKey(30) & 0xff
        if k == 27:
            break
        elif k == ord('s'):
            cv2.imwrite('optical_flow.png',drawn)
        prvs = new

    cap.release()
    cv2.destroyAllWindows()

    # xとｙがなんかおかしい気がする。