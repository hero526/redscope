from subutils import syscall_info

import logging

def detect(record, threshold):
    ## Do Detection
    logging.info(f"[DETECTION] {record.experiment_info_str} START")

    # if record.workload != "idle" and record.db != "rocks" and record.db != "level":
    #     ## Want to find socket related "recv", "read", "send", "write" only
    #     opt = syscall_info.CLIENT_RELATED_RSRW
    #     record.find_longest_correlated_pattern(opt, threshold)

    ## Do not want to find kernel
    opt = syscall_info.NOT_RANDOM
    record.find_longest_correlated_pattern(opt, threshold)
    
    logging.debug(f"[DETECTION] {record.experiment_info_str} SUCCEED")