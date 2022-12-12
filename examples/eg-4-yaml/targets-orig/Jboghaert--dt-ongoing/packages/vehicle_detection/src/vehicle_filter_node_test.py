#!/usr/bin/env python
from cv_bridge import CvBridge, CvBridgeError
from duckietown_msgs.msg import VehicleCorners, VehiclePose
from duckietown_utils import get_duckiefleet_root
from geometry_msgs.msg import Point32
from sensor_msgs.msg import CameraInfo
import rospy
import cv2
import io
import numpy as np
import threading
import os.path
import yaml

class VehicleFilterNodeTest(object):
	def __init__(self):
		self.node_name = "Vehicle Filter Test"
		self.bridge = CvBridge()
		
		self.cali_file_name = self.setupParam("~cali_file_name","default") 
		self.cali_file = (get_duckiefleet_root() + "/calibrations/camera_intrinsic/"
						   +  self.cali_file_name + ".yaml")
		if not os.path.isfile(self.cali_file):
			rospy.logwarn("[%s] Can't find calibration file: %s.\nUsing default calibration instead."
						  %(self.node_name,self.cali_file))
			self.cali_file = (get_duckiefleet_root() + "/calibrations/camera_intrinsic/default.yaml")
		if not os.path.isfile(self.cali_file):
			rospy.signal_shutdown("Found no calibration file ... aborting")
		rospy.loginfo("[%s] Using calibration file: %s" %(self.node_name,self.cali_file))
		self.camera_info_msg = load_camera_info(self.cali_file)
		self.camera_info_msg.header.frame_id = rospy.get_namespace() + "camera_optical_frame"
		rospy.loginfo("[%s] CameraInfo: %s" %(self.node_name,self.camera_info_msg))
		
				
		self.sub_pose = rospy.Subscriber("~pose", VehiclePose, 
				self.processPose, queue_size=1)
		self.pub_corners = rospy.Publisher("~corners", VehicleCorners, queue_size=1)
		self.pub_camera_info = rospy.Publisher("~camera_info", CameraInfo, queue_size=1)
		
		rospy.loginfo("Initialization of [%s] completed" % (self.node_name))
		pub_period = rospy.get_param("~pub_period", 1.0)
		rospy.Timer(rospy.Duration.from_sec(pub_period), self.pubCorners)
		
	def setupParam(self,param_name,default_value):
		value = rospy.get_param(param_name,default_value)
		rospy.set_param(param_name,value) #Write to parameter server for transparancy
		rospy.loginfo("[%s] %s = %s " %(self.node_name,param_name,value))
		return value

	def pubCorners(self, args=None):
		self.pub_camera_info.publish(self.camera_info_msg)
		corners_msg_out = VehicleCorners()
		corners_msg_out.header.stamp = rospy.Time.now()
		corners_msg_out.H = 3
		corners_msg_out.W = 7
		corners_msg_out.detection.data = True
# 		p_1 = Point32()
# 		p_2 = Point32()
# 		p_3 = Point32()
# 
# 		p_1.x = 0.0
# 		p_1.y = 10.0
# 
# 		p_2.x = 1.0
# 		p_2.y = 11.0
# 
# 		p_3.x = 2.0
# 		p_3.y = 12.0
# 
# 		corners_msg_out.corners.append(p_1)
# 		corners_msg_out.corners.append(p_2)
# 		corners_msg_out.corners.append(p_3)
		
		
		for i in range(0, 21):
			point = Point32()
			point.x = i*2.0
			point.y = i*3.0
			corners_msg_out.corners.append(point)
		
		
		self.pub_corners.publish(corners_msg_out)

		rospy.loginfo("Publishing corners")
		

	def processPose(self, pose_msg):
		rospy.loginfo('Pose received : (rho = %.2f, theta = %.2f, psi = %.2f)' %
					(pose_msg.rho.data, pose_msg.theta.data, pose_msg.psi.data))
		
def load_camera_info(filename):
    stream = file(filename, 'r')
    calib_data = yaml.load(stream)
    cam_info = CameraInfo()
    cam_info.width = calib_data['image_width']
    cam_info.height = calib_data['image_height']
    cam_info.K = calib_data['camera_matrix']['data']
    cam_info.D = calib_data['distortion_coefficients']['data']
    cam_info.R = calib_data['rectification_matrix']['data']
    cam_info.P = calib_data['projection_matrix']['data']
    cam_info.distortion_model = calib_data['distortion_model']
    return cam_info

if __name__ == '__main__': 
	rospy.init_node('vehicle_filter_node', anonymous=False)
	vehicle_filter_test_node = VehicleFilterNodeTest()
	rospy.spin()

