#!/usr/bin/env python3

import sys, os
from argparse import ArgumentParser

from const import * 
from _utils import get_all_data_per_tid, get_arrival_rate

from runner_mongo import run_mongo
from runner_redis_memcached import run_redis_memcached

def check_valid_metric(args):
    valid_list = ["Cycle", "RetiredInst", "ActualCycle", "UopsLoads", "UopsStores", "RDCAS_0_0", "WRCAS_0_0", "RDCAS_0_1", "WRCAS_0_1", "RDCAS_1_0", "WRCAS_1_0", "RDCAS_1_1", "WRCAS_1_1"]

    metric_list = args.split(",")
    for metric in metric_list:
        if metric not in valid_list:
            raise Exception("Invalid metric: " + metric)

    return metric_list

def check_valid_trim_value(value):
    value = float(value)
    if value < 0 or value>1:
        raise Exception("Invalid trim parameter range(0<=value<1)")

    return value
def check_valid_bool(value):
    if value.lower() in ["true", "t", "1"]:
        return True
    elif value.lower() in ["false", "f", "0" ]:
        return False
    else:
        raise Exception(f"Invalid opt({value})")

if __name__ == "__main__":
    parser =  ArgumentParser()
    parser.add_argument("-d", "--db", dest="db", required=True, type=str, help="Database name")
    parser.add_argument('-c', "--col", dest="col", required=True, type=str, help="Collection name")
    parser.add_argument('-m', "--metric", dest="metric", required=True, type=check_valid_metric, help="metric", default="Cycle")
    parser.add_argument("-o", "--output", dest="output", required=True, type=str, help="output file prefix")
    parser.add_argument("--output-dir", dest="output_dir", required=True, type=str, help="output dir")
    parser.add_argument("-r", dest="real_pattern", required=True, type=check_valid_bool, help="real pattern print")
    parser.add_argument("--ip", dest="mongo_ip", type=str)
    parser.add_argument("--trim", dest="trim_sec", type=float, help="trim(unit:sec)" )
    args = parser.parse_args()
        
    db_name = args.db
    col_name = args.col
    metric_list = args.metric
    output_prefix = args.output
    output_dir = args.output_dir
    REAL_PATTERN_PRINT = args.real_pattern

    experiments = col_name.split("_") # @TODO Need to customization
    db_type = experiments[0]
    op_type = experiments[1]
    mongo_ip = args.mongo_ip
    trim_sec = args.trim_sec

    arrival_rate = get_arrival_rate(db_name, col_name, mongo_ip)
    experiments.append(arrival_rate)

    # 1. get all data from db
    evt_data_tid = get_all_data_per_tid(db_name, col_name, mongo_ip, trim_sec)
    if len(evt_data_tid.keys()) == 0:
        raise Exception(f"Error: There is no event data: {db_name} - {col_name}")
    
    if db_type == DB_TYPE_MONGO:
        run_mongo(evt_data_tid, col_name, experiments, output_prefix, output_dir, metric_list, REAL_PATTERN_PRINT)
    elif db_type == DB_TYPE_REDIS or db_type == DB_TYPE_MEMCACHED:
        run_redis_memcached(evt_data_tid, col_name, experiments, output_prefix, output_dir, metric_list, REAL_PATTERN_PRINT)
    else:
        raise Exception("Invalid db_type")
