import numpy as np
import time
import pylibmc
import argparse
import logging
import tkinter as tk
from collections import deque

# keys for memcached
keyControllerToRobot = 'Controller.Robot'
keyControllerToRobotCorrect = 'Controller.Correct'
keyRobotToSensor = 'Sensor.Robot'

# logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Robot:
    def __init__(self, vector=np.array([0.0, 0.0, 0.0]), random_error_y=True, verbose=True):
        # The current location of the robot. Defaults to [0.0, 0.0, 0.0]
        self.location = vector

        # client for connecting to memcached.
        self.memcache_client = pylibmc.Client(['localhost'], binary=True, behaviors={"tcp_nodelay": True, "ketama": True})

        # Structure for queueing commands that are sent from the controller.
        # Commands are a 3-dimension numpy array
        self.commands = deque()

        # Boolean parameter that causes the robot to randomly error on the y-axis if set to True.
        self.random_error_y = random_error_y

        # Verbose logging
        self.verbose = verbose

    # Accessor functino to return robot's current location
    def getPosition(self):
        return self.location

    # Moves the robot
    # @param vector The value to move the robot by.
    # An error component is randomly chosen if random_error_y is True.
    def processMove(self, vector):
        self.location += vector
        if self.random_error_y:
            # choose between 0 and 1.
            chance = np.random.randint(2)

            # choose a floating point number between 0 and 1.
            # value is added to robot's location if chance > 0.
            error = chance * np.random.uniform(0, 1, size=1)[0]
            self.location += [0.0, error, 0.0]

    # Function to pop the latest command from the controller. Calls processMove to move the robot.
    def fetchAndMove(self):
        vector = self.commands.popleft()
        if type(vector).__module__ == np.__name__:
            self.processMove(vector)
        return vector

    # Receives data from the controller using data from the keyControllerToRobot and keyControllerToRobotCorrect keys
    # Only applies correctional movement if data from keyControllerToRobotCorrect is found.
    def receiveDataFromController(self):
        vector = self.memcache_client.get(keyControllerToRobot)
        correction = self.memcache_client.get(keyControllerToRobotCorrect)
        if type(vector).__module__ == np.__name__:
            if correction is not None:
                vector[1] += correction[1]
                self.memcache_client.delete(keyControllerToRobotCorrect)
            self.commands.append(vector)
            self.memcache_client.delete(keyControllerToRobot)

    # Function to communicate robot's position to the sensor. Sends data to the keyRobotToSensor key.
    def sendPositionToSensor(self):
        position = self.getPosition()
        if self.memcache_client.get(keyRobotToSensor) is not None:
            self.memcache_client.delete(keyRobotToSensor)
        self.memcache_client.set(keyRobotToSensor, position, time=2)

    # Function to return status of queue.
    def areCommandsAvailable(self):
        if self.commands:
            return True
        return False

    # Function to output info logging
    def doILog(self):
        return self.verbose


def main():
    # Code for parsing command line arguments
    parser = argparse.ArgumentParser(description='Robot setup')
    parser.add_argument('--randomerror', action='store_true', help='If true, robot will randomly error on the y-axis')
    parser.add_argument('--verbose', action='store_true', help='If true, provide verbose output')
    args = parser.parse_args()
    random_error = args.randomerror
    verbose = args.verbose

    # The starting coordinates for the robot.
    start_pos = np.array([0.0, 0.0, 0.0])

    # Instantiates a robot object with the specified parameters
    robot = Robot(start_pos, random_error_y=random_error, verbose=verbose)

    # Main loop that is run by tkinter
    def run():
        robot.receiveDataFromController()
        robot.sendPositionToSensor()
        if robot.areCommandsAvailable():
            if robot.doILog():
                logstr = "Robot: " + np.array2string(robot.getPosition())
                logger.info('%s', logstr)
            robot.fetchAndMove()
        robot_gui.after(1000, run)

    # Tkinter gui
    robot_gui = tk.Tk()
    robot_gui.title('Robot Process')
    robot_gui.geometry('200x200')

    exit_button = tk.Button(robot_gui, text="Exit", command=robot_gui.destroy)
    exit_button.pack()

    robot_gui.after(1000, run)
    robot_gui.mainloop()


main()
