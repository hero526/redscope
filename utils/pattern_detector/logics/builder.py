from subclasses.record import RelatedRecordSet
from subclasses.collector import MongoCTL

from subutils import pname_info
from subutils import syscall_info

import logging
import concurrent.futures
import traceback

def build(collector, db, experiment, filtered_all_data_tid_col=dict()):
    experiment_info = tuple([db]+experiment.split('_'))

    server_info = get_server_info(collector)

    record = RelatedRecordSet(collector, server_info, experiment_info)

    mongo_ctl_build = MongoCTL()
    related_cols = mongo_ctl_build.get_collection_list(collector, find=f"{db}_{experiment}")
    mongo_ctl_build.close()

    logging.info(f"[BUILD] {db} {experiment} Total target length {len(related_cols)}")

    if len(related_cols) == 0:
        raise Exception(f"Can't find any collection in {collector}. Please check whether {db}_{experiment} exists")

    # logging.info(f"[BUILD] {db} {experiment} START")

    col_future = dict()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        already_quried_cols = []

        for col in related_cols:
            filtered_all_data_tid = filtered_all_data_tid_col.get(col)
            if filtered_all_data_tid is None:
                col_future[executor.submit(query_all_data_tid, collector, col)] = col
            else:
                already_quried_cols.append(col)
            
        for col in already_quried_cols:
            all_data_tid = filtered_all_data_tid_col[col]
            update_record(record, col, all_data_tid)
            

        for future in concurrent.futures.as_completed(col_future):
            col = col_future[future]
            try:
                all_data_tid = future.result()
            except Exception as exc:
                logging.error(f"[BUILD] {collector} {col} FAILED: {traceback.format_exc()}")
                continue
            logging.debug(f"[QUERY] {col} SUCCEED")
            update_record(record, col, all_data_tid)
            logging.debug(f"[BUILD] {col} SUCCEED")

    record.update_op_counts()
    record.update_iterations_opc()
    record.update_common_pnames()

    for opc, reseq_tid_opt_iter in record.reseq_tid_opt_iter_opc.items():
        for iteration, reseq_tid_opt in reseq_tid_opt_iter.items():
            for opt in reseq_tid_opt.keys():
                record.update_pdict_pname_opt(opt)

    return record


def query_all_data_tid(collector, col):
    mongo_ctl_query = MongoCTL()
    all_data_tid = mongo_ctl_query.get_data_in_collection(collector, col)
    return all_data_tid


def update_record(record, col, all_data_tid):
    try:
        experiment_info, opc, iteration = get_experiment_info(col)
    except Exception as exc:
        raise exc

    tids_pname = pname_info.get_tids_pname(all_data_tid)
    
    record.update_tids_pname_iter_opc(opc, iteration, tids_pname)
    record.update_all_data_tid_iter_opc(opc, iteration, all_data_tid)

    futures_opt = dict()
    with concurrent.futures.ThreadPoolExecutor() as executor:

        for opt in syscall_info.CONVERT_OPTIONS:
            if opt == syscall_info.CLIENT_RELATED_RSRW:
                continue
            #if opt == syscall_info.CLIENT_RELATED_RSRW and (record.workload == "idle" or record.db == "rocks" or record.db == "level"):
            #    continue

            # futures_opt[opt] = build_reseq_tid(all_data_tid, opt)
            futures_opt[opt] = executor.submit(build_reseq_tid, all_data_tid, opt)

        for opt in futures_opt.keys():
            # reseq_tid = futures_opt[opt]
            reseq_tid = futures_opt[opt].result()
            record.update_reseq_tid_opt_iter_opc(opc, iteration, opt, reseq_tid)



def build_reseq_tid(all_data_tid, opt):
    reseq_tid = dict()
    for tid in all_data_tid:
        reseq_tid[tid] = syscall_info.convert_sequence_to_tuple_events(all_data_tid[tid], opt)
    return reseq_tid


def get_server_info(collector):
    parsed_collector = collector.split('_')
    if len(parsed_collector) != 5:
        raise Exception(f"Wrong DB name {collector}")

    server, cpu, mem, disk = parsed_collector[1], int(parsed_collector[2]), int(parsed_collector[3]), parsed_collector[4]
    return (server, cpu, mem, disk)
        
def get_experiment_info(col):
    parsed_col = col.split('_')
    if len(parsed_col) != 8:
        raise Exception(f"Wrong Collection name {col}")
    
    db = parsed_col[0]
    workload = parsed_col[1]
    record_count = int(parsed_col[2])
    record_size = int(parsed_col[3])
    client = int(parsed_col[4])
    intervalms = int(parsed_col[5])
    op_count = int(parsed_col[6])
    iteration = int(parsed_col[7][1:])

    return (db, workload, record_count, record_size, client, intervalms), op_count, iteration
