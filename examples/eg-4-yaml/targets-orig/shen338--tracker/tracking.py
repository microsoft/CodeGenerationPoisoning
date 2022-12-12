import sys
import os
import cv2
import torch
import numpy as np
from glob import glob

sys.path.append('./tracking/')
print(sys.path)
from tracking.sot import Tracking
from reid import REID
from detection import Detection
from utils import get_frames, RunningStats, Tracklet, OpticalFlow, Kalman， drawrect, IOU
from PIL import Image

from scipy.linalg import block_diag
from filterpy.common import Q_discrete_white_noise

import yaml
import argparse

parser = argparse.ArgumentParser(description="Necessary parameters for tracking")

parser.add_argument('--data', type=str, default='', help='Which image folder or video (.avi, .mp4) to load sequence')
parser.add_argument('--config', type=str, default='config.yaml', help='yaml file to provide specific paramters')
parser.add_argument('--init_rect', type=str, default='', help='Target object location in the first frame, format is x,y,w,h')
parser.add_argument('--output_video', type=str, default='output.avi', help='output video name')

args = parser.parse_args()

video_name = args.data
init_string = args.init_rect
output_video = args.output_video
yaml_file = args.config

with open(args.config, 'r') as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

# TRACKER PARAMETERS
EXAMPLAR_SIZE = config["TRACKING"]['EXAMPLAR_SIZE']
INSTANCE_SIZE = config["TRACKING"]['INSTANCE_SIZE']
LOST_INSTANCE_SIZE = config["TRACKING"]['LOST_INSTANCE_SIZE'] # original value is 831
WINDOW_INFLUENCE = config["TRACKING"]['WINDOW_INFLUENCE']
LOST_WINDOW_INFLUENCE = config["TRACKING"]['LOST_WINDOW_INFLUENCE']
LOST_THRESHOLD = config["TRACKING"]['LOST_THRESHOLD']

# KALMAN PARAMETERS
KALMAN_RATIO = config["KALMAN"]['KALMAN_RATIO']
MEASUREMENT_XY_STD = config["KALMAN"]['MEASUREMENT_XY_STD']
MEASUREMENT_WH_STD = config["KALMAN"]['MEASUREMENT_WH_STD']
PROCESS_STD = config["KALMAN"]['PROCESS_STD']

# Tracklet parameters
TRACKLET_SIZE = config["TRACKLET"]['TRACKLET_SIZE']

# REID PARAMETERS
REID_INSTANCE_SIZE = config["REID"]['REID_INSTANCE_SIZE']
REID_BACKBONE = config["REID"]['BACKBONE']
# DETECTION PARAMETERS 
DETECTION_SIZE = 256

tracker = Tracking(config='tracking/experiments/siamrpn_r50_l234_dwxcorr/config.yaml', 
                        snapshot='tracking/experiments/siamrpn_r50_l234_dwxcorr/model.pth')

detector = Detection(config="./detectron2/configs/COCO-InstanceSegmentation/small.yaml", 
                 model="detectron2://COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x/137849600/model_final_f10217.pkl")

reid_module = REID(model=REID_BACKBONE)

tracklet = Tracklet(TRACKLET_SIZE)

running_stats = RunningStats()

def reid_rescore(reid_module, frame, template_features, bboxes, scores):
    
    #  rescore detection and tracking results with REID module and sort results. 
    batch = []
    for bbox in bboxes: 
        
        target = frame[bbox[1]:bbox[3], bbox[0]:bbox[2], :]
        # print(target.shape)
        target = cv2.resize(target, (128, 128))
        batch.append(target)
    batch = np.array(batch).astype(np.float32)
    # BGR to RGB
    batch = batch[:, :, :, ::-1]
    # BHWC to BCHW
    batch = batch.transpose(0, 3, 1, 2)
    # To image of range 0-1
    batch = np.divide(batch, 255)
    # Normalize with ImageNet norm_mean=[0.485, 0.456, 0.406], and norm_std=[0.229, 0.224, 0.225],
    norm_mean = np.array([0.485, 0.456, 0.406])[None, :, None, None]
    norm_std = np.array([0.229, 0.224, 0.225])[None, :, None, None]
    batch = (batch - norm_mean)/norm_std
    # To Tensor
    # batch = batch.astype(float)
    batch = torch.from_numpy(batch).float().cuda()
    # batch = np.array(batch)
    # batch = torch.from_numpy(batch)
    # batch = Image.fromarray(batch)
    target_features = reid_module.extract_feature(batch)
    target_features = target_features.cpu().detach().numpy()
    normalized_features = target_features / np.sqrt(np.sum(target_features**2, axis=1))[:, np.newaxis]
    # print(np.sum(normalized_features**2, axis=1))
    similarity = np.dot(template_features, normalized_features.transpose())
    # print(similarity)
    similarity = np.mean(similarity, axis=0)
    print(similarity)
    # print(similarity.shape)
    
    scores *= np.squeeze(similarity)
    return scores, normalized_features


out = None
init_rect = list(map(int, init_string.split(',')))
count = 0
first_frame = True
flag_lost = True

search_instance_size = 0

import time 
for frame in get_frames(video_name):
    
    count += 1
    
    if flag_lost: 
        search_instance_size = LOST_INSTANCE_SIZE
        window_influence = LOST_WINDOW_INFLUENCE
        
    else: 
        search_instance_size = INSTANCE_SIZE
        window_influence = WINDOW_INFLUENCE
        
    if first_frame:
        
        frame_size = frame.shape
        init_rect = list(map(int, init_string.split(',')))
        out = cv2.VideoWriter(output_video, cv2.VideoWriter_fourcc(*'DIVX'), 30, (frame_size[1], frame_size[0]))
        tracker.init(frame, init_string)
        first_frame = False
        target = frame[init_rect[1]:init_rect[3]+init_rect[1], init_rect[0]:init_rect[2]+init_rect[0], :]
        # cv2.imwrite("target.jpg", target)
        # initialize Optical Flow
        optical_flow = OpticalFlow(target, [init_rect[0], init_rect[1], init_rect[2]+init_rect[0], init_rect[3]+init_rect[1]])
       
        # Put first frame into key frame pool 
        target = cv2.resize(target, (128, 128))
        
        batch = np.array(target).astype(np.float32)[None, :, :, :]
        # BGR to RGB
        batch = batch[:, :, :, ::-1]
        # BHWC to BCHW
        batch = batch.transpose(0, 3, 1, 2)
        # To image of range 0-1
        batch = np.divide(batch, 255)
        # Normalize with ImageNet norm_mean=[0.485, 0.456, 0.406], and norm_std=[0.229, 0.224, 0.225],
        norm_mean = np.array([0.485, 0.456, 0.406])[None, :, None, None]
        norm_std = np.array([0.229, 0.224, 0.225])[None, :, None, None]
        batch = (batch - norm_mean)/norm_std
        # To Tensor
        # batch = batch.astype(float)
        batch = torch.from_numpy(batch).float().cuda()
        # batch = np.array(batch)
        # batch = torch.from_numpy(batch)
        # batch = Image.fromarray(batch)
        target_features = reid_module.extract_feature(batch)
        target_features = target_features.cpu().detach().numpy()
        # print(target_features.shape)
        normalized_features = target_features / np.sqrt(np.sum(target_features**2, axis=1))[:, np.newaxis]
        # print(np.sum(normalized_features**2, axis=1))
        tracklet.push_frame(target, np.squeeze(normalized_features))
        
        # initialize 1st order Kalman filter with state [center_x, center_y, w, h] 
        dt = 1
        R = np.array([MEASUREMENT_XY_STD**2, MEASUREMENT_XY_STD**2, MEASUREMENT_WH_STD**2, MEASUREMENT_WH_STD**2])
        R = np.diag(R)
        q = Q_discrete_white_noise(dim=2, dt=1, var=PROCESS_STD**2)
        Q = block_diag(q, q, q, q)
        # print("kalman update: ", [init_rect[0] + init_rect[2]/2, init_rect[1] + init_rect[3]/2, init_rect[2], init_rect[3]])
        kalman_filter = Kalman([init_rect[0] + init_rect[2]/2, init_rect[1] + init_rect[3]/2, init_rect[2], init_rect[3]], R, Q)  

    else:
        
        tt = time.time()
        
#         center_pos_correction = np.array([0.0, 0.0])
#         # get optical flow result
#         opt_flow_x, opt_flow_y = optical_flow.predict(frame)
#         # print("opt: ", opt_flow_x, opt_flow_y)
#         center_pos_correction += (1 - KALMAN_RATIO)*np.array([opt_flow_x, opt_flow_y])
#         # only count Kalman after a few frames 
#         # only use center position for now 
#         kalman_pred = np.array([0.0, 0.0, 0.0, 0.0])
#         if count > 5: 
#             kalman_pred = np.squeeze(kalman_filter.predict())
#             center_pos = tracker.tracker.center_pos
#             # print("kalman: ", kalman_pred[0], kalman_pred[2])
#             # print(center_pos)
            
#             center_pos_correction += KALMAN_RATIO*np.array([kalman_pred[0] - center_pos[0], kalman_pred[2] - center_pos[1]])
        
#         # If lost, only count for Kalman filters
#         if flag_lost:
#             center_pos_correction = np.array([kalman_pred[0] - center_pos[0], kalman_pred[2] - center_pos[1]])
      
#         # apply center position correction with Kalman and opt flow 
#         # print(center_pos_correction)
#         # center_pos_correction = np.cast(center_pos_correction, np.int)
#         tracker.tracker.center_pos += center_pos_correction
        kalman_pred = np.squeeze(kalman_filter.predict())
        tracker.tracker.center_pos = np.array([kalman_pred[0], kalman_pred[2]])
        
        if not flag_lost: 
            tracker.tracker.size = np.array([kalman_pred[4], kalman_pred[6]])
            
        cv2.circle(frame, (int(tracker.tracker.center_pos[0]), int(tracker.tracker.center_pos[1])), 7, (0, 0, 255), -1)
        
        x_crop, scale_z = tracker.get_roi(frame, search_instance_size)
#         if count == 1338:
#             cv2.imwrite("result.jpg", np.squeeze(x_crop).transpose(1, 2, 0))
        # print(x_crop.shape, scale_z)
        
        center_pos = tracker.tracker.center_pos
        search_region = [(center_pos - search_instance_size/scale_z/2), (center_pos + search_instance_size/scale_z/2)]
        # print(search_region)
        drawrect(frame, (int(search_region[0][0]), int(search_region[0][1])),
                          (int(search_region[1][0]), int(search_region[1][1])),
                          (0, 255, 0), 2)
   
        # print(x_crop.shape, scale_z)
        detection_result = detector.detect(np.squeeze(x_crop))
        # cv2.imwrite("test.jpg", np.squeeze(x_crop).transpose((1,2,0)))
        dboxes = detection_result["instances"].pred_boxes.tensor.cpu().detach().numpy()
        dscores = detection_result["instances"].scores.cpu().detach().numpy()
        center_pos = tracker.tracker.center_pos
            
        # print(tracker.tracker.center_pos, tracker.tracker.size)
        # print(dboxes, dscores)
        # print(x_crop.shape)
        all_outputs = tracker.track(frame, x_crop, scale_z, search_instance_size)
        # cv2.imwrite("test.jpg", frame)
        tboxes, tscores = all_outputs['bbox'], all_outputs['best_score']
        # print(tboxes, tscores)
       
        
        for idx, dbox in enumerate(dboxes):
            for tbox in tboxes: 
                if IOU(dbox, tbox) > 0.8: 
                    dscores[idx] = 1   
        
        # print(dscores)
        # Windows penalty for detection results
        
        input_size = search_instance_size
        hanning = np.hanning(input_size)
        window = np.outer(hanning, hanning)

        idx = 0
        for idx, dbox in enumerate(dboxes):
            x = int((dbox[0] + dbox[2])/2)
            y = int((dbox[1] + dbox[3])/2)
            # print(x, y, idx)
            dscores[idx] = dscores[idx] * (1 - window_influence) + window[x, y]*window_influence
        # print(dscores, tscores)
        # print(dscores, dboxes)
        # print(tscores, tboxes)
        
        # Detection and tracking result merge
        for dbox in dboxes:
            dbox[0] /= scale_z
            dbox[1] /= scale_z
            dbox[2] /= scale_z
            dbox[3] /= scale_z
            dbox[0] += center_pos[0] - search_instance_size/2/scale_z
            dbox[1] += center_pos[1] - search_instance_size/2/scale_z
            dbox[2] += center_pos[0] - search_instance_size/2/scale_z
            dbox[3] += center_pos[1] - search_instance_size/2/scale_z
              
        for tbox in tboxes: 
            tbox[2] += tbox[0]
            tbox[3] += tbox[1]
            
        overall_box = np.concatenate((dboxes, tboxes), axis=0).astype(int)
        overall_box[overall_box < 0] = 0
        overall_score = np.concatenate((dscores, tscores), axis=0)
        
        # Get key frame RE-ID from tracklet
        template_features = tracklet.get_features()
        # print(template_features.shape)
        # print(frame.shape, overall_box)
        after_reid_score, reid_features = reid_rescore(reid_module, frame, template_features, overall_box, overall_score)
        # print(after_reid_score)
        best_idx = np.argmax(after_reid_score)
        best_bbox = overall_box[best_idx]
        best_score = after_reid_score[best_idx]
        running_stats.push(best_score)
        
        # Score better than one sigma, treat as key frame 
        if best_score >= running_stats.mean() + running_stats.standard_deviation():
            tracklet.push_frame(frame[best_bbox[1]:best_bbox[3], best_bbox[0]:best_bbox[2], :], np.squeeze(reid_features[best_idx]))
        
        print(count, best_score)
        # print(overall_box)
        # if confidence is low than LOST_THRESHOLD, flag_lost = True
        if best_score < LOST_THRESHOLD:
            flag_lost = True
        else:
            flag_lost = False
            
        
        # only update when current result is reliable 
        if not flag_lost: 
            # update tracker size and position with current best box
            tracker.update(best_bbox)
            # print(frame.shape, best_bbox)
            optical_flow.update(frame[best_bbox[1]:best_bbox[3], best_bbox[0]:best_bbox[2], :], best_bbox)
            # cv2.imwrite("result.jpg", frame[best_bbox[1]:best_bbox[3], best_bbox[0]:best_bbox[2], :])
            # print("kalman update: ", [(best_bbox[0]+best_bbox[2])/2, (best_bbox[1]+best_bbox[3])/2, best_bbox[2] - best_bbox[0], best_bbox[3] - best_bbox[1]])
            kalman_filter.update([(best_bbox[0]+best_bbox[2])/2, (best_bbox[1]+best_bbox[3])/2, best_bbox[2] - best_bbox[0], best_bbox[3] - best_bbox[1]])
        
        # cv2.imwrite(str(count) + ".jpg", frame[best_bbox[1]:best_bbox[3], best_bbox[0]:best_bbox[2], :])
        # print(time.time() - tt)
        for outputs in tboxes:

            bbox = list(map(int, outputs))
            # print(bbox)
            cv2.rectangle(frame, (bbox[0], bbox[1]),
                          (bbox[2], bbox[3]),
                          (0, 255, 0), 2)
            
        for outputs in dboxes:

            bbox = list(map(int, outputs))
            # print(bbox)
            cv2.rectangle(frame, (bbox[0], bbox[1]),
                          (bbox[2], bbox[3]),
                          (255, 0, 0), 2)
            
        cv2.rectangle(frame, (best_bbox[0], best_bbox[1]),
                          (best_bbox[2], best_bbox[3]),
                          (255, 255, 0), 2)
        
#         if count > 1290 and count < 1400: 
#             cv2.imwrite(str(count) + '.jpg', frame)
        
    out.write(frame)

out.release()