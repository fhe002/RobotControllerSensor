#!/bin/bash

sudo apt-get install curl -y
sudo apt-get install python3 -y
sudo apt-get install python3.7 -y
sudo apt-get install python3-pip -y
sudo apt-get install python3-tk -y
sudo apt-get install memcached -y
sudo apt-get install influxdb -y
sudo apt-get install influxdb-client -y

sudo pip3 install numpy
sudo pip3 install pylibmc
sudo pip3 install influxdb

wget https://dl.grafana.com/oss/release/grafana_6.2.1_amd64.deb 
sudo dpkg -i grafana_6.2.1_amd64.deb 
rm ./grafana_6.2.1_amd64.deb 
sudo /bin/systemctl start grafana-server
sleep 3

python3 createDB.py --host 'localhost' --user 'root' --password 'root' --dbname 'sensor' --policy 'sensor_data' --port 8086

curl -X POST 'http://admin:admin@localhost:3000/api/datasources' -H "Content-Type: application/json" --data-binary '{"id":1,"orgId":1,"name":"InfluxDB","type":"influxdb","typeLogoUrl":"public/app/plugins/datasource/influxdb/img/influxdb_logo.svg","access":"proxy","url":"http://localhost:8086","password":"","user":"root","database":"sensor","basicAuth":false,"isDefault":true,"jsonData":{"httpMode":"GET","keepCookies":[],"timeInterval":"0s"},"readOnly":false}'
#curl -X POST -i 'http://admin:admin@localhost:3000/api/dashboards/db' -H "Content-Type: application/json" --data-binary @"./grafana/RobotSensor.json"
