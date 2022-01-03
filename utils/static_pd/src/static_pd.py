from const import *
from config import CONFIG

VALID_EVT_LIST_MEMCACHED = [232, 0, 46, -10]
VALID_EVT_LIST_REDIS = [232, 0, 1, -10]
VALID_EVT_LIST_MONGO_RRS = [46, 47, -10]

def get_filterting_target_evts(db_type):
    filtering_pattern_list = []
    valid_evt_list = None

    if db_type == "mongo":
        valid_evt_list = VALID_EVT_LIST_MONGO_RRS
    elif db_type == "redis":
        filtering_pattern_list.append([39, 257, 0, 3])
        valid_evt_list = VALID_EVT_LIST_REDIS
    elif db_type == "memcached":
        filtering_pattern_list.append([0, 52, 233])
        filtering_pattern_list.append([0, 10, 10, 52, 233])
        valid_evt_list = VALID_EVT_LIST_MEMCACHED
    else:
        raise Exception("Invalid db_type")
    
    return (filtering_pattern_list, valid_evt_list)


def do_filltering(evt_data, filtering_pattern_list, valid_evt_list):
    if len(filtering_pattern_list) != 0: 
        for filtering_pattern in filtering_pattern_list:
            evt_data = do_filtering_ptrn(evt_data, filtering_pattern)
    evt_data = do_filtering_ptrn_with_valid_evt_list(evt_data, valid_evt_list)

    return evt_data

def do_filtering_ptrn(evt_data, ptrn):
    result = []

    tmp_pattern = []
    skip_count = 0
    for i in range(len(evt_data)):
        evt = evt_data[i]
        result.append(evt)
        cur_idx = len(list(filter(lambda x: x["eventId"] != EVT_ID_CPU_OFF, tmp_pattern)))
        
        if skip_count > 0:
            skip_count -= 1            
            continue

        # Hit
        if evt["eventId"] == EVT_ID_CPU_OFF and cur_idx != 0:
            tmp_pattern.append(evt)
        elif evt["eventId"] == ptrn[cur_idx]:
            tmp_pattern.append(evt)
            # clear
            if cur_idx + 1 == len(ptrn):
                last_cpu_off_idx = get_cpu_off_idx_belong_to_prev_evt(evt_data, i)
                if last_cpu_off_idx != i:
                    cpu_off_evts = evt_data[i:last_cpu_off_idx+1]
                    skip_count += last_cpu_off_idx - i
                    tmp_pattern.extend(cpu_off_evts)

                result = result[:-len(tmp_pattern)]
                tmp_pattern=[]
        else:
            tmp_pattern=[]
            if evt["eventId"] == ptrn[0]:
                tmp_pattern.append(evt)
            continue

    return result

def do_filtering_ptrn_with_valid_evt_list(evt_data, valid_evt_list):
    result = []
    for evt in evt_data:
        if evt["eventId"] in valid_evt_list:
            result.append(evt)

    return result

def find_ptrns(evt_data, db_type, client=None, opt=None):
    result = None
    if db_type == "mongo":
        result = find_ptrns_mongo(evt_data, opt)
    elif db_type == "redis":
        result = find_ptrns_redis(evt_data, client)
    elif db_type == "memcached":
        result = find_ptrns_memcached(evt_data, client)
    else:
        raise Exception("Invalid db_type")

    return result

def find_ptrns(evt_data, db_type, client=None, opt=None):
    result = None
    if db_type == "mongo":
        result = find_ptrns_mongo(evt_data, opt)
    elif db_type == "redis":
        result = find_ptrns_redis(evt_data, client)
    elif db_type == "memcached":
        result = find_ptrns_memcached(evt_data, client)
    else:
        raise Exception("Invalid db_type")

    return result

def find_ptrns_memcached(evt_data, client):
    GOAL_PATTERN_FORMAT = []
    GOAL_START_FORMAT = [232]
    GOAL_REPEAT_FORMAT = [0, 46]
    
    GOAL_PATTERN_FORMAT.extend(GOAL_START_FORMAT)
    for _ in range(client):
        GOAL_PATTERN_FORMAT.extend(GOAL_REPEAT_FORMAT)
    result = []

    tmp_pattern = []
    skip_count = 0
    for i in range(len(evt_data)):
        evt = evt_data[i]
        cur_idx = len(list(filter(lambda x: x["eventId"] != EVT_ID_CPU_OFF, tmp_pattern)))
    
        if skip_count > 0:
            skip_count -= 1            
            continue
        
        if evt["eventId"] == EVT_ID_CPU_OFF and cur_idx != 0:
            tmp_pattern.append(evt)
        elif evt["eventId"] == GOAL_PATTERN_FORMAT[cur_idx]:
            tmp_pattern.append(evt)

            if cur_idx + 1 == len(GOAL_PATTERN_FORMAT):
                # (e r s r s) include (e r s)
                if i + 1 <= len(evt_data) - 1 and evt_data[i+1]["eventId"] == 0:
                    tmp_pattern = []
                    continue
                last_cpu_off_idx = get_cpu_off_idx_belong_to_prev_evt(evt_data, i)
                if last_cpu_off_idx != i:
                    cpu_off_evts = evt_data[i+1:last_cpu_off_idx+1]
                    skip_count += last_cpu_off_idx - i
                    tmp_pattern.extend(cpu_off_evts)

                result.append(tmp_pattern)
                tmp_pattern = []
        else:
            tmp_pattern = []
            if evt["eventId"] == GOAL_PATTERN_FORMAT[0]:
                tmp_pattern.append(evt)
            continue
    return result


def find_ptrns_redis(evt_data, client):
    GOAL_PATTERN_FORMAT_START = [232]
    GOAL_PATTERN_FORMAT_READ_REPEAT = [0]
    GOAL_PATTERN_FORMAT_MID = [0]
    GOAL_PATTERN_FORMAT_WRITE_REPEAT = [1]

    GOAL_PATTERN_FORMAT = GOAL_PATTERN_FORMAT_START

    for i in range(client):
        GOAL_PATTERN_FORMAT.extend(GOAL_PATTERN_FORMAT_READ_REPEAT)
    eagain_read_idx = len(GOAL_PATTERN_FORMAT)
    GOAL_PATTERN_FORMAT.extend(GOAL_PATTERN_FORMAT_MID)
    for i in range(client):
        GOAL_PATTERN_FORMAT.extend(GOAL_PATTERN_FORMAT_WRITE_REPEAT)
        
    result = []

    skip_count = 0
    tmp_pattern = []
    for i in range(len(evt_data)):
        evt = evt_data[i]
        cur_idx = len(list(filter(lambda x: x["eventId"] != EVT_ID_CPU_OFF, tmp_pattern)))

        if skip_count >0:
            skip_count -= 1            
            continue

        if evt["eventId"] == EVT_ID_CPU_OFF and cur_idx != 0:
            tmp_pattern.append(evt)
        elif evt["eventId"] == GOAL_PATTERN_FORMAT[cur_idx]:
            if cur_idx == eagain_read_idx:
                if int(evt["returnValue"]) != -11:
                    tmp_pattern = []
                    continue

            tmp_pattern.append(evt)
            if cur_idx + 1 == len(GOAL_PATTERN_FORMAT):
                last_cpu_off_idx = get_cpu_off_idx_belong_to_prev_evt(evt_data, i)
                if last_cpu_off_idx != i:
                    cpu_evts = evt_data[i+1:last_cpu_off_idx+1]
                    skip_count += last_cpu_off_idx - i
                    tmp_pattern.extend(cpu_evts)
                
                result.append(tmp_pattern)
                tmp_pattern = []
        else:
            tmp_pattern = []
            if evt["eventId"] == GOAL_PATTERN_FORMAT[0]:
                tmp_pattern.append(evt)
            continue

    return result

def find_ptrns_mongo(evt_data, opt):
    GOAL_PATTERN_FORMAT = None
    if opt == MONGO_PTRN_CONN:
        GOAL_PATTERN_FORMAT = [47, 47, 46]
    elif opt == MONGO_PTRN_FLUSHER:
        GOAL_PATTERN_FORMAT = [18, 75]
    elif opt == MONGO_PTRN_MONGOD or opt == MONGO_PTRN_CONN_FLUSH:
        GOAL_PATTERN_FORMAT = [18]
    else:
        raise Exception("Invalid opt")
    
    result = []

    skip_count=0
    tmp_pattern = []
    for i in range(len(evt_data)):
        evt = evt_data[i]
        cur_idx = len(list(filter(lambda x: x["eventId"] != EVT_ID_CPU_OFF, tmp_pattern)))

        if skip_count >0:
            skip_count -= 1            
            continue

        if evt["eventId"] == EVT_ID_CPU_OFF and cur_idx != 0:
            tmp_pattern.append(evt)
        elif evt["eventId"] == GOAL_PATTERN_FORMAT[cur_idx]:
            if opt == MONGO_PTRN_MONGOD or opt == MONGO_PTRN_CONN_FLUSH:
                pathname = str(evt["args"][-1]["value"])
                if FLUSH_PATH_NAME not in str(pathname):
                    continue

            tmp_pattern.append(evt)

            if cur_idx + 1 == len(GOAL_PATTERN_FORMAT):
                last_cpu_off_idx = get_cpu_off_idx_belong_to_prev_evt(evt_data, i)
                if last_cpu_off_idx != i:
                    cpu_evts = evt_data[i+1:last_cpu_off_idx+1]
                    skip_count += last_cpu_off_idx - i
                    tmp_pattern.extend(cpu_evts)

                result.append(tmp_pattern)
                tmp_pattern = []
        else:
            tmp_pattern = []
            if evt["eventId"] == GOAL_PATTERN_FORMAT[0]:
                tmp_pattern.append(evt)
            continue
    
    return result

def get_cpu_off_idx_belong_to_prev_evt(evt_data, checked_idx):
    last_checked_evt = evt_data[checked_idx]
    last_checked_evt_start_ts = last_checked_evt["timestamp"]
    last_checked_evt_end_ts = last_checked_evt["endTimestamp"]

    for idx in range(checked_idx + 1, len(evt_data)):
        cur_evt = evt_data[idx]
        cur_evt_id = cur_evt["eventId"]
        cur_evt_start_ts = cur_evt["timestamp"]
        cur_evt_end_ts = cur_evt["endTimestamp"]

        if cur_evt_id == EVT_ID_CPU_OFF:
            if last_checked_evt_start_ts <= cur_evt_start_ts and last_checked_evt_end_ts >= cur_evt_end_ts:
                if idx == len(evt_data) -1:
                    return idx
                else:
                    continue
            else:
                return idx - 1
        else:
            return idx - 1

    return checked_idx

def trim_cpu_off_evts_front(evt_data):
    not_cpu_off_start_idx = None
    for idx in range(len(evt_data)):
        evt = evt_data[idx]
        if evt["eventId"] != EVT_ID_CPU_OFF:
            not_cpu_off_start_idx = idx
            break

    if not_cpu_off_start_idx == None:
        raise Exception("There is only CPU OFF evts")

    return not_cpu_off_start_idx

def trim_cpu_off_evts_end(evt_data):
    last_idx = len(evt_data) - 1
    non_cpu_off_evt_idx = None
    cur_idx = last_idx
    while True:
        if cur_idx < 0:
            raise Exception("Invalid event data")

        cur_evt = evt_data[cur_idx]
        cur_evt_id = cur_evt["eventId"]

        if cur_evt_id != EVT_ID_CPU_OFF:
            non_cpu_off_evt_idx = cur_idx
            break  
        else:
           cur_idx -= 1
    
    return get_cpu_off_idx_belong_to_prev_evt(evt_data, non_cpu_off_evt_idx)

def trim_cpu_off_evts(evt_data):
    if len(evt_data) == 0:
        return evt_data
    
    all_evt_is_cpu_off = len(list(filter(lambda x: x["eventId"] != EVT_ID_CPU_OFF, evt_data))) == 0

    if not all_evt_is_cpu_off:
        front_idx = trim_cpu_off_evts_front(evt_data.copy())
        end_idx = trim_cpu_off_evts_end(evt_data.copy())
    else:
        return []

    return evt_data[front_idx: end_idx+1]

def get_original_ptrn_list(ptrn_list, original_evt_data_tid):
    last_found_idx_tid = dict()
    result = []

    for ptrn in ptrn_list:
        tid = ptrn[0]["threadId"]
        evt_data = original_evt_data_tid[tid]
        tmp_ptrn = []
        is_found_start_evt = False

        ptrn_id_list = [] 
        for e in ptrn:
            ptrn_id_list.append(str(e["_id"]))

        if last_found_idx_tid.get(tid) is None:
            last_found_idx_tid[tid] = 0

        for idx in range(last_found_idx_tid[tid], len(evt_data)):
            evt = evt_data[idx]
            evt_obj_id = str(evt["_id"])
            
            if evt_obj_id == ptrn_id_list[0]:
                is_found_start_evt = True
                tmp_ptrn = []
            if is_found_start_evt:
                if evt_obj_id in ptrn_id_list and evt["eventId"] != EVT_ID_CPU_OFF:
                    evt["isPattern"] = True
                else:
                    evt["isPattern"] = False
                tmp_ptrn.append(evt)

            if evt_obj_id == ptrn_id_list[-1]:
                if len(tmp_ptrn) != 0:
                    result.append(tmp_ptrn)
                last_found_idx_tid[tid] = idx
                break
    return result


#   'endActualCycle': 1414976924,
#   'endCPU': 5,
#   'endTimestamp': 37985.446560037,
#   'eventId': 0,
#   'eventName': 'read',
#   'overheadEnterActualCycle': 22460,
#   'overheadExitActualCycle': 27280,
#   'processId': 354597,
#   'processName': 'redis-server',
#   'returnValue': -11,
#   'startActualCycle': 1414904768,
#   'startCPU': 5,

#   'threadId': 354597,
#   'timestamp': 37985.446499767,
##################################################################
#   'eventName': 'epoll_wait',
#   'startActualCycle': 949897277,
#   'endActualCycle': 950119030,

#   'overheadEnterActualCycle': 22052,
#   'overheadExitActualCycle': 26134,

#   'timestamp': 38188.534880274,
#   'endTimestamp': 38188.535278944,
#   'processName': 'memcached',

# # ------------------------------------------------
#   'eventName': 'CPU_OFF',
#   'startActualCycle': 949944637,
#   'endActualCycle': 950070274,

#   'overheadEnterActualCycle': 23016,
#   'overheadExitActualCycle': 22748,

#   'timestamp': 38188.534919833,
#   'endTimestamp': 38188.535238219,
#   'processName': 'memcached',



def get_resource_usage(ptrn, metric_list):
    result = []
    # user_event_hooking_overhead = {"ActualCycle":0, "RetiredInst":0,"UopsLoads":951.452,"UopsStores":659.679,"RDCAS":0,"WRCAS":0}
    
    if CONFIG["UK_TYPE"] == "U":
        # (LOAD STORE)
        #                   EVENT               CPUOFF    
        # MEAN95    1281.738318	1059            3020.75	2401
        # AVG       1286.965388	1061.813377     3385.431818	2634.477273

        event_hooking_overhead = {"RetiredInst":0,"ActualCycle":0, "UopsLoads":1281.738318,"UopsStores":1059,"RDCAS_0_0":0,"WRCAS_0_0":0,"RDCAS_0_1":0,"WRCAS_0_1":0,"RDCAS_1_0":0,"WRCAS_1_0":0,"RDCAS_1_1":0,"WRCAS_1_1":0}
        cpuoff_hooking_overhead = {"RetiredInst":0, "ActualCycle":0, "UopsLoads":3020.75,"UopsStores":2401,"RDCAS_0_0":0,"WRCAS_0_0":0,"RDCAS_0_1":0,"WRCAS_0_1":0,"RDCAS_1_0":0,"WRCAS_1_0":0,"RDCAS_1_1":0,"WRCAS_1_1":0}
        
    elif CONFIG["UK_TYPE"] == "K":
        # (ACT INST LOAD STORE)

        # EVENT
        # MEAN95 28129.98582 7630 1309 1064
        # AVG 28260.65245 7644.755857 1313.38346 1066.715511
        # KK 23523.0099 7079.980198 0 0

        # CPUOFF (ACT INST LOAD STORE)
        # MEAN95 34502.66667 9822.666667 1849.666667 1385
        # AVG 39007.22 11159.51 2269.88 1656.64
        # KK 28262 9185 0 0

        #               	EVENT					        CPUOFF	
        # MEAN95    7514	20964.82353 3 1             17423.6 46955.8 3 1
        # AVG   7523.506619 21121.75143 3.0802213       1.038134756 19223.87952 51082.26506 190.4698795 78.63855422

        event_hooking_overhead = {"RetiredInst":7630, "ActualCycle":28129.98582, "UopsLoads":0,"UopsStores":0,"RDCAS_0_0":0,"WRCAS_0_0":0,"RDCAS_0_1":0,"WRCAS_0_1":0,"RDCAS_1_0":0,"WRCAS_1_0":0,"RDCAS_1_1":0,"WRCAS_1_1":0}
        cpuoff_hooking_overhead = {"RetiredInst":9822.666667, "ActualCycle":34502.66667,"UopsLoads":0,"UopsStores":0,"RDCAS_0_0":0,"WRCAS_0_0":0,"RDCAS_0_1":0,"WRCAS_0_1":0,"RDCAS_1_0":0,"WRCAS_1_0":0,"RDCAS_1_1":0,"WRCAS_1_1":0}

        for metric in event_hooking_overhead:
            cpuoff_hooking_overhead[metric] = cpuoff_hooking_overhead[metric] - event_hooking_overhead[metric]

    else:
        raise Exception(f"Invalid UK_TYPE {CONFIG['UK_TYPE']}")
    
    prev_cpu_off = None
    cpu_off_inside = False
    cur_event = ptrn[0]
    for next_event in ptrn[1:]:
        cur_resource = dict() 
        if cur_event["eventId"] != EVT_ID_CPU_OFF:
            if next_event["eventId"] == EVT_ID_CPU_OFF and next_event["timestamp"] >= cur_event["timestamp"] and next_event["endTimestamp"] <= cur_event["endTimestamp"]: # CPU OFF in current event
                cur_resource["eventId"] = cur_event["eventId"]
                cur_resource["returnValue"] = cur_event["returnValue"]
                cur_resource["isPattern"] = cur_event["isPattern"]
                if cpu_off_inside is False: # First CPU_OFF in current event
                    cpu_off_inside = True                    
                    for metric in metric_list:
                        cur_resource[metric] = next_event["start" + metric] - cur_event["start" + metric] \
                        - cur_event["overheadEnter" + metric] - cur_event["overheadExit" + metric] - event_hooking_overhead[metric] - cpuoff_hooking_overhead[metric] # set current event's resource without CPU_OFF
                    
                    result.append(cur_resource)
                else: # More CPU_OFF in current event
                    for metric in metric_list:
                        result[-1][metric] = result[-1][metric] + (next_event["start" + metric] - prev_cpu_off["end" + metric]) - cpuoff_hooking_overhead[metric]
                
                prev_cpu_off = next_event
                continue

            else: # CPU OFF not in current event
                if cpu_off_inside is True:
                    for metric in metric_list:
                        result[-1][metric] = result[-1][metric] + (cur_event["end" + metric] - prev_cpu_off["end" + metric])
                    prev_cpu_off = None
                    cpu_off_inside = False
                else:
                    cur_resource["eventId"] = cur_event["eventId"]
                    cur_resource["returnValue"] = cur_event["returnValue"]
                    cur_resource["isPattern"] = cur_event["isPattern"]
                    for metric in metric_list:
                        cur_resource[metric] = cur_event["end" + metric] - cur_event["start" + metric] \
                        - cur_event["overheadEnter" + metric] - cur_event["overheadExit" + metric] - event_hooking_overhead[metric]
                    result.append(cur_resource)

        interval_resource = dict()
        interval_resource["eventId"] = EVT_ID_INTERVAL
        interval_resource["returnValue"] = 0
        interval_resource["isPattern"] = False
        for metric in metric_list:
            interval_resource[metric] = next_event["start" + metric] - cur_event["end" + metric]

        result.append(interval_resource)
        cur_event = next_event

    if ptrn[-1]["eventId"] != EVT_ID_CPU_OFF and ptrn[-1]["startCPU"] == ptrn[-1]["endCPU"]:
        cur_resource = dict()
        cur_resource["eventId"] = ptrn[-1]["eventId"]
        cur_resource["returnValue"] = ptrn[-1]["returnValue"]
        cur_resource["isPattern"] = ptrn[-1]["isPattern"]
        for metric in metric_list:
            cur_resource[metric] = ptrn[-1]["end" + metric] - ptrn[-1]["start" + metric] \
            - ptrn[-1]["overheadEnter" + metric] - ptrn[-1]["overheadExit" + metric] - event_hooking_overhead[metric]
        result.append(cur_resource)
    elif cpu_off_inside is True: # if last event is CPU_OFF inside of result[-1]
        for metric in metric_list:
            result[-1][metric] = result[-1][metric] + (cur_event["end" + metric] - prev_cpu_off["end" + metric])
        prev_cpu_off = None
        cpu_off_inside = False

    interval_num = 0
    merged_result = []
    for data in result:
        # for metric in ["ActualCycle"]:
        #     if data[metric] < 0:
        #         # import pprint
        #         # pprint.pprint(ptrn)
        #         # for e in ptrn:
        #         #     print(e["eventId"], end=" ")
        #         # print()
        #         # pprint.pprint(result)
        #         raise Exception(f"Invalid value: {data} ")

        if data["eventId"] != -11:
            merged_result.append(data)
        elif merged_result[-1]["eventId"] != -11:
            merged_result.append(data)
            merged_result[-1]["returnValue"] = interval_num
            merged_result[-1]["isPattern"] = True
            interval_num += 1
        else:
            for metric in metric_list:
                merged_result[-1][metric] += data[metric]

    return merged_result


def is_belong(next_event, cur_event):
    cur_start_ts = cur_event["timestamp"]
    cur_end_ts = cur_event["endTimestamp"]
    next_start_ts = next_event["timestamp"]
    next_end_ts = next_event["endTimestamp"]
    if next_start_ts >= cur_start_ts:
        if next_end_ts <= cur_end_ts:
            return True
        else:
            raise Exception("Strange event 창호 화이팅")
    return False


def get_non_irregular_ptrn_usage(ptrn_list, original_ptrn_list, metric_list):
    non_irregular_usage = []
    num_of_not_irregular_ptrn = 0
    
    for idx in range(len(ptrn_list)):
        ptrn = ptrn_list[idx]
        original_ptrn = original_ptrn_list[idx]
        is_contain_irregular = len(ptrn) != len(original_ptrn)

        if is_contain_irregular is True:
            continue
        
        usage = get_resource_usage(ptrn, metric_list)
        if len(non_irregular_usage) == 0:
            for ptrn_idx in range(len(usage)):
                non_irregular_usage.append(dict())
                for metric in metric_list:
                    non_irregular_usage[ptrn_idx][metric] = 0

        for j in range(len(usage)):
            non_irregular_usage[j]["eventId"] = usage[j]["eventId"]
            for metric in metric_list:
                if "Uops" not in metric:
                    if CONFIG["UK_TYPE"] == "K" and usage[j]["eventId"] == EVT_ID_INTERVAL:
                        continue
                    elif CONFIG["UK_TYPE"] == "U" and usage[j]["eventId"] != EVT_ID_INTERVAL:
                        continue
                non_irregular_usage[j][metric] += usage[j][metric]
    
        num_of_not_irregular_ptrn += 1

    return (non_irregular_usage, num_of_not_irregular_ptrn)
            

def do_multi_req_handling(non_irregular_usage, metric_list, db_type):
    if db_type == "redis":
        return do_multi_req_handling_redis(non_irregular_usage, metric_list)
    elif db_type == "memcached":
        return do_multi_req_handling_memcached(non_irregular_usage, metric_list)
    else:
        raise Exception(f"Invalid db type: {db_type}")

def do_multi_req_handling_redis(non_irregular_usage, metric_list):
    result = [] # Redis result: e i [ r i ] r(-11) [ i w ]
    for _ in range(7):
        item = dict()
        for metric in metric_list:
            item[metric] = 0
        result.append(item)

    ptrn_len = len(non_irregular_usage)
    req_count = (ptrn_len - 3)/4
    if req_count % 1 != 0:
        raise Exception("Invalid redis ptrn")
    req_count = int(req_count)

    idx_epoll_wait = 0
    idx_interval_after_epoll_wait = 1
    idx_eagain_read = 2 * req_count + 2

    result[idx_epoll_wait] = non_irregular_usage[idx_epoll_wait]
    result[idx_interval_after_epoll_wait] = non_irregular_usage[idx_interval_after_epoll_wait]
    result[4] = non_irregular_usage[idx_eagain_read]
    front = non_irregular_usage[idx_interval_after_epoll_wait + 1: idx_eagain_read]
    end = non_irregular_usage[idx_eagain_read + 1: ]

    for idx in range(len(front)):
        item = front[idx]
        result_idx = None
        if idx % 2 == 0: # read 
            result_idx = 2
        else: # interval 
            result_idx = 3

        for metric in metric_list:
            result[result_idx][metric] += item[metric]
    
    for idx in range(len(end)):
        item = end[idx]
        result_idx = None
        if idx % 2 == 0: # interval 
            result_idx = 5
        else: # write
            result_idx = 6

        for metric in metric_list:
            result[result_idx][metric] += item[metric]

    return result
        
def do_multi_req_handling_memcached(non_irregular_usage, metric_list):
    result = [] # Redis result: e [i r i w]

    for _ in range(5):
        item = dict()
        for metric in metric_list:
            item[metric] = 0
        result.append(item)

    ptrn_len = len(non_irregular_usage)
    req_count = (ptrn_len - 1)/4
    if req_count % 1 != 0:
        raise Exception("Invalid memcached ptrn")
    req_count = int(req_count)

    idx_epoll_wait = 0

    result[idx_epoll_wait] = non_irregular_usage[idx_epoll_wait]
    trimmed = non_irregular_usage[idx_epoll_wait+ 1: ]

    for idx in range(len(trimmed)):
        item = trimmed[idx]
        result_idx = idx % 4 + 1
        for metric in metric_list:
            result[result_idx][metric] += item[metric]
   
    return result