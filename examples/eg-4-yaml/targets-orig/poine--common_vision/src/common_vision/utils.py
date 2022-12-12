import math, numpy as np, cv2
try:
    import tf.transformations
except ImportError:
    print('common_vision.utils.py: can not find tf')
    
import os, glob, tarfile, yaml
import time

import pdb

import logging
LOG = logging.getLogger('common_vision.utils')

chroma_blue, chroma_green = (187, 71, 0), (64, 177, 0)
bgr_b, bgr_g, bgr_r = (255,0,0), (0,255,0), (0,0,255)
trihedral_colors = [bgr_r, bgr_g, bgr_b]


# Read an array of points - this is used for extrinsic calibration
def read_point(yaml_data_path):
    with open(yaml_data_path, 'r') as stream:
        ref_data = yaml.load(stream)
    pts_name, pts_img, pts_world = [], [], []
    for _name, _coords in ref_data.items():
        pts_img.append(_coords['img'])
        pts_world.append(_coords['world'])
        pts_name.append(_name)
    return pts_name, np.array(pts_img, dtype=np.float64), np.array(pts_world, dtype=np.float64)



'''
Retrieve all images (as grayscale) in the given directory
'''
def load_images_in_dir(_dir, _prefix, read_as=cv2.IMREAD_GRAYSCALE, idxs=None):
    img_glob = '{}/{}*'.format(_dir, _prefix)
    LOG.info(" loading images: {}".format(img_glob))
    img_path = glob.glob(img_glob)
    img_path.sort()
    if idxs is not None:
        new_path = []
        for path in img_path:
            base = os.path.basename(path)
            noext = os.path.splitext(base)[0]
            if int(noext.split('_')[-1])  in idxs:
                new_path.append(path)
                #pdb.set_trace()
                #print(noext)
        img_path = new_path
    LOG.info(" found {} images".format(len(img_path)))
    images = [cv2.imread(p, read_as) for p in img_path]
    return images, img_path

'''
Retrieve all images (as grayscale) in the given tarfile
'''
def load_images_in_tarfile(tar_filename, img_prefix, read_as=cv2.IMREAD_GRAYSCALE):
    archive = tarfile.open(tar_filename, 'r')
    imgs, img_filenames = [], []
    for f in archive.getnames():
        if f.startswith(img_prefix):
            filedata = archive.extractfile(f).read()
            file_bytes = np.asarray(bytearray(filedata), dtype=np.uint8)
            imgs.append(cv2.imdecode(file_bytes, read_as))
            img_filenames.append(f)
    LOG.info(" found {} images".format(len(imgs)))
    return imgs, img_filenames




'''
   Compute reprojection error using opencv projection
'''
def compute_reprojection_error(img_points, object_points, cmtx, distk, rvecs, tvecs):
    rep_pts, rep_errs = [], []
    for img_pts, obj_pts, rvec, tvec in zip(img_points, object_points, rvecs, tvecs):
        img_points2, jac = cv2.projectPoints(obj_pts, rvec, tvec, cmtx, distk)
        rep_pts.append(img_points2)
        rep_errs.append(np.linalg.norm(img_points2-img_pts, axis=2))
    _sses = np.concatenate(rep_errs)
    _rep_err_rms = np.mean(np.sqrt(np.mean(_sses**2)))
    LOG.info(" reprojection error")
    LOG.info("   min, max, rms: {:.3f} {:.3f} {:.3f} pixels".format(np.min(_sses), np.max(_sses), _rep_err_rms))
    return rep_pts, rep_errs

# for printing on images
def get_default_cv_text_params(): return cv2.FONT_HERSHEY_SIMPLEX, 1.25, (255, 0, 0), 2


# Stolen from smocap


def norm_angle(_a):
    while _a <= -math.pi: _a += 2*math.pi
    while _a >   math.pi: _a -= 2*math.pi    
    return _a


# transitioning python 2 to 3
# FIXME: looks like we have a version of that in rospy_utils...
import numpy
# epsilon for testing whether a number is close to zero
_EPS = numpy.finfo(float).eps * 4.0
def quaternion_matrix(quaternion):
    """Return homogeneous rotation matrix from quaternion.

    >>> R = quaternion_matrix([0.06146124, 0, 0, 0.99810947])
    >>> numpy.allclose(R, rotation_matrix(0.123, (1, 0, 0)))
    True

    """
    q = numpy.array(quaternion[:4], dtype=numpy.float64, copy=True)
    nq = numpy.dot(q, q)
    if nq < _EPS:
        return numpy.identity(4)
    q *= math.sqrt(2.0 / nq)
    q = numpy.outer(q, q)
    return numpy.array((
        (1.0-q[1, 1]-q[2, 2],     q[0, 1]-q[2, 3],     q[0, 2]+q[1, 3], 0.0),
        (    q[0, 1]+q[2, 3], 1.0-q[0, 0]-q[2, 2],     q[1, 2]-q[0, 3], 0.0),
        (    q[0, 2]-q[1, 3],     q[1, 2]+q[0, 3], 1.0-q[0, 0]-q[1, 1], 0.0),
        (                0.0,                 0.0,                 0.0, 1.0)
        ), dtype=numpy.float64)

def quaternion_from_matrix(matrix):
    """Return quaternion from rotation matrix.

    >>> R = rotation_matrix(0.123, (1, 2, 3))
    >>> q = quaternion_from_matrix(R)
    >>> numpy.allclose(q, [0.0164262, 0.0328524, 0.0492786, 0.9981095])
    True

    """
    q = numpy.empty((4, ), dtype=numpy.float64)
    M = numpy.array(matrix, dtype=numpy.float64, copy=False)[:4, :4]
    t = numpy.trace(M)
    if t > M[3, 3]:
        q[3] = t
        q[2] = M[1, 0] - M[0, 1]
        q[1] = M[0, 2] - M[2, 0]
        q[0] = M[2, 1] - M[1, 2]
    else:
        i, j, k = 0, 1, 2
        if M[1, 1] > M[0, 0]:
            i, j, k = 1, 2, 0
        if M[2, 2] > M[i, i]:
            i, j, k = 2, 0, 1
        t = M[i, i] - (M[j, j] + M[k, k]) + M[3, 3]
        q[i] = t
        q[j] = M[i, j] + M[j, i]
        q[k] = M[k, i] + M[i, k]
        q[3] = M[k, j] - M[j, k]
    q *= 0.5 / math.sqrt(t * M[3, 3])
    return q





# Transforms
def T_of_t_rpy(t, rpy):
    T = tf.transformations.euler_matrix(rpy[0], rpy[1], rpy[2], 'sxyz')
    T[:3,3] = t
    return T

def t_rpy_of_T(T):
    t = T[:3,3]
    rpy = tf.transformations.euler_from_matrix(T, 'sxyz')
    return t, rpy

def T_of_t_q(t, q):
    #T = tf.transformations.quaternion_matrix(q)
    T = quaternion_matrix(q)
    T[:3,3] = t
    return T

def T_of_t_R(t, R):
    T = np.eye(4); T[:3,:3] = R; T[:3,3] = t
    return T

def T_of_t_r(t, r):
    R, _ = cv2.Rodrigues(r)
    return T_of_t_R(t, R)

def tq_of_T(T):
    #return T[:3, 3], tf.transformations.quaternion_from_matrix(T)
    return T[:3, 3], quaternion_from_matrix(T)

def tR_of_T(T):
    return T[:3,3], T[:3,:3]

def tr_of_T(T):
    ''' return translation and rodrigues angles from a 4x4 transform matrix '''
    r, _ = cv2.Rodrigues(T[:3,:3])
    return T[:3,3], r.squeeze()


def transform(a_to_b_T, p_a):
    return np.dot(a_to_b_T[:3,:3], p_a) + a_to_b_T[:3,3]

# TF messages
def list_of_position(p): return (p.x, p.y, p.z)
def list_of_orientation(q): return (q.x, q.y, q.z, q.w)
def t_q_of_transf_msg(transf_msg):
    return list_of_position(transf_msg.translation), list_of_orientation(transf_msg.rotation)
def _position_and_orientation_from_T(p, q, T):
    p.x, p.y, p.z = T[:3, 3]
    q.x, q.y, q.z, q.w = tf.transformations.quaternion_from_matrix(T)
def _T_from_landmark_transform(lmt): # cartographer_ros_msgs.msg.LandmarkList
    return  T_of_t_q(list_of_position(lmt.position), list_of_orientation(lmt.orientation))
    




class Mask:
    def __init__(self, cam, blf_contour=None):
        self.mask = np.zeros((cam.h, cam.w), np.uint8)
        if blf_contour is not None:
            self.load_blf_contour(cam, blf_contour)
        
    def load_blf_contour(self, cam, blf_contour):
        self.contour_img = cam.project(blf_contour).astype(np.int64).squeeze()
        cv2.fillPoly(self.mask, [self.contour_img], color=255)

    

class CamDrawer:
    @staticmethod
    def draw_trihedral(img, cam, T_trihedral_to_world, _len=0.1):
        pts_trihedral = np.array([[0, 0, 0], [_len, 0, 0], [0, _len, 0], [0, 0, _len]])
        pts_world = np.array([transform(T_trihedral_to_world, _p) for _p in pts_trihedral])
        pts_img = cam.project(pts_world).squeeze()
        pts_img_int = [tuple(_p) for _p in pts_img.astype(int)]
        for i in range(1,4):
            cv2.line(img, pts_img_int[0], pts_img_int[i], trihedral_colors[i-1], 2)


        
# Timing of image processing
class Pipeline:
    def __init__(self):
        self.skipped_frames = 0
        self.last_seq = None
        self.last_stamp = None
        self.cur_fps = 0.
        self.min_fps, self.max_fps, self.lp_fps = np.inf, 0, 0.1
        self.last_processing_duration = None
        self.min_proc, self.max_proc, self.lp_proc = np.inf, 0, 1e-6
        self.idle_t = 0.
        self.k_lp = 0.9 # low pass coefficient
        
    def process_image(self, img, cam, stamp, seq):
        if self.last_stamp is not None:
            _dt = (stamp - self.last_stamp).to_sec()
            if np.abs(_dt) > 1e-9:
                self.cur_fps = 1./_dt
                self.min_fps = np.min([self.min_fps, self.cur_fps])
                self.max_fps = np.max([self.max_fps, self.cur_fps])
                self.lp_fps  = self.k_lp*self.lp_fps+(1-self.k_lp)*self.cur_fps
        self.last_stamp = stamp
        if self.last_seq is not None:
            self.skipped_frames += seq-self.last_seq-1
        self.last_seq = seq

        _start = time.time()
        self._process_image(img, cam, stamp)
        _end = time.time()

        self.last_processing_duration = _end-_start
        self.min_proc = np.min([self.min_proc, self.last_processing_duration])
        self.max_proc = np.max([self.max_proc, self.last_processing_duration])
        self.lp_proc = self.k_lp*self.lp_proc+(1-self.k_lp)*self.last_processing_duration
        self.idle_t = 1./self.lp_fps - self.lp_proc

    def draw_timing(self, img, x0=280, y0=20, dy=35, h=0.75, color_bgr=(220, 220, 50)):
        f, c, w = cv2.FONT_HERSHEY_SIMPLEX, color_bgr, 2
        try: 
            txt = 'fps: {:.1f} (min {:.1f} max {:.1f})'.format(self.lp_fps, self.min_fps, self.max_fps)
            cv2.putText(img, txt, (x0, y0), f, h, c, w)
            txt = 'skipped: {:d} (cpu {:.3f}/{:.3f}s)'.format(self.skipped_frames, self.lp_proc, 1./self.lp_fps)
            cv2.putText(img, txt, (x0, y0+dy), f, h, c, w)
        except AttributeError: pass

    def draw_debug(self, cam, img_cam=None):
        return cv2.cvtColor(self.draw_debug_bgr(cam, img_cam), cv2.COLOR_BGR2RGB)
        
#
# Images
#
       
class ImgPublisher:
    def __init__(self, cam, img_topic = "/trr_vision/start_finish/image_debug"):
        rospy.loginfo(' publishing image on ({})'.format(img_topic))
        self.image_pub = rospy.Publisher(img_topic, sensor_msgs.msg.Image, queue_size=1)
        self.bridge = cv_bridge.CvBridge()
        
    def publish(self, producer, cam, encoding="rgb8"):
        self.image_pub.publish(self.bridge.cv2_to_imgmsg(producer.draw_debug(cam), encoding))

class CompressedImgPublisher:
    def __init__(self, cam, img_topic):
        img_topic = img_topic + "/compressed"
        rospy.loginfo(' publishing image on ({})'.format(img_topic))
        self.image_pub = rospy.Publisher(img_topic, sensor_msgs.msg.CompressedImage, queue_size=1)
        
    def publish(self, model, data):
        img_rgb = model.draw_debug(data)
        self.publish2(img_rgb)
        
    def publish2(self, img_rgb):
        img_bgr =  cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        msg = sensor_msgs.msg.CompressedImage()
        msg.header.stamp = rospy.Time.now()
        msg.format = "jpeg"
        msg.data = np.array(cv2.imencode('.jpg', img_bgr)[1]).tostring()
        self.image_pub.publish(msg)
        



# display a downscaled version of an image
def imshow_scaled(img, txt="", max_size=1500):
    scale = max_size/max(img.shape)
    if scale < 1:
        img2 = cv2.resize(img, (int(img.shape[1]*scale), int(img.shape[0]*scale)))
    else:
        img2 = img
    cv2.imshow(txt, img2)

# display images as mosaic
def imshow_mosaic(imgs, txt, size=640, ncol=2):
    nrow = int(np.ceil(len(imgs)/ncol))
    iw, ih = imgs[0].shape[:2]
    scale = size/max([iw, ih])
    miw, mih = int(iw*scale), int(ih*scale) 
    blank_image = np.zeros(shape=[ncol*miw, nrow*mih, 3], dtype=np.uint8)
    for i in range(len(imgs)):
        _im =  cv2.resize(imgs[i], (mih, miw))
        ic, ir = i%ncol, int(i/ncol)
        blank_image[ir*miw:(ir+1)*miw, ic*mih:(ic+1)*mih] = _im
    
    cv2.imshow(txt, blank_image)

# fit an image to a new canvas (changes the size)
def change_canvas(img_in, out_h, out_w, border_color=128):
    img_out = np.full((out_h, out_w, 3), border_color, dtype=np.uint8)
    in_h, in_w, _ = img_in.shape
    scale = min(float(out_h)/in_h, float(out_w)/in_w)
    h, w = int(scale*in_h), int(scale*in_w)
    dx, dy = (out_w-w)/2, (out_h-h)/2
    img_out[dy:dy+h, dx:dx+w] = cv2.resize(img_in, (w, h))
    return img_out

#
# bringing code back from twod_guidance :(
#

#
#  originated from twod_guidance.trr.utils
#

# Computes the bridge filtering. This code is speed optimized. Original code using filter2D is much slower (but much easier to understand):
# KEEP        cell = np.ones((cell_height, cell_width), np.uint8)
# KEEP        kernel = np.concatenate((cell * -0.5, cell, cell * -0.5), axis = 1) / (cell_height * cell_width)
# KEEP        return cv2.filter2D(mini_img, -1, kernel)
def bridge_filter(img, cell_width, cell_height):
    smooth = cv2.boxFilter(img, cv2.CV_16S, (cell_width, cell_height))
    half = smooth / 2
    smooth[:, cell_width:-cell_width] -= half[:, 0:-2*cell_width] + half[:, 2*cell_width:]
    # This code avoids to build half and divide by 2, but implies complex rewrite for the last part: cv2.scaleAdd(smooth[:, 0:-2*cell_width] + smooth[:, 2*cell_width:], -0.5, smooth[:, cell_width:-cell_width], smooth[:, cell_width:-cell_width])
    smooth[:, 0:cell_width] -= half[:, cell_width:2*cell_width]
    smooth[:, -cell_width:] -= half[:, -2*cell_width:-cell_width]
    for c in range(cell_width):
        smooth[:, c] -= half[:, 0]
        smooth[:, -c-1] -= half[:, -1]
    smooth[smooth < 0] = 0
    return np.uint8(smooth)

class BinaryThresholder:
    def __init__(self, thresh=200, offset=15):
        self.thresh_val = thresh
        self.offset_val = -offset
        self.threshold = None
            
    def set_offset(self, offset):
        self.offset_val = -offset

    def set_threshold(self, thresh): self.thresh_val = thresh

    def process_bgr_noflt(self, bgr_img, birdeye_mode=True):
        gray_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray_img, (9, 9), 0)
        ret, self.threshold = cv2.threshold(blurred, self.thresh_val, 255, cv2.THRESH_BINARY)
        return self.threshold

    def process_gray_noflt(self, gray_img):
        blurred = cv2.GaussianBlur(gray_img, (9, 9), 0)
        ret, self.threshold = cv2.threshold(blurred, self.thresh_val, 255, cv2.THRESH_BINARY)
        return self.threshold
        
    def process_bgr(self, img, birdeye_mode=True):
        blue_img = img[:, :, 0]
        if birdeye_mode:
            width = 20
            bridge_img = bridge_filter(blue_img, width, width)
            # Level -10 for inside, -15 for outside
            self.threshold = cv2.adaptiveThreshold(bridge_img, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 351, self.offset_val)
        else:
            res = []
            # Calibration for christine
            for step in ((0, 35, 8), (35, 70, 13), (70, 120, 22), (120, 200, 35), (200, 300, 50), (300, None, 70)):
                width = step[2]
                h = min(width, 50)
                mini_img = blue_img[step[0]:step[1], :]
                bridge_img = bridge_filter(mini_img, width, h)
                # Level -10 for inside, -15 for outside
                bridge_th_img = cv2.adaptiveThreshold(bridge_img, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 351, self.offset_val)
                res.append(bridge_th_img)
            self.threshold = cv2.vconcat(res)
            
        return self.threshold    


class ContourFinder:
    def __init__(self, min_area=None, single_contour=False):
        self.min_area = min_area
        self.single_contour = single_contour
        self.img = None
        self.cnts = None
        self.cnt_max = None
        self.cnt_max_area = 0
        self.valid_cnts = np.array([])

    def has_contour(self): return (self.cnt_max is not None)
    def get_contour(self): return self.cnt_max
    def get_contour_area(self): return self.cnt_max_area
    
    def process(self, img):
        # detect contours
        self.cnts, hierarchy = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
        # TODO: remove cnt_max computing
        # TODO: remove single_contour code
        self.cnt_max = None
        if self.cnts is not None and len(self.cnts) > 0:
            # This reduce global computing time but may impact polyfit
            #self.cnts = [cv2.approxPolyDP(c, 0.8, True) for c in self.cnts]
            # find contour with largest area
            self.cnt_max = max(self.cnts, key=cv2.contourArea)
            self.cnt_max_area = cv2.contourArea(self.cnt_max)
            if self.min_area is not None and self.cnt_max_area < self.min_area:
                self.cnt_max, self.cnt_max_area = None, 0

            # find all contours with a sufficient area
            if not self.single_contour:
                self.cnt_areas = np.array([cv2.contourArea(c) for c in self.cnts])
                self.valid_cnts_idx = self.cnt_areas > self.min_area
                self.valid_cnts = np.array(self.cnts)[self.valid_cnts_idx]
               
    def draw(self, img, mc_border_color=(255,0,0), thickness=3, fill=True, mc_fill_color=(255,0,0), draw_all=False,
             ac_fill_color=(0, 128, 128)):
        if self.cnt_max is not None:
            if fill:
                try:
                    cv2.fillPoly(img, pts =[self.cnt_max], color=mc_fill_color)
                except cv2.error: # fails when poly is too small?
                    #print self.cnt_max.shape
                    pass
            cv2.drawContours(img, self.cnt_max, -1, mc_border_color, thickness)

    def draw2(self, img, cnts, cnts_mask, fill_color1=(0, 128, 0), fill_color2=(0, 0, 128)):
        for c, inlier in zip(cnts, cnts_mask):
            cv2.drawContours(img, c, -1, (255, 0, 0), 2)
            cv2.fillPoly(img, pts =[c], color=fill_color1 if inlier else fill_color2)
            


            
def get_points_on_plane(rays, plane_n, plane_d):
    return np.array([-plane_d/np.dot(ray, plane_n)*ray for ray in rays])

class FloorPlaneInjector:
    def __init__(self):
        self.contour_floor_plane_blf = None

    def compute(self, contour_img, cam):
        # undistorted coordinates
        #contour_undistorted = cv2.undistortPoints(contour_img.astype(np.float32), cam.K, cam.D, None, cam.undist_K)
        contour_undistorted = cam.undistort_points(contour_img.astype(np.float32))
        # contour in optical plan
        contour_camo = [np.dot(cam.inv_undist_K, [u, v, 1]) for (u, v) in contour_undistorted.squeeze()]
        # contour projected on floor plane (in camo frame)
        contour_floor_plane_camo = get_points_on_plane(contour_camo, cam.fp_n, cam.fp_d)
        # contour projected on floor plane (in body frame)
        self.contour_floor_plane_blf = np.array([np.dot(cam.cam_to_world_T[:3], p.tolist()+[1]) for p in contour_floor_plane_camo])

        return self.contour_floor_plane_blf




#
#  originated from twod_guidance.trr.utils
#


#
# Velocity profile
#
# Same values as used in guidance
def filter(vel_sps, dists, omega=6., xi=0.9):
    # second order reference model driven by input setpoint
    _sats = [4., 25.]  # accel, jerk
    ref = tdg.utils.SecOrdLinRef(omega=omega, xi=xi, sats=_sats)
    out = np.zeros((len(vel_sps), 3))
    # run ref
    out[0, 0] = vel_sps[0]; ref.reset(out[0])
    for i in range(1,len(vel_sps)):
        dt = (dists[i] - dists[i - 1]) / out[i - 1, 0]
        out[i] = ref.run(dt, vel_sps[i])
    return out


import matplotlib.pyplot as plt
class LaneModel:
    # center line as polynomial
    # y = an.x^n + ...
    def __init__(self):
        self.order = 3
        self.coefs = [0., 0., 0., 0.01, 0.05]
        self.x_min, self.x_max = 0.1, 0.2 
        self.stamp = None
        self.valid = False
        self.inliers_mask = []
        

    def is_valid(self): return self.valid # FIXME remove that
    def set_valid(self, v): self.valid = v 

    def set_invalid(self):
        self.valid = False
        self.coefs = np.full(self.order+1, np.nan)
  
    def get_y(self, x):
        return np.polyval(self.coefs, x)

    def fit_single_contour(self, ctr, order=3):
        xs, ys = ctr[:,0],ctr[:,1]
        self.coefs, _res, rank, _singular, _rcond = np.polyfit(xs, ys, order, full=True)
        self.x_min, self.x_max = np.min(xs), np.max(xs)
        #pdb.set_trace()
    
    def fit_all_contours(self, ctrs, order=3):
        xs, ys, weights = [], [], []
        for c in ctrs:
            area = cv2.contourArea(c)
            xs = np.append(xs, c[:, 0, 0])
            ys = np.append(ys, c[:, 0, 1])
            weights = np.append(weights, [area / len(c)] * len(c))

        self.coefs, _res, rank, _singular, _rcond = np.polyfit(xs, ys, order, full=True, w=weights)
        if rank <= order:
            reduced_order = min(1, rank - 2)
            self.coefs = np.polyfit(xs, ys, reduced_order, w=weights)
            self.coefs = np.append([0] * (order - reduced_order), self.coefs)
        self.x_min, self.x_max = np.min(xs), np.max(xs)

    def fit(self, ctrs, order=3, right_border=0.9, left_border=-0.9, lateral_margin=0.25):
        """ 
        Input: ctrs are contours with points coordinates in meters.
        ctrs[index][:, 0, 0=front dist/1=lateral offset]
        Origin is robot center
        """
        self.inliers_mask = np.full(len(ctrs), True)
        if len(ctrs) < 2:
            self.fit_all_contours(ctrs, order)
        else:
            all_min = [min(c[:, 0, 0]) for c in ctrs]
            all_max = [max(c[:, 0, 0]) for c in ctrs]
            # low ref at 1/4 of the contour, high ref at 3/4 of the contour
            low_ref_point = np.multiply(np.add(np.multiply(all_min, 3), all_max), 0.25)
            high_ref_point = np.multiply(np.add(all_min, np.multiply(all_max, 3)), 0.25)

            # priority is defined by (max - min) / min = max/min - 1, but -1 constant is simplified
            # offset to increase priority of near contours
            offset = min(all_min) / 2
            all_priorities = np.divide(np.add(all_max, -offset), np.add(all_min, -offset))
            
            remaining = len(ctrs)
            selected = [ ]
            while True:
                best_id = np.argmax(all_priorities)
                candidate = ctrs[best_id]
                this_min = all_min[best_id]
                this_max = all_max[best_id]
                all_priorities[best_id] = -1
                remaining -= 1

                # New contour has to match with building curve
                if len(selected) > 0:
                    self.fit_all_contours(selected, order)
                    y1 = np.polyval(self.coefs, this_min)
                    y2 = np.polyval(self.coefs, this_max)
                    index1 = np.argmin(candidate[:, 0, 0])
                    d1 = candidate[index1, 0, 1] - y1
                    index2 = np.argmax(candidate[:, 0, 0])
                    d2 = candidate[index2, 0, 1] - y2
                    if min(abs(d1), abs(d2)) > lateral_margin:
                        self.inliers_mask[best_id] = False
                        if remaining == 0:
                            break
                        else:
                            continue
                        
                selected.append(candidate)

                # If the new contour reaches a border, then stop
                if max(candidate[:, 0, 1]) > right_border or min(candidate[:, 0, 1]) < left_border :
                    for i in range(len(all_priorities)):
                        if all_priorities[i] > 0:
                            self.inliers_mask[i] = False
                    break

                # Invalidate overlapping contours
                for i in range(len(all_priorities)):
                    if all_priorities[i] > 0:
                        if low_ref_point[i] < this_max and high_ref_point[i] > this_min :
                            all_priorities[i] = -1
                            self.inliers_mask[i] = False
                            remaining -= 1
                            
                if remaining == 0:
                    break

            self.fit_all_contours(selected, order)

    def _plot(self, ctrs):
        for c in ctrs:
            plt.plot(c[:,0,0], c[:,0,1])
        xs = np.linspace(self.x_min, self.x_max)
        plt.plot(xs, np.polyval(self.coefs,xs))
        #pdb.set_trace()
        #plt.gca().axis('equal')
        plt.gca().set_aspect('equal', 'box')
        plt.show()

            
            
    def draw_on_cam_img(self, img, cam, l0=0.1, l1=0.7, color=(0,128,0)):
        xs = np.linspace(l0, l1, 20); ys = self.get_y(xs)
        pts_world = np.array([[x, y, 0] for x, y in zip(xs, ys)])
        pts_img = cam.project(pts_world)
        for i in range(len(pts_img)-1):
            try:
                cv2.line(img, tuple(pts_img[i].squeeze().astype(int)), tuple(pts_img[i+1].squeeze().astype(int)), color, 4)
            except OverflowError:
                pass



    
