#!/usr/bin/env bash

python3 controller/controller.py --data "./data/simple.csv" --verbose &
sleep 1
python3 sensor/sensor1.py --host 'localhost' --user 'root' --password 'root' --dbname 'sensor' --port 8086 --verbose &
sleep 1
python3 robot/robot.py --randomerror --verbose &
