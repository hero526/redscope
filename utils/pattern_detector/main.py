#!/usr/bin/env python3

from subutils import dir_manager
from subutils import printer
from config import Config
from worker import work

import coloredlogs, logging
import concurrent.futures

import sys
import traceback
sys.setrecursionlimit(10**7)

if __name__ == "__main__":
    cfg = Config()

    LOG_FORMAT = "[%(levelname)s] (%(module)s line: %(lineno)d) - %(message)s"
    coloredlogs.install(fmt=LOG_FORMAT, level=cfg.loglevel)

    logging.info(f"TARGETS: {cfg.targets_with_db}")

    ## Cleaning
    dir_manager.mkdirs(Config.RESULT_DIR)
    dir_manager.clean(cfg)

    db_future = dict()
    executor = concurrent.futures.ProcessPoolExecutor()
    
    for db in cfg.dbs:
        logging.info(f"[WORK] {db} START")
        db_future[executor.submit(work, db, cfg.targets, cfg)] = db

    for future in concurrent.futures.as_completed(db_future):
        db = db_future[future]
        try:
            future.result()
        except Exception as exc:
            logging.error(f"[WORK] {db} FAIL: {traceback.format_exc()}")
            continue
        logging.debug(f"[WORK] {db} SUCCEED")
    executor.shutdown()

    # printer.merge_result_tsvs()