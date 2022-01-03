from re import I
import sys
from pymongo import MongoClient, collation

COLLECTION_FORMAT=["databaseType","operationType","recordCount","recordSize","client","interval(ms)","operationCount","iteration"]
ITERATION=1
OPERATION_COUNT=[1000000]
RECORD_NUM=1000000
NUM_CLIENT=[40]
RECORD_TIME_SEC=3
DBRUNNER_RECORD_SIZE_KBYTE=[1]
DBRUNNER_WORKLOAD_TYPES="insert select delete".split(' ')

DBRUNNER_OPERATION_INTERVAL_MILLI_SEC="3000 800 500 340 220 140 120 70 52 40 34".split(' ')
TARGET_DB="redis memcached mongo".split(' ')

# redis additional data
# DBRUNNER_OPERATION_INTERVAL_MILLI_SEC="40 380 240".split(' ')
# TARGET_DB="redis".split(' ') 

def init_mongo_client():
    user_id = "XXXXX" # MongoDB Username
    user_pw = "XXXXXXXX" # MongoDB Password
    mongo_port = "XXXXX" # MongoDB Port
    mongo_ip="XXX.XXX.XXX.XXX" # MongoDB IP address
    mongo_url = f"mongodb://{user_id}:{user_pw}@{mongo_ip}:{mongo_port}/admin"
    
    return MongoClient(mongo_url, unicode_decode_error_handler='ignore')

def get_arrival_rate(target_db_name, target_col_name):
    ARRIVAL_RATE_DB_NAME="ARRIVAL_RATE"
    client = init_mongo_client()
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
        return False
    else:
        return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise Exception("Invalid argument!, need 1 argument(db_name)")

    db_name = sys.argv[1]
    mongo_client = init_mongo_client()
    db = mongo_client[db_name]
    colList = sorted([collection for collection in db.list_collection_names()])
    total_count = 0
    no_count = 0

    for i in range(1, ITERATION+1):
        for rsize in DBRUNNER_RECORD_SIZE_KBYTE:
            for opc in OPERATION_COUNT:
                for cli in NUM_CLIENT:
                    for wk in DBRUNNER_WORKLOAD_TYPES:
                        for intms in DBRUNNER_OPERATION_INTERVAL_MILLI_SEC:
                            for target_db in TARGET_DB:
                                total_count += 1
                                col_name = f"{target_db}_{wk}_{RECORD_NUM}_{rsize}_{cli}_{intms}_{opc}_i{i}"
                                if col_name in colList:
                                    if not get_arrival_rate(db_name, col_name):
                                        print("ARRIVAL:", db_name, col_name)
                                        no_count += 1
                                else:
                                    no_count += 1
                                    print("DATA:", db_name, col_name)
                                    
    print(f"{total_count - no_count}/{total_count}")
    mongo_client.close()
