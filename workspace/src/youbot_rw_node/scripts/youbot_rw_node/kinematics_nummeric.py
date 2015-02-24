#!/usr/bin/env python2

import math
import sys
import numpy as np
from numpy import sin, cos
from time import sleep
from numpy import sin, cos, arctan2, arccos
from scipy.optimize import minimize
from sensor_msgs.msg import JointState
from vrep_common.srv import *
from vrep_controll import *
from sync import *

from numpy.core.umath import arccos

import rospy
from std_msgs.msg import Float64
from kinematics_base import Kinematics_base


class Kinematics_num(Kinematics_base):
    destination_point = np.array([0, 0, 0])
    last_solution = np.array([-4.5284128798882501e-09, 0.84351333295648456, 1.2692013125752315, 0.014612536532375684, 0])
    last_point = np.array([0, 0, 0])
    init_point = np.array([-4.5284128798882501e-09, 0.84351333295648456, 1.2692013125752315, 0.014612536532375684, 0])


    def __init__(self):
        self.last_solution = self.minimize(self.last_solution)
        # print self.last_solution

    def err_function(self, thetas):
        """ Error function used for optimisation

        @param [in] thetas <b><i><c> [vector-4]: </c></i></b> Arm-Joint Angles in radians.
        @return <b><i><c> [skalar]: </c></i></b> Error of thetas to point
        """
        new_theta = [thetas[0], thetas[1], thetas[2], thetas[3], 0]
        errors = self.direct_kin(new_theta) - self.destination_point
        return (errors ** 2).sum()

    def ist_rund(self, point):
        """ check point is around destination_point
        @param [in] point <b><i><c> [vector-3]: </c></i></b> point to check
        @return <b><i><c> [bool]: </c></i></b> true if point near to destination_point
        """
        if abs(point[0] - self.destination_point[0]) > 0.03:
            return False
        if abs(point[1] - self.destination_point[1]) > 0.03:
            return False
        if abs(point[2] - self.destination_point[2]) > 0.03:
            return False
        return True


    def update_progresss(self, progress):
        """ updates Progressbar
        @param [in] progress <b><i><c> [skalar]: </c></i></b> point percent of progress
        """
        sys.stdout.write('\r[{0}{1}] {2:3.2f}%'.format('#' * (int(progress / 2)), ' ' * ((100 / 2) - (int(progress / 2))), progress))
        sys.stdout.flush()


    def search_all_solutions(self, point, resolution):
        """ solves the inverse kinematics problem (brute force)
        @param [in] point <b><i><c> [vector-3]: </c></i></b> point to reach
        @param [in] resolution <b><i><c> [skalar]: </c></i></b> search resolution in degree
        @return <b><i><c> [list of vector-4]: </c></i></b> solutions found
        """
        resolution = math.fabs(resolution)
        self.destination_point = point
        solutions = list()
        print "Caluclating solutions..."
        print "Resolution: ", resolution

        wp = np.matrix(np.resize(point, 4)).transpose()
        wp[3] = 1  # make homogenous coordinates

        wp_0 = self.get_inv_transform(self.dh[0]) * wp
        theta_0 = np.empty([2])
        theta_0[0] = arctan2(wp_0[1], wp_0[0])
        if theta_0[0] < 0:
            theta_0[1] = theta_0[0] + np.pi
        else:
            theta_0[1] = theta_0[0] - np.pi
        theta0 = list()
        for solution in theta_0:
            if self.isSolutionValid_single(solution, 0):
                theta0.append(solution)

        print "{a} possible solutions".format(a=(155 * 297 * 204 * len(theta0)) / resolution)

        resolution = math.radians(resolution)
        percent = 0
        for i in theta0:
            i1 = self.min_angles_[1]
            while i1 <= self.max_angles_[1]:
                progress = percent + (((i1 - self.min_angles_[1]) / (self.max_angles_[1] - self.min_angles_[1]) * 100) / len(theta0))
                self.update_progresss(progress)
                i2 = self.min_angles_[2]
                while i2 <= self.max_angles_[2]:
                    i3 = self.min_angles_[3]
                    while i3 <= self.max_angles_[3]:
                        thetas = [i, i1, i2, i3, 0]
                        tmp = self.direct_kin(thetas)
                        if self.ist_rund(tmp) and self.direct_kin_wp(thetas)[2] > 0.1:
                            solutions.append(thetas)

                        i3 += (204 / 155.) * resolution
                    i2 += (297 / 155.) * resolution
                i1 += resolution
            percent += 50
        self.update_progresss(100)
        print "\n{a} Solutions found!".format(a=len(solutions))
        return solutions


    def find_best_solution(self, solutions):
        """ finds and optimizes the best solution from a list of solutions
        @param [in] solutions <b><i><c> [list of vector-4]: </c></i></b> list of solutions
        @return <b><i><c> [vector-4]: </c></i></b> best solution
        """
        best_sol = np.array(solutions.pop(0))
        min = self.err_function(best_sol)
        for sol in solutions:
            if self.err_function(sol) < min:
                min = self.err_function(sol)
                best_sol = np.array(sol)

        tmp = np.degrees(best_sol)
        ##print "BestSolution: [  {0:5.2f} , {1:5.2f} , {2:5.2f} , {3:5.2f}  , {4:5.2f}  ]".format(tmp[0],tmp[1],tmp[2],tmp[3], tmp[4])
        print "BestSolution:", np.degrees(best_sol)
        print "Error:", min

        new_thetas = self.minimize(best_sol)
        print "optimized Solution: ", np.round(np.degrees(new_thetas), 2)
        print "optimized Error:", self.err_function(new_thetas)
        print "Point: ", self.direct_kin(new_thetas)
        print "z-Axes: ", self.direct_kin_wp(new_thetas)[2]

        return new_thetas


    def step_to_point(self, point):
        """ gets an solution to reach point if possible, uses optimizer or brute force if necessary
        @param [in] point <b><i><c> [vector-3]: </c></i></b> point to reach
        @return <b><i><c> [vector-4]: </c></i></b> joint states (solution)
        """

        # print "Distance from arm: ", math.sqrt((point[0]+0.35)**2+(point[1])**2)
        #if math.sqrt((point[0] + 0.35) ** 2 + (point[1]) ** 2) > 0.50:
        #    print "Point is not reachable"
        #    return None

        self.last_point = self.destination_point
        self.destination_point = point
        if self.last_solution is None:
            self.last_solution = self.find_best_solution(self.search_all_solutions(point, 6))

        erg = self.minimize(self.last_solution)

        if self.checkSolution(erg):
            return erg
        else:
            init_res = 10
            erg = self.minimize(self.init_point)
            while not self.checkSolution(erg):
                if init_res < 9:
                    print "Point is not reachable, resolution 2 smal?"
                    return None
                test = self.search_all_solutions(point, init_res)
                if len(test) > 0:
                    erg = self.find_best_solution(test)
                    if not self.checkSolution(erg):
                        print "Point is not reachable, error to high!"
                        return None

                init_res -= 1

        self.last_solution = erg
        return erg


    def checkSolution(self, solution):
        """ Checked solution on validity and fault tolerance
        @param [in] solution <b><i><c> [vector-4]: </c></i></b> solution to check
        @return <b><i><c> [bool]: </c></i></b> true if solution is good
        """
        if self.err_function(solution) > 0.0001 or not self.isSolutionValid(solution):
            return False
        else:
            return True

    def distance(point, last_solution):
        return 0

    def minimize(self, startPoint):
        """ minimize the distance to destination point

        @param [in] startPoint <b><i><c> [vector-4]: </c></i></b> Point to start the optimisation (Joint-Angles)
        @return <b><i><c> [vector-5]: </c></i></b> hopefully a solution of the ik problem
        """
        erg = minimize(self.err_function, startPoint[0:4], method='SLSQP', options={'maxiter': 1e6, 'disp': False},
                       bounds=[(self.min_angles_[0], self.max_angles_[0]), (self.min_angles_[1], self.max_angles_[1]),
                               (self.min_angles_[2], self.max_angles_[2]), (self.min_angles_[3], self.max_angles_[3])])
        return [erg.x[0], erg.x[1], erg.x[2], erg.x[3], 0]


    def isSolutionValid(self, solution):
        """ checks the solution validity, (angle bounds)
        @param [in] solution <b><i><c> [vector-4]: </c></i></b> solution solution to check
        @return <b><i><c> [bool]: </c></i></b> true if solution is valid
        """
        if len(solution) != 5:
            return False
        for i in range(0, len(solution)):
            if math.isnan(solution[i]):
                return False
            elif solution[i] < self.min_angles_[i] or solution[i] > self.max_angles_[i]:
                return False
        if (self.direct_kin_wp(solution)[2] < 0.1):
            return False
        return True


    def isSolutionValid_single(self, solution, number):
        """ checks the solution validity for only one angle, (angle bounds)
        @param [in] solution <b><i><c> [vector-4]: </c></i></b> solution to check
        @param [in] number <b><i><c> [skalar]: </c></i></b> number of angle to check
        @return <b><i><c> [bool]: </c></i></b> true if angle is OK
        """
        if solution < self.min_angles_[number] or solution > self.max_angles_[number]:
            return False

        return True



test = Kinematics_num()

rospy.init_node('kinPublisher', anonymous=True)

pub = rospy.Publisher('/youbot_rw/vrep/arm_joint1_target', Float64, queue_size=10)
pub1 = rospy.Publisher('/youbot_rw/vrep/arm_joint2_target', Float64, queue_size=10)
pub2 = rospy.Publisher('/youbot_rw/vrep/arm_joint3_target', Float64, queue_size=10)
pub3 = rospy.Publisher('/youbot_rw/vrep/arm_joint4_target', Float64, queue_size=10)
pub4 = rospy.Publisher('/youbot_rw/vrep/arm_joint5_target', Float64, queue_size=10)

# erg = test.step_to_point([0,0,0])

init_sync()

stopSimualtion()
TriggerSimualtion()

startSimualtion()
TriggerSimualtion()
TriggerSimualtion()
startSimualtion()
TriggerSimualtion()
TriggerSimualtion()

setSyncSimualtion()
TriggerSimualtion()

startSimualtion()
TriggerSimualtion()
TriggerSimualtion()



def linearMovement2Point(point, resolution=1000):
        lastPoint = test.last_point
        steps=math.sqrt(sum(i*i for i in point-lastPoint))
        print steps
        for i in xrange(0,int(resolution*steps),1):
            dummy = lastPoint+((point-lastPoint)/(resolution*steps))*i
            erg=test.step_to_point(dummy)
            pub.publish(erg[0])
            pub1.publish(erg[1])
            pub2.publish(erg[2])
            pub3.publish(erg[3])
            pub4.publish(erg[4])
            wait_untel_pos_eq(erg)


def linearAngleMovement2Point(point, resolution=100):
        angle = np.array(test.step_to_point(point))
        test.last_point=np.array(point)
        if angle is not None:
            joint_pos = getJointPostition()
            steps=math.sqrt(sum(i*i for i in joint_pos-angle))
            for i in xrange(0,int(resolution*steps),1):
                erg=joint_pos + (((angle-joint_pos)/(resolution*steps))*i)
                pub.publish(erg[0])
                pub1.publish(erg[1])
                pub2.publish(erg[2])
                pub3.publish(erg[3])
                pub4.publish(erg[4])
                wait_untel_pos_eq(erg)



linearAngleMovement2Point([0,0,0.02])
linearMovement2Point([0,0,0])
linearMovement2Point([0.2,0.2,0.0])
linearMovement2Point([0.2,0.0,0.0])


#
#
# for i in xrange(0, 210, 1):
#     erg = test.step_to_point([-0.05 + i / 1000., 0.0, 0.04])
#     if erg is not None:
#         pub.publish(erg[0])
#         pub1.publish(erg[1])
#         pub2.publish(erg[2])
#         pub3.publish(erg[3])
#         pub4.publish(erg[4])
#         pub.publish(erg[0])
#         pub1.publish(erg[1])
#         pub2.publish(erg[2])
#         pub3.publish(erg[3])
#         pub4.publish(erg[4])
#         pub.publish(erg[0])
#         pub1.publish(erg[1])
#         pub2.publish(erg[2])
#         pub3.publish(erg[3])
#         pub4.publish(erg[4])
#         wait_untel_pos_eq(erg)
#     else:
#         stopSimualtion()
#     print "Step: ", i

TriggerSimualtion()
unsetSyncSimualtion()
TriggerSimualtion()
pauseSimualtion()
TriggerSimualtion()