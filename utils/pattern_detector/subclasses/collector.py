from pymongo import MongoClient
from config import Config

import re
import logging

class MongoCTL:
    def __init__(self):
        mongo_uri=f"mongodb://{Config.COLLECTOR_USER_ID}:{Config.COLLECTOR_USER_PW}@{Config.COLLECTOR_IP}:{Config.COLLECTOR_PORT}/admin"
        self.client = MongoClient(mongo_uri, unicode_decode_error_handler='ignore')

    def __del__(self):
        self.client.close()
    
    def close(self):
        self.client.close()

    
    def get_collection_list(self, collector, find="", log=True):
        db = self.client[collector]
        col_list = db.list_collection_names()
        result = set()
        col_list_str = ' '.join(col_list)
        find = find.replace("*", "[0-9]*")

        for col in col_list:
            if len(find) > 0:
                if re.search(f"{find}_[0-9]*_i[0-9]*$", col):
                    result.add(col)
            else:
                result.add(col)

        # colname = db_workload_(rc)_rc_size__(cli)_(interval)_(opc)_i(iter)
        
        if log and len(result) == 0:
            logging.warning(f"Can't find any {find}_[0-9]*_i[0-9]*$ collection in {collector}")
            return []

        return sorted(
            list(result),\
            key = lambda e:
            (
                e.split('_')[0],\
                e.split('_')[1],\
                int(e.split('_')[2]),\
                int(e.split('_')[3]),\
                int(e.split('_')[4]),\
                int(e.split('_')[5]),\
                int(e.split('_')[6]),\
                int(e.split('_')[7][1:])
            )
        )


    def get_data_in_collection(self, collector, col_name):
        db = self.client[collector]
        collection = db[col_name]
        target = col_name.split('_')[0]

        first_accept = None        
        if "IDLE" not in collector and target != "level" and target != "rocks":
            first_accept = self.get_first_accept_event(collector, col_name)
    
        # Aggregation for find each thread's tid
        result = list(collection.aggregate([{'$group':{"_id": "$threadId"}}]))
        thread_ids = [x["_id"] for x in result]
        thread_ids.sort()

        query = {'$and': []}
        if first_accept is not None:
            query['$and'].append( {'timestamp': {"$gte": first_accept['timestamp']}} )

        all_data_tid = {}
        for tid in thread_ids:
            query['$and'].append( {'threadId': {"$eq": tid} } )

            query_result = list(collection.find(query))
            if len(query_result) > 0:
                all_data_tid[tid] = query_result
                all_data_tid[tid].sort(key=lambda e: (e['timestamp']))
            query['$and'].pop()
            
        return all_data_tid
        
    def get_tids_pname(self, collector, col_name):
        tids_pname = {}

        for tid, pnames in self.get_pnames_tid(collector, col_name).items():
            pnames_t = tuple(pnames)
            if tids_pname.get(pnames_t) is None:
                tids_pname[pnames_t] = set()
            tids_pname[pnames_t].add(tid)
            
        return tids_pname
            
        
    def get_pnames_tid(self, collector, col_name):
        name_data = self._get_pname_from_collection(collector, col_name)
        pnames_tid = {}

        for elem in name_data:
            tid = elem['threadId']
            pname = elem['processName']

            if pnames_tid.get(tid) is None:
                pnames_tid[tid] = []
            pnames_tid[tid].append(''.join(i for i in pname if not i.isdigit()))
        
        return pnames_tid
    
    
    def _get_pname_from_collection(self, collector, col_name):
        db = self.client[collector]
        collection = db[col_name]

        pipeline=[
            {"$group": {"_id": {"threadId": "$threadId", "processName": "$processName"}}}
        ]

        # Aggregation for find each thread's tid
        result = list(collection.aggregate(pipeline))
        name_data = [x["_id"] for x in result]

        return name_data

    def put_filtered_data_into_collection(self, collector, col_name, data):
        db = self.client[collector]
        collection = db[col_name]

        if len(data) > 1:
            collection.insert_many(data)
        

    def drop_collections(self, collector, cols):
        db = self.client[collector]
        
        for col_name in cols:
            collection = db[col_name]
            try:
                collection.drop()
            except:
                pass


    # 43: ('accept', 'net', []),
    # 288: ('accept4', 'net', ['flags']),
    def get_first_accept_event(self, collector, col_name):
        db = self.client[collector]
        collection = db[col_name]

        # TODO: change returnValue string to int in STAP
        query = {'$and': [
            {'$or': [
                {'eventId': {"$eq": 43}},
                {'eventId': {"$eq": 288}}
            ]},
            {'returnValue': {"$gte": 0}}
        ]}
        
        # query = {
        #     '$or': [
        #         {'eventId': {"$eq": 43}},
        #         {'eventId': {"$eq": 288}}
        #     ]
        # }

        data = list(collection.find(query))
        if len(data) == 0:
            raise Exception(f"There's no accept or accept4 event in [{collector} {col_name}]")

        # accept = []
        # for event in data:
        #     event["returnValue"] = int(event["returnValue"])
        #     if event["returnValue"] < 0:
        #         continue
        #     accept.append(event)
        # accept.sort(key=lambda e: (e['timestamp']))
        # return accept[0]

        data.sort(key=lambda e: (e['timestamp']))
        return data[0]
        
