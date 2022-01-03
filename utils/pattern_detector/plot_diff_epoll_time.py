import sys, os
from glob import glob
import pickle
import coloredlogs, logging, traceback

import concurrent.futures

import pandas as pd
import matplotlib as mpl
mpl.use('TkAgg')
version = mpl.__version__
import matplotlib.pyplot as plt
# plt.switch_backend('TkAgg')
from matplotlib.backends.backend_pdf import PdfPages

import seaborn as sns

from subclasses.collector import MongoCTL

from subutils import syscall_info

def del_file(path):
    try:
        os.remove(path)
    except:
        pass


def get_data():
    
    mongo_ctl = MongoCTL()
    related_cols = mongo_ctl.get_collection_list(collector, find=f"{sys.argv[2]}_*_*_*_*")
    len_cols = len(related_cols)

    results = []

    for i in range(len_cols):
        col = related_cols[i]
        client = col.split('_')[4]

        all_data_tid = mongo_ctl.get_data_in_collection(collector, col)
        for tid, all_data in all_data_tid.items():
            epoll = 0
            read_req = 0
            write_req = 0
            first_read = None
            last_write = None
            for data in all_data:
                if data["eventName"] == "epoll_wait":
                    if epoll == 0:
                        print(f"<<<================= {col} ====================")
                        epoll = 1
                        first = data
                        continue

                    if epoll == 1:
                        epoll = 0
                        second = data
                        if read_req == write_req:
                            multi = read_req
                        else:
                            read_req = 0
                            write_req = 0
                            print(f"Unmatched req read({read_req}) write({write_req})")
                            continue

                        epoll_ss = second["timestamp"] - first["timestamp"]
                        epoll_se = second["timestamp"] - first["endTimestamp"]
                        epoll_self = first["endTimestamp"] - first["timestamp"]
                        epoll_self_actual = first["endActualCycle"] - first["startActualCycle"]
                        if last_write is not None and first_read is not None:
                            operation = last_write["endTimestamp"] - first_read["timestamp"]
                            operation_actual = last_write["endActualCycle"] - first_read["startActualCycle"]
                            per_op = operation / multi
                            per_op_actual = operation_actual / multi
                        else:
                            operation = 0
                            operation_actual = 0
                            per_op = 0
                            per_op_actual = 0

                        results.append([f"cli{client}", multi, epoll_ss, epoll_se, epoll_self, epoll_self_actual, operation, operation_actual, per_op, per_op_actual])
                        read_req = 0
                        write_req = 0
                        first_read = None
                        last_write = None
                        print(f"================= {col} ====================>>>")

                if epoll == 0:
                    continue
                evt = syscall_info.convert_data_to_tuple_event(data)
                if evt == None:
                    continue
                    
                if syscall_info.get_opt_from_event(evt) == syscall_info.CLIENT_RELATED_RSRW:
                    if evt[1] in syscall_info.rr_syscall_table:
                        read_req += 1
                        if first_read is None:
                            first_read = data

                        print("read", data["returnValue"])
                    elif evt[1] in syscall_info.ws_syscall_table:
                        write_req += 1
                        print("write", data["returnValue"])

                        last_write = data
                    else:
                        print(f"Who are you? {evt}")

    return results


if len(sys.argv) < 3:
    print("put target e.g. redis_insert")
    exit(1)
collector = sys.argv[1]

metrics = [
    "epoll_ss",
    "epoll_se",
    "epoll_self",
    "epoll_self_actual",
    "operation",
    "operation_actual",
    "per_op",
    "per_op_actual"
]

basename = f"{collector}-{sys.argv[2]}"
dat_filename = basename + ".dat"
csv_filename = basename + ".csv"

for metric in metrics:
    del_file(basename + "-" + metric + ".svg")

if os.path.isfile(dat_filename):
    with open(dat_filename, "rb") as f:
        df = pickle.load(f)
else:
    data = get_data()
    df = pd.DataFrame(data, columns=["type", "multi_rq"] + metrics)
    with open(dat_filename, "wb") as f:
        pickle.dump(df, f, pickle.HIGHEST_PROTOCOL)

    df.to_csv(csv_filename)

print(df)
## FOR COUNT CHECKING
# grouped = df_epoll_se.groupby(['type', 'multi-rq'])
# grouped = df_epoll_ss.groupby(['type', 'multi-rq'])
# print(grouped.count())
# print(df.shape)
# print(df.head)


for metric in metrics:

    plt.figure(figsize=(27,8))
    # manager = plt.get_current_fig_manager()
    # manager.resize(*manager.window.maxsize())

    ax = sns.boxplot(x="multi_rq", y=metric, hue="type", data=df,
    linewidth=0.3,
    showfliers=False,
    showmeans=True,
    meanprops={"marker":"x",
                "markeredgecolor":"black",
                "markersize":"1"}
    )
    # iterate over boxes
    for i, box in enumerate(ax.artists):
        color = box.get_facecolor()
        box.set_edgecolor(color)
        # box.set_fill(False)

        # iterate over whiskers and median lines
        # for j in range(5*i,5*(i+1)): without fliers, mean
        for j in range(6*i,6*(i+1)):
            ax.lines[j].set_color(color)

    max_multi=max(df["multi_rq"])
    [plt.axvline(x+0.5, color = 'black', linestyle='--') for x in list(range(0,max_multi))]


    handles, labels = ax.get_legend_handles_labels()
    for i, handle in enumerate(handles):
        color = handle.get_facecolor()
        handle.set_edgecolor(color)
        # handle.set_fill(False)

    plt.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 1), ncol=len(set(df["multi_rq"])))
    plt.savefig(f"{basename}-{metric}.svg")
    plt.clf()