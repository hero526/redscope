from pymongo import MongoClient
import sys

def getColList(client, db_name):
    db = client[db_name]
    colList = sorted([collection for collection in db.list_collection_names()])
    return db, colList


def getTargetDBs(client):
    db_list = client.list_database_names()
    target = []
    for db in db_list:
        if 'STAPv2' in db and 'IDLE' not in db:
            target.append(db)

    return target


def parse_db(db_name):
    info = db_name.split('_')
    parsed_db = {'memo': info[0], 'size': info[1], 'server': info[2], 'core': info[3], 'mem': info[4], 'storage': info[5]}

    return parsed_db


def parse_col(col):
    info = col.split('_')
    parsed_col = {'db': info[0], 'operation': info[1], 'record_count': info[2], 'op_count': info[3], 'client': info[4], 'iter': info[5]}

    return parsed_col


# def set_new_db(db, new_db, col, parsed_db, parsed_col):
def set_new_db(db, new_db, col):
    collection = db[col]

    target_data = list(collection.find())
    # new_col = f'{parsed_col["db"]}_{parsed_col["operation"]}_{parsed_col["record_count"]}_{parsed_db["size"][:-2]}_{parsed_col["client"]}_{parsed_col["op_count"]}_{parsed_col["iter"]}'
    # print(new_col)
    new_collection = new_db[col]
    new_collection.insert_many(target_data)
    


if __name__ == '__main__':
    client = MongoClient("mongodb://auth_id:auth_pw@XXX.XXX.XXX.XXX:XXXXX/admin")
    # target_dbs = getTargetDBs(client)
    target_dbs = ["1-UK-PERFPID_HOTH_24_1024_SSD"]
    for db_name in target_dbs:
        # parsed_db = parse_db(db_name)
        # print(f'{parsed_db["memo"]}_{parsed_db["server"]}_{parsed_db["core"]}_{parsed_db["mem"]}_{parsed_db["storage"]}')
        # new_db = client[f'{parsed_db["memo"]}_{parsed_db["server"]}_{parsed_db["core"]}_{parsed_db["mem"]}_{parsed_db["storage"]}']
        new_db = client["UK-PERFPID_HOTH_24_1024_SSD"]
        db, colList = getColList(client, db_name)
        for col in colList:
            # parsed_col = parse_col(col)
            # set_new_db(db, new_db, col, parsed_db, parsed_col)
            set_new_db(db, new_db, col)
