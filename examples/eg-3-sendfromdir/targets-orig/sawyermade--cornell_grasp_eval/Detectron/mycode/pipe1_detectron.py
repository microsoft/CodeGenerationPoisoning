from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os, sys, flask, werkzeug as wz, json
from zipfile import ZipFile
from collections import defaultdict
import argparse
import cv2  # NOQA (Must import before importing caffe2 due to bug in cv2)
import glob
import logging
import time

def parse_args():
	parser = argparse.ArgumentParser(description='End-to-end inference')
	parser.add_argument(
		'--cfg',
		dest='cfg',
		help='cfg model file (/path/to/model_config.yaml)',
		default=None,
		type=str
	)
	parser.add_argument(
		'--wts',
		dest='weights',
		help='weights model file (/path/to/model_weights.pkl)',
		default=None,
		type=str
	)
	parser.add_argument(
		'--output-dir',
		dest='output_dir',
		help='directory for visualization pdfs (default: /tmp/infer_simple)',
		default='/tmp/infer_simple',
		type=str
	)
	parser.add_argument(
		'--image-ext',
		dest='image_ext',
		help='image file name extension (default: jpg)',
		default='jpg',
		type=str
	)
	# parser.add_argument(
	# 	'--always-out',
	# 	dest='out_when_no_box',
	# 	help='output image even when no object is found',
	# 	action='store_true'
	# )
	parser.add_argument(
		'--output-ext',
		dest='output_ext',
		help='output image file format (default: pdf)',
		default='pdf',
		type=str
	)
	parser.add_argument(
		'--thresh',
		dest='thresh',
		help='Threshold for visualizing detections',
		default=0.7,
		type=float
	)
	parser.add_argument(
		'--kp-thresh',
		dest='kp_thresh',
		help='Threshold for visualizing keypoints',
		default=2.0,
		type=float
	)
	# parser.add_argument(
	# 	'--im-or-folder', help='image or folder of images', default=None, dest='im_or_folder'
	# )
	parser.add_argument(
		'--cuda',
		dest='cuda',
		help='Enter cuda card number to use as integer',
		default=0,
		type=str
	)
	parser.add_argument(
		'--ip',
		dest='ip',
		help='Server IP',
		default=0,
		type=str
	)
	parser.add_argument(
		'--port',
		dest='port',
		help='Server Port',
		default=0,
		type=str
	)
	if len(sys.argv) == 1:
		parser.print_help()
		sys.exit(1)
	return parser.parse_args()


args = parse_args()
DOMAIN = str(args.ip)
PORT = int(args.port)
FULLDOMAIN = 'http://{}:{}'.format(DOMAIN, PORT)
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif', 'tiff', 'bmp'])
UPLOAD_FOLDER = 'uploads-pipe1'
UPLOAD_FOLDER_REL = '/uploads-pipe1/'
app = flask.Flask(__name__)

dummy_coco_dataset = None
model = None

os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"]=str(args.cuda)

from caffe2.python import workspace

from detectron.core.config import assert_and_infer_cfg
from detectron.core.config import cfg
from detectron.core.config import merge_cfg_from_file
from detectron.utils.io import cache_url
from detectron.utils.logging import setup_logging
from detectron.utils.timer import Timer
import detectron.core.test_engine as infer_engine
import detectron.datasets.dummy_datasets as dummy_datasets
import detectron.utils.c2 as c2_utils
import detectron.utils.vis as vis_utils

c2_utils.import_detectron_ops()

# OpenCL may be enabled by default in OpenCV3; disable it because it's not
# thread safe and causes unwanted GPU memory allocations.
cv2.ocl.setUseOpenCL(False)

def allowedFile(fname):
	if fname[-3:].lower() in ALLOWED_EXTENSIONS or fname[-4:].lower() in ALLOWED_EXTENSIONS:
		return True
	else:
		return False

@app.route('/', methods=['GET', 'POST'])
def upload_file():
	# global logger, model
	if flask.request.method == 'POST':
		file = flask.request.files['file']
		if file and allowedFile(file.filename):
			# print('**found file: {}'.format(file.filename))
			fname = wz.secure_filename(file.filename)
			fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
			# print(fname)
			file.save(fpath)

			
			# relPath = flask.url_for('uploaded_file', filename=fname)
			# # print(relPath)
			# retUrl = os.path.join(FULLDOMAIN, *relPath.split(os.sep))
			# # retUrl = FULLDOMAIN + UPLOAD_FOLDER_REL + fname
			# print(retUrl)
			
			# Run inference on file
			
			im = cv2.imread(fpath)
			# logger.info('Processing {} -> {}'.format(fname, out_name))
			timers = defaultdict(Timer)
			# t = time.time()
			with c2_utils.NamedCudaScope(0):
				cls_boxes, cls_segms, cls_keyps = infer_engine.im_detect_all(
					model, im, None, timers=timers
				)
			# logger.info('Inference time: {:.3f}s'.format(time.time() - t))
			# for k, v in timers.items():
			# 	logger.info(' | {}: {:.3f}s'.format(k, v.average_time))
			# if i == 0:
			# 	logger.info(
			# 		'\nNote: inference on the first image will be slower than the '
			# 		'rest (caches and auto-tuning need to warm up)'
			# 	)

			# vis_utils.vis_one_image(
			# 	im[:, :, ::-1],  # BGR -> RGB for visualization
			# 	fname + '-test.' + args.output_ext,
			# 	args.output_dir,
			# 	cls_boxes,
			# 	cls_segms,
			# 	cls_keyps,
			# 	dataset=dummy_coco_dataset,
			# 	box_alpha=0.3,
			# 	show_class=True,
			# 	thresh=args.thresh,
			# 	kp_thresh=args.kp_thresh,
			# 	ext=args.output_ext,
			# 	out_when_no_box=False
			# )

			# def vis_one_image_opencv(
			# im, boxes, segms=None, keypoints=None, thresh=0.9, kp_thresh=2,
			# show_box=False, dataset=None, show_class=False):
			# print('*************** vis_one_image_opencv')
			cvimg, retVals = vis_utils.vis_one_image_opencv(
				im, 
				cls_boxes,
				cls_segms,
				cls_keyps,
				dataset=dummy_coco_dataset,
				show_class=True,
				show_box=True,
				thresh=args.thresh,
				kp_thresh=args.kp_thresh
			)
			# print('*************** after')
			if not retVals:
				return 'No Objects Found'

			bbList, classList, scoreList, maskList = retVals
			print('\nlen(maskList) = {}, len(bbList) = {}\n'.format(len(maskList), len(bbList)))
			# maskList = []
			# for i in range(masks.shape[-1]):
			# 	maskList.append(masks[...,i])
			# print(len(maskList))

			# Creates json and images
			ofname = os.path.basename(fname) + '.csv'
			out_name = os.path.join(args.output_dir, ofname)
			opathList = [out_name]
			onameList = [ofname]
			arcnameList = ['info.csv']
			count = 0
			with open(out_name, 'w') as of:
				for bb, cl, sc, ma in zip(bbList, classList, scoreList, maskList):
					# Adds info to csv
					ostr = ','.join((str(count) + '.' + args.output_ext, str(sc), str(cl), str(bb[0]), str(bb[1]), str(bb[2]), str(bb[3])))
					of.write(ostr + '\n')
					# print(ostr)

					# Saves mask image
					oname = os.path.basename(ofname) + '-m{}.'.format(count) + args.output_ext
					opath = os.path.join(args.output_dir, oname)
					opathList.append(opath)
					onameList.append(oname)
					arcnameList.append('{}.{}'.format(count, args.output_ext))
					cv2.imwrite(opath, ma)
					count += 1



			# Save image
			ofname = os.path.basename(fname) + '-vis.' + args.output_ext
			out_name = os.path.join(args.output_dir, ofname)
			cv2.imwrite(out_name, cvimg)
			opathList.append(out_name)
			arcnameList.append('vis.' + args.output_ext)

			# Creates urllist.txt
			# print(onameList)
			urlfname = 'urllist-{}.txt'.format(fname.split('.')[0])
			flistPath = os.path.join(args.output_dir, urlfname)
			opathList.append(flistPath)
			arcnameList.append('urllist.txt')
			# onameList.append(urlfname)
			with open(flistPath, 'w') as fl:
				count = 0
				for oname in onameList:
					if not oname.endswith('csv'):
						fl.write(FULLDOMAIN + UPLOAD_FOLDER_REL + oname + ',' + '{}.{}'.format(count, args.output_ext) + '\n')
						count += 1
				fl.write(FULLDOMAIN + UPLOAD_FOLDER_REL + ofname + ',' + 'vis.{}'.format(args.output_ext) + '\n')

			# Zip files
			zipFname = fname + '.zip'
			zipFpath = os.path.join(args.output_dir, zipFname)
			with ZipFile(zipFpath, 'w') as ofz:
				# print(opathList, arcnameList)
				for opath, arcname in zip(opathList, arcnameList):
					# print(opath, arcname)
					ofz.write(opath, arcname=arcname)


			# print('\n{} {} {} {}'.format(type(bbList), type(classList), type(scoreList), type(maskList)))
			# for count, box in enumerate(bbList):
			# 	print(count, box, classList[count], scoreList[count])

			

			# retUrl = os.path.join(FULLDOMAIN, UPLOAD_FOLDER, zipFname)
			retUrl = FULLDOMAIN + UPLOAD_FOLDER_REL + zipFname
			print('\n***** retUrl = {}, ofname = {} *****\n'.format(retUrl, ofname))

			# cv2.imshow('image', cvimg)
			# wk = cv2.waitKey(0)
			# if wk == 27:
			#     cv2.destroyAllWindows()

			

			return retUrl

	return None

@app.route('/{}/<filename>'.format(UPLOAD_FOLDER))
def uploaded_file(filename):
	return flask.send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def main():
	# Load network
	global model, dummy_coco_dataset
	# logger = logging.getLogger(__name__)

	merge_cfg_from_file(args.cfg)
	cfg.NUM_GPUS = 1
	# args.weights = cache_url(args.weights, cfg.DOWNLOAD_CACHE)
	assert_and_infer_cfg(cache_urls=False)

	assert not cfg.MODEL.RPN_ONLY, \
		'RPN models are not supported'
	assert not cfg.TEST.PRECOMPUTED_PROPOSALS, \
		'Models that require precomputed proposals are not supported'

	model = infer_engine.initialize_model_from_cfg(args.weights)
	dummy_coco_dataset = dummy_datasets.get_coco_dataset()
	
	# Setup upload folder and run server
	if not os.path.exists(UPLOAD_FOLDER):
		os.makedirs(UPLOAD_FOLDER)

	app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
	app.run(port=PORT, host='0.0.0.0', debug=False)
	# app.run(port=PORT, host=DOMAIN, debug=False)

if __name__ == '__main__':
	workspace.GlobalInit(['caffe2', '--caffe2_log_level=0'])
	setup_logging(__name__)
	# args = parse_args()
	main()