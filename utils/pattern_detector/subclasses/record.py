from subutils import syscall_info
from subutils import pname_info

from subclasses.pattern import Pattern
from subclasses.correlation import Correlation

from scipy import stats
import logging
import os
import concurrent.futures
from pprint import pprint
import traceback


class RelatedRecordSet:
    def __init__(self, collector, server_info, experiment_info):
        self.collector = collector

        self.server_info = server_info
        self.server_info_str = '_'.join(str(x) for x in server_info)

        self.experiment_info = experiment_info
        self.experiment_info_str = '_'.join(str(x) for x in experiment_info)
        
        self.server, self.cpu, self.mem, self.disk = server_info[0], server_info[1], server_info[2], server_info[3]
        self.db, self.workload, self.record_count, self.record_size, self.client, self.interval_ms = experiment_info[0], experiment_info[1], experiment_info[2], experiment_info[3], experiment_info[4], experiment_info[5]

        # base data
        self.iterations_opc = dict()
        self.tids_pname_iter_opc = dict()
        self.all_data_tid_iter_opc = dict()

        # event data
        self.reseq_tid_opt_iter_opc = dict()
        self.pdict_pname_opt_iter_opc = dict()
        

    # base data
    def update_op_counts(self):
        self.op_counts = sorted(list(self.tids_pname_iter_opc.keys()))

    def update_iterations_opc(self):
        for op_count in self.op_counts:
            iterations = []
            tids_pname_iter = self.tids_pname_iter_opc[op_count]
            
            for i in tids_pname_iter.keys():
                iterations.append(i)
            self.iterations_opc[op_count] = sorted(iterations)

    def update_common_pnames(self):
        self.common_pnames = set.intersection( *[set(tids_pname.keys()) for tids_pname_iter in self.tids_pname_iter_opc.values() for tids_pname in tids_pname_iter.values()] )

    def update_tids_pname_iter_opc(self, op_count, iteration, tids_pname):
        if self.tids_pname_iter_opc.get(op_count) is None:
            self.tids_pname_iter_opc[op_count] = dict()
        
        self.tids_pname_iter_opc[op_count][iteration] = tids_pname

    def update_all_data_tid_iter_opc(self, op_count, iteration, all_data_tid):
        if self.all_data_tid_iter_opc.get(op_count) is None:
            self.all_data_tid_iter_opc[op_count] = dict()
        
        self.all_data_tid_iter_opc[op_count][iteration] = all_data_tid


    # event data
    def update_reseq_tid_opt_iter_opc(self, op_count, i, opt, reseq_tid):
        if self.reseq_tid_opt_iter_opc.get(op_count) is None:
            self.reseq_tid_opt_iter_opc[op_count] = dict()
        
        if self.reseq_tid_opt_iter_opc[op_count].get(i) is None:
            self.reseq_tid_opt_iter_opc[op_count][i] = dict()

        self.reseq_tid_opt_iter_opc[op_count][i][opt] = reseq_tid
    
    def update_pdict_pname_opt_iter_opc(self, pdict_pname_opt_iter_opc, op_count, i, opt, pdict_pname):
        if pdict_pname_opt_iter_opc.get(op_count) is None:
            pdict_pname_opt_iter_opc[op_count] = dict()
        
        if pdict_pname_opt_iter_opc[op_count].get(i) is None:
            pdict_pname_opt_iter_opc[op_count][i] = dict()

        pdict_pname_opt_iter_opc[op_count][i][opt] = pdict_pname


    def update_pdict_pname_opt(self, opt):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            opc_future = dict()

            for opc in self.op_counts:
                opc_future[executor.submit(self.update_pdict_pname_in_opc, opc, opt)] = opc

            for future in concurrent.futures.as_completed(opc_future):
                opc = opc_future[future]
                try:
                    future.result()
                except Exception as exc:
                    logging.error(f"[UPDATE-PDICT] {self.experiment_info_str}, {opc} FAIL: {traceback.format_exc()}")
                    continue
                logging.debug(f"[UPDATE-PDICT] {self.experiment_info_str}, {opc} SUCCEED")

    def update_pdict_pname_in_opc(self, opc, opt):
        tids_pname_iter = self.tids_pname_iter_opc[opc]
        reseq_tid_opt_iter = self.reseq_tid_opt_iter_opc[opc]
        pdict_pname_iter = dict()
        for iteration in self.iterations_opc[opc]:
            tids_pname = tids_pname_iter[iteration]
            reseq_tid = reseq_tid_opt_iter[iteration][opt]

            pdict_pname_iter[iteration] = pname_info.build_pdict_pname(self.common_pnames, tids_pname, reseq_tid)

        for pname in self.common_pnames:
            common_pts = set.intersection( *[set(pdict_pname[pname].keys()) for pdict_pname in pdict_pname_iter.values()] )

            for iteration, pdict_pname in pdict_pname_iter.items():
                pdict = pdict_pname[pname]

                pdict_copy = pdict.copy()
                for pt in pdict.keys():
                    if pt not in common_pts:
                        del pdict_copy[pt]
                        for tid in tids_pname_iter[iteration][pname]:
                            self.reseq_tid_opt_iter_opc[opc][iteration][opt][tid] = list(filter(lambda x: x != pt[0], self.reseq_tid_opt_iter_opc[opc][iteration][opt][tid]))

                pdict_pname[pname] = pdict_copy

        for iteration in self.iterations_opc[opc]:
            self.update_pdict_pname_opt_iter_opc(self.pdict_pname_opt_iter_opc, opc, iteration, opt, pdict_pname_iter[iteration])


    def find_longest_correlated_pattern(self, opt, threshold):
        logging.debug(f"[LONGEST] opt{opt}, {self.experiment_info_str} START")
        self.correlation_pt_pname = dict()

        plen = 1

        with concurrent.futures.ThreadPoolExecutor() as executor:
            opc_future = dict()

            updated = self.calculate_correlation_pt_pname(self.pdict_pname_opt_iter_opc, opt, threshold)

            while updated:
                updated = False
                plen += 1
                self.expanded_pdict_pname_opt_iter_opc = dict()
                for opc in self.op_counts:
                    opc_future[executor.submit(self.expand_pdict_pname_iter_in_opc, opc, opt, plen, threshold)] = opc

                for future in concurrent.futures.as_completed(opc_future):
                    opc = opc_future[future]
                    try:
                        future.result()
                    except Exception as exc:
                        logging.error(f"[LONGEST] plen{plen} patterns in {self.db}, opc{opc} FAIL: {traceback.format_exc()}")
                        continue
                    logging.debug(f"[LONGEST] plen{plen} patterns in {self.db}, opc{opc} SUCCEED")

                updated = self.calculate_correlation_pt_pname(self.expanded_pdict_pname_opt_iter_opc, opt, threshold)

        self.apply_correlation_to_pt_objs(opt)
    
    
    def expand_pdict_pname_iter_in_opc(self, op_count, opt, plen, threshold):
        reseq_tid_opt_iter = self.reseq_tid_opt_iter_opc[op_count]
        # tids_pname_iter = self.tids_pname_iter_opc[op_count]
        pdict_pname_opt_iter = self.pdict_pname_opt_iter_opc[op_count]
        iterations = self.iterations_opc[op_count]

        for i in iterations:
            reseq_tid = reseq_tid_opt_iter[i][opt]
            # tids_pname = tids_pnames[i]
            pdict_pname = pdict_pname_opt_iter[i][opt]

            self.expand_pdict_pname_in_iteration(op_count, i, opt, reseq_tid, pdict_pname, plen, threshold)
    
    def expand_pdict_pname_in_iteration(self, op_count, iteration, opt, reseq_tid, origin_pdict_pname, plen, threshold):
        new_pdict_pname = dict()
        for pname in self.common_pnames:
            new_pdict_pname[pname] = dict()

            origin_pdict = origin_pdict_pname[pname]
            for cur_pt, base_pt_obj in origin_pdict.items():
                cur_correlation = self.correlation_pt_pname[pname][cur_pt]
                     
                if cur_correlation.max_check or cur_correlation.grade < Correlation.GRADE[threshold]:
                    continue

                if opt == syscall_info.CLIENT_RELATED_RSRW and syscall_info.rr_syscall_table.get(cur_pt[0][1]) is None:
                    continue

                tids = base_pt_obj.start_idx_tid.keys()
                for tid in tids:
                    reseq = reseq_tid[tid]
                    len_reseq = len(reseq)
                    
                    if len_reseq < plen:
                        continue
                    
                    for idx in base_pt_obj.start_idx_tid[tid]:
                        if idx+plen <= len_reseq:
                            pt = tuple(reseq[idx:idx+plen])
                        else:
                            pt = tuple(reseq[idx:])

                        if pt != cur_pt:
                            last_index = idx + len(pt) -1
                            if last_index in base_pt_obj.start_idx_tid[tid]:
                                self.correlation_pt_pname[pname][cur_pt].max_check = True
                                continue

                            last_correlation = self.correlation_pt_pname[pname][(pt[-1],)]
                            correlation_similarity = cur_correlation.spearman / last_correlation.spearman if last_correlation.spearman != 0 else 0 
                            if correlation_similarity != 1:
                                self.correlation_pt_pname[pname][cur_pt].max_check = True
                                continue
                        

                        if new_pdict_pname[pname].get(pt) is None:
                            new_pdict_pname[pname][pt] = Pattern(pt)

                        if new_pdict_pname[pname][pt].start_idx_tid.get(tid) is None:
                            new_pdict_pname[pname][pt].start_idx_tid[tid] = []

                        new_pdict_pname[pname][pt].start_idx_tid[tid].append(idx)

        for pdict in new_pdict_pname.values():
            for pt_obj in pdict.values():
                pt_obj.update_remain()

        self.update_pdict_pname_opt_iter_opc(self.expanded_pdict_pname_opt_iter_opc, op_count, iteration, opt, new_pdict_pname)
        

    def calculate_correlation_pt_pname(self, pdict_pname_opt_iter_opc, opt, threshold):
        # opc pattern means for iterations 
        mean_opc_remain_pt_pname = self.calculate_mean_opc_remain_pt_pname_for_iterations(pdict_pname_opt_iter_opc, self.common_pnames, opt)
        # pattern correlation
        correlation_pt_pname = dict()

        for pname in self.common_pnames:
            correlation_pt_pname[pname] = dict()
        
            for pt, mean_opc_remain in mean_opc_remain_pt_pname[pname].items():
                correlation_pt_pname[pname][pt] = Correlation(self.op_counts, mean_opc_remain)

        updated = self.apply_correlation_pt_pname(pdict_pname_opt_iter_opc, correlation_pt_pname, opt, threshold)
        return updated

    
    def calculate_mean_opc_remain_pt_pname_for_iterations(self, pdict_pname_opt_iter_opc, target_pnames, opt, target_pt_pname=dict()):
        mean_opc_remain_pt_pname = dict()
        len_op_counts = len(self.op_counts)
        target_exist = True if len(target_pt_pname) > 0 else False

        for pname in target_pnames:
            mean_opc_remain_pt_pname[pname] = dict()

            for c in range(len_op_counts):
                op_count = self.op_counts[c]
                pdict_pname_opt_iter = pdict_pname_opt_iter_opc[op_count]
                iterations = self.iterations_opc[op_count]
                
                opc_remain_pt = dict()
                for i in iterations:
                    pdict_pname = pdict_pname_opt_iter[i][opt]
                    pdict = pdict_pname[pname]

                    for pt, pt_obj in pdict.items():
                        if target_exist and pt not in target_pt_pname[pname]:
                            continue

                        if opc_remain_pt.get(pt) is None:
                            opc_remain_pt[pt] = [0 for opc in self.op_counts]
                        opc_remain_pt[pt][c] += pt_obj.remain

                iteration_count = len(iterations)
                for pt in opc_remain_pt.keys():
                    if mean_opc_remain_pt_pname[pname].get(pt) is None:
                        mean_opc_remain_pt_pname[pname][pt] = [0 for opc in self.op_counts]
                    mean_opc_remain_pt_pname[pname][pt][c] = opc_remain_pt[pt][c] / iteration_count

        return mean_opc_remain_pt_pname


    def apply_correlation_pt_pname(self, pdict_pname_opt_iter_opc, correlation_pt_pname, opt, threshold):
        updated = False
        
        local_update_correlation_pt_pname = dict()

        if len(self.correlation_pt_pname) <= 0:
            self.correlation_pt_pname = correlation_pt_pname
            return True
        
        for pname in correlation_pt_pname.keys():
            local_update_correlation_pt_pname[pname] = []
        
            for pt in correlation_pt_pname[pname].keys():
                del_pt = pt[:-1]
                
                if del_pt == ():
                    self.correlation_pt_pname[pname][pt].max_check = True
                    continue
                
                if all(int(x) == 1 or int(x) == 0 for x in correlation_pt_pname[pname][pt].comp_set):
                    self.correlation_pt_pname[pname][del_pt].max_check = True
                    continue

                prev_correlation = self.correlation_pt_pname[pname][del_pt].spearman
                new_correlation = correlation_pt_pname[pname][pt].spearman
                if prev_correlation > new_correlation:
                    self.correlation_pt_pname[pname][del_pt].max_check = True
                    continue

                if correlation_pt_pname[pname][pt].grade < Correlation.GRADE[threshold]:
                    self.correlation_pt_pname[pname][del_pt].max_check = True
                    continue

                # Update new pattern
                updated = True
                self.correlation_pt_pname[pname][pt] = correlation_pt_pname[pname][pt]

                for op_count, pdict_pname_opt_iter in pdict_pname_opt_iter_opc.items():
                    for i, pdict_pname_opt in pdict_pname_opt_iter.items():
                        pdict = pdict_pname_opt[opt][pname]

                        # Although pdict fetched from same pname with correlation_pt_pname, pdict.get(pt) can be None.
                        # It is because correlation_pt_pname contains all patterns for every op_count, but pdict contains patterns for only one op_count
                        if pdict.get(pt) is None:
                            continue

                        # Delete start index for del pattern
                        for tid, start_idx in pdict[pt].start_idx_tid.items():
                            for idx in start_idx:
                                self.pdict_pname_opt_iter_opc[op_count][i][opt][pname][del_pt].start_idx_tid[tid].remove(idx)

                        self.pdict_pname_opt_iter_opc[op_count][i][opt][pname][del_pt].update_remain()
                        local_update_correlation_pt_pname[pname].append(del_pt)

                        self.pdict_pname_opt_iter_opc[op_count][i][opt][pname][pt] = pdict[pt]
        
        # Local correlation update need becuase start indices were deleted
        target_pnames = list(local_update_correlation_pt_pname.keys())
        mean_opc_remain_pt_pname = self.calculate_mean_opc_remain_pt_pname_for_iterations(self.pdict_pname_opt_iter_opc, target_pnames, opt, target_pt_pname=local_update_correlation_pt_pname)
        
        for pname, mean_opc_remain_pt in mean_opc_remain_pt_pname.items():
            for pt, mean_opc_remain in mean_opc_remain_pt.items():
                prev_max_check = self.correlation_pt_pname[pname][pt].max_check
                self.correlation_pt_pname[pname][pt] = Correlation(self.op_counts, mean_opc_remain)
                self.correlation_pt_pname[pname][pt].max_check = prev_max_check
        
        return updated

    
    def apply_correlation_to_pt_objs(self, opt):
        self.select_pdict_pname_opt_iter_opc(opt)

        for opc, pdict_pname_opt_iter in self.pdict_pname_opt_iter_opc.items():
            for iteration, pdict_pname_opt in pdict_pname_opt_iter.items():
                pdict_pname = pdict_pname_opt[opt]
                for pname, pdict in pdict_pname.items():
                    # sum of execution time for pname
                    time = 0
                    tids = self.tids_pname_iter_opc[opc][iteration][pname]
                    for tid in tids:
                        time += syscall_info.get_thread_excution_time(self.all_data_tid_iter_opc[opc][iteration][tid])
                        
                    for pt, pt_obj in pdict.items():
                        pt_obj.update_correlation(self.correlation_pt_pname[pname][pt])
                        pt_obj.update_frequency(time)


    
    def select_pdict_pname_opt_iter_opc(self, opt):
        local_update_correlation_pt_pname = dict()

        for opc, pdict_pname_opt_iter in self.pdict_pname_opt_iter_opc.items():
            for iteration, pdict_pname_opt in pdict_pname_opt_iter.items():
                pdict_pname = pdict_pname_opt[opt]
                for pname, pdict in pdict_pname.items():
                    local_update_correlation_pt_pname[pname] = []
                    pt_objs = []
                    for pt_obj in pdict.values():
                        if pt_obj.remain == 0:
                            continue
                        pt_objs.append(pt_obj)
                    
                    # Set priorities to select pattern
                    pt_objs.sort(
                        key = lambda e: (
                            -self.correlation_pt_pname[pname][e.pattern].spearman,
                            -self.correlation_pt_pname[pname][e.pattern].pearson,
                            -e.length,
                            -sum(self.correlation_pt_pname[pname][e.pattern].comp_set)
                        )
                    )
                    with open("record.log", "a") as f:
                        print(f"========== {self.db}, {self.workload}, opc{opc}, i{iteration}, {pname}, opt{opt} ==========", file=f)
                        for pt_obj in pt_objs:
                            pt = pt_obj.pattern
                            print(
                                pt,
                                pt_obj.remain,
                                '\t(sp)%.3f'%self.correlation_pt_pname[pname][pt].spearman,
                                '\t(pr)%.3f'%self.correlation_pt_pname[pname][pt].pearson,
                                [float('%.2f'%cnt) for cnt in self.correlation_pt_pname[pname][pt].comp_set],
                                file=f
                            )

                    for cur in range(len(pt_objs)-1):
                        base_pt_obj = pt_objs[cur]
                        base_pt_set = set(base_pt_obj.pattern)

                        tids = base_pt_obj.start_idx_tid.keys()
                        for tid in tids:
                            sub_indices = set()
                            for base_idx in base_pt_obj.start_idx_tid[tid]:
                                sub_indices.update( set([base_idx+j for j in range(base_pt_obj.length)]) )
                            
                            for k in range(cur + 1, len(pt_objs)-1):
                                comp_pt_obj = pt_objs[k]
                                comp_pt_set = set(pt_objs[k].pattern)
                                if len(base_pt_set.intersection(comp_pt_set)) <= 0:
                                    continue
                                
                                comp_start_idx = comp_pt_obj.start_idx_tid.get(tid)
                                if comp_pt_obj.start_idx_tid.get(tid) is None:
                                    continue

                                remove_comp_idx = []
                                for comp_idx in comp_start_idx:
                                    comp_indices = set([comp_idx+j for j in range(comp_pt_obj.length)])
                                    if len(sub_indices.intersection(comp_indices)) <= 0:
                                        continue
                                    remove_comp_idx.append(comp_idx)
                                
                                if len(remove_comp_idx) > 0:
                                    for idx in remove_comp_idx:
                                        comp_pt_obj.start_idx_tid[tid].remove(idx)
                                    comp_pt_obj.update_remain()

                                    local_update_correlation_pt_pname[pname].append(comp_pt_obj.pattern)
                    

        # Local correlation update need becuase start indices were deleted
        target_pnames = list(local_update_correlation_pt_pname.keys())
        mean_opc_remain_pt_pname = self.calculate_mean_opc_remain_pt_pname_for_iterations(self.pdict_pname_opt_iter_opc, target_pnames, opt, target_pt_pname=local_update_correlation_pt_pname)
        
        for pname, mean_opc_remain_pt in mean_opc_remain_pt_pname.items():
            for pt, mean_opc_remain in mean_opc_remain_pt.items():
                self.correlation_pt_pname[pname][pt] = Correlation(self.op_counts, mean_opc_remain)


        # for opc, pdict_pname_opt_iter in self.pdict_pname_opt_iter_opc.items():
        #     for iteration, pdict_pname_opt in pdict_pname_opt_iter.items():
        #         pdict_pname = pdict_pname_opt[opt]
        #         for pname, pdict in pdict_pname.items():
        #             local_update_correlation_pt_pname[pname] = []
        #             pt_objs = []
        #             for pt_obj in pdict.values():
        #                 if pt_obj.remain == 0:
        #                     continue
        #                 pt_objs.append(pt_obj)
                    
        #             # Set priorities to select pattern
        #             pt_objs.sort(
        #                 key = lambda e: (
        #                     -self.correlation_pt_pname[pname][e.pattern].spearman,
        #                     -e.length,
        #                     -sum(self.correlation_pt_pname[pname][e.pattern].comp_set)
        #                 )
        #             )
        #             print(f"========== opc{opc}, i{iteration}, {pname}, opt{opt} ==========")
        #             for pt_obj in pt_objs:
        #                 pt = pt_obj.pattern
        #                 print(pt, self.correlation_pt_pname[pname][pt].spearman, self.correlation_pt_pname[pname][pt].comp_set)
                
