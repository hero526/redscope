#!/usr/bin/env python3

import os
import subprocess
import time
import sys
import zmq
import numpy as np
from pymongo import MongoClient
import signal

ARRIVAL_RATE_DB_NAME = "ARRIVAL_RATE"
COLLECTOR_USER_ID = "XXXXX" # user name
COLLECTOR_USER_PW = "XXXXXXXX" # user password

CLIENT_STATE = {
    "start": 0,
    "ready": 1,
    "done": 2
}

COLLECTION_FORMAT = ["databaseType","operationType","recordCount","recordSize","client","interval(ms)","operationCount","iteration"]

def init_publisher(port):
    ctx = zmq.Context()
    pub_socket = ctx.socket(zmq.PUB)
    rep_socket = ctx.socket(zmq.REP)
    pull_socket = ctx.socket(zmq.PULL)

    pub_socket.bind(f'tcp://*:{port}')
    rep_socket.bind(f'tcp://*:{port+1}')
    pull_socket.bind(f'tcp://*:{port+2}')

    return pub_socket, rep_socket, pull_socket

def wait_subscribers(wait_state):
    while True:
        message = rep_socket.recv_string()
        client_num, state = message.split(',')
        client_num = int(client_num)

        if state not in CLIENT_STATE:
            raise Exception(f"Can't find such state: {state}!")
        
        if wait_state != state:
            raise Exception(f"I'm waiting {wait_state} for subscriber no.{client_num}!")   

        if subscriber_state[client_num] >= CLIENT_STATE[state]:
            raise Exception(f"Wrong state for no.{client_num} subscriber: {state}!")
        
        subscriber_state[client_num] = CLIENT_STATE[state]
        
        rep_socket.send_string('OK')
        # print(f"{client_num} \033[0;33m{wait_state}\033[0m OK.", flush=True)
        
        if all(s == CLIENT_STATE[wait_state] for s in subscriber_state[1:]):
            print(f"Every node is in \033[0;31m{wait_state}\033[0m state.", flush=True)
            return get_timestamp_ms()


def get_timestamp_ms():
    return round(time.time() * 1000)

def put_arrival_rate(COLLECTOR_NAME, COLLECTION_NAME, whole_arrival_rate, whole_diff_timestamp, monitored_arrival_rate, mon_diff_timestamp):
    global whole_counter
    global monitoring_counter

    mongo_uri=f"mongodb://{COLLECTOR_USER_ID}:{COLLECTOR_USER_PW}@{COLLECTOR_IP}:{COLLECTOR_PORT}/admin"
    client = MongoClient(mongo_uri, unicode_decode_error_handler='ignore')

    db = client[ARRIVAL_RATE_DB_NAME]
    col = db[COLLECTOR_NAME]
    
    item = {}
    splited = COLLECTION_NAME.split("_")
    for idx in range(len(splited)):
        item[COLLECTION_FORMAT[idx]] = splited[idx]
    col.update_one(item, {"$set": {"wholeArrivalRate": whole_arrival_rate}}, upsert=True)
    col.update_one(item, {"$set": {"monitoredArrivalRate": monitored_arrival_rate}}, upsert=True)
    col.update_one(item, {"$set": {"wholeRequest": whole_counter}}, upsert=True)
    col.update_one(item, {"$set": {"monitoredRequest": monitoring_counter}}, upsert=True)
    col.update_one(item, {"$set": {"wholeTime(ms)": whole_diff_timestamp}}, upsert=True)
    col.update_one(item, {"$set": {"monitoredTime(ms)": mon_diff_timestamp}}, upsert=True)

    client.close()

def sig_term_handler(signum, frame):
    global monitoring_start_timestamp
    global monitoring_end_timestamp
    global monitoring_started
    global flag

    if not monitoring_started:
        monitoring_start_timestamp = get_timestamp_ms()
        monitoring_started = True
    else:
        monitoring_end_timestamp = get_timestamp_ms()
        monitoring_started = False



def sig_int_handler(signum, frame):
    global monitoring_start_timestamp
    global monitoring_end_timestamp
    global whole_counter
    global monitoring_counter
    global start_time

    end_timestamp = get_timestamp_ms()

    # Get count until end of stream
    get_count(flags=zmq.NOBLOCK)

    whole_diff_timestamp = end_timestamp - start_time
    mon_diff_timestamp = monitoring_end_timestamp - monitoring_start_timestamp

    whole_arrival_rate = round(whole_counter / float(whole_diff_timestamp) * 1000, 2)
    monitored_arrival_rate = round(monitoring_counter / float(mon_diff_timestamp) * 1000, 2)

    pub_socket.close()
    rep_socket.close()
    pull_socket.close()

    # record arrival rate
    if len(sys.argv) > 7:   # if not load operation
        print("elapsed: \033[0;34m", whole_diff_timestamp, "(ms)", "\033[0m")
        print("whole request/sec: \033[0;34m", whole_arrival_rate, "\033[0m")
        print("monitored request/sec: \033[0;34m", monitored_arrival_rate, "\033[0m")
        
        put_arrival_rate(COLLECTOR_NAME, COLLECTION_NAME, whole_arrival_rate, whole_diff_timestamp, monitored_arrival_rate, mon_diff_timestamp)
    
    exit(0)


def get_count(flags=0):
    global whole_counter
    global monitoring_started
    global monitoring_counter

    while True:
        try:
            data = pull_socket.recv(flags=flags)
            num = int.from_bytes(data, 'big')
        except zmq.ZMQError as e:
            break
        except Exception as e:
            raise Exception("Wrong data: "+data+" e.message: "+e.message)

        if num == 1:
            whole_counter += num
            if monitoring_started:
                monitoring_counter += num
        else:
            raise Exception("Should be '1' but.. " + num)


def sig_hup_handler(signum, frame):
    exit()

if __name__ == "__main__":
    monitoring_started = False
    whole_counter = 0
    monitoring_counter = 0

    signal.signal(signal.SIGHUP, sig_hup_handler)
    signal.signal(signal.SIGINT, sig_int_handler)
    signal.signal(signal.SIGTERM, sig_term_handler)

    DBRUNNER_PUBLISHER_PORT = int(sys.argv[1])
    NUM_CLIENTS = int(sys.argv[2])
    OP_COUNT = int(sys.argv[3])
    if len(sys.argv) > 7:
        COLLECTOR_NAME = sys.argv[4]
        COLLECTION_NAME = sys.argv[5]

        COLLECTOR_IP = sys.argv[6]
        COLLECTOR_PORT = sys.argv[7]


    subscriber_state = [0] + [-1 for _ in range(NUM_CLIENTS)]
    
    pub_socket, rep_socket, pull_socket = init_publisher(DBRUNNER_PUBLISHER_PORT)
    
    wait_subscribers("start")
    time.sleep(2)

    # send runner signal
    pub_socket.send_string("dr:0")

    wait_subscribers("ready")

    #     while(os.path.isfile('/tmp/dr_state')):
    #         time.sleep(0.1)
    #     time.sleep(1)

    start_time = get_timestamp_ms()
    

    # send work signal
    pub_socket.send_string("dr:1")

    time.sleep(5)
    if len(sys.argv) > 7:
        with open('/tmp/dr_state', "w") as f:
            f.write('1')

        get_count()

    # wait until work done
    end_time = wait_subscribers("done")

    # send close signal
    pub_socket.send_string("dr:2")
    print("PUBLISHER WELLDONE")
    
