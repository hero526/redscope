from subclasses.collector import MongoCTL
from subclasses.pattern import Pattern

from subutils import syscall_info
from subutils import pname_info

import concurrent.futures
import logging
import traceback


def extract(collector, db, experiment, pinfo_opt_pname):
    mongo_ctl_extract = MongoCTL()
    related_cols = mongo_ctl_extract.get_collection_list(collector, find=f"{db}_{experiment}")
    mongo_ctl_extract.close()

    logging.info(f"[EXTRACT] {db} {experiment} Total target length {len(related_cols)}")

    col_future = dict()
    
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for col in related_cols:
            col_future[executor.submit(extract_in_col, collector, col, pinfo_opt_pname)] = col
        
        pdict_pname_col = dict()
        all_data_tid_col = dict()
        tids_pname_col = dict()
        for future in concurrent.futures.as_completed(col_future):
            col = col_future[future]
            try:
                pdict_pname_col[col], all_data_tid_col[col], tids_pname_col[col] = future.result()
            except Exception as exc:
                logging.error(f"[EXTRACT] {col} FAIL: {traceback.format_exc()}")
                continue
            logging.debug(f"[EXTRACT] {col} SUCCEED")

    return pdict_pname_col, all_data_tid_col, tids_pname_col


def extract_in_col(collector, col, pinfo_opt_pname):
    mongo_ctl = MongoCTL()
    all_data_tid = mongo_ctl.get_data_in_collection(collector, col)
    tids_pname = pname_info.get_tids_pname(all_data_tid)

    pname_future = dict()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for pname, tids in tids_pname.items():
            pname_str = ','.join(list(pname))
            if pinfo_opt_pname.get(pname_str) is None:
                continue
            pname_future[executor.submit(extract_in_pname, pname_str, all_data_tid, tids, pinfo_opt_pname[pname_str])] = pname

        pdict_pname = dict()
        for future in concurrent.futures.as_completed(pname_future):
            pname = pname_future[future]
            try:
                pdict_pname[pname] = future.result()
            except Exception as exc:
                logging.error(f"[EXTRACT] {col} {pname} FAIL: {traceback.format_exc()}")

    return pdict_pname, all_data_tid, tids_pname
    
def extract_in_pname(pname, all_data_tid, tids, pinfo_opt):
    pdict = dict()
    time = 0

    for tid in tids:
        time += syscall_info.get_thread_excution_time(all_data_tid[tid])
        sequence = syscall_info.convert_all_sequence_to_tuple_events(all_data_tid[tid])
        pt_ranges = []

        extracted_range = syscall_info.client_related_pt_to_ranges(sequence, all_data_tid[tid])
        if len(extracted_range) > 0:
            pt_ranges.extend(extracted_range)
        else:
           logging.debug(f"{pname}: Can't find any client related pattern range")
    
        pinfo = pinfo_opt[syscall_info.NOT_RANDOM]
        for pt, info in pinfo.items():
            extracted_range = syscall_info.extract_regex_pt_to_ranges(sequence, syscall_info.NOT_RANDOM, pt)
            if len(extracted_range) == 0:
                continue
            
            pt_ranges.extend(extracted_range)
            
        if len(pt_ranges) == 0:
            continue
        pt_ranges.sort(key = lambda e: e[0])

        i = 0
        while True:
            if not (i < len(pt_ranges)-1):
                break

            base_range_start = pt_ranges[i][0]
            base_range_end = pt_ranges[i][-1]
            next_range_start = pt_ranges[i+1][0]
            next_range_end = pt_ranges[i+1][-1]

            if next_range_start <= base_range_end:
                new_range = [base_range_start, max(next_range_end, base_range_end)]
                del pt_ranges[i+1]
                del pt_ranges[i]
                pt_ranges.insert(i, new_range)
            else:
                i += 1

        for pt_range in pt_ranges:
            start = pt_range[0]
            end = pt_range[-1]

            pt = tuple(sequence[start:end+1])

            if pdict.get(pt) is None:
                pdict[pt] = Pattern(pt)

            if pdict[pt].start_idx_tid.get(tid) is None:
                pdict[pt].start_idx_tid[tid] = []

            pdict[pt].start_idx_tid[tid].append(start)

    for pt_obj in pdict.values():
        pt_obj.update_remain()
        pt_obj.update_frequency(time)

    return pdict
