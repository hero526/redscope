from pymongo import MongoClient
from const import *

def get_all_data_per_tid(db_name, col_name, mongo_ip, trim_sec=None):
    client = init_mongo_client(mongo_ip)
    db = client[db_name]
    collection = db[col_name]

    # Aggregation for find each thread's tid
    result = list(collection.aggregate([{'$group':{"_id": "$threadId"}}]))
    thread_ids = [x["_id"] for x in result]
    thread_ids.sort()

    all_data = {}       # Dict for store each thread's event records
    for tid in thread_ids:   # data: threadId
        all_data[tid] = sorted(list(collection.find({'threadId': {"$eq": tid}})), key=lambda x: x["timestamp"])
    client.close()

    if trim_sec is not None:
        fastest_ts = float("inf")
        for tid, evt_data in all_data.items():
            ts = evt_data[0]["timestamp"]
            if ts < fastest_ts:
                fastest_ts = ts
        
        deadline_ts = fastest_ts + trim_sec
        for tid, evt_data in all_data.items():
            for idx in range(len(evt_data)):
                evt = evt_data[idx]
                cur_end_ts = evt["endTimestamp"]
                if cur_end_ts > deadline_ts:
                    all_data[tid] = evt_data[:idx]
                    break
        
        empty_tid = []
        for tid, evt_data in all_data.items():
            if len(evt_data) == 0:
                empty_tid.append(tid)
        for tid in empty_tid:
            del all_data[tid]
    return all_data

def get_arrival_rate(target_db_name, target_col_name, mongo_ip):
    client = init_mongo_client(mongo_ip)
    db = client[ARRIVAL_RATE_DB_NAME]
    collection = db[target_db_name]
    
    experiments = target_col_name.split("_")

    query = {"$and": []}
    for idx in range(len(experiments)):
        condition_name = COLLECTION_FORMAT[idx]
        condition = experiments[idx]
        query["$and"].append({condition_name: condition})
    
    arrival_rate = list(collection.find(query, {"monitoredArrivalRate" : 1,}))
    client.close()
    if len(arrival_rate) != 1:
        raise Exception(f"Cannot find arrival rate!({target_col_name})")
    else:
        return arrival_rate[0]["monitoredArrivalRate"]

def init_mongo_client(mongo_ip):
    user_id = "XXXXX" # Database auth username
    user_pw = "XXXXXXXX" # Database auth password
    mongo_port = "XXXXX" # Database port
    mongo_url = f"mongodb://{user_id}:{user_pw}@{mongo_ip}:{mongo_port}/admin"
    
    return MongoClient(mongo_url, unicode_decode_error_handler='ignore')

def get_found_ptrn_count(ptrn_list):
    return len(ptrn_list)

def get_found_ptrn_count_per_client(ptrn_list_per_client):
    sum = 0
    for c, ptrn_list in ptrn_list_per_client.items():
        sum += len(ptrn_list) * c
    return sum
