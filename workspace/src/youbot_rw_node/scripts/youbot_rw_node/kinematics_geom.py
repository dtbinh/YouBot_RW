#!/usr/bin/env python2

import math
import numpy as np
from numpy.core.multiarray import int_asbuffer
from kinematics_base import Kinematics_base

from numpy import sin, cos, arctan2, arccos
from numpy.core.umath import arccos


class Kinematics_geom(Kinematics_base):
    def __init__(self):
        pass

    def transform2wrist_point_under_condition(self, point, beta):
        # translation to wrist point
        dz = (self.dh[5]['d']+self.dh[6]['d'])
        point_d = np.matrix(( 0., 0., dz, 1. )).transpose()
        #print "point_d: ", point_d

        theta = 0.0

        if float(point[1]) != 0:
            #print "point[1]: ", float(point[1])
            #print "a: ", self.dh[0]['a']
            #calc angle of y diff with triangle rules
            theta =  -1*np.arctan2( float(point[1]), (self.dh[0]['a']-float(point[0])))
            #print "angle_y_diff: ", theta

        # first: rotation around z axis by angle of y diff; second: rotation around y axis by angle of condition
        rotation = np.matrix((  (cos(theta)*cos(beta),      -sin(theta),    cos(theta)*sin(beta),       0),
                                (sin(theta)*cos(beta),      cos(theta),     sin(theta)*sin(beta),       0),
                                (-sin(beta),                0,              cos(beta),                  0),
                                (0,                         0,              0,                          1)  ))

        point_rot = rotation * point_d
        #print "point_rot: ", point_rot

        point_res = (np.matrix((point)) + point_rot )
        point_res[3] = 1

        return point_res


    def resetZeroEquality(self, point):

        for i in range(0,len(point)):
            if np.abs(point[i]) < self.ALMOST_ZERO:
                point[i] = 0

        return point

    def offset2world(self, thetas):
        """ todo

        :param todo
        :type todo
        :returns: todo
        :rtype: todo
        """
        return -thetas


    def offset2world_for_ik_nullconfig(self, thetas):
        """ todo

        :param todo
        :type todo
        :returns: todo
        :rtype: todo
        """
        result = thetas
        result[1] = result[1] - (math.pi/2.0)

        # handle wrong turning direction--> make robot turn the shortest direction
        if result[1] < -np.pi:
            result[1] += np.pi*2
        elif result[1] > np.pi:
            result[1] -= np.pi*2

        return result


    def inverse_kin( self, point , condition_angle):
        """ inverse kinematic calculation

        @param [in] point <b><i><c> [point_type]: </c></i></b> point desc
        @param [in] condition_angle <b><i><c> [condition_angle_type]: </c></i></b> condition_angle desc
        @return <b><i><c> [return_type]: </c></i></b> return desc
        """

        tcp= np.matrix(( float(point[0]), float(point[1]), float(point[2]),float(1) )).transpose()
        #tcp[3]=1                                                         # make homogenous coordinates
        #print "====================================================================="
        #print "tcp: [%.4f; %.4f; %.4f; %.4f]" % (tcp[0],tcp[1],tcp[2], tcp[3])
        #print "tcp: ", tcp.transpose()
        tcp = self.resetZeroEquality(tcp)

        # offset calculate Wrist point under condition that Wrist is condition_angle degree up on write plane
        wp_cond  = self.transform2wrist_point_under_condition(tcp,math.radians(condition_angle))
        wp_cond = self.resetZeroEquality(wp_cond)
        #print "wpoint: [%.4f; %.4f; %.4f; %.4f]" % (wp_cond[0],wp_cond[1],wp_cond[2], wp_cond[3])
        #print "wpoint: ", wp_cond.transpose()

        wp_cond_dz = np.sqrt(( (wp_cond[0]-tcp[0])**2 + (wp_cond[1]-tcp[1])**2 + (wp_cond[2]-tcp[2])**2))
        #print "wpoint_d(0.2375):", wp_cond_dz


        wp_0 = self.get_inv_transform(self.dh[0]) * np.matrix((wp_cond))                    # transform wp into KS0
        tcp_0 = self.get_inv_transform(self.dh[0]) * np.matrix((tcp))
        wp_0 = self.resetZeroEquality(wp_0)
        tcp_0 = self.resetZeroEquality(tcp_0)
        #print "wp_0: [%.4f; %.4f; %.4f; %.4f]" % (wp_0[0],wp_0[1],wp_0[2], wp_0[3])
        #print "wp_0: ", wp_0
        #print "tcp_0: ", tcp_0.transpose()




        theta_0 = np.empty([2])     #theta_0:  [ 3.05370051 -0.08789215]
        theta_0[0]=np.arctan2(wp_0[1],wp_0[0])                 # turn robot arm into wrist point plane

        if theta_0[0] < 0:
            theta_0[1] = theta_0[0] + np.pi
        else:
            theta_0[1] = theta_0[0] - np.pi
        #print "theta_0: [%.4f; %.4f]" % (math.degrees(theta_0[0]),math.degrees(theta_0[1]))
        #print "theta_0: ", theta_0

        wp_1 = np.array([self.get_inv_transform(self.dh[1],float(theta_0[0]))*np.matrix((wp_0)), self.get_inv_transform(self.dh[1],float(theta_0[1]))*np.matrix((wp_0))])       # numpy array of 2 points
        tcp_1 = np.array([self.get_inv_transform(self.dh[1],float(theta_0[0]))*np.matrix((tcp_0)), self.get_inv_transform(self.dh[1],float(theta_0[1]))*np.matrix((tcp_0)) ])       # numpy array of 2 points
        wp_1[0] = self.resetZeroEquality(wp_1[0])
        wp_1[1] = self.resetZeroEquality(wp_1[1])
        tcp_1[0] = self.resetZeroEquality(tcp_1[0])
        tcp_1[1] = self.resetZeroEquality(tcp_1[1])

        #print "wp_1_0: [%.4f; %.4f; %.4f; %.4f]" % (wp_1[0][0],wp_1[0][1],wp_1[0][2], wp_1[0][3])
        #print "wp_1_0: ", wp_1[0].transpose()
        #print "wp_1_1: [%.4f; %.4f; %.4f; %.4f]" % (wp_1[1][0],wp_1[1][1],wp_1[1][2], wp_1[1][3])
        #print "wp_1_1: ", wp_1[1].transpose()

        #print "tcp_1_0(z zero): ", tcp_1[0].transpose()
        #print "tcp_1_1(z zero): ", tcp_1[1].transpose()

        d_wp_1 = np.array(( np.sqrt((wp_1[0][0]**2 + wp_1[0][1]**2)),np.sqrt((wp_1[1][0]**2 + wp_1[1][1]**2)) ))    # array of 2 distances
        #print "d_wp_1: ", d_wp_1

        s=np.array([arctan2(wp_1[0][1],wp_1[0][0]),arctan2(wp_1[1][1],wp_1[1][0])])                                 # array of 2 angles
        #print "s: [%.4f; %.4f]" % (math.degrees(s[0]), math.degrees(s[1]))
        #print "r arcos 0: ", (self.dh[3]['a']**2-d_wp_1[0]**2-self.dh[2]['a']**2) / (-2*d_wp_1[0]*self.dh[2]['a'])
        #print "r arcos 1: ", (self.dh[3]['a']**2-d_wp_1[1]**2-self.dh[2]['a']**2) / (-2*d_wp_1[1]*self.dh[2]['a'])

        acos_content = np.array(( ( (self.dh[3]['a']**2-d_wp_1[0]**2-self.dh[2]['a']**2) / (-2*d_wp_1[0]*self.dh[2]['a']) ),
                                  ( (self.dh[3]['a']**2-d_wp_1[1]**2-self.dh[2]['a']**2) / (-2*d_wp_1[1]*self.dh[2]['a']) ) ))

        r = np.array([float('nan'),float('nan')])
        if acos_content[0] < 1 and acos_content[0] > -1:
            r[0]= arccos( acos_content[0] )
        if acos_content[1] < 1 and acos_content[1] > -1:
            r[1]= arccos( acos_content[1] )

        #print "r: [%.4f; %.4f]" % (math.degrees(r[0]), math.degrees(r[1]))

        theta_1_0 = np.empty([2])                                                                                   #array of 2 angles
        theta_1_1 = np.empty([2])                                                                                   #array of 2 angles

        theta_1_0[0] = (s[0]+r[0]) - math.pi/2.0
        theta_1_0[1] = (s[0]-r[0]) - math.pi/2.0
        theta_1_1[0] = (s[1]+r[1]) - math.pi/2.0
        theta_1_1[1] = (s[1]-r[1]) - math.pi/2.0

        # handle wrong turning direction--> make robot turn the shortest direction
        for i in range(0,len(theta_1_0)):
            if theta_1_0[i] < -np.pi:
                theta_1_0[i] += np.pi*2
            elif theta_1_0[i] > np.pi:
                theta_1_0[i] -= np.pi*2
        for i in range(0,len(theta_1_1)):
            if theta_1_1[i] < -np.pi:
                theta_1_1[i] += np.pi*2
            elif theta_1_1[i] > np.pi:
                theta_1_1[i] -= np.pi*2

        #print "theta_1_0: [%.4f; %.4f]" % (math.degrees(theta_1_0[0]), math.degrees(theta_1_0[1]))
        #print "theta_1_1: [%.4f; %.4f]" % (math.degrees(theta_1_1[0]), math.degrees(theta_1_1[1]))

        wp_2=  np.array([self.get_inv_transform(self.dh[2],theta_1_0[0])*np.matrix((wp_1[0])), self.get_inv_transform(self.dh[2],theta_1_0[1])*np.matrix((wp_1[0])) ,     # numpy array of 4 points
                         self.get_inv_transform(self.dh[2],theta_1_1[0])*np.matrix((wp_1[1])), self.get_inv_transform(self.dh[2],theta_1_1[1])*np.matrix((wp_1[1])) ])
        tcp_2=  np.array([self.get_inv_transform(self.dh[2],theta_1_0[0])*np.matrix((tcp_1[0])), self.get_inv_transform(self.dh[2],theta_1_0[1])*np.matrix((tcp_1[0])) ,     # numpy array of 4 points
                         self.get_inv_transform(self.dh[2],theta_1_1[0])*np.matrix((tcp_1[1])), self.get_inv_transform(self.dh[2],theta_1_1[1])*np.matrix((tcp_1[1])) ])
        wp_2[0] = self.resetZeroEquality(wp_2[0])
        wp_2[1] = self.resetZeroEquality(wp_2[1])
        wp_2[2] = self.resetZeroEquality(wp_2[2])
        wp_2[3] = self.resetZeroEquality(wp_2[3])
        tcp_2[0] = self.resetZeroEquality(tcp_2[0])
        tcp_2[1] = self.resetZeroEquality(tcp_2[1])
        tcp_2[2] = self.resetZeroEquality(tcp_2[2])
        tcp_2[3] = self.resetZeroEquality(tcp_2[3])

        #print "wp_2: ", wp_2
        #print "wp_2_0: [%.4f; %.4f; %.4f; %.4f]" % (wp_2[0][0],wp_2[0][1],wp_2[0][2], wp_2[0][3])
        #print "wp_2_1: [%.4f; %.4f; %.4f; %.4f]" % (wp_2[1][0],wp_2[1][1],wp_2[1][2], wp_2[1][3])
        #print "wp_2_3: [%.4f; %.4f; %.4f; %.4f]" % (wp_2[2][0],wp_2[2][1],wp_2[2][2], wp_2[2][3])
        #print "wp_2_4: [%.4f; %.4f; %.4f; %.4f]" % (wp_2[3][0],wp_2[3][1],wp_2[3][2], wp_2[3][3])
        #print "wp_2_0: ", wp_2[0]
        #print "wp_2_1: ", wp_2[1]
        #print "wp_2_2: ", wp_2[2]
        #print "wp_2_3: ", wp_2[3]

        #print "tcp_2_0(z zero): ", tcp_2[0].transpose()
        #print "tcp_2_1(z zero): ", tcp_2[1].transpose()
        #print "tcp_2_2(z zero): ", tcp_2[2].transpose()
        #print "tcp_2_3(z zero): ", tcp_2[3].transpose()

        theta_2_0 = np.empty([2])                                                                                   #array of 2 angles
        theta_2_1 = np.empty([2])                                                                                   #array of 2 angles

        theta_2_0[0] = arctan2(wp_2[0][1], wp_2[0][0])
        theta_2_0[1] = arctan2(wp_2[1][1], wp_2[1][0])
        theta_2_1[0] = arctan2(wp_2[2][1], wp_2[2][0])
        theta_2_1[1] = arctan2(wp_2[3][1], wp_2[3][0])

        #print "theta_2_0: [%.4f; %.4f]" % (math.degrees(theta_2_0[0]), math.degrees(theta_2_0[1]))
        #print "theta_2_1: [%.4f; %.4f]" % (math.degrees(theta_2_1[0]), math.degrees(theta_2_1[1]))

        wp_3=  np.array([  self.get_inv_transform(self.dh[3],theta_2_0[0])*np.matrix((wp_2[0])), self.get_inv_transform(self.dh[3],theta_2_0[1])*np.matrix((wp_2[1])) ,     # numpy array of 4 points
                           self.get_inv_transform(self.dh[3],theta_2_1[0])*np.matrix((wp_2[2])), self.get_inv_transform(self.dh[3],theta_2_1[1])*np.matrix((wp_2[3])) ])
        tcp_3=  np.array([  self.get_inv_transform(self.dh[3],theta_2_0[0])*np.matrix((tcp_2[0])), self.get_inv_transform(self.dh[3],theta_2_0[1])*np.matrix((tcp_2[1])) ,     # numpy array of 4 points
                            self.get_inv_transform(self.dh[3],theta_2_1[0])*np.matrix((tcp_2[2])), self.get_inv_transform(self.dh[3],theta_2_1[1])*np.matrix((tcp_2[3])) ])

        wp_3[0] = self.resetZeroEquality(wp_3[0])
        wp_3[1] = self.resetZeroEquality(wp_3[1])
        wp_3[2] = self.resetZeroEquality(wp_3[2])
        wp_3[3] = self.resetZeroEquality(wp_3[3])
        tcp_3[0] = self.resetZeroEquality(tcp_3[0])
        tcp_3[1] = self.resetZeroEquality(tcp_3[1])
        tcp_3[2] = self.resetZeroEquality(tcp_3[2])
        tcp_3[3] = self.resetZeroEquality(tcp_3[3])

        #print "wp_3: ", wp_3
        #print "wp_3_0: [%.4f; %.4f; %.4f; %.4f]" % (wp_3[0][0],wp_3[0][1],wp_3[0][2], wp_3[0][3])
        #print "wp_3_1: [%.4f; %.4f; %.4f; %.4f]" % (wp_3[1][0],wp_3[1][1],wp_3[1][2], wp_3[1][3])
        #print "wp_3_2: [%.4f; %.4f; %.4f; %.4f]" % (wp_3[2][0],wp_3[2][1],wp_3[2][2], wp_3[2][3])
        #print "wp_3_3: [%.4f; %.4f; %.4f; %.4f]" % (wp_3[3][0],wp_3[3][1],wp_3[3][2], wp_3[3][3])
        #print "wp_3_0(zero): ", wp_3[0].transpose()
        #print "wp_3_1(zero): ", wp_3[1].transpose()
        #print "wp_3_2(zero): ", wp_3[2].transpose()
        #print "wp_3_3(zero): ", wp_3[3].transpose()
        # wp_3 must be zero if all is correct

        #print "tcp_3_0: [%.4f; %.4f; %.4f; %.4f]" % (tcp_3[0][0],tcp_3[0][1],tcp_3[0][2], tcp_3[0][3])
        #print "tcp_3_1: [%.4f; %.4f; %.4f; %.4f]" % (tcp_3[1][0],tcp_3[1][1],tcp_3[1][2], tcp_3[1][3])
        #print "tcp_3_2: [%.4f; %.4f; %.4f; %.4f]" % (tcp_3[2][0],tcp_3[2][1],tcp_3[2][2], tcp_3[2][3])
        #print "tcp_3_3: [%.4f; %.4f; %.4f; %.4f]" % (tcp_3[3][0],tcp_3[3][1],tcp_3[3][2], tcp_3[3][3])
        #print "tcp_3_0(z zero): ", tcp_3[0].transpose()
        #print "tcp_3_1(z zero): ", tcp_3[1].transpose()
        #print "tcp_3_2(z zero): ", tcp_3[2].transpose()
        #print "tcp_3_3(z zero): ", tcp_3[3].transpose()

        tcp_3_norm = np.array(( np.sqrt((tcp_3[0][0]**2 + tcp_3[0][1]**2 + tcp_3[0][2]**2)), np.sqrt((tcp_3[1][0]**2 + tcp_3[1][1]**2 + tcp_3[1][2]**2)),
                                np.sqrt((tcp_3[2][0]**2 + tcp_3[2][1]**2 + tcp_3[2][2]**2)), np.sqrt((tcp_3[3][0]**2 + tcp_3[3][1]**2 + tcp_3[3][2]**2))  ))
        #print "tcp_3_norms(all 0.2375): ", tcp_3_norm.transpose()

        # should be as long as 0.2375

        theta_3_0 = np.empty([2])                                                                                   #array of 2 angles
        theta_3_1 = np.empty([2])                                                                                   #array of 2 angles

        theta_3_0[0] = arctan2(tcp_3[0][1], tcp_3[0][0])
        theta_3_0[1] = arctan2(tcp_3[1][1], tcp_3[1][0])
        theta_3_1[0] = arctan2(tcp_3[2][1], tcp_3[2][0])
        theta_3_1[1] = arctan2(tcp_3[3][1], tcp_3[3][0])


        tcp_4=  np.array([  self.get_inv_transform(self.dh[4],theta_3_0[0])*np.matrix((tcp_3[0])),
                            self.get_inv_transform(self.dh[4],theta_3_0[1])*np.matrix((tcp_3[1])),     # numpy array of 4 points
                            self.get_inv_transform(self.dh[4],theta_3_1[0])*np.matrix((tcp_3[2])),
                            self.get_inv_transform(self.dh[4],theta_3_1[1])*np.matrix((tcp_3[3]))   ])
        tcp_4[0] = self.resetZeroEquality(tcp_4[0])
        tcp_4[1] = self.resetZeroEquality(tcp_4[1])
        tcp_4[2] = self.resetZeroEquality(tcp_4[2])
        tcp_4[3] = self.resetZeroEquality(tcp_4[3])


        #print "tcp_4_0(z 0.2375): ", tcp_4[0].transpose()
        #print "tcp_4_1(z 0.2375): ", tcp_4[1].transpose()
        #print "tcp_4_2(z 0.2375): ", tcp_4[2].transpose()
        #print "tcp_4_3(z 0.2375): ", tcp_4[3].transpose()

        tcp_4_norm = np.array(( np.sqrt((tcp_4[0][0]**2 + tcp_4[0][1]**2 + tcp_4[0][2]**2)), np.sqrt((tcp_4[1][0]**2 + tcp_4[1][1]**2 + tcp_4[1][2]**2)),
                                np.sqrt((tcp_4[2][0]**2 + tcp_4[2][1]**2 + tcp_4[2][2]**2)), np.sqrt((tcp_4[3][0]**2 + tcp_4[3][1]**2 + tcp_4[3][2]**2))  ))
        #print "tcp_4_norms(all 0.2375): ", tcp_4_norm.transpose()
        # should be as long as 0.2375

        tcp_6=  np.array([  self.get_inv_transform(self.dh[6],0.)*self.get_inv_transform(self.dh[5],0.) * np.matrix((tcp_4[0])),
                            self.get_inv_transform(self.dh[6],0.)*self.get_inv_transform(self.dh[5],0.) * np.matrix((tcp_4[1])),     # numpy array of 4 points
                            self.get_inv_transform(self.dh[6],0.)*self.get_inv_transform(self.dh[5],0.) * np.matrix((tcp_4[2])),
                            self.get_inv_transform(self.dh[6],0.)*self.get_inv_transform(self.dh[5],0.) * np.matrix((tcp_4[3]))     ])

        tcp_6[0] = self.resetZeroEquality(tcp_6[0])
        tcp_6[1] = self.resetZeroEquality(tcp_6[1])
        tcp_6[2] = self.resetZeroEquality(tcp_6[2])
        tcp_6[3] = self.resetZeroEquality(tcp_6[3])

        #print "tcp_6_0(zero): ", tcp_6[0].transpose()
        #print "tcp_6_1(zero): ", tcp_6[1].transpose()
        #print "tcp_6_2(zero): ", tcp_6[2].transpose()
        #print "tcp_6_3(zero): ", tcp_6[3].transpose()
        # should be zero


        result = list()
        result.append(np.array([ theta_0[0], theta_1_0[0], theta_2_0[0], theta_3_0[0], 0.0 ]))
        result.append(np.array([ theta_0[0], theta_1_0[1], theta_2_0[1], theta_3_0[1], 0.0 ]))
        result.append(np.array([ theta_0[1], theta_1_1[0], theta_2_1[0], theta_3_1[0], 0.0 ]))
        result.append(np.array([ theta_0[1], theta_1_1[1], theta_2_1[1], theta_3_1[1], 0.0 ]))



        for i in result:
            #i = self.offset2world_for_ik_nullconfig(i)
            #print "[%.4f; %.4f; %.4f; %.4f; %.4f;]" % (math.degrees(i[0]), math.degrees(i[1]), math.degrees(i[2]), math.degrees(i[3]), math.degrees(i[4]) ) , self.isSolutionValid(i)
            dk_pos = self.direct_kin(i)
            #print "     dk_pos: [%.4f; %.4f; %.4f]" % (dk_pos[0],dk_pos[1],dk_pos[2])
            #print "     dk_pos: ", dk_pos.transpose()

            dk_pos_wp = self.direct_kin_2_wristPoint(i)
            #print "     dk_pos_wp: [%.4f; %.4f; %.4f]" % (dk_pos_wp[0],dk_pos_wp[1],dk_pos_wp[2])
            #print "     dk_pos_wp: ", dk_pos_wp.transpose()

        #print "====================================================================="
        return result


    def isSolutionValid(self, solution):
        """ todo

        :param todo
        :type todo
        :returns: todo
        :rtype: todo
        """
        if len(solution) != 5:
            #print("length is not 5!")
            return False
        for i in range(0,len(solution)):
            if math.isnan(solution[i]):
                #print("index"), i, ("is nan!")
                return False
            elif solution[i] < self.min_angles_[i] or solution[i] > self.max_angles_[i]:
                #print("index:"), i, (" %.4f [%.4f; %.4f]") %(solution[i], self.min_angles_[i], self.max_angles_[i])
                return False

        return True


    def get_valid_inverse_kin_solutions(self, point, fastCalc, limit_solution, return_conditions, trgt_condition):
        """ todo

        :param todo
        :type todo
        :returns: todo
        :rtype: todo
        """
        debug = False

        #ik_solutions = self.inverse_kin(point, condition_angle)
        condition_angle = np.array
        if(trgt_condition != -1):
            condition_angle = np.array([trgt_condition])
        else:
            if(fastCalc):
                condition_angle = np.array([ 5.0, 25.0, 45.0, 65])
            else:
                condition_angle = np.array([ 0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0 , 50.0, 55.0, 60.0, 65.0])
        #ik_solutions = list()
        #ik_solutions_condition = list()

        #print("ik_point: "), point, ("ik_condition_angle_vec: "), condition_angle

        valid_solutions = list()
        valid_solutions_condition = list()
        found_Solution = False
        for i in range(0,len(condition_angle)):
            if(debug):
                if(found_Solution):
                    break
            #print "condition: ", condition_angle[i]
            tmpSol =  self.inverse_kin(point, condition_angle[i])
            #print("raw ik Sol: "), tmpSol
            for k in tmpSol:
                if self.isSolutionValid(k) == True:
                    if not (limit_solution):
                        valid_solutions.append(k)
                        valid_solutions_condition.append(condition_angle[i])
                    else:
                        if(k[0] < (np.pi/2) and k[0] > -(np.pi/2)):
                            valid_solutions.append(k)
                            valid_solutions_condition.append(condition_angle[i])
                            if(debug):
                                found_Solution = True
                                break

        if(debug):
            #refinement
            found_refinement = False
            tmp_cond_angle = valid_solutions_condition[0]
            tmp_valid_solution = valid_solutions[0]
            while(found_refinement == False):
                cur_cond_angle = tmp_cond_angle - 0.1

                tmpSol =  self.inverse_kin(point, cur_cond_angle)
                oneSolIsValid = False
                for k in tmpSol:
                    if self.isSolutionValid(k) == True:
                        if(k[0] < (np.pi/2) and k[0] > -(np.pi/2)):
                            cur_valid_solution = k
                            oneSolIsValid = True
                            break
                if(oneSolIsValid == False):
                    found_refinement = True
                else:
                    tmp_cond_angle = cur_cond_angle
                    tmp_valid_solution = cur_valid_solution

            valid_solutions[0] = tmp_valid_solution
            valid_solutions_condition[0] = tmp_cond_angle

        #valid_solutions = list()
        #valid_solutions_condition = list()
        #int_count = -1
        #for i in ik_solutions:
        #    int_count = int_count + 1
        #    if self.isSolutionValid(i) == True:
        #        if not (limit_solution):
        #            valid_solutions.append(i)
        #            valid_solutions_condition.append(ik_solutions_condition[int_count])
       #         else:
       #             if(i[0] < (np.pi/2) and i[0] > -(np.pi/2)):
       #                 valid_solutions.append(i)
       #                 valid_solutions_condition.append(ik_solutions_condition[int_count])

        #print "valid solutions:"
        #print valid_solutions, valid_solutions_condition
        #int_count = -1
        #for i in valid_solutions:
        #    int_count = int_count + 1

         #   print "   %.f  [%.4f; %.4f; %.4f; %.4f; %.4f]" % (valid_solutions_condition[int_count], math.degrees(i[0]), math.degrees(i[1]), math.degrees(i[2]), math.degrees(i[3]), math.degrees(i[4]) )
            #dk_pos = self.direct_kin(i)
            #print "             dk_pos: [%.4f; %.4f; %.4f]" % (dk_pos[0],dk_pos[1],dk_pos[2])


        if(return_conditions):
            return valid_solutions, valid_solutions_condition
        else:
            return valid_solutions
