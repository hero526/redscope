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

from subutils import syscall_info

def del_file(path):
    try:
        os.remove(path)
    except:
        pass

def get_cycles(pt_obj, all_data_tid):
    plen = pt_obj.length
    cycles = []
    for tid, start_idx in pt_obj.start_idx_tid.items():
        all_data = all_data_tid[tid]
        for sidx in start_idx:
            all_events = all_data[sidx:sidx+plen]
            cycle = 0
            for event in all_events:
                cycle += event["endCycle"] - event["startCycle"]

            cycles.append(cycle)

    return cycles

def get_data(type_dir):
    if type_dir != "new-conn" and type_dir != "re-conn":
        logging.error(f"Wrong type_dir {type_dir}")
        exit()

    all_data_files = sorted(list(glob(f'{type_dir}/{sys.argv[1]}*all_data_col.pickle')), key=lambda e: int(e.split('_')[4]))
    pdict_files = sorted(list(glob(f'{type_dir}/{sys.argv[1]}*pdict_pname_col.pickle')), key=lambda e: int(e.split('_')[4]))
    len_files = len(all_data_files)

    data = []

    for i in range(len_files):
        client = pdict_files[i].split('_')[4]
        if all_data_files[i].split('_')[:5] != pdict_files[i].split('_')[:5]:
            logging.error("Wrong file matched")
            exit(1)

        try:
            with open(f"{all_data_files[i]}", "rb") as f:
                all_data_tid_col = pickle.load(f)
            with open(f"{pdict_files[i]}", "rb") as f:
                pdict_pname_col = pickle.load(f)
        except Exception as exc:
            raise Exception(f"[LOAD] {db} {experiment} FAIL: {traceback.format_exc()}")
        
        for col, pdict_pname in pdict_pname_col.items():
            all_data_tid = all_data_tid_col[col]
            for pname, pdict in pdict_pname.items():
                for pt, pt_obj in pdict.items():
                    nreq = 0
                    for event in pt:
                        if syscall_info.get_opt_from_event(event) == syscall_info.CLIENT_RELATED_RSRW:
                            nreq += 1
                    multi = int(nreq / 2)
                    if multi > 0:
                        cycles = get_cycles(pt_obj, all_data_tid)
                        for cycle in cycles:
                            data.append([f'{type_dir}_cli{client}', multi, cycle])

    return data


if len(sys.argv) < 2:
    print("put target e.g. redis_insert")
    exit(1)

dat_filename = f"multi-{sys.argv[1]}.dat"
svg_filename = f"multi-{sys.argv[1]}.svg"

del_file(svg_filename)

if os.path.isfile(dat_filename):
    with open(dat_filename, "rb") as f:
        df = pickle.load(f)
else:
    future_dir = dict()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        data = []
    
        for dir_name in ["re-conn", "new-conn"]:
            future_dir[dir_name] = executor.submit(get_data, dir_name)

        for dir_name in future_dir:
            future = future_dir[dir_name]
            try:
                data.extend(future.result())
                logging.info(f"{dir_name} DONE")
            except Exception as exc:
                logging.error(f"{dir_name} FAILED: {traceback.format_exc()}")
                continue

    df = pd.DataFrame(data, columns=["type", "multi-rq", "cycles"])
    with open(dat_filename, "wb") as f:
        pickle.dump(df, f, pickle.HIGHEST_PROTOCOL)
    
grouped = df.groupby(['type', 'multi-rq'])
# print(grouped.count())
# print(df.shape)
# print(df.head)

plt.figure(figsize=(27,8))
# manager = plt.get_current_fig_manager()
# manager.resize(*manager.window.maxsize())

ax = sns.boxplot(x="multi-rq", y="cycles", hue="type", data=df,
linewidth=0.3,
showfliers=False,
showmeans=True,
meanprops={"marker":"x",
            "markeredgecolor":"black",
            "markersize":"0.4"}
)
# iterate over boxes
for i, box in enumerate(ax.artists):
    color = box.get_facecolor()
    box.set_edgecolor(color)
    box.set_fill(False)

    # iterate over whiskers and median lines
    # for j in range(5*i,5*(i+1)): without fliers, mean
    for j in range(6*i,6*(i+1)):
         ax.lines[j].set_color(color)

max_multi=max(df["multi-rq"])
[plt.axvline(x+0.5, color = 'black', linestyle='--') for x in list(range(0,max_multi-1))]


handles, labels = ax.get_legend_handles_labels()
for i, handle in enumerate(handles):
    color = handle.get_facecolor()
    handle.set_edgecolor(color)
    handle.set_fill(False)

plt.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 1), ncol=len(set(df["multi-rq"])))

plt.savefig(svg_filename)

plt.show()