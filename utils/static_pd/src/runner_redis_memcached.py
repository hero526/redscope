
from printer import *
from static_pd import *
from _utils import *
from const import *

def run_redis_memcached(evt_data_tid, col_name, experiments, output_prefix, output_dir, metric_list, REAL_PATTERN_PRINT):
    db_type = experiments[0]
    op_type = experiments[1]
    num_clients = int(experiments[4])
    ptrn_list_per_client = dict()
    
    filtering_target = get_filterting_target_evts(db_type)
    filtering_pattern_list = filtering_target[0]
    valid_evt_list = filtering_target[1] 

    for evt_data in evt_data_tid.values():
        # 1) filtering
        filtered_evt_data = do_filltering(evt_data, filtering_pattern_list, valid_evt_list)
        if len(filtered_evt_data) == 0:
            continue
        # 2) find ptrns
        found_ptrn_list_per_client = find_ptrns_per_client(filtered_evt_data, num_clients, db_type)
        for c, ptrn_list in found_ptrn_list_per_client.items():
            if ptrn_list_per_client.get(c) is None:
                ptrn_list_per_client[c] = list()
            ptrn_list_per_client[c].extend(ptrn_list)

    # sorting
    for c, ptrn_list in ptrn_list_per_client.items():
        ptrn_list = sorted(ptrn_list, key = lambda x: x[0]["timestamp"])

    # 3) get found ptrn count
    req_count = get_found_ptrn_count_per_client(ptrn_list_per_client)
    if req_count == 0:
        raise Exception("Error: The number of found ptrn: 0")
    print(col_name,"- #request: ", req_count)
    
    total_non_irregular_ptrn_usage = None
    total_non_irregular_ptrn_count = 0
    for c, ptrn_list in ptrn_list_per_client.items():
        if len(ptrn_list) != 0:
            original_ptrn_list = get_original_ptrn_list(ptrn_list, evt_data_tid)
            r = get_non_irregular_ptrn_usage(ptrn_list, original_ptrn_list, metric_list)
            non_irregular_ptrn_usage = r[0]
            non_irregular_ptrn_count = r[1]
            total_non_irregular_ptrn_count += non_irregular_ptrn_count
            if non_irregular_ptrn_count == 0:
                continue
            relocated_non_irregular_ptrn_usage = do_multi_req_handling(non_irregular_ptrn_usage, metric_list, db_type)

            if total_non_irregular_ptrn_usage is None:
                total_non_irregular_ptrn_usage = relocated_non_irregular_ptrn_usage
            else:
                for idx in range(len(relocated_non_irregular_ptrn_usage)):
                    for metric in metric_list:
                        total_non_irregular_ptrn_usage[idx][metric] += relocated_non_irregular_ptrn_usage[idx][metric]

    avg_non_irregular_usage = []
    for idx in range(len(total_non_irregular_ptrn_usage)):
        item = dict()
        for metric in metric_list:
            item[metric] = total_non_irregular_ptrn_usage[idx][metric]/total_non_irregular_ptrn_count
        avg_non_irregular_usage.append(item)


    # Legacy
    total_usages = list()
    for c, ptrn_list in ptrn_list_per_client.items():
        if len(ptrn_list) != 0:
            original_ptrn_list = get_original_ptrn_list(ptrn_list, evt_data_tid)
            usages = list()
            for ptrn in original_ptrn_list:
                usages.append(get_resource_usage(ptrn, metric_list))
            total_usages.extend(usages)

    print_usage_sum(experiments, output_prefix, output_dir, total_usages, metric_list, evt_data_tid, REAL_PATTERN_PRINT, req_count)
    print_usage_sum(experiments, output_prefix, output_dir, total_usages, metric_list, evt_data_tid, REAL_PATTERN_PRINT, req_count, mean=True)
    print_dist_info(ptrn_list_per_client, experiments, output_prefix, output_dir)


    if db_type == "redis":
        print_ptrn_avg_usage(experiments, output_prefix, output_dir, metric_list, avg_non_irregular_usage, req_count, total_non_irregular_ptrn_count, PTRN_HEADER_REDIS)
    elif db_type == "memcached":
        print_ptrn_avg_usage(experiments, output_prefix, output_dir, metric_list, avg_non_irregular_usage, req_count, total_non_irregular_ptrn_count, PTRN_HEADER_MEMCACHED)
    else:
        raise Exception(f"Invalid db type({db_type})")

def find_ptrns_per_client(evt_data, num_clients, db_type):
    ptrn_list_per_client = dict()

    for c in range(1, num_clients+1):
        found_pattern = find_ptrns(evt_data, db_type, c)
        ptrn_list_per_client[c] = found_pattern

    return ptrn_list_per_client

