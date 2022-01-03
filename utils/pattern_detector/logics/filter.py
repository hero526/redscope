from subclasses.collector import MongoCTL

from subutils import syscall_info
from subutils import pname_info

import concurrent.futures
import logging
import traceback

def idle_filter(collector, db, experiment, idle_pinfo_opt_pname):
    mongo_ctl = MongoCTL()
    related_cols = mongo_ctl.get_collection_list(collector, find=f"{db}_{experiment}")
    already_filtered_cols = mongo_ctl.get_collection_list(f"FILTERED-{collector}", find=f"{db}_{experiment}", log=False)
    mongo_ctl.close()

    target_cols = [x for x in related_cols if x not in already_filtered_cols]

    logging.info(f"[FILTER] {db} {experiment} Total target length {len(target_cols)}")

    col_future = dict()
    with concurrent.futures.ProcessPoolExecutor() as executor:

        for col in target_cols:
            col_future[executor.submit(filter_in_col, collector, col, idle_pinfo_opt_pname)] = col
        
        filtered_all_data_tid_col = dict()
        for future in concurrent.futures.as_completed(col_future):
            col = col_future[future]
            try:
                filtered_all_data_tid_col[col] = future.result()
            except Exception as exc:
                logging.error(f"[FILTER] {col} FAIL: {traceback.format_exc()}")
                continue
            logging.debug(f"[FILTER] {col} SUCCEED")


    return filtered_all_data_tid_col


def filter_in_col(collector, col, idle_pinfo_opt_pname):
    mongo_ctl = MongoCTL()
    all_data_tid = mongo_ctl.get_data_in_collection(collector, col)
    pnames_tid = pname_info.get_pname_tid(all_data_tid)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures_tid = dict()

        for tid in all_data_tid.keys():
            # Find matches (target, idle)
            matched_idle_pinfo = []
            for pname in idle_pinfo_opt_pname.keys():
                if pname in ','.join(pnames_tid[tid]):
                # if set(pname.split(',')).issubset(set(pnames_tid[tid])):   # If idle_pnames are subset of target_pnames
                    matched_idle_pinfo.append(idle_pinfo_opt_pname[pname][syscall_info.NOT_RANDOM])

            if len(matched_idle_pinfo) > 0:
                futures_tid[tid] = executor.submit(filter_in_tid, all_data_tid[tid], matched_idle_pinfo)

        filtered_all_data_tid = dict()
        for tid in all_data_tid.keys():
            if futures_tid.get(tid) is None:
                filtered_all_data_tid[tid] = all_data_tid[tid]
            else:
                filtered_all_data_tid[tid] = futures_tid[tid].result()
               
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
                
        for tid in filtered_all_data_tid:
            data = filtered_all_data_tid[tid]
            futures.append(executor.submit(mongo_ctl.put_filtered_data_into_collection, f"FILTERED-{collector}", col, data))

        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                logging.error(f"[FILTER-UPLOAD] {col} FAIL: {traceback.format_exc()}")

    # for tid in all_data_tid.keys():
        # mongo_ctl.put_filtered_data_into_collection(f"FILTERED-{collector}", col, filtered_all_data_tid[tid])

    return filtered_all_data_tid


def filter_in_tid(all_data, matched_idle_pinfo):
    sequence = syscall_info.convert_sequence_to_tuple_events(all_data)
    
    for pinfo in matched_idle_pinfo:
        for pt, info in pinfo.items():
            frequency = info["frequency"]

            del_targets = syscall_info.extract_regex_pt_to_ranges(sequence, syscall_info.NOT_RANDOM, pt)
            if len(del_targets) == 0:
                continue

            target_frequency = len(del_targets) / syscall_info.get_thread_excution_time(all_data)
            if target_frequency / frequency > 1.1:
                continue
            
            plen = len(pt)
            # TODO: if the distance value for del_target is too big, that target might be skipped?
            for del_target in del_targets:
                start = del_target[0]
                end = del_target[-1]
                del_pt_idx = 0
                
                for idx in range(start, end):
                    if not syscall_info.check_event_opt(sequence[idx], syscall_info.NOT_RANDOM):
                        continue
                    
                    if sequence[idx] == pt[del_pt_idx]:
                        all_data[idx]["eventId"] = -1
                        continue

                    if del_pt_idx+1 < plen and sequence[idx] == pt[del_pt_idx+1]:
                        all_data[idx]["eventId"] = -1
                        del_pt_idx += 1
                        continue

                    raise Exception("Extract logic error")

    return all_data