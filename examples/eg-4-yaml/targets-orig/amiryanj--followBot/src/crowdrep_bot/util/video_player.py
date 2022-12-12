# Author: Javad Amirian
# Email: amiryan.j@gmail.com

import os
import yaml
import numpy as np
from crowdrep_bot.util.cv_importer import *


class DatasetVideoPlayer:
    def __init__(self, video_files):
        self.num_cams = len(video_files)

        self.video_caps = []
        for i in range(self.num_cams):
            self.video_caps.append(cv2.VideoCapture(video_files[i]))

    def set_frame_id(self, frame_id):
        for cap in self.video_caps:
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_id - 1))

    def get_frame(self):
        while True:
            frames = []
            result = True
            for cap in self.video_caps:
                ret_i, im_i = cap.read()
                frames.append(im_i)
                result = result & ret_i
            if not result:
                # raise Exception("end of video!")
                yield None

            if self.num_cams == 1:
                yield frames[0]

            else:  # Hermes Dataset
                im_i = cv2.cvtColor(frames[0], cv2.COLOR_RGB2GRAY)
                im_r = cv2.cvtColor(frames[1], cv2.COLOR_RGB2GRAY)

                overlap_px = 2
                h = im_i.shape[0]
                w_r = np.tile(np.linspace(0, 1, overlap_px), [h, 1])
                w_l = 1 - w_r

                im_l_padded = np.zeros((h, im_i.shape[1] + im_r.shape[1] - overlap_px), np.uint8)
                im_r_padded = np.zeros((h, im_i.shape[1] + im_r.shape[1] - overlap_px), np.uint8)
                im_l_padded[:, :im_i.shape[1] - overlap_px] = im_i[:, :im_i.shape[1] - overlap_px]
                im_r_padded[:, im_i.shape[1]:] = im_r[:, overlap_px:]

                im_l_padded[:, im_i.shape[1] - overlap_px:im_i.shape[1]] = \
                    np.multiply(w_l, im_i[:, im_i.shape[1] - overlap_px:])
                im_r_padded[:, im_i.shape[1] - overlap_px:im_i.shape[1]] = \
                    np.multiply(w_r, im_r[:, :overlap_px])
                out_im = np.stack([im_l_padded, np.zeros_like(im_l_padded), im_r_padded])
                out_im = np.transpose(out_im, (1, 2, 0))
                out_im = cv2.flip(out_im, 1)
                yield out_im


if __name__ == "__main__":
    config_file = os.path.abspath(
        os.path.join(__file__, "../../../..", "config/repbot_sim/real_scenario_config.yaml"))

    with open(config_file) as stream:
        config = yaml.load(stream, Loader=yaml.FullLoader)
        video_files = config['Dataset']['Video']
        # fps = config['Dataset']['fps']
        # annotation_file = config['Dataset']['Annotation']
        # robot_id = config['Dataset']['RobotId']
        # dataset = load_bottleneck(annotation_file)

    # FixMe: set frame_id to sync
    player = DatasetVideoPlayer(video_files)
    frame_id = -1
    # player.set_frame_id(frame_id)

    pause = False
    for frame in player.get_frame():
        cv2.imshow("frame", frame)
        frame_id += 1
        print(frame_id)

        k = cv2.waitKey(100 * (1 - pause)) & 0xFF
        if k == 27:
            break
        elif k == 32:
            pause = not pause
