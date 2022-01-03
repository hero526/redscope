
from subclasses.pattern import Pattern

def get_pname_tid(all_data_tid):
    pname_tid = {}
    for tid, all_data in all_data_tid.items():
        for event in all_data:
            pname = ''.join(i for i in event["processName"] if not i.isdigit())

            if pname_tid.get(tid) is None:
                pname_tid[tid] = set()
                # pname_tid[tid] = [""]
            
            pname_tid[tid].add(pname)
            # if pname_tid[tid][-1] != pname:
                # pname_tid[tid].append(pname)
    for tid in pname_tid:
        pname_tid[tid] = sorted(list(pname_tid[tid]))

    return pname_tid

def get_tids_pname(all_data_tid):
    pname_tid = get_pname_tid(all_data_tid)
    return convert_pname_tid_to_tids_pname(pname_tid)

def convert_pname_tid_to_tids_pname(pname_tid):
    tids_pname = {}
    for tid, pnames in pname_tid.items():
        # pnames_t = tuple(pnames[1:])
        pnames_t = tuple(pnames)
        if tids_pname.get(pnames_t) is None:
            tids_pname[pnames_t] = set()
        tids_pname[pnames_t].add(tid)
        
    return tids_pname


def build_pdict_pname(pnames, tids_pname, reseq_tid):
    pdict_pname = dict()

    for pname in pnames:
        pdict_pname[pname] = dict()
        tids = tids_pname[pname]

        for tid in tids:
            for idx in range(len(reseq_tid[tid])):
                event = reseq_tid[tid][idx]
                pt = (event,)

                if pdict_pname[pname].get(pt) is None:
                    pdict_pname[pname][pt] = Pattern(pt)
                
                if pdict_pname[pname][pt].start_idx_tid.get(tid) is None:
                    pdict_pname[pname][pt].start_idx_tid[tid] = []

                pdict_pname[pname][pt].start_idx_tid[tid].append(idx)
        
    for pdict in pdict_pname.values():
        for pt_obj in pdict.values():
            pt_obj.update_remain()

    return pdict_pname