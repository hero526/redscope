#!/usr/bin/env python3

import sys
import random, string
import pickle
import concurrent.futures
import signal

WORKLOAD_TYPE_INSERT="insert"
WORKLOAD_TYPE_LOAD="load"
WORKLOAD_TYPE_SELCT_DELETE="select_delete"
WORKLOAD_TYPE_DUP_SELECT="dup-select"

def make_key_val(workload, max_client_num, client_num_no, key_lookup_range_per_client_num, opc, opc_per_client_num, filename):
        inputs = []
        if workload == WORKLOAD_TYPE_DUP_SELECT:
            # Make random key with duplicated number
            keys = [str(random.randrange(1, max_client_num + 1))  + "_" + str(random.randrange(key_lookup_range_per_client_num)) for _ in range(opc)] 
            for k in keys:
                inputs.append( (k,) )
        else:
            # Make random keys without duplicated number
            keys = random.sample(range(key_lookup_range_per_client_num), opc_per_client_num)
            for i in range(opc_per_client_num):
                keys[i] = str(client_num_no) + "_" + str(keys[i])
                if workload == WORKLOAD_TYPE_INSERT or workload == WORKLOAD_TYPE_LOAD:
                    # Make random string value
                    value = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(record_size_byte))
                    if workload == WORKLOAD_TYPE_INSERT:
                        keys[i] = "i" + str(keys[i])
                    inputs.append( ( str(keys[i]), value, ) )
                else:
                    inputs.append( ( str(keys[i]), ) )

        with open(filename, "wb") as f:
            pickle.dump(inputs, f, pickle.HIGHEST_PROTOCOL)
        print(f"Write a pickle({workload}, {client_num_no}/{max_client_num}) -> len:", len(inputs))

def sig_hup_handler(signum, frame):
    exit()

if __name__ == "__main__":
    signal.signal(signal.SIGHUP, sig_hup_handler)
    
    if len(sys.argv) < 4:
        raise Exception("Need num of client_num, num of opc parameter, lookup range, pwd")

    max_client_num = int(sys.argv[1])
    opc = int(sys.argv[2])
    dup_select_range = int(sys.argv[3])
    pwd = sys.argv[4]

    record_size_byte = 1000

    # filename {client_num}_{opc}_{dup_select_range}_{workload}_{client_num_no}.pickle
    base_filename = f"{max_client_num}_{opc}_{dup_select_range}"
    workload_type = [WORKLOAD_TYPE_INSERT, WORKLOAD_TYPE_LOAD, WORKLOAD_TYPE_SELCT_DELETE, WORKLOAD_TYPE_DUP_SELECT]

    opc_per_client_num = int(opc/max_client_num)
    key_lookup_range = None
    key_lookup_range_per_client_num = None

    executor = concurrent.futures.ProcessPoolExecutor()
    future_list = []

    for workload in workload_type:
        if workload == WORKLOAD_TYPE_DUP_SELECT:
            key_lookup_range = dup_select_range
        else:
            key_lookup_range = opc
        key_lookup_range_per_client_num = int(key_lookup_range/max_client_num)

        for client_num_no in range(1, max_client_num+1):
            filename = f"{pwd}/key_val_pickles/{base_filename}_{workload}_{client_num_no}.pickle"
            future_list.append(executor.submit(make_key_val, workload, max_client_num, client_num_no, key_lookup_range_per_client_num, opc, opc_per_client_num, filename))
        
        for f in future_list:
            f.result()
            
