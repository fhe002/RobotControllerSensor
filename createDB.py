from influxdb import InfluxDBClient
import logging
import sys
import argparse

# logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='DB setup')
    parser.add_argument('--user', help='Username for DB')
    parser.add_argument('--password', help='Password for DB')
    parser.add_argument('--host', help='Host for connecting to DB')
    parser.add_argument('--dbname', help='Database to insert data to')
    parser.add_argument('--port', type=int, help='Port for connecting to DB')
    parser.add_argument('--policyname', help='Policy for DB')
    args = parser.parse_args()

    user = args.user
    password = args.password
    host = args.host
    port = args.port
    db_name = args.dbname
    policy_name = args.policyname

    client = InfluxDBClient(host=host, username=user, password=password, port=port)

    try:
        client.create_database(db_name)
        client.create_retention_policy(policy_name, '1d', database=db_name, replication='1', default=False)
    except Exception as exception:
        logger.error(exception)
        sys.exit(1)

    logger.info(client.get_list_database())


main()
