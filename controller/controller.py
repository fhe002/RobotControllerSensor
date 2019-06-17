import numpy as np
import pylibmc
import tkinter as tk
import argparse
import logging
import sys
from collections import deque

# keys for memcached
keyControllerToRobot = 'Controller.Robot'
keyControllerToRobotCorrect = 'Controller.Correct'
keyControllerToSensor = 'Controller.Sensor'
keySensorToController = 'Sensor.Controller'

# logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Controller:
    def __init__(self, data="", verbose=True):
        # Structure for queueing commands that will be sent to the robot.
        # Commands are a 3-dimension numpy array.
        self.commands = deque()

        # client for connecting to memcached.
        self.memcache_client = pylibmc.Client(['localhost'], binary=True, behaviors={"tcp_nodelay": True, "ketama": True})

        # Controller will not correct for over this amount in one command.
        self.max_correction_bound = 1.0

        # CSV file to read in.
        self.data = data

        # Verbose logging.
        self.verbose = verbose

    # Pops first data in queue and sends it to the robot using the keyControllerToRobot key.
    # Also sends data to the sensor to calculate robot's expected location.
    def sendDataToRobot(self):
        if self.memcache_client.get(keyControllerToRobot) is None:
            vector = self.commands.popleft()
            if self.doILog():
                logstr = "Controller - Sending to robot " + np.array2string(vector)
                logger.info('%s', logstr)
            self.memcache_client.set(keyControllerToRobot, vector, time=1000)
            self.memcache_client.set(keyControllerToSensor, vector, time=1000)

    # Fetches data from the keySensorToController key.
    # If data is found, clear the corresponding key in memcache and return the data.
    def getDataFromSensor(self):
        vector = self.memcache_client.get(keySensorToController)
        if vector is not None and type(vector).__module__ == np.__name__:
            self.memcache_client.delete(keySensorToController)
        return vector

    # Apply a simple correction by subtracting the previous error component if data from sensor is found
    # and apply it to the next move.
    # Correction amount will not exceed the max_correction_bound.
    # Note that the robot can error on correctional movements as well.
    def correctPath(self):
        correction_data = self.getDataFromSensor()
        if correction_data is not None:
            if correction_data[1] > 0:
                correction_data[1] = min(correction_data[1], self.max_correction_bound)
            elif correction_data[1] < 0:
                correction_data[1] = max(correction_data[1], -self.max_correction_bound)
            if self.doILog():
                logstr = "Controller - Correcting robot " + np.array2string(correction_data)
                logger.info('%s', logstr)
            self.memcache_client.set(keyControllerToRobotCorrect, correction_data)

    # Function to return status of queue.
    def areCommandsAvailable(self):
        if self.commands:
            return True
        return False

    # Function for reading in the specified datafile.
    def readData(self):
        try:
            arr = np.genfromtxt(self.data, skip_header=1, delimiter=',')
        except Exception as exception:
            logger.error(exception)
            sys.exit(1)
        for i in arr:
            self.commands.append(i)

    # Function to output info logging
    def doILog(self):
        return self.verbose


def main():
    # Code for parsing command line arguments
    parser = argparse.ArgumentParser(description='Controller setup')
    parser.add_argument('--data', help='File to read')
    parser.add_argument('--verbose', action='store_true', help='If true, provide verbose output')
    args = parser.parse_args()

    verbose = args.verbose
    data = args.data
    if not args.data:
        logger.error("Controller - Cannot run controller without specifying a data source.")
        sys.exit(1)

    # Instantiates a controller object with the specified parameters
    c = Controller(data=data, verbose=verbose)
    c.memcache_client.flush_all()
    c.readData()

    # Main loop that is run by tkinter
    def run():
        if loop.get() and c.areCommandsAvailable():
            c.correctPath()
            c.sendDataToRobot()
        controller_gui.after(1000, run)

    # Tkinter gui
    controller_gui = tk.Tk()
    controller_gui.title('Robot Controller')
    controller_gui.geometry('200x200')
    loop = tk.BooleanVar(controller_gui)
    loop.set(True)
    radiobutton_widget1 = tk.Radiobutton(controller_gui, text="Enable Controller", variable=loop, value=True,
                                         indicatoron=False, command=run)
    radiobutton_widget2 = tk.Radiobutton(controller_gui, text="Disable Controller", variable=loop, value=False,
                                         indicatoron=False, command=run)
    exit_button = tk.Button(controller_gui, text="Exit", command=controller_gui.destroy)

    radiobutton_widget1.pack()
    radiobutton_widget2.pack()
    exit_button.pack()

    controller_gui.after(1000, run)
    controller_gui.mainloop()


main()
