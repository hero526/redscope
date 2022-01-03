#!/usr/bin/env python3

from re import I
import sys
from pymongo import MongoClient, collation

COLLECTION_FORMAT=["databaseType","operationType","recordCount","recordSize","client","interval(ms)","operationCount","iteration"]

def init_mongo_client():
    user_id = "XXXXX" # Collector auth username
    user_pw = "XXXXXXXX" # Collector auth password
    mongo_port = "XXXXX" # Collector port
    mongo_ip="XXX.XXX.XXX.XXX" # Collector IP address
    mongo_url = f"mongodb://{user_id}:{user_pw}@{mongo_ip}:{mongo_port}/admin"

    return MongoClient(mongo_url, unicode_decode_error_handler='ignore')

def get_client_info(target_db_name, target_col_name):
    ARRIVAL_RATE_DB_NAME="ARRIVAL_RATE"
    mongo_client = init_mongo_client()
    db = mongo_client[ARRIVAL_RATE_DB_NAME]
    collection = db[target_db_name]
    
    experiments = target_col_name.split("_")

    query = {"$and": []}
    for idx in range(len(experiments)):
        condition_name = COLLECTION_FORMAT[idx]
        condition = experiments[idx]
        query["$and"].append({condition_name: condition})
    
    client_info = list(collection.find(query, {"monitoredArrivalRate" : 1, "monitoredRequest": 1}))
    mongo_client.close()
    if len(client_info) != 1:
        raise Exception(f"Cannot find arrival rate and # request! ({target_col_name})")
    else:
        return (client_info[0]["monitoredArrivalRate"], client_info[0]["monitoredRequest"])

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise Exception("Invalid argument!, need 1 argument(db_name)")

    db_name = sys.argv[1]
    mongo_client = init_mongo_client()
    db = mongo_client[db_name]
    colList = sorted([collection for collection in db.list_collection_names()])
    print("database,operation,client,interval,arrivalRate,requestCount,iteration,socket,eventName,value")

    for collection in colList:
        col_info = collection.split('_')
        database = col_info[0]
        operation = col_info[1]
        client = col_info[4]
        interval = col_info[5]
        iteration = col_info[7]
        data = list(db[collection].find())
        client_info = get_client_info(db_name, collection)
        arrival_rate = client_info[0]
        req_count = client_info[1]
        
        for row in data:
            if "eventName" not in row:
                continue
            if row["eventName"] == "cpu/event=0x3C" and "umask=0x00/" in row["eventMask"]:
                metric = "Actual Cycle"
            elif row["eventName"] == "cpu/event=0xC0" and "umask=0x00/" in row["eventMask"]:
                metric = "Retired Instruction"
            elif row["eventName"] == "cpu/event=0xD0" and "umask=0x81/" in row["eventMask"]:
                metric = "Memory Load"
            elif row["eventName"] == "cpu/event=0xD0" and "umask=0x82/" in row["eventMask"]:
                metric = "Memory Store"
            elif row["eventName"] == "uncore_imc_*/event=0x04" and "umask=0x0c/" in row["eventMask"]:
                metric = "WRCAS"
            elif row["eventName"] == "uncore_imc_*/event=0x04" and "umask=0x03/" in row["eventMask"]:
                metric = "RDCAS"
            else:
                metric = "Unknown Resource Metric"
            if row["value"] == "<not counted>":
                value = 0
            else:
                value = row["value"]
            print(f'{database},{operation},{client},{interval},{arrival_rate},{req_count},{iteration},{row["socket-d-core"]},{metric},{value}')
        
    mongo_client.close()
