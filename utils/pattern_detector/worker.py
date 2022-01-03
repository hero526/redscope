from logics.filter import idle_filter
from logics.detector import detect
from logics.builder import build

from logics.extractor import extract
from subclasses.collector import MongoCTL

from subutils import printer
from config import Config

import concurrent.futures
import os
import logging
import traceback

from pprint import pprint
import pickle

import time
def work(db, targets, cfg):
    # Save idle patterns
    experiment_idle = "idle_0_0_0_0"
    save_patterns(cfg.idle_db_name, db, experiment_idle, cfg.spearman_threshold)
    idle_pinfo_opt_pname = printer.load_pickle_to_patterns(db, experiment_idle)

    experiment_future = dict()
    executor = concurrent.futures.ProcessPoolExecutor()
    
    mongo_ctl_work = MongoCTL()
    for target in targets:
        related_cols = mongo_ctl_work.get_collection_list(cfg.db_name, find=f"{db}_{target}")

        experiments = set()
        for col in related_cols:
            parsed_col = col.split('_')

            workload = parsed_col[1]
            record_count = int(parsed_col[2])
            record_size = int(parsed_col[3])
            client = int(parsed_col[4])
            interval_ms = int(parsed_col[5])

            experiments.add( f"{workload}_{record_count}_{record_size}_{client}_{interval_ms}" )

        for experiment in experiments:
            experiment_future[executor.submit(work_in_experiment, db, experiment, idle_pinfo_opt_pname, cfg)] = experiment
    mongo_ctl_work.close()

    for future in concurrent.futures.as_completed(experiment_future):
        experiment = experiment_future[future]
        try:
            pdict_pname_col, all_data_tid_col, tids_pname_col = future.result()
        except Exception as exc:
            logging.error(f"[WORK-EXPR] {db} {experiment} FAIL: {traceback.format_exc()}")
            continue
        logging.debug(f"[WORK-EXPR] {db} {experiment} SUCCEED")

        with open(f"{db}_{experiment}_pdict_pname_col.pickle", "wb") as f:
            pickle.dump(pdict_pname_col, f, pickle.HIGHEST_PROTOCOL)
        with open(f"{db}_{experiment}_pdict_pname_col.txt", "w") as f:
            for col, pdict_pname in pdict_pname_col.items():
                for pname, pdict in pdict_pname.items():
                    f.write(f"{col}, {pname}\n")
                    for pt, pt_obj in pdict.items():
                        tmp = [e for e in pt if e[1] >= 0]
                        f.write(f"{f'[{str(pt_obj.remain)}]':5s} {tuple(tmp)}\n")
        
        # with open(f"{db}_{experiment}_test.txt", "w") as f:
        #     for col, pdict_pname in pdict_pname_col.items():
        #         for pname, pdict in pdict_pname.items():
        #             f.write(f"{col}, {pname}\n")
        #             for pt, pt_obj in pdict.items():
        #                 f.write(f"===== {pt} =====\n")
        #                 for tid, start_idx in pt_obj.start_idx_tid.items():
        #                     for idx in start_idx:
        #                         f.write(f"{all_data_tid_col[col][tid][idx]['eventId']} ")
        #                 f.write("\n===============\n")

        with open(f"{db}_{experiment}_all_data_col.pickle", "wb") as f:
            pickle.dump(all_data_tid_col, f, pickle.HIGHEST_PROTOCOL)
        # with open(f"{db}_{experiment}_all_data_col.txt", "w") as f:
        #     pprint(all_data_tid_col, stream=f)

        # with open(f"{db}_{experiment}_tids_pname_col.pickle", "wb") as f:
            # pickle.dump(tids_pname_col, f, pickle.HIGHEST_PROTOCOL)
        # with open(f"{db}_{experiment}_tids_pname_col.txt", "w") as f:
            # pprint(tids_pname_col, stream=f)

        ## Print result
        # JERRY
        logging.info(f"[PRINT] {db} {experiment} OK")

    executor.shutdown()

def work_in_experiment(db, experiment, idle_pinfo_opt_pname, cfg):
    filtered_all_data_tid_col = idle_filter(cfg.db_name, db, experiment, idle_pinfo_opt_pname)
    save_patterns(cfg.filtered_db_name, db, experiment, cfg.spearman_threshold, filtered_all_data_tid_col)

    op_pinfo_opt_pname = printer.load_pickle_to_patterns(db, experiment)
    
    return extract(cfg.db_name, db, experiment, op_pinfo_opt_pname)


def save_patterns(collector, db, experiment, threshold, filtered_all_data_tid_col=dict()):
    filename = f'{Config.RESULT_DIR}/{db}/{experiment}.pickle'

    if os.path.isfile(filename):
        logging.info(f"Found {filename}!")
        return

    logging.info(f"[SAVE] Can't find {filename}.. Make {db}_{experiment} patterns now!")
    
    record = build(collector, db, experiment, filtered_all_data_tid_col)

    detect(record, threshold)
    # printer.print_correlation_tsv(record)
    printer.save_patterns_to_pickle(record, threshold)
    
