from printer import *
from static_pd import *
from _utils import *
from const import *

def run_mongo(evt_data_tid, col_name, experiments, output_prefix, output_dir, metric_list, REAL_PATTERN_PRINT):
    # Variables
    rrs_ptrn_list = list()
    db_type = experiments[0]
    op_type = experiments[1]

    req_count = None
    # total_flush_count = None
    
    if op_type == OP_TYPE_INSERT:
        flush_ptrn_list_per_ptrn_type = dict()
        for ptrn_type in TARGET_MONGO_PTRN_TYPE:
            if ptrn_type != MONGO_PTRN_CONN:
                flush_ptrn_list_per_ptrn_type[ptrn_type] = list()
        
        # flush_counts = None
        # flush_evt_counts = None
    
    filtering_target = get_filterting_target_evts(db_type)
    filtering_pattern_list = filtering_target[0]
    valid_evt_list = filtering_target[1] 

    # Logic
    for evt_data in evt_data_tid.copy().values():
        # 1) filtering
        filtered_evt_data = do_filltering(evt_data, filtering_pattern_list, valid_evt_list)
        if filtered_evt_data is None or len(filtered_evt_data) == 0:
            continue
        # 2) find ptrns
        if op_type == OP_TYPE_INSERT: 
            run_mongo_static_pd(filtered_evt_data, rrs_ptrn_list, flush_ptrn_list_per_ptrn_type)
        else:
            run_mongo_static_pd(filtered_evt_data, rrs_ptrn_list)

    # 3) get count of found ptrns 
    req_count = len(rrs_ptrn_list)
    # for ptrn in rrs_ptrn_
    print(col_name,"- #request: ", req_count)

    original_ptrn_list = get_original_ptrn_list(rrs_ptrn_list, evt_data_tid) 
    usages = list()
    for ptrn in original_ptrn_list:
        usages.append(get_resource_usage(ptrn, metric_list))

    r = get_non_irregular_ptrn_usage(rrs_ptrn_list, original_ptrn_list, metric_list)
    non_irregular_ptrn_usage = r[0]
    non_irregular_ptrn_count = r[1]
    if non_irregular_ptrn_count == 0:
        print("Cannot find non irregular ptrn")
    avg_non_irregular_usage = []
    for idx in range(len(non_irregular_ptrn_usage)): ## TO-DO TypeError: object of type 'NoneType' has no len()
        item = dict()
        for metric in metric_list:
            item[metric] = non_irregular_ptrn_usage[idx][metric]/non_irregular_ptrn_count
        avg_non_irregular_usage.append(item)
    print_ptrn_avg_usage(experiments, output_prefix, output_dir, metric_list, avg_non_irregular_usage, req_count, non_irregular_ptrn_count, PTRN_HEADER_MONGO)

    print_usage_sum(experiments, output_prefix, output_dir, usages, metric_list, evt_data_tid, REAL_PATTERN_PRINT, req_count) 
    print_usage_sum(experiments, output_prefix, output_dir, usages, metric_list, evt_data_tid, REAL_PATTERN_PRINT, req_count, mean=True)


def run_mongo_static_pd(evt_data, rrs_ptrn_list, flush_ptrn_list_per_ptrn_type = None):
    pname = evt_data[0]["processName"]
    db_type = DB_TYPE_MONGO

    # check ptrn type
    flush_ptrn_type = None
    is_conn_thread = False
     
    if MONGO_PNAME_CONN_1 in pname or MONGO_PNAME_CONN_2 in pname:
        flush_ptrn_type = MONGO_PTRN_CONN_FLUSH
        is_conn_thread = True
    elif MONGO_PNAME_MONGOD in pname:
        flush_ptrn_type = MONGO_PTRN_MONGOD
    elif MONGO_PNAME_FLUSHER in pname:
        flush_ptrn_type = MONGO_PTRN_FLUSHER
    else:
        return

    # find flush ptrn_list
    if flush_ptrn_list_per_ptrn_type is not None:
        found_flush_ptrn_list = find_ptrns(evt_data, db_type, opt = flush_ptrn_type)
        flush_ptrn_list_per_ptrn_type[flush_ptrn_type].extend(found_flush_ptrn_list)
    
    if flush_ptrn_type is None or  is_conn_thread:
        found_rrs_ptrn_list = find_ptrns(evt_data, db_type, opt = MONGO_PTRN_CONN)
        rrs_ptrn_list.extend(found_rrs_ptrn_list)

def get_flush_count_per_ptrn_type(ptrn_list_per_ptrn_type):
    flush_counts = dict()
    for ptrn_type in TARGET_MONGO_PTRN_TYPE:
        if ptrn_type != MONGO_PTRN_CONN:
            flush_counts[ptrn_type] = get_flush_count(ptrn_list_per_ptrn_type[ptrn_type])

    return flush_counts

def get_flush_count(ptrn_list):
    total_flushed_req = 0
    for idx in range(len(ptrn_list)):
        ptrn = ptrn_list[idx]
        pwrite = ptrn[0]
        flush_count = int(pwrite["returnValue"]/MONGO_FLUSH_RETURN_BYTES)
        total_flushed_req += flush_count
    return total_flushed_req

def get_flush_evt_count_per_ptrn_type(ptrn_list_per_ptrn_type):
    flush_evt_counts = dict()
    for ptrn_type in TARGET_MONGO_PTRN_TYPE:
        if ptrn_type != MONGO_PTRN_CONN:
            flush_evt_counts[ptrn_type] = len(ptrn_list_per_ptrn_type[ptrn_type])

    return flush_evt_counts

# def get_flush_dist(ptrn_list):
#     dist = dict()
#     sum = 0
#     for ptrn in ptrn_list:
#         flush_count = get_flushed_req(ptrn[0])
#         if dist.get(flush_count) is None:
#             dist[flush_count] = 0
#         dist[flush_count] += 1
#         sum+=flush_count

#     return (sum, dist)
