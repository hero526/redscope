#!/usr/bin/env python3

import os
import time
import sys
import zmq
import random, string
import numpy as np
from glob import glob
import pickle
import signal
    
def create_connection(db_type, ip, port, db_name):
    obj_for_close = None
    obj_for_op = None

    if db_type == "redis":
        import redis
        obj_for_op = redis.StrictRedis(host=ip, port=port)
        obj_for_close = obj_for_op
    elif db_type == "memcached":
        import memcache
        obj_for_op = memcache.Client([(ip, port)])
        obj_for_close = obj_for_op
    elif db_type == "mongo":
        from pymongo import MongoClient

        obj_for_close = MongoClient(ip, int(port))
        db_instance = obj_for_close[db_name]
        obj_for_op = db_instance.testcol
    else:
        raise InvalidDBTypeError(db_type)
    
    return (obj_for_op, obj_for_close)

def close_connection(db_type, obj_for_close):
    if db_type == "redis":
        obj_for_close.close()
    elif db_type == "mongo":
        obj_for_close.close()
    elif db_type == "memcached":
        pass
    else:
        raise InvalidDBTypeError(db_type)

    del obj_for_close


def do_operation(db_type, op_type, obj_for_op, obj_for_close, inputs):
    input_key = inputs[0]
    if op_type == "load" or op_type == "insert":
        input_value = inputs[1]
        if db_type == "redis":
            obj_for_op.set(input_key, input_value)
        elif db_type == "memcached":
            obj_for_op.set(input_key, '{"value": "'+input_value+'"}')
        elif db_type == "mongo":
            doc = {"_id": input_key, "value": input_value}
            obj_for_op.insert_one(doc)
        else:
            raise InvalidDBTypeError(db_type)
        
    elif op_type == "select" or op_type == "dup-select":
        if db_type == "redis":
            obj_for_op.get(input_key)
        elif db_type == "memcached":
            obj_for_op.get(input_key)
        elif db_type == "mongo":
            for row in obj_for_op.find({"_id":input_key}):
                pass
        else:
            raise InvalidDBTypeError(db_type)

    elif op_type == "delete":
        if db_type == "redis":
            obj_for_op.delete(input_key)
        elif db_type == "memcached":
            obj_for_op.delete(input_key)
        elif db_type == "mongo":
            obj_for_op.delete_one({"_id": input_key})
        else:
            raise InvalidDBTypeError(db_type)
    else:
        close_connection(db_type, obj_for_close)
        raise InvalidOperationTypeError(op_type)

def run(db_type, ip, port, db_name, op_type, record_size, reuse_connection, inputs, interval_times, client_no):
    obj_for_close = None
    obj_for_op = None
        
    conn = create_connection(db_type, ip, port, db_name)
    obj_for_op = conn[0]
    obj_for_close = conn[1]
    mark_state_to_pub(CLIENT_NO, "ready")

    if int(sub_socket.recv_string().split("dr:")[1]) != 1: # receive resume runner signal
        raise Exception(f"Unexpected signal!")
    
    for i in range(len(interval_times)):
        do_operation(db_type, op_type, obj_for_op, obj_for_close, inputs[i])
        if op_type != "load":
            count_to_pub()
            time.sleep(interval_times[i])

        if not reuse_connection:
            close_connection(db_type, obj_for_close)

            conn = create_connection(db_type, ip, port, db_name)
            obj_for_op = conn[0]
            obj_for_close = conn[1]

    mark_state_to_pub(CLIENT_NO, "done")

    if int(sub_socket.recv_string().split("dr:")[1]) == 2: # receive close signal
        close_connection(db_type, obj_for_close)
    else:
        raise Exception(f"Unexpected signal!")

 
def get_interval_samples(interval, op_count):
    return list(np.random.exponential(interval, op_count))


def init_subscriber(publisher_port):
    ctx = zmq.Context()
    sub_socket = ctx.socket(zmq.SUB)
    req_socket = ctx.socket(zmq.REQ)
    push_socket = ctx.socket(zmq.PUSH)

    sub_socket.connect("tcp://XXX.XXX.XXX.XXX:%s" % publisher_port)
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, 'dr:')

    req_socket.connect("tcp://XXX.XXX.XXX.XXX:%s" % (publisher_port+1))
    push_socket.connect("tcp://XXX.XXX.XXX.XXX:%s" % (publisher_port+2))
    
    return sub_socket, req_socket, push_socket

def mark_state_to_pub(client_no, state):
    req_socket.send_string(f"{client_no},{state}")
    rep = req_socket.recv_string()

    if rep == "OK":
        return
    else:
        raise Exception('Unexpected response')

def count_to_pub():
    push_socket.send((1).to_bytes(8, 'big'))
    
    
class InvalidOperationTypeError(Exception):
    def __init__(self, op_type):
        msg = "Invalid operation type" 
        if op_type is not None:
            msg += ": " + str(op_type)
        super().__init__(msg)

class InvalidDBTypeError(Exception):
    def __init__(self, db_type):
        msg = "Invalid database type" 
        if db_type is not None:
            msg += ": " + str(db_type)   
        super().__init__(msg)
           
def sig_hup_handler(signum, frame):
    exit()

if __name__ == "__main__":
    signal.signal(signal.SIGHUP, sig_hup_handler)

    PUBLISHER_PORT = int(sys.argv[1])
    DB_TYPE = sys.argv[2]
    IP = sys.argv[3]
    PORT = int(sys.argv[4])
    CLIENT_NO = int(sys.argv[5])
    NUM_CLIENTS = int(sys.argv[6])
    DB_NAME = sys.argv[7]
    OP_TYPE = sys.argv[8]
    OP_COUNT = int(sys.argv[9])
    DUP_SELECT_RANGE = int(sys.argv[10])
    RECORD_SIZE_KBYTE = int(sys.argv[11])
    REUSE_CONNECTION = sys.argv[12]
    OPERATION_INTERVAl_MILLE_SEC = float(sys.argv[13])/1000
    pwd = sys.argv[14]

    num_interval_samples = int(OP_COUNT/NUM_CLIENTS)
    
    if REUSE_CONNECTION.lower() or REUSE_CONNECTION.lower()[0] == "t":
        REUSE_CONNECTION = True
    else:
        REUSE_CONNECTION = False

    RECORD_SIZE_BYTE = RECORD_SIZE_KBYTE * 1000

    optype = OP_TYPE.lower()
    data_file = glob(f"{pwd}/key_val_pickles/{NUM_CLIENTS}_{OP_COUNT}_{DUP_SELECT_RANGE}_*{optype}*_{CLIENT_NO}.pickle")
    if len(data_file) == 0:
        raise Exception(f"Path.. eRror? {pwd}/key_val_pickles/{NUM_CLIENTS}_{OP_COUNT}_{DUP_SELECT_RANGE}_*{optype}*_{CLIENT_NO}.pickle")
    with open(data_file[0], "rb") as f:
        inputs = pickle.load(f)

    interval_times = get_interval_samples(OPERATION_INTERVAl_MILLE_SEC, num_interval_samples)
    
    sub_socket, req_socket, push_socket = init_subscriber(PUBLISHER_PORT)
    mark_state_to_pub(CLIENT_NO, "start")

    if int(sub_socket.recv_string().split("dr:")[1]) == 0:
        run(DB_TYPE, IP, PORT, DB_NAME, OP_TYPE, RECORD_SIZE_KBYTE, REUSE_CONNECTION, inputs, interval_times, CLIENT_NO)
    else:
        print("Error: Invalid publisher signal", file=sys.stderr)
        exit(1)

    sub_socket.close()
    req_socket.close()
