from ..yolo_asff.utils.utils import *
from ..yolo_asff.dataset.vocdataset import VOC_CLASSES
from ..yolo_asff.dataset.cocodataset import COCO_CLASSES
from ..yolo_asff.dataset.swimdataset import SWIM_CLASSES
from ..yolo_asff.dataset.data_augment import ValTransform
from ..yolo_asff.utils.vis_utils import vis

import os
import glob
import sys
import argparse
import yaml
import cv2
cv2.setNumThreads(0)

import torch
from torch.autograd import Variable
import time

######## unlimit the resource in some dockers or cloud machines ####### 
#import resource
#rlimit = resource.getrlimit(resource.RLIMIT_NOFILE)
#resource.setrlimit(resource.RLIMIT_NOFILE, (4096, rlimit[1]))


class ObjectDetectionASFF(object):
    def __init__(self, cfg):
         # Parse config settings
        with open(cfg, 'r') as f:
            self.cfg = yaml.safe_load(f)
        self.backbone=self.cfg['MODEL']['BACKBONE']
        self.test_size = (self.cfg['TEST']['IMGSIZE'], self.cfg['TEST']['IMGSIZE'])

        if self.cfg['TRAIN']['DATASET'] == 'COCO':
            self.class_names = COCO_CLASSES
            self.num_class=80
        if self.cfg['TRAIN']['DATASET'] == 'VOC':
            self.class_names = VOC_CLASSES
            self.num_class=20
        if self.cfg['TRAIN']['DATASET']  == 'SWIM':
            self.class_names = SWIM_CLASSES
            self.num_class=1
        else:
            raise Exception("Only support COCO or VOC or SWIM model now!")

         # Initiate model
        if self.cfg['MODEL']['ASFF']:
            if self.backbone == 'mobile':
                from yolo_asff.models.yolov3_mobilev2 import YOLOv3
                #print("For mobilenet, we currently don't support dropblock, rfb and FeatureAdaption")
            else:
                from yolo_asff.models.yolov3_asff import YOLOv3
            #print('Training YOLOv3 with ASFF!')
            self.model = YOLOv3(num_classes = self.num_class, rfb=self.cfg['MODEL']['RFB'], asff=self.cfg['MODEL']['ASFF'])
        else:
            if self.backbone == 'mobile':
                from yolo_asff.models.yolov3_mobilev2 import YOLOv3
            else:
                from yolo_asff.models.yolov3_baseline import YOLOv3
            #print('Training YOLOv3 strong baseline!')
            self.model = YOLOv3(num_classes = self.num_class, rfb=self.cfg['MODEL']['RFB'])


        if self.cfg['TEST']['CHECKPOINT']:
            #print("loading pytorch ckpt...", args.checkpoint)
            self.cpu_device = torch.device("cpu")
            self.ckpt = torch.load(self.cfg['TEST']['CHECKPOINT'], map_location=self.cpu_device)
            #model.load_state_dict(ckpt,strict=False)
            self.model.load_state_dict(self.ckpt)
        if self.cfg['MODEL']['USE_CUDA']:
            print("using cuda")
            torch.backends.cudnn.benchmark = True
            self.device = torch.device("cuda")
            self.model = self.model.to(self.device)

        if self.cfg['MODEL']['HALF']:
            self.model = self.model.half()

        self.model = self.model.eval()
        self.dtype = torch.float16 if self.cfg['MODEL']['HALF'] else torch.float32

    def detect(self, im):
        #load img
        transform = ValTransform(rgb_means=(0.485, 0.456, 0.406), std=(0.229,0.224,0.225))
        #im = cv2.imread(args.img)
        #im = cv2.imread(os.path.join(img_pth, img))
        height, width, _ = im.shape
        #ori_im = im.copy()
        im_input, _ = transform(im, None, self.test_size)
        if self.cfg['MODEL']['USE_CUDA']:
            im_input = im_input.to(self.device)

        im_input = Variable(im_input.type(self.dtype).unsqueeze(0))
        outputs= self.model(im_input) #xc,yc, w, h
        outputs = postprocess(outputs, self.num_class, 0.1, 0.65)
        if None in outputs:
            return None, None, None
        outputs = outputs[0].cpu().data

        bboxes = outputs[:, 0:4] #x1, y1, x2, y2
        bboxes[:, 0::2] *= width / self.test_size[0] #rescale
        bboxes[:, 1::2] *= height / self.test_size[1] #rescale
        #bboxes[:, 2] = bboxes[:,2] - bboxes[:,0] # w
        #bboxes[:, 3] = bboxes[:,3] - bboxes[:,1] # h
        cls = outputs[:, 6]
        scores = outputs[:, 4]* outputs[:,5]

        #pred_im=vis(ori_im, bboxes.numpy(), scores.numpy(), cls.numpy(), conf=0.6, class_names=self.class_names)
        #cv2.imshow('Detection', pred_im)
        #cv2.imwrite(os.path.join(self.cfg['TEST']['SAVED'], img), pred_im)
        #cv2.waitKey(0)
        #cv2.destroyAllWindows()
        return bboxes.tolist(), cls.tolist(), scores.tolist()


if __name__ == '__main__':
    img_pth = './example/test/gray'
    cfg = 'config/yolov3_baseline.cfg'
    for img in os.listdir(img_pth):
        detector = ObjectDetectionASFF(cfg)
        img_arr = cv2.imread(os.path.join(img_pth, img))
        bboxes, cls, scores = detector.detect(img_arr)
        print("bboxes: {}, cls: {}, scores: {}".format(bboxes, cls, scores))
    sys.exit(0)
