from subutils import syscall_info
from config import Config

from subclasses.correlation import Correlation

from pprint import pprint
import pickle
import os
import traceback

PATTERN_HEADER = ["PNAME","PATTERN","CORRELATION"]
PATTERN_DEBUG_HEADER = ["PLENGTH","PATTERN_VERBOSE","ORIGIN_PATTERN"]
EXPERIMENT_HEADER = ["ITERATION","SERVER","CPU","MEM","DISK","DB","WORKLOAD","RECORDCOUNT","OP_COUNTS","CLIENT"]
CAT_HEADER = ["FS","MM","IPC","NET","ARCH","KERNEL","SECUIRTY"]

# SEQUENCE_HEADER = ["START","END","TURNAROUND","RETURNS"]
# DISTRIBUTION_HEADER = EXPERIMENT_HEADER + PATTERN_HEADER + ["RANGE","TURNAROUND","NET_USAGE","DISK_USAGE"]


def merge_correlation_tsv(experiment_infos):
    delimeter = '\t'
    CORRELATION_HEADER = ["TYPE","SERVER","EXPERIMENT"] + PATTERN_HEADER + ["REPEATS","SPEARMAN"] + PATTERN_DEBUG_HEADER + ["OP_COUNTS","DEBUG(MAX_CHECK)"]
    merged_file_name = f'{Config.RESULT_DIR}/correlation.tsv'
    
    if not os.path.isfile(merged_file_name):
        f_out = open(merged_file_name, "w")
        header = delimeter.join(CORRELATION_HEADER)
        f_out.write(header+'\n')
    else:
        f_out = open(merged_file_name, "a")

    for experiment_info in experiment_infos:
        file_name = f'{Config.RESULT_DIR}/correlation_{experiment_info}.tsv'
        f = open(file_name, "r")
        f_out.write(f.read())
        f.close()
        # os.remove(file_name)
    
    f_out.close()



def print_correlation_tsv(record):
    delimeter = '\t'
    file_name = f'{Config.RESULT_DIR}/correlation_{record.experiment_info_str}.tsv'
    f = open(file_name, "w")

    op_counts_str = ', '.join( [str(c) for c in record.op_counts] )

    for opt in syscall_info.CONVERT_OPTIONS:
        if opt == syscall_info.CLIENT_RELATED_RSRW and (record.workload == "idle" or record.db == "rocks" or record.db == "level"):
            continue

        pt_correlation = set()
        for opc, pdict_pname_opt_iter in record.pdict_pname_opt_iter_opc.items():
            for pdict_pname_opt in pdict_pname_opt_iter.values():
                pdict_pname = pdict_pname_opt[opt]
                for pname, pdict in pdict_pname.items():
                    for pt, pt_obj in pdict.items():
                        if (pname, pt) in pt_correlation:
                            continue

                        if pt_obj.remain == 0:
                            continue

                        pt_correlation.add((pname, pt))

                        correlation = pt_obj.correlation

                        concated_pname = ','.join(list(pname))
                        syscall_names = '@@@'.join(syscall_info.pattern_to_name(pt))
                        comp_set_str = ', '.join( [str(c) for c in correlation.comp_set] )

                        correlation_logs = [f"opt{opt}", record.server_info_str, record.experiment_info_str, \
                                            concated_pname, syscall_names, correlation.grade_str, \
                                            comp_set_str, str(correlation.spearman), \
                                            str(len(pt)), syscall_info.pattern_to_verbose_str(pt), str(pt), \
                                            op_counts_str, str(correlation.max_check)]

                        correlation_log = delimeter.join(correlation_logs)
                        f.write(correlation_log+'\n')

    f.close()


def find_target_patterns(record, threshold):
    pinfo_opt_pname = dict()

    for pdict_pname_opt_iter in record.pdict_pname_opt_iter_opc.values():
        for pdict_pname_opt in pdict_pname_opt_iter.values():
            opt = syscall_info.NOT_RANDOM
            pdict_pname = pdict_pname_opt[opt]
            for pname, pdict in pdict_pname.items():
                
                concated_pname = ','.join(list(pname))
                if pinfo_opt_pname.get(concated_pname) is None:
                    pinfo_opt_pname[concated_pname] = dict()
                
                if pinfo_opt_pname[concated_pname].get(opt) is None:
                    pinfo_opt_pname[concated_pname][opt] = dict()

                for pt, pt_obj in pdict.items():
                    if pt_obj.remain == 0:
                        continue

                    if pt_obj.correlation.grade < Correlation.GRADE[threshold]:
                        continue
                    
                    if pinfo_opt_pname[concated_pname][opt].get(pt) is None:
                        pinfo_opt_pname[concated_pname][opt][pt] = dict()
                        pinfo_opt_pname[concated_pname][opt][pt]["spearman"] = []
                        pinfo_opt_pname[concated_pname][opt][pt]["frequency"] = []
                        pinfo_opt_pname[concated_pname][opt][pt]["DEBUG"] = pt_obj.correlation.comp_set

                    pinfo_opt_pname[concated_pname][opt][pt]["spearman"].append(pt_obj.correlation.spearman)
                    pinfo_opt_pname[concated_pname][opt][pt]["frequency"].append(pt_obj.frequency)

    for pname, pinfo_opt in pinfo_opt_pname.items():
        for opt, pinfo in pinfo_opt.items():
            for pt, info in pinfo.items():
                pinfo_opt_pname[pname][opt][pt]["spearman"] = caculate_mean(info["spearman"])
                pinfo_opt_pname[pname][opt][pt]["frequency"] = caculate_mean(info["frequency"])

    # tmp_pinfo_opt_pname = dict()
    # for pname, pinfo_opt in pinfo_opt_pname.items():
    #     tmp_pinfo_opt_pname[pname] = dict()

    #     for opt, pinfo in pinfo_opt.items():
    #         if len(pinfo) == 0:
    #             continue

    #         tmp_pinfo_opt_pname[pname][opt] = dict()

    #         for pt, info in pinfo.items():
    #             tmp_pinfo_opt_pname[pname][opt][pt] = pinfo_opt_pname[pname][opt][pt]
    #             tmp_pinfo_opt_pname[pname][opt][pt]["spearman"] = caculate_mean(info["spearman"])
    #             tmp_pinfo_opt_pname[pname][opt][pt]["frequency"] = caculate_mean(info["frequency"])

    # for pname, pinfo_opt in tmp_pinfo_opt_pname.items():
    #     if len(pinfo_opt) == 0:
    #         del pinfo_opt_pname[pname]
    #     else:
    #         pinfo_opt_pname[pname] = tmp_pinfo_opt_pname[pname]
    
    return pinfo_opt_pname

def caculate_mean(values):
    if len(values) == 0:
        return 0
    return sum(values, 0.0) / len(values)

def save_patterns_to_pickle(record, threshold):
    if record.workload == "idle" and (record.db == "rocks" or record.db == "level"):
        return

    filename = f'{Config.RESULT_DIR}/{record.db}/{record.workload}_{record.record_count}_{record.record_size}_{record.client}_{record.interval_ms}.pickle'

    pinfo_opt_pname = find_target_patterns(record, threshold)

    with open(f"{filename}_tmp", "wb") as f:
        pickle.dump(pinfo_opt_pname, f, pickle.HIGHEST_PROTOCOL)

    os.rename(f'{filename}_tmp', filename)

    # DEBUG
    with open(f"{filename}.txt", "w") as f:
        pprint(pinfo_opt_pname, stream=f)


def load_pickle_to_patterns(db, experiment):
    if experiment.split('_')[0] == "idle" and (db == "rocks" or db == "level"):
        return dict()

    filename = f'{Config.RESULT_DIR}/{db}/{experiment}.pickle'

    try:
        with open(f"{filename}", "rb") as f:
            data = pickle.load(f)
    except Exception as exc:
        raise Exception(f"[LOAD] {db} {experiment} FAIL: {traceback.format_exc()}")

    return data
