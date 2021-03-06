#!/usr/bin/env python2

# from time import sleep, time
import math
import threading
import xml.etree.ElementTree as ET
import os

import rospy
from std_msgs.msg import *
import numpy as np

import kinematics_geom as kin
import kinematics_nummeric
import status_intf as status
from youbot_rw_rqt_gui.msg import *
from std_msgs.msg import Empty
import sync
import vrep_controll


class Node(object):
    def __init__(self):
        """ init main ros node of youbot remote writing
        @return <b><i><c> [void]: </c></i></b> nothing
        """

        super(Node, self).__init__()
        self.run = True
        self.pause = False

        self.lock = threading.Lock()
        self.kinematic_type = "Nummeric"

        rospy.init_node('youbot_rw_node')
        self.init_params(0)
        self.run_status = True
        self.spin_count = 0
        self.r = rospy.Rate(self.rate)

        rospy.Subscriber('/youbot_rw/gui2node', rw_node, self.callback_process_cmd)
        rospy.Subscriber('/youbot_rw/reset', Empty, self.init_params)
        self.pub2gui = rospy.Publisher('/youbot_rw/node2gui', rw_node_state, tcp_nodelay=True, queue_size=1)
        # Publisher for vrep interface
        self.pub2vrep_joint_1_trgt = rospy.Publisher('/youbot_rw/vrep/arm_joint1_target', Float64, tcp_nodelay=True, queue_size=1)
        self.pub2vrep_joint_2_trgt = rospy.Publisher('/youbot_rw/vrep/arm_joint2_target', Float64, tcp_nodelay=True, queue_size=1)
        self.pub2vrep_joint_3_trgt = rospy.Publisher('/youbot_rw/vrep/arm_joint3_target', Float64, tcp_nodelay=True, queue_size=1)
        self.pub2vrep_joint_4_trgt = rospy.Publisher('/youbot_rw/vrep/arm_joint4_target', Float64, tcp_nodelay=True, queue_size=1)
        self.pub2vrep_joint_5_trgt = rospy.Publisher('/youbot_rw/vrep/arm_joint5_target', Float64, tcp_nodelay=True, queue_size=1)



        self.spin()


    def init_params(self, msg):
        """ init parameters for main node of youbot remote writing
        @return <b><i><c> [void]: </c></i></b> nothing
        """
        self.rate = 100
        self.res = 1000
        self.disable = False
        self.status = 1  # 0= error 1= no error
        self.status_string = "no error"
        self.status_vrep = 0  # 0=doing nothing 1= in progress 2= movement done
        self.kinematics = kin.Kinematics_geom()
        self.kin_num = kinematics_nummeric.Kinematics_num()

        self.config_trgt_pos = np.array([np.nan,
                                         np.nan,
                                         np.nan])

        self.hoverOffset = 0.01
        self.line = 0
        self.line_ending_threshold = 0.1
        self.start_line_offset = -0.00
        self.nextLetterPos = np.array([self.start_line_offset, -self.line_ending_threshold, 0])
        # z coordinate

        # parse xml letter database
        script_path = os.path.dirname(os.path.abspath(__file__))
        print("script dir: "), script_path
        tmp_use_rosparam_path = rospy.get_param("/youbot_rw_node/general/USE_ROSPARAM_PATH_FOR_DATABASE")
        if (tmp_use_rosparam_path):
            db_path = rospy.get_param("/youbot_rw_node/general/PATH_OF_LETTER_DATABASE")
        else:
            db_path = script_path + '/../../../../../material/YouBot_RW_Material/Buchstaben_Datenbank/letter_database.xml'

        print("opening following letter_database: "), db_path
        self.letter_database = ET.parse(db_path)
        self.ldb_root = self.letter_database.getroot()

        # print loaded ldb elements
        print("Loaded "), self.ldb_root.tag, (": "), [x.tag for x in self.ldb_root]

        sync.init_sync()
        vrep_controll.TriggerSimualtion()
        vrep_controll.unsetSyncSimualtion()
        vrep_controll.TriggerSimualtion()
        vrep_controll.stopSimualtion()
        vrep_controll.TriggerSimualtion()
        vrep_controll.startSimualtion()
        vrep_controll.TriggerSimualtion()
        vrep_controll.startSimualtion()
        vrep_controll.TriggerSimualtion()
        vrep_controll.setSyncSimualtion()
        vrep_controll.TriggerSimualtion()
        vrep_controll.TriggerSimualtion()
        vrep_controll.TriggerSimualtion()
        vrep_controll.TriggerSimualtion()
        vrep_controll.TriggerSimualtion()
        vrep_controll.TriggerSimualtion()
        vrep_controll.TriggerSimualtion()
        vrep_controll.TriggerSimualtion()
        vrep_controll.TriggerSimualtion()
        vrep_controll.TriggerSimualtion()
        vrep_controll.TriggerSimualtion()
        vrep_controll.TriggerSimualtion()

        self.config_thetas_bogen = np.array(sync.getJointPostition())
        self.desired_thetas_bogen =  self.config_thetas_bogen


        self.config_cur_pos = self.kinematics.direct_kin(self.config_thetas_bogen)


    def spin(self):
        """ Program main loop
        """
        self.spin_count += 1
        if (self.spin_count > 1):
            return

        rospy.loginfo("started")
        self.send_status2gui(status.STATUS_NODE_NO_ERROR, status.STATUS_VREP_WAITING_4_CMD, "controller ready for input")
        while (not rospy.is_shutdown() and self.run and self.run_status):
            self.r.sleep()

        rospy.loginfo("stopped")
        self.spin_count -= 1


    def send_vrep_joint_targets(self, trgts):
        """ Sends joint angles to V-REP and waits for reach
        @param [in] trgts <b><i><c> [vector-5]: </c></i></b> Angles to apply in V-REP in radians
        """
        self.pub2vrep_joint_1_trgt.publish(trgts[0])
        self.pub2vrep_joint_2_trgt.publish(trgts[1])
        self.pub2vrep_joint_3_trgt.publish(trgts[2])
        self.pub2vrep_joint_4_trgt.publish(trgts[3])
        self.pub2vrep_joint_5_trgt.publish(trgts[4])
        self.desired_thetas_bogen=trgts
        sync.wait_untel_pos(trgts)




    def move_arm(self, trgts, bogen):
        """ move the Arm and tests for large angle changes, to prevent destroying write plain
        @param [in] thetas <b><i><c> [vector-5]: </c></i></b> joint angles
        """

        if bogen:
            trgts_bogen = np.array([(trgts[0]),
                                    (trgts[1]),
                                    (trgts[2]),
                                    (trgts[3]),
                                    (trgts[4])])
        else:
            trgts_bogen = np.array([(((2. * np.pi) / 360.) * trgts[0]),
                                    (((2. * np.pi) / 360.) * trgts[1]),
                                    (((2. * np.pi) / 360.) * trgts[2]),
                                    (((2. * np.pi) / 360.) * trgts[3]),
                                    (((2. * np.pi) / 360.) * trgts[4])])
        if self.check_angle_movement(trgts_bogen):
                self.send_vrep_joint_targets(trgts_bogen)
        else:
                self.process_linear_angle_movement(trgts_bogen)
        self.config_cur_pos = self.kinematics.direct_kin(trgts_bogen)
        self.config_thetas_bogen=trgts_bogen



    def check_angle_movement(self, trgts):
        """ checks for large angle changes in trgts-thetas to desired_thetas_bogen
        @param [in] trgts <b><i><c> [vector-5]: </c></i></b> target joint angles
        @return <b><i><c> [Bool]: </c></i></b> true if change is small
        """
        joint_angle_thresholds =    np.array([  (0.05),
                                                (0.05),
                                                (0.05),
                                                (0.05),
                                                (0.001)])# last angle, we dont care
        small = True
        for i,j in enumerate(trgts):# for i,j ???
            if abs(trgts[i]-self.desired_thetas_bogen[i]) > joint_angle_thresholds[i]:
                print("angle_diff in joint_"), i,("["),abs(trgts[i]-self.desired_thetas_bogen[i]), (" rad] "),  ("bigger than "), joint_angle_thresholds[i]
                small=False
                break
        return small

    def process_linear_angle_movement(self, trgts):
        """ changes arm configuration without leaving target Point
        @param [in] trgts <b><i><c> [vector-5]: </c></i></b> target joint angles
        """
        print "Process linear angle movement , elbow change or singularity?"
        res=0.01#0.005
        angle_change=trgts-self.desired_thetas_bogen
        max_change=max(abs(angle_change))
        steps=max_change/res
        print "steps: ", steps
        for i in xrange(1, int(steps)):
            new_joints=self.desired_thetas_bogen+(angle_change/int(steps))
            if self.kinematic_type == "Nummeric":
                erg=self.kin_num.step_to_point(self.config_cur_pos,new_joints[3])
                self.send_vrep_joint_targets(erg)
            else:
                # TODO: calc ik for geometric!
                self.send_vrep_joint_targets(new_joints)

        print "Process linear angle movement, DONE!"



    def callback_process_cmd(self, msg):
        """ Ros callback triggers all actions from gui
        """

        if (not self.run_status):
            return

        self.lock.acquire()

        rospy.loginfo("process_cmd callback")
        if msg.kinematic == 0:
            self.kinematic_type = "Gerometric"
        else:
            self.kinematic_type = "Nummeric"

        self.time = rospy.get_time()
        self.parse_input_from_gui(msg)
        self.send_status2gui(status.STATUS_NODE_NO_ERROR, status.STATUS_VREP_WAITING_4_CMD, "received write command")

        # DO WRITING WITH ROBOT HERE
        if (self.config_processMode == status.PROCESSING_MODE_WRITING):
            self.process_writing()
        elif (self.config_processMode == status.PROCESSING_MODE_LOGO):
            print("triggered logo")
            # TODO: implement Logo

        elif (self.config_processMode == status.PROCESSING_MODE_PTP_ANGLES):
            self.process_ptp_angles()
        elif (self.config_processMode == status.PROCESSING_MODE_LIN_ANGLES):
            print("ERROR - linear movement through angle input is not implemented yet")
            self.send_status2gui(status.STATUS_NODE_NO_ERROR, status.STATUS_VREP_WAITING_4_CMD, "ERROR - linear movement through angle input is not implemented yet")
        elif (self.config_processMode == status.PROCESSING_MODE_PTP_POSITION):
            self.process_ptp_position()
            print("pos: [%.4f; %.4f; %.4f]" % (self.config_cur_pos[0], self.config_cur_pos[1], self.config_cur_pos[2]) )
        elif (self.config_processMode == status.PROCESSING_MODE_LIN_POSITION):
            self.process_lin_position()


            #self.send_status2gui( status.STATUS_NODE_NO_ERROR, status.STATUS_VREP_WAITING_4_CMD, "movement in progress")

        #rospy.logwarn('self.poly_y == 0')

        self.lock.release()


    def process_ptp_angles(self):
        """ moves Arm without any logic to config_thetas_bogen
        """
        print("triggered angles")
        #tmp = self.kinematics.offset2world(self.config_thetas_bogen)
        #print("angles: "), self.config_thetas_bogen
        if (self.kinematics.isSolutionValid(self.config_thetas_bogen)):
            self.send_vrep_joint_targets(self.config_thetas_bogen)
            self.config_cur_pos = self.kinematics.direct_kin(self.config_thetas_bogen)
            print("pos: [%.4f; %.4f; %.4f]" % (self.config_cur_pos[0], self.config_cur_pos[1], self.config_cur_pos[2]) )
            pos_wp = self.kinematics.direct_kin_2_wristPoint(self.config_thetas_bogen)
            print("pos_wp: [%.4f; %.4f; %.4f]" % (pos_wp[0], pos_wp[1], pos_wp[2]) )
            self.send_status2gui(status.STATUS_NODE_NO_ERROR, status.STATUS_VREP_WAITING_4_CMD, "angle processing done")
        else:
            print("ERROR: Target angles are not valid! This should never happen, if GUI is used.")


    def process_lin_position(self):
        print("== triggered lin position ==")
        tmpPos = list()
        tmpPos.append(np.array([self.config_trgt_pos[0], self.config_trgt_pos[1], self.config_trgt_pos[2]]))
        print tmpPos
        self.process_linear_movement(tmpPos, False, True)

        # self.process_linear_movement_with_angles(tmpPos, True, True)
        print("== lin position movement done==")

    def process_ptp_position(self):
        print("== triggered ptp position ==")
        valid_sol = False
        if self.kinematic_type == "Nummeric":
            print("== using  nummeric kinematics ==")
            resolution = 100
            point = [0, 0, 0.1]
            erg = [0, 0, 0, 0, 0]
            angle = np.array(self.kin_num.step_to_point(point))
            self.kin_num.last_point = np.array(point)
            if angle is not None:
                joint_pos = sync.getJointPostition()
                for i in xrange(0, int(resolution), 1):
                    erg = joint_pos + (((angle - joint_pos) / (resolution)) * i)
                    self.send_vrep_joint_targets(erg)

            self.config_cur_pos = self.kinematics.direct_kin(erg)
            self.config_thetas_bogen = erg

        else:
            print("== using  geometric kinematics ==")
            # time.sleep(0.2)
            #self.config_cur_pos = self.kinematics.direct_kin(self.config_thetas_bogen)
            #tmpPos = np.matrix((self.config_trgt_pos[0], self.config_trgt_pos[1], self.config_trgt_pos[2])).transpose()
            print "target pos:", self.config_trgt_pos
            valid_ik_solutions = self.kinematics.get_valid_inverse_kin_solutions(self.config_trgt_pos, True, False, False,-1)
            #print("debug get valid ik solutions")
            #time.sleep(0.2)

            if not valid_ik_solutions:
                # try again without fast calculation
                valid_ik_solutions = self.kinematics.get_valid_inverse_kin_solutions(self.config_trgt_pos, False, False, False, -1)
                #print("debug get valid ik solutions again")
                #time.sleep(0.2)

                if not valid_ik_solutions:
                    print "// no valid ik solution possible! //"
                    self.send_status2gui(status.STATUS_NODE_NO_ERROR, status.STATUS_VREP_WAITING_4_CMD, "position processing not possible, found no ik solution")
                else:
                    valid_sol = True
            else:
                valid_sol = True

            if valid_sol:
                #print "// valid ik solution possible! //"
                #print "first valid ik solution: [%.4f; %.4f; %.4f; %.4f; %.4f;]" % (math.degrees(valid_ik_solutions[0][0]), math.degrees(valid_ik_solutions[0][1]), math.degrees(valid_ik_solutions[0][2]), math.degrees(valid_ik_solutions[0][3]), math.degrees(valid_ik_solutions[0][4]) ) , self.kinematics.isSolutionValid(valid_ik_solutions[0])
                #dk_pos = self.kinematics.direct_kin(valid_ik_solutions[0], True)
                #print "dk_pos: [%.4f; %.4f; %.4f]" % (dk_pos[0],dk_pos[1],dk_pos[2])

                #print("debug solutions:"),valid_ik_solutions

                self.send_vrep_joint_targets(valid_ik_solutions[0])
                self.config_cur_pos = self.kinematics.direct_kin(valid_ik_solutions[0])
                self.config_thetas_bogen = valid_ik_solutions[0]

        self.send_status2gui(status.STATUS_NODE_NO_ERROR, status.STATUS_VREP_WAITING_4_CMD, "position processing done, found solution")
        if valid_sol:
            print("== ptp position movement done==")

    def get_circle(self, radius, from_degree=0, to_degree=360):

        data = list()
        while from_degree > 360:
            from_degree -= 360
        while to_degree > 360:
            to_degree -= 360
        for x in xrange(-100, 100, 1):
            data.append(np.array([x / 100., math.sqrt(1 - (x / 100.) ** 2), 0]))
        for x in xrange(-100, 100, 1):
            data.append(np.array([-x / 100., -math.sqrt(1 - (x / 100.) ** 2), 0]))
        for x in data:
            x[0] = x[0] * radius
            x[1] = x[1] * radius
        if from_degree < to_degree:
            data = data[int(len(data) * (from_degree / 360.)):int(len(data) * (to_degree / 360.))]

        else:
            data = data[::-1]
            data = data[int(len(data) * ((360 - from_degree) / 360.)):int(len(data) * ((360 - to_degree) / 360.))]
        return data


    def process_writing(self):
        print("== triggered writing ==")
        # all letter coorinates are in font_size 100(100mm high)
        self.base_fs = 100.0
        self.centimeter2meter_factor = 0.01
        self.letter_size_factor = float(self.config_fontsize) / self.base_fs

        self.between_letter_margin = self.letter_size_factor * 0.01  # 0.001  # x coordinate
        self.between_line_margin = self.letter_size_factor * 0.03  # y coordinate
        self.letter_height = self.config_fontsize * 0.001  # height of written letters in m

        # print("start write pos: "), current_write_pos

        # at the start of writing go to the start position in linear movement without singularity checking to prevent collisions
        tmp = [[self.nextLetterPos[0], self.nextLetterPos[1], self.hoverOffset]]
        #####self.process_linear_movement(tmp, True, False)

        print("moved to start write pos: [%.4f; %.4f; %.4f]" % (self.config_cur_pos[0], self.config_cur_pos[1], self.config_cur_pos[2]) )

        for letter in self.data_string:
            # search letter in database
            pointlist = self.get_pointlist4letter(letter)
            if not pointlist:
                print(letter), ("WTF! THIS SHOULD NEVER HAPPEN!")
            else:

                #self.process_linear_movement(self.get_circle(1, 360, 90), True, True)


                #self.process_linear_movement([[self.nextLetterPos[0], self.nextLetterPos[1], self.hoverOffset]], True, True)
                dummy = pointlist[0] + self.nextLetterPos
                dummy[2] = self.hoverOffset
                self.process_linear_movement([dummy], True, True)
                self.process_linear_movement([x + self.nextLetterPos for x in pointlist], True, True)
                self.nextLetterPos[1] += ( max([x[1] for x in pointlist]) + self.between_letter_margin)
                if(self.nextLetterPos[1] > self.line_ending_threshold):
                    self.nextLetterPos[0] = self.nextLetterPos[0] + self.letter_height + self.between_line_margin
                    self.nextLetterPos[1] = -self.line_ending_threshold

                # # transform pointlist to current write position     # let out z coordinate
                # max_y_of_pointlist = current_write_pos[1]
                # for point in pointlist:
                #     point[0] = float(point[0]) + current_write_pos[0]
                #     point[1] = float(point[1]) + current_write_pos[1]
                #     if(point[1] > max_y_of_pointlist):
                #         max_y_of_pointlist = point[1]
                #
                #
                # # move from current position to next write position with hoveroffset and then to the write plane
                # toNextLetter = np.array([ np.array([ current_write_pos[0], current_write_pos[1], current_write_pos[2]]),
                #                           np.array([ pointlist[0][0], pointlist[0][1], self.hoverOffset ]),
                #                           np.array([ pointlist[0][0], pointlist[0][1], pointlist[0][2] ]) ])
                # print("toNextLetter: "), toNextLetter
                # self.process_linear_movement(toNextLetter, True, True)
                #
                # # transform pointlist to current position
                # self.process_linear_movement(pointlist, True, True)
                #
                # # move to hover position
                # toHoverPos = np.array([ np.array([ self.config_cur_pos[0], self.config_cur_pos[1], (self.config_cur_pos[2] + self.hoverOffset) ])  ])
                # print("toHoverPos: "), toHoverPos
                # self.process_linear_movement(toHoverPos, True, True)
                #
                # # update current write position
                # current_write_pos = np.array([ self.config_cur_pos[0], self.config_cur_pos[1], self.config_cur_pos[2] ])
                #
                # # before writing the next letter put in a margin after most right position of letter
                # current_write_pos[1] = max_y_of_pointlist + self.between_letter_margin
                #
                # #check for line ending
                # if(current_write_pos[1] > self.line_ending_threshold):
                #     current_write_pos[0] = current_write_pos[0] + self.letter_height + self.between_line_margin
                #     current_write_pos[1] = -self.line_ending_threshold

                print("== letter "), letter, (" done ==")

        print("== writing done ==")


    def get_pointlist4letter(self, letter):
        print("get pointlist for letter: "), letter

        # convert lowercase letters to upper case letters
        letter = letter.upper()
        dbElement = self.ldb_root.find(letter)
        resPointlist = list()
        if (dbElement == None):
            dbElement = self.ldb_root.find("NOT_IMPL")
            print("WARNING: no element found with tag %s!") % (letter)

        if (dbElement != None):
            dbPointlist = list(dbElement)
            isHovering = False
            for point in dbPointlist:
                if point.tag == "point":
                    # handle hover from last point
                    if (isHovering):
                        isHovering = False
                        resPointlist.append(np.array(
                            [float(point.attrib['x']) * self.letter_size_factor * self.centimeter2meter_factor, float(point.attrib['y']) * self.letter_size_factor * self.centimeter2meter_factor,
                             self.hoverOffset]))

                    # append point coordinates
                    resPointlist.append(np.array(
                        [float(point.attrib['x']) * self.letter_size_factor * self.centimeter2meter_factor, float(point.attrib['y']) * self.letter_size_factor * self.centimeter2meter_factor,
                         float(point.attrib['z']) * self.letter_size_factor * self.centimeter2meter_factor]))

                    # handle hover to next point
                    if ( int(point.attrib['hov2nxt']) == 1 ):
                        print("= HOVER2NEXT =")
                        isHovering = True
                        resPointlist.append(np.array(
                            [float(point.attrib['x']) * self.letter_size_factor * self.centimeter2meter_factor, float(point.attrib['y']) * self.letter_size_factor * self.centimeter2meter_factor,
                             self.hoverOffset]))
                elif point.tag == "circle":
                    data = self.get_circle(float(point.attrib['r']), float(point.attrib['from']), float(point.attrib['to']))
                    for x in data:
                        x[0] = ((x[0] + float(point.attrib['x'])) * self.letter_size_factor * self.centimeter2meter_factor)
                        x[1] = ((x[1] + float(point.attrib['y'])) * self.letter_size_factor * self.centimeter2meter_factor)
                        if (isHovering):
                            x[2] = self.hoverOffset
                        resPointlist.append(np.array(x))

                    if ( int(point.attrib['hov2nxt']) == 1 ):
                        print("= HOVER2NEXT =")
                        isHovering = True
                        resPointlist.append(np.array(
                            [float(data[-1][0]), float(data[-1][1]), self.hoverOffset]))



        else:
            print("ERROR: no element found with tag %s!") % (letter)

        return resPointlist



    def process_linear_movement(self, point_list, limit_solution, check_singularities):
        """ takes np.array of 3d points(np.matrix) and processes linear movement from current position to all points

        :param todo
        :type todo
        :returns: todo
        :rtype: todo
        """
        self.config_cur_pos = self.kinematics.direct_kin(self.config_thetas_bogen)
        if self.kinematic_type == "Nummeric":
            print("== using  nummeric kinematics ==")
            resolution = self.res
            erg = [0, 0, 0, 0, 0]
            for point in point_list:
                lastPoint = self.config_cur_pos
                print("lin_move from: "), np.round(lastPoint, 3), (" to: "), np.round(point, 3)
                steps = math.sqrt(sum(i * i for i in point - lastPoint))
                for i in xrange(0, int(resolution * steps)+1):
                    if steps != 0:
                        dummy = lastPoint + ((point - lastPoint) / (resolution * steps)) * i
                        erg = self.kin_num.step_to_point(dummy)
                        self.move_arm(erg, True)
                self.config_cur_pos = np.array(point)
                self.config_thetas_bogen = erg

                last_angles = erg

        else:
            print("== using geometric kinematics ==")
            # calc step size
            step_size = 1./self.res
            # max_step = int(1.0/step_size)

            # init on current angles
            last_angles = self.config_thetas_bogen
            last_condition = -1
            last_condition_vec = -1

            current_condition_match = -1

            # process pointlist
            for i in point_list:
                origin = self.config_cur_pos
                print("lin_move from: "), np.round(origin, 3), (" to: "), i

                move_vec = np.array([i[0] - origin[0], i[1] - origin[1], i[2] - origin[2]])
                move_length = np.sqrt(move_vec[0] ** 2 + move_vec[1] ** 2 + move_vec[2] ** 2)
                step_count_int = int(move_length / step_size) + 1
                step_count_float = move_length / step_size
                # do nothing if distance is zero
                if step_count_float != 0:

                    # check for matching condition
                    last_condition_match = current_condition_match
                    valid_ik_solutions_origin, valid_ik_solutions_condition_origin = self.kinematics.get_valid_inverse_kin_solutions(origin, False, limit_solution, True, -1)
                    valid_ik_solutions_i, valid_ik_solutions_condition_i = self.kinematics.get_valid_inverse_kin_solutions(i, False, limit_solution, True, -1)
                    current_condition_match = -1
                    for a in valid_ik_solutions_condition_origin:
                        if(a in valid_ik_solutions_condition_i):
                            if(current_condition_match == -1):
                                current_condition_match = a
                            if(a == last_condition_match):
                                current_condition_match = a
                                break

                    if(current_condition_match != -1):
                        print("condition match for current line found: "), current_condition_match

                    step_vec = np.array([move_vec[0] / step_count_float, move_vec[1] / step_count_float, move_vec[2] / step_count_float])
                    #print("current point: "), i
                    #print("stepcount: "), step_count_int

                    # process single point out of pointlist (interpolate position changes between letter points)
                    for k in range(1, step_count_int + 1):

                        current_valid = False
                        # for the last step: go to target position
                        if (k == step_count_int):
                            current_trgt = np.array([i[0], i[1], i[2]])
                        # for the other steps
                        else:
                            current_trgt = np.array([origin[0] + k * step_vec[0], origin[1] + k * step_vec[1], origin[2] + k * step_vec[2]])

                        # calc inverse kinematik for current target
                        #valid_ik_solutions, valid_ik_solutions_condition = self.kinematics.get_valid_inverse_kin_solutions(current_trgt, True, limit_solution, True, -1)
                        #if not valid_ik_solutions:
                            # try again without fast calculation
                        if(current_condition_match != -1):
                            valid_ik_solutions, valid_ik_solutions_condition = self.kinematics.get_valid_inverse_kin_solutions(current_trgt, False, limit_solution, True, current_condition_match)
                        else:
                            valid_ik_solutions, valid_ik_solutions_condition = self.kinematics.get_valid_inverse_kin_solutions(current_trgt, False, limit_solution, True, -1)

                        if not valid_ik_solutions:
                            print("Found no ik solution for point(%.4f; %.4f; %.4f). Processing goes on with next point.") % (current_trgt[0], current_trgt[1], current_trgt[2])
                        else:
                            current_valid = True
                        #else:
                        #    current_valid = True

                        if current_valid:

                            # TODO: check for singularities in angles
                            # search solutions without singularities
                            if (check_singularities):
                                valid_sol_nosing = list()
                                valid_sol_nosing_cond = list()
                                int_counter = -1
                                for s in valid_ik_solutions:
                                    int_counter = int_counter + 1
                                    has_sing = False
                                    if (last_condition != -1):
                                        if ( (s[0] > 0.0 and last_angles[0] < 0.0) or (s[0] < 0.0 and last_angles[0] > 0.0)): has_sing = True
                                        if ( (s[1] > 0.0 and last_angles[1] < 0.0) or (s[1] < 0.0 and last_angles[1] > 0.0)): has_sing = True
                                        if ( (s[2] > 0.0 and last_angles[2] < 0.0) or (s[2] < 0.0 and last_angles[2] > 0.0)): has_sing = True
                                        if ( (s[3] > 0.0 and last_angles[3] < 0.0) or (s[3] < 0.0 and last_angles[3] > 0.0)): has_sing = True

                                    if not has_sing:
                                        valid_sol_nosing.append(s)
                                        valid_sol_nosing_cond.append(valid_ik_solutions_condition[int_counter])

                                # if singularity is not preventable, hover and go to new condition
                                if not valid_sol_nosing:
                                    print("!!! SINGULARITY happened !!!")
                                    best_sol = valid_ik_solutions[0]
                                    last_condition = valid_ik_solutions_condition[0]
                                    last_condition_vec = valid_ik_solutions_condition
                                else:
                                    last_condition_tmp = last_condition
                                    best_sol, last_condition, last_condition_vec, condChangeHandleTrgt = self.get_best_sol_through_condition(last_condition, last_condition_vec, valid_sol_nosing, valid_sol_nosing_cond)
                                    #print("cur_condition:"), last_condition
                                    # TODO: if condition changes, handle this
                                    if(condChangeHandleTrgt != -1):
                                        # transfer to condChangeHandleTrgt in the last point through interpolation
                                        print("curPos_tmp: "), lastPos_tmp
                                        handle_steps = 40
                                        conditionDiffStep = (condChangeHandleTrgt - last_condition_tmp) / float(handle_steps)
                                        print("conditionDiffStep: "), conditionDiffStep
                                        for h in range(1, handle_steps + 1):
                                            cur_inter_condition = last_condition_tmp + (h * conditionDiffStep)
                                            print("curpoint: "), lastPos_tmp, ("| cur_inter_condition: "), cur_inter_condition
                                            valid_ik_solutions_tmp, valid_ik_solutions_condition_tmp = self.kinematics.get_valid_inverse_kin_solutions(lastPos_tmp, False, limit_solution, True, cur_inter_condition)
                                            print("valid_ik_solutions_tmp: "), valid_ik_solutions_tmp#, ("| valid_ik_solutions_condition_tmp: "), valid_ik_solutions_condition_tmp
                                            self.move_arm(valid_ik_solutions_tmp[0], True)

                                        # go to current target point under condChangeHandleTrgt
                                        valid_ik_solutions_tmp = self.kinematics.get_valid_inverse_kin_solutions(current_trgt, False, limit_solution, False, condChangeHandleTrgt)
                                        best_sol = valid_ik_solutions_tmp[0]
                                        last_condition = condChangeHandleTrgt

                            else:
                                best_sol = valid_ik_solutions[0]

                            # workaround for bug in condition change handling
                            lastPos_tmp = current_trgt

                            # do the movement
                            self.move_arm(best_sol, True)
                            self.config_cur_pos = np.array([i[0], i[1], i[2]])
                            self.config_thetas_bogen = best_sol

                            last_angles = best_sol

                            # TODO: sending status to gui here produces sometimes memory errors (WTF!)
                            #self.send_status2gui( status.STATUS_NODE_NO_ERROR, status.STATUS_VREP_WAITING_4_CMD, "linear movement in progress...")
                            # sleep a moment to prevent unsynchronization
                            #tmp_wait = 0.1
                            #print("wait")
                            #time.sleep(tmp_wait)     # sleep 0.1 sec
                            #print("waited for "), tmp_wait, ("sec")

                    #self.config_current_pos = np.array([ i[0], i[1], i[2] ])
                    self.send_status2gui(status.STATUS_NODE_NO_ERROR, status.STATUS_VREP_WAITING_4_CMD, "linear movement in progress...")


    def get_best_sol_through_condition(self, last_condition, last_has_no_sing_conditions, solutions, solutions_cond):
        if not solutions:
            print("WARNING: solutions is empty")
            return -1, -1, -1, -1

        if (last_condition == -1):
            # take first solution
            return solutions[0], solutions_cond[0], solutions_cond, -1

        else:
            # take best solution
            int_counter = -1
            for s in solutions_cond:
                int_counter = int_counter + 1
                if (s == last_condition):
                    return solutions[int_counter], s, solutions_cond, -1
            print("WARNING: condition changed in this step")
            print("last_condition: "), last_condition, ("| last has_no_sing_conditions: "), last_has_no_sing_conditions, ("| current has_no_sing_conditions: "), solutions_cond
            # condition change handling --> search matching condition in last and current solution conditions and transfer to found match(condition) in the last point
            # afterwards go on with current point

            match = -1

            for a in last_has_no_sing_conditions:
                if(a in solutions_cond):
                    match = a
                    break

            return solutions[0], solutions_cond[0], solutions_cond, match


    def parse_input_from_gui(self, msg):

        # CONFIG
        self.config_fontsize = int(msg.Fontsize)
        self.config_pencil_length = float(msg.PencilLength)
        self.config_processMode = int(msg.processmode)
        self.res=msg.res

        if self.config_processMode == status.PROCESSING_MODE_PTP_ANGLES:
            tmp = np.deg2rad(np.array([msg.Theta_1,
                            msg.Theta_2,
                            msg.Theta_3,
                            msg.Theta_4,
                            msg.Theta_5]))
            self.config_thetas_bogen =  self.kinematics.offset2world(tmp)

        elif self.config_processMode == status.PROCESSING_MODE_PTP_POSITION or self.config_processMode == status.PROCESSING_MODE_LIN_POSITION:
            self.config_trgt_pos = np.array([msg.Pos_X,
                                             msg.Pos_Y,
                                             msg.Pos_Z])
        #DATA
        self.data_string = msg.letters

    def send_status2gui(self, nodestatus, vrepstatus, error_txt):
        msg = rw_node_state()
        msg.nodestatus = nodestatus
        msg.vrepstatus = vrepstatus
        msg.error = error_txt

        # setting GUI output
        msg.Pos_X = self.config_cur_pos[0]
        msg.Pos_Y = self.config_cur_pos[1]
        msg.Pos_Z = self.config_cur_pos[2]
        tmp = self.kinematics.offset2world(np.rad2deg(self.config_thetas_bogen))
        msg.Theta_1 = tmp[0]
        msg.Theta_2 = tmp[1]
        msg.Theta_3 = tmp[2]
        msg.Theta_4 = tmp[3]
        msg.Theta_5 = tmp[4]

        self.status = nodestatus
        self.status_vrep = vrepstatus
        self.status_string = error_txt
        # set status: [nodestatus;vrepstatus;]
        self.pub2gui.publish(msg)

        #rospy.loginfo("send status 2 gui")
        #rospy.loginfo(commandStr)


if __name__ == '__main__':
    Node()
