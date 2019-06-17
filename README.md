# Readme

# About
- This program simulates a robot, controller, and sensor program. The controller reads in a list of moves to send the robot, the robot receives commands from the controller in order to move to a coordinate, and the sensor attempts to correct for any errors that the robot may make while moving. The 3 programs communicate via memcached.

The sensor outputs data to a local InfluxDb instance that can be viewed by a real-time monitoring solution such as Grafana.

**Dependencies**

    * Developed on Linux Mint 19.1+ 'Tessa'. Should work with Ubuntu 18.04 LTS.
    * Created and tested with Python 3.7
    * python3-pip=9.0.1-2.3~ubuntu1
    * python3-tk=3.6.7-1~18.04
    * memcached=1.5.6-0ubuntu1.1
    * influxdb=1.1.1+dfsg1-4
    * The Python packages/versions listed in ./requirements.txt
    * Grafana v6.2.1 (9e40b07)\
    
    * This setup assumes a fresh Ubuntu 18.04 install is used.
    
# Instructions
- Run "sudo ./setup.sh" to install dependencies.
- Run "./run.sh" to start the controller, robot, and sensor.
- Open your web browser and open Grafana by typing in http://localhost:3000 in the browser.
- Login with username "admin" and password "admin".
- Navigate to http://localhost:3000/dashboard/import
- Click on the "Upload .json File" button
- Import the "./grafana/RobotSensor.json" file and enter a name for the dashboard
- Open the "Robot Sensor" dashboard

# Usage
- The "Robot Controller" window allows you to enable or disable the controller that sends commands to the robot.
- The "Robot Process" window allows you to terminate the robot.
- The "Robot Sensor" window allows you to enable or disable the sensor.
    - Observe over time the effects of disabling the sensor on the Grafana dashboard.
    - Note that the UI is sluggish so you may have to hold on the button for a moment to observe a change.

# Known Issues
- Sensor UI is sluggish due to it using a time.sleep() command with tkinter.
- Disabling the controller can cause the robot and sensor coordinates to mis-align.

# Todo
- Implement a better error correcting algorithm.
- Implement sensor noise and a possible solution to it.
    - Maybe use a Kalman filter?

