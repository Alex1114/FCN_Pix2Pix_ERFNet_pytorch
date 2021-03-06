#!/usr/bin/env python
import numpy as np
import cv2
import roslib
import rospy
import tf
import struct
import math
import time
import csv
from std_msgs.msg import Header
from subt_msgs.srv import *
from sensor_msgs.msg import Image, LaserScan
from sensor_msgs.msg import CameraInfo
from tf import TransformListener,TransformerROS
from tf import LookupException, ConnectivityException, ExtrapolationException
from geometry_msgs.msg import PoseArray, Pose, PoseStamped, Point
from visualization_msgs.msg import Marker, MarkerArray
from nav_msgs.msg import OccupancyGrid, MapMetaData, Path
import rospkg
from cv_bridge import CvBridge, CvBridgeError
from subt_msgs.msg import ArtifactPose, ArtifactPoseArray
from apriltags2_ros.msg import AprilTagDetectionArray, AprilTagDetection

class arti_map():
	def __init__(self):
		self.map_frame = "/slam_map"
		self.robot_frame = "/base_link"
		self.node_name = rospy.get_name()
		self.header = Header()
		self.header.frame_id = self.map_frame
		rospy.loginfo("[%s] Initializing " %(self.node_name))
		self.dis_thres = 3
		self.labels = ['background' , # always index 0
				'extinguisher','backpack','drill', 'survivor']		
		self.count_thres_list = [0, 20, 20, 20, 20, 20]    # [0, 5, 3, 4, 15, 15]
		self.artifact_list = ArtifactPoseArray()
		self.had_pub_arti = ArtifactPoseArray()
		self.last_pub_arti = ArtifactPose()


		## timer callback for net lost
		self.net_lost_arti = ArtifactPoseArray()
		self.net_lost_pub = rospy.Publisher('/net_lost_pub', ArtifactPoseArray, queue_size=1)
		self.timer = rospy.Timer(rospy.Duration(1), self.publish_arti_netlost)

		self.marker_pub = rospy.Publisher('/marker_arti_pub', MarkerArray, queue_size=1)
		self.pub_arti_map = rospy.Publisher('/artifact_map', ArtifactPoseArray, queue_size=1)
		self.sub_arti = rospy.Subscriber("/artifact_pose", ArtifactPoseArray, self.call_back, queue_size=1)
		
		frame_switch_srv = rospy.Service('/switch_main/artifact_frame', frame_switch, self.frame_switch)

	def publish_arti_netlost(self, timer):
		# print "Pub !!!!!"
		self.net_lost_pub.publish(self.net_lost_arti)

	def frame_switch(self, req):
		self.map_frame = '/' + req.frame
		res = frame_switchResponse()
		res.result = "arti_map: Turn frame node to {}".format(req.frame)
		# try:
		# 	rospy.wait_for_service('/switch/SubTINFO_frame', timeout = 1)
		# 	SubTINFO_frame = rospy.ServiceProxy('/switch/SubTINFO_frame', frame_switch)
		# 	req_subtinfo = frame_switchRequest()
		# 	req_subtinfo.frame = req.frame
		# 	resp1 = SubTINFO_frame(req_subtinfo)
		# 	res.result += " ,SubTINFO : Turn frame node to {}".format(req.frame)
		# except rospy.ServiceException, e:
		# 	print "Service call failed: %s"%e

		# try:
		# 	rospy.wait_for_service('/switch/map_frame', timeout = 1)
		# 	MapINFO_frame = rospy.ServiceProxy('/switch/map_frame', frame_switch)
		# 	req_mapinfo = frame_switchRequest()
		# 	req_mapinfo.frame = req.frame
		# 	resp1 = MapINFO_frame(req_mapinfo)
		# 	res.result += " ,MapINFO : Turn frame node to {}".format(req.frame)
		# except rospy.ServiceException, e:
		# 	print "Service call failed: %s"%e
		self.header.frame_id = self.map_frame

		return res


	def call_back(self, msg):
		camera_type = msg.camera
		self.header.stamp = msg.header.stamp
		if camera_type == "middle":
			self.tf_transform("camera_middle_link", msg.pose_array)
		elif camera_type == "left":
			self.tf_transform("camera_left_link", msg.pose_array)
		elif camera_type == "right":
			self.tf_transform("camera_right_link", msg.pose_array)
		else:
			rospy.loginfo("PLZ do not print this!!!!!")


	def tf_transform(self, frame, arti_arr):
		marker_array = MarkerArray()
		try:
			listener.waitForTransform(self.map_frame, frame, rospy.Time(0), rospy.Duration(1.0))
			(trans, rot) = listener.lookupTransform(self.map_frame, frame, rospy.Time(0))
		except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
			print "Error TF listening"
			return
		transpose_matrix = transformer.fromTranslationRotation(trans, rot)
		new_arit_arr = ArtifactPoseArray()
		new_arit_arr.header = self.header
		new_arit_arr.count = 0
		# print(rot)
		p = np.array([0, 0, 0, 1])

		# count_for_true = 0

		# true_list = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30] # [3,6,8]
		# false_list = []
		# i = 0
		# for num in range(self.had_pub_arti.count):
		# 	#if self.had_pub_arti.pose_array[num].appear_count >= self.count_thres:
		# 	if count_for_true in (true_list + false_list):
		# 		pos = self.had_pub_arti.pose_array[num].pose.position
		# 		## Marker
		# 		marker = Marker()
		# 		marker.header.frame_id = self.map_frame
		# 		marker.id = i
		# 		marker.header.stamp = rospy.Time.now()
		# 		marker.type = Marker.CUBE
		# 		marker.action = Marker.ADD
		# 		marker.lifetime = rospy.Duration(0)
		# 		marker.pose.position.x = pos.x
		# 		marker.pose.position.y = pos.y
		# 		marker.pose.position.z = pos.z
		# 		marker.scale.x = 7
		# 		marker.scale.y = 7
		# 		marker.scale.z = 7
		# 		if count_for_true in false_list:
		# 			marker.color.r = 1
		# 			marker.color.g = 1
		# 			marker.color.b = 0
		# 		elif count_for_true in true_list:
		# 			marker.color.r = 0
		# 			marker.color.g = 0
		# 			marker.color.b = 1
		# 		marker.color.a = 0.7
		# 		marker_array.markers.append(marker)
		# 		i += 1

		# 		marker_text = Marker()
		# 		marker_text.header.frame_id = self.map_frame
		# 		marker_text.id = i
		# 		marker_text.header.stamp = rospy.Time.now()
		# 		marker_text.type = Marker.TEXT_VIEW_FACING
		# 		marker_text.action = Marker.ADD
		# 		marker_text.lifetime = rospy.Duration(0)
		# 		marker_text.scale.z = 6
		# 		marker_text.pose.position.x = pos.x
		# 		marker_text.pose.position.y = pos.y
		# 		marker_text.pose.position.z = pos.z
		# 		marker_text.text = self.had_pub_arti.pose_array[num].Class
		# 		marker_text.color.r = 1
		# 		marker_text.color.g = 0
		# 		marker_text.color.b = 0
		# 		marker_text.color.a = 1
		# 		marker_array.markers.append(marker_text)
		# 		i += 1
		# 		## 
		# 	count_for_true += 1


		for arti in arti_arr:
			# if arti.pose.position.x > 0.2:
			p = np.array([arti.pose.position.x, arti.pose.position.y, arti.pose.position.z, 1])
			new_p = np.dot(transpose_matrix, p)
			tf_pose = ArtifactPose()
			tf_pose.pose.position.x = new_p[0]
			tf_pose.pose.position.y = new_p[1]
			tf_pose.pose.position.z = new_p[2]
			tf_pose.pose.orientation.x = rot[0]
			tf_pose.pose.orientation.y = rot[1]
			tf_pose.pose.orientation.z = rot[2]
			tf_pose.pose.orientation.w = rot[3]
			tf_pose.Class = arti.Class
			tf_pose.probability = arti.probability

			## Marker
			marker = Marker()
			marker.header.frame_id = self.map_frame
			marker.id = i
			marker.header.stamp = rospy.Time.now()
			marker.type = Marker.CUBE
			marker.action = Marker.ADD
			marker.lifetime = rospy.Duration(1)
			marker.pose.position.x = new_p[0]
			marker.pose.position.y = new_p[1]
			marker.pose.position.z = new_p[2]
			marker.pose.orientation.x = rot[0]
			marker.pose.orientation.y = rot[1]
			marker.pose.orientation.z = rot[2]
			marker.pose.orientation.w = rot[3]
			marker.scale.x = 1
			marker.scale.y = 1
			marker.scale.z = 1
			marker.color.r = 1
			marker.color.g = 0
			marker.color.b = 0
			marker.color.a = 0.5
			marker_array.markers.append(marker)
			i += 1
			check, arti = self.matching(tf_pose)
			if check:
				new_arit_arr.pose_array.append(arti)
				new_arit_arr.count = new_arit_arr.count + 1

		if new_arit_arr.count:
			self.pub_arti_map.publish(new_arit_arr)

		## Marker pub
		self.marker_pub.publish(marker_array)

	def matching(self, tf_pose):
		# TODO
		print self.artifact_list.count
		for i in range(self.artifact_list.count):
			if self.artifact_list.pose_array[i].Class == tf_pose.Class:
				p_s = self.artifact_list.pose_array[i].pose.position
				p_t = tf_pose.pose.position
				if (p_s.x - p_t.x)**2 + (p_s.y - p_t.y)**2 + (p_s.z - p_t.z)**2 <= self.dis_thres:
					## update 
					c = self.artifact_list.pose_array[i].appear_count
					self.artifact_list.pose_array[i].appear_count = self.artifact_list.pose_array[i].appear_count + 1
					self.artifact_list.pose_array[i].pose.position.x = (p_s.x*c + p_t.x) / (c+1)
					self.artifact_list.pose_array[i].pose.position.y = (p_s.y*c + p_t.y) / (c+1)
					self.artifact_list.pose_array[i].pose.position.z = (p_s.z*c + p_t.z) / (c+1)
					self.artifact_list.pose_array[i].probability = (self.artifact_list.pose_array[i].probability*c + tf_pose.probability) / (c+1)
					rospy.loginfo("Old artifact =.= ")
					print self.labels.index(self.artifact_list.pose_array[i].Class)
					if self.artifact_list.pose_array[i].appear_count >= self.count_thres_list[self.labels.index(self.artifact_list.pose_array[i].Class)]:
						
						### Before

						# for j in range(self.had_pub_arti.count):
						# 	p_h = self.had_pub_arti.pose_array[j].pose.position
							# if (p_h.x - p_t.x)**2 + (p_h.y - p_t.y)**2 + (p_h.z - p_t.z)**2 >= self.dis_thres \
							# 	or self.artifact_list.pose_array[i].Class != self.had_pub_arti.pose_array[j].Class:
						
						###

						p_h = self.last_pub_arti.pose.position
						if self.last_pub_arti.Class != tf_pose.Class or (p_h.x - p_t.x)**2 + (p_h.y - p_t.y)**2 + (p_h.z - p_t.z)**2 >= self.dis_thres:
							self.last_pub_arti = tf_pose
							self.had_pub_arti.pose_array.append(tf_pose)
							self.had_pub_arti.count = self.had_pub_arti.count + 1 

							self.net_lost_arti.pose_array.append(tf_pose)
							self.net_lost_arti.count = self.net_lost_arti.count + 1
						rospy.loginfo("Publish Arti")
						return True, self.artifact_list.pose_array[i]
					else:
						return False, tf_pose
						
		# if tf_pose.pose.position.z <= 12.0:

		tf_pose.appear_count = 0
		self.artifact_list.pose_array.append(tf_pose)
		self.artifact_list.count = self.artifact_list.count + 1 
		rospy.loginfo("============ New artifact !! ============")
		return False, tf_pose


####################################### april tag ##################################################
	# def april_cb(self, msg):
	# 	try:
	# 		listener.waitForTransform(self.map_frame, "camera_middle_link", rospy.Time(0), rospy.Duration(1.0))
	# 		(trans, rot) = listener.lookupTransform(self.map_frame, "camera_middle_link", rospy.Time(0))
	# 	except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
	# 		print "Error TF listening when april cb"
	# 		return
	# 	transpose_matrix = transformer.fromTranslationRotation(trans, rot)
	# 	marker_array = MarkerArray()

	# 	for april in msg.detections:
	# 		_bool = False
	# 		p = np.array([april.pose.pose.pose.position.z, -april.pose.pose.pose.position.x, -april.pose.pose.pose.position.y, 1])
	# 		new_p = np.dot(transpose_matrix, p)
	# 		tf_pose = ArtifactPose()
	# 		tf_pose.pose.position.x = new_p[0]
	# 		tf_pose.pose.position.y = new_p[1]
	# 		tf_pose.pose.position.z = new_p[2]
	# 		tf_pose.pose.orientation.x = rot[0]
	# 		tf_pose.pose.orientation.y = rot[1]
	# 		tf_pose.pose.orientation.z = rot[2]
	# 		tf_pose.pose.orientation.w = rot[3]
	# 		tf_pose.appear_count = april.id[0]
	# 		for i in range(self.apriltag_list.count):
	# 			if self.apriltag_list.pose_array[i].appear_count == april.id[0]:
	# 				_bool = True
	# 				self.apriltag_list.pose_array[i] = tf_pose
	# 		if not _bool:
	# 			self.apriltag_list.count = self.apriltag_list.count + 1
	# 			self.apriltag_list.pose_array.append(tf_pose)

	# 	i = 0


	# 	color_list = [[0,1,[0.82,0,0.82]],[2,3,[1,0.55,1]],[4,5,[0.29,0.29,1]],[6,7,[0.67,0.67,1]],[8,9,[0,0.96,0.56]],\
	# 		[10,11,[0.59,1,0.82]],[12,13,[0.57,1,0]],[14,15,[0.8,1,0.5]],[16,17,[1,0.57,0.14]],[18,19,[1,0.78,0.55]]]
	# 			# d200d2  ff8eff 4a4aff, aaaaff 	02f78e 96fed1 9aff02 ccff80 ff9224 ffc78e  
	# 	for num in range(self.apriltag_list.count):
	# 		#if self.had_pub_arti.pose_array[num].appear_count >= self.count_thres:
	# 		if True:
	# 			pos = self.apriltag_list.pose_array[num].pose.position
	# 			## Marker
	# 			marker = Marker()
	# 			marker.header.frame_id = self.map_frame
	# 			marker.id = i
	# 			i += 1
	# 			marker.header.stamp = rospy.Time.now()
	# 			marker.type = Marker.CUBE
	# 			marker.action = Marker.ADD
	# 			marker.lifetime = rospy.Duration(0)
	# 			marker.pose.position.x = pos.x
	# 			marker.pose.position.y = pos.y
	# 			marker.pose.position.z = pos.z
	# 			marker.scale.x = 3
	# 			marker.scale.y = 3
	# 			marker.scale.z = 3

	# 			for j in range(10):
	# 				if self.apriltag_list.pose_array[num].appear_count in color_list[j][:2]:
	# 					marker.color.r = color_list[j][2][0]
	# 					marker.color.g = color_list[j][2][1]
	# 					marker.color.b = color_list[j][2][2]
	# 					marker.color.a = 0.7
						
	# 					marker_array.markers.append(marker)
						

	# 					marker_text = Marker()
	# 					marker_text.header.frame_id = self.map_frame
	# 					marker_text.id = i
	# 					marker_text.header.stamp = rospy.Time.now()
	# 					marker_text.type = Marker.TEXT_VIEW_FACING
	# 					marker_text.action = Marker.ADD
	# 					marker_text.lifetime = rospy.Duration(0)
	# 					marker_text.scale.z = 3;
	# 					marker_text.pose.position.x = pos.x
	# 					marker_text.pose.position.y = pos.y
	# 					marker_text.pose.position.z = pos.z
	# 					marker_text.text = str(self.apriltag_list.pose_array[num].appear_count)
	# 					marker_text.color.r = 1
	# 					marker_text.color.g = 0
	# 					marker_text.color.b = 0
	# 					marker_text.color.a = 1
	# 					marker_array.markers.append(marker_text)
	# 					i += 1

	# 	self.april_marker_pub.publish(marker_array)

	def onShutdown(self):
		_f = []
		for num in range(self.apriltag_list.count):
			p = self.apriltag_list.pose_array[num]
			_t = []
			_t.append(p.appear_count)
			_t.append(str(p.pose.position.x))
			_t.append(str(p.pose.position.y))
			_t.append(str(p.pose.position.z))
			_f.append(_t)
		with open('/root/SubT/bag.txt', mode='w') as csv_file:
			writer = csv.writer(csv_file)
			writer.writerows(_f)
			print(len(_f))
		rospy.loginfo("Shutdown and save file!!!")


if __name__ == '__main__':
	rospy.init_node('arti_map')
	listener = TransformListener()
	transformer = TransformerROS()
	foo = arti_map()
	rospy.on_shutdown(foo.onShutdown)
	rospy.spin()
