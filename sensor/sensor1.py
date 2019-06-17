import numpy as np
import time
from datetime import datetime as dt
import pylibmc
import tkinter as tk
from influxdb import InfluxDBClient
import argparse
import logging
import sys

# keys for memcached
keyControllerToSensor = 'Controller.Sensor'
keySensorToController = 'Sensor.Controller'
keyRobotToSensor = 'Sensor.Robot'

# logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Sensor:
    def __init__(self, user, password, host, port, db_name, tolerance=0.000001, polling_rate=10, verbose=True):
        # Last location the sensor registered robot at.
        self.sensor_robot_location = None

        # Location the sensor expects the robot to be.
        self.expected_robot_location = None

        # Last command sent by the controller.
        self.saved_controller_data = None

        # client for connecting to memcached.
        self.memcache_client = pylibmc.Client(['localhost'], binary=True, behaviors={"tcp_nodelay": True, "ketama": True})

        # How large an error must be for the sensor to attempt to correct it.
        # TODO: Implement sensor noise
        self.tolerance = tolerance

        # How frequently the sensor scans the robot and controller.
        self.polling_rate = polling_rate

        # Influx Database to write to.
        self.db_name = db_name

        # Instantiates a DB client.
        self.client = InfluxDBClient(host=host, username=user, password=password, database=db_name, port=port)

        # Verbose Logging.
        self.verbose = verbose

        # Timeout length in seconds
        self.timeout = 10

    # Gets the robot's latest location from the keyRobotToSensor key.
    # The function will wait until the robot reports before returning data.
    # TODO: Fix bug where time.sleep() causes the sensor GUI to hang.
    def checkRobotLocation(self):
        vector = self.memcache_client.get(keyRobotToSensor)

        # Counter to time out sensor if no data is found.
        i = 0

        # Waits for the next robot location update
        while vector is None:
            vector = self.memcache_client.get(keyRobotToSensor)
            time.sleep(1 / self.polling_rate)
            i += 1
            if i > self.timeout * self.polling_rate:
                logging.error("Sensor - Sensor waiting for robot time out")
                sys.exit(1)

        return vector

    # Accessor functino to get robot's last recorded location
    def getSensorRobotLocation(self):
        return self.sensor_robot_location

    # Accessor functino to get robot's expected location
    def getSensorExpectedLocation(self):
        return self.expected_robot_location

    # Gets robot's latest location at the keyRobotToSensor key and clears the value from memcache
    def fetchSensorRobotLocation(self):
        vector = self.checkRobotLocation()
        if vector is not None and type(vector).__module__ == np.__name__:
            self.sensor_robot_location = vector
            self.memcache_client.delete(keyRobotToSensor)
        return self.sensor_robot_location

    # Gets the controller's command to the robot from the keyControllerToSensor key.
    # Saves the data as the last sent command.
    def getControllerData(self):
        controller_data = self.memcache_client.get(keyControllerToSensor)
        if controller_data is not None:
            self.saved_controller_data = controller_data
            self.memcache_client.delete(keyControllerToSensor)
        return controller_data

    # Sends correctional data to the controller through the keySensorToController key.
    def sendDataToController(self, vector):
        if vector is not None and type(vector).__module__ == np.__name__:
            self.memcache_client.set(keySensorToController, vector)

    # Updates the estimated location of the robot if the conditions are met.
    def updateEstimate(self):
        if self.expected_robot_location is None and (self.sensor_robot_location is not None
                                                     and self.saved_controller_data is not None):
            self.expected_robot_location = self.sensor_robot_location + self.saved_controller_data
        elif self.expected_robot_location is not None:
            self.expected_robot_location += self.saved_controller_data

    # Calculates the amount of error the robot has made on the y-axis and sends correctional data to the controller.
    # Writes the error to InfluxDB for reporting.
    # Does not send data to the controller if sensor is disabled in the GUI.
    # Technically sensor isn't disabled, but it is necessary to record the error.
    def sendCorrectionData(self, is_sensor_on):
        actual_pos = self.checkRobotLocation()
        diff = self.expected_robot_location - actual_pos
        self.writeToDB(diff[1])
        if abs(diff[1]) > self.tolerance and is_sensor_on:
            if self.doILog():
                logstr = "Sensor: Expected location: " + np.array2string(self.expected_robot_location)\
                         + "Actual Location: ", np.array2string(actual_pos)
                logger.info('%s', logstr)
            self.sendDataToController(diff)

    # Clears sensor data in memcache (not used)
    def clearSensorRobotLocation(self):
        if self.getSensorRobotLocation is not None:
            self.sensor_robot_location = None
        if self.getSensorExpectedLocation is not None:
            self.expected_robot_location = None
        if self.memcache_client.get(keyControllerToSensor) is not None:
            self.memcache_client.delete(keyControllerToSensor)
        if self.memcache_client.get(keyRobotToSensor) is not None:
            self.memcache_client.delete(keyRobotToSensor)

    # Writes data to the DB specified in the sensor's parameters.
    # Timestamp is the current UTC time in milliseconds.
    def writeToDB(self, data):
        databases = self.client.get_list_database()
        db_check = {'name': self.db_name}
        if db_check in databases:
            json_body = [{
                    "measurement": "robot_sensor",
                    "time": dt.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    "fields": {
                        "error": data
                    }
                }]
            try:
                self.client.write_points(json_body)
                logger.info("Writing to DB: %s", json_body)
            except Exception as exception:
                logger.error("Exception writing to DB: %s", exception)

    # Function to output info logging
    def doILog(self):
        return self.verbose


def main():
    # Code for parsing command line arguments
    parser = argparse.ArgumentParser(description='Sensor setup')
    parser.add_argument('--user', help='Username for DB')
    parser.add_argument('--password', help='Password for DB')
    parser.add_argument('--host', help='Host for connecting to DB')
    parser.add_argument('--port', type=int, help='Port for connecting to DB')
    parser.add_argument('--dbname', help='Database to insert data to')
    parser.add_argument('--verbose', action='store_true', help='If true, provide verbose output')
    args = parser.parse_args()

    user = args.user
    password = args.password
    host = args.host
    port = args.port
    db_name = args.dbname
    verbose = args.verbose

    # Instantiates a Sensor object with the specified parameters
    s = Sensor(user, password, host, port, db_name, verbose=verbose)
    sensor_gui = tk.Tk()

    # Main loop that is run by tkinter
    # Note that this loop will hang when the sensor waits for the next robot's location to be updated.
    def run():
        controller_data = s.getControllerData()
        s.fetchSensorRobotLocation()
        if s.doILog() and loop.get():
            logstr = "Sensor Robot Location: " + np.array2string(s.getSensorRobotLocation())
            logger.info('%s', logstr)
        if controller_data is not None and s.getSensorRobotLocation() is not None:
            s.updateEstimate()
            s.sendCorrectionData(loop.get())
        sensor_gui.after(1000 // s.polling_rate, run)

    sensor_gui.title('Robot Sensor')
    sensor_gui.geometry('200x200')
    loop = tk.BooleanVar(sensor_gui)
    loop.set(True)
    radiobutton_widget1 = tk.Radiobutton(sensor_gui, text="Hold to Enable Sensor", variable=loop, value=True,
                                         indicatoron=False, command=run)
    radiobutton_widget2 = tk.Radiobutton(sensor_gui, text="Hold to Disable Sensor", variable=loop, value=False,
                                         indicatoron=False, command=run)
    exit_button = tk.Button(sensor_gui, text="Hold to Exit", command=sensor_gui.destroy)

    radiobutton_widget1.pack()
    radiobutton_widget2.pack()
    exit_button.pack()

    sensor_gui.after(1000, run)
    sensor_gui.mainloop()


main()
