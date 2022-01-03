import sys, os
from config import CONFIG
from const import *
from static_pd import get_resource_usage, trim_cpu_off_evts


def get_experiments_str(experiments, client=None):
    experiments_str = ""
    is_first = True
    for value in experiments:
        if is_first:
            is_first = False
        else:
            experiments_str += ","
        experiments_str += str(value)
    if client is not None:
        experiments_str += "," + str(client)
    return experiments_str

def do_metric_scaling(value, metric):
    if metric == "Cycle" or metric == "RefCycle":
        return int(value/2)
    elif metric == "RDCAS" or metric == "WRCAS":
        return value * 64
    else:
        return value

# for redis, memcached
def print_dist_info(ptrn_list_per_client, experiments, output_prefix, output_dir):
    output_file = output_dir + "/" + output_prefix + "/" + output_prefix + "Dist.csv"
    max_client = int(experiments[CLIENT_IDX_NUM])

    if not os.path.isdir(output_dir + "/" + output_prefix):
        os.makedirs(output_dir + "/" + output_prefix)

    with open(output_file, "a") as f:
        if os.stat(output_file).st_size == 0:
            print(COMMON_HEADER, file=f, end="")
            for c in range(1, max_client+1):
                print(",MultiReq-" + str(c), file=f, end="")

        expr_str = get_experiments_str(experiments)
        
        buf = expr_str
        for c in range(1, max_client+1):
            if ptrn_list_per_client.get(c) is None:
                buf += ",0"
            else:
                buf += f",{len(ptrn_list_per_client[c])*c}"

        print(buf, file=f)

def print_usage_sum(experiments, output_prefix, output_dir, usages, metric_list, evt_data_tid, REAL_PATTERN_PRINT, req_count, mean=False):
    sum_type_list = ["event"]
    mean_count = 1

    if REAL_PATTERN_PRINT:
        event_ids = set()
        for usage in usages:
            for event in usage:
                if event["isPattern"]:
                    event_ids.add( ( int(event["eventId"]), int(event["returnValue"]) ) )
        sum_type_list.extend(event_ids)

    if not mean:
        output_file = output_dir + "/" + output_prefix + "/" + output_prefix + "UsageSum.csv"
    else:
        output_file = output_dir + "/" + output_prefix + "/" + output_prefix + "UsageAvg.csv"
    if not os.path.isdir(output_dir + "/" + output_prefix):
        os.makedirs(output_dir + "/" + output_prefix)

    with open(output_file, "a") as f:
        if os.stat(output_file).st_size == 0:
            HEADER_STR=""
            HEADER_STR += COMMON_HEADER
            HEADER_STR += ",SUM_TYPE,RETURN,count"
            metric_str = ""
            for metric in metric_list:
                if "RDCAS" not in metric_str and "RDCAS" in metric:
                    metric_str += f",RDCAS"
                elif "WRCAS" not in metric_str and "WRCAS" in metric:
                    metric_str += f",WRCAS"
                elif "CAS" not in metric:
                    metric_str += f",{metric}"
            HEADER_STR += metric_str
            print(HEADER_STR, file = f)

        experiments_str = get_experiments_str(experiments)

        for s_type in sum_type_list:
            if s_type == "event":
                s_type = s_type+",NULL"

                evt_sum_usages = list()
                counter = 0
                for evt_data in evt_data_tid.values():
                    for evt in evt_data:
                        evt["isPattern"] = False
                    evt_data = trim_cpu_off_evts(evt_data)
                    if len(evt_data) == 0:
                        continue
                    usage = get_resource_usage(evt_data, metric_list)
                    counter += len(usage)
                    evt_sum_usages.append(usage)
                
                data = get_ptrn_sum(evt_sum_usages, metric_list)
                count = counter
                if mean:
                    mean_count = counter

            elif s_type == "pattern":
                s_type = s_type+",NULL"

                data = get_ptrn_sum(usages, metric_list)
                count = req_count
                if mean:
                    mean_count = req_count

            elif syscall_table.get(s_type[0]) is not None or s_type[0] == EVT_ID_INTERVAL:
                eid = s_type[0]
                retval = s_type[1]
                
                if eid == EVT_ID_INTERVAL:
                    s_type = f"INTERVAL,{retval}"
                else:
                    s_type = f"{syscall_table[eid][0]},{retval}"

                data, count = get_syscall_sum(usages, eid, retval, metric_list)
                if mean:
                    mean_count = count

            else:
                raise Exception(f"Invalid sum_type: {s_type}")

            print(experiments_str, file=f, end="")
            print(f",{s_type}", file=f, end="")

            print(f",{count}", file = f, end="")

            CAS_P=[False, False]
            for metric in metric_list:
                if not CAS_P[0] and "RDCAS" in metric:
                    CAS_P[0] = True
                    print(f",{data['RDCAS']/mean_count}", file = f, end="")
                elif not CAS_P[1] and "WRCAS" in metric:
                    CAS_P[1] = True
                    print(f",{data['WRCAS']/mean_count}", file = f, end="")
                elif "CAS" not in metric:
                    print(f",{data[metric]/mean_count}", file = f, end="")
                    
            print(file = f)

def print_ptrn_avg_usage(experiments, output_prefix, output_dir, metric_list, avg_non_irregular_usage, num_req, num_non_irregular_req, ptrn_header):
    output_file = output_dir + "/" + output_prefix + "/" + output_prefix + "PtrnUsageAvg.csv"
    if not os.path.isdir(output_dir + "/" + output_prefix):
        os.makedirs(output_dir + "/" + output_prefix)

    with open(output_file, "a") as f:
        if os.stat(output_file).st_size == 0:
            print(COMMON_HEADER, file = f, end="")
            print(",Req,NonIrregularReq,Metric", file =f, end="")
            for ptrn_name in ptrn_header:
                print(f",{ptrn_name}", file = f, end="")
            print(file = f)

        experiments_str = get_experiments_str(experiments)
        
        for metric in metric_list:
            print(experiments_str, file = f, end="")
            print(f",{num_req},{num_non_irregular_req},{metric}", file = f, end="")
            for idx in range(len(avg_non_irregular_usage)):
                print(f",{avg_non_irregular_usage[idx][metric]}", file=f, end="")
            print(file=f)


def get_ptrn_sum(usages, metric_list): 
    sum_per_metric = dict()

    for metric in metric_list:
        if "RDCAS" in metric:
            sum_per_metric["RDCAS"] = 0
        elif "WRCAS" in metric:
            sum_per_metric["WRCAS"] = 0
        sum_per_metric[metric] = 0

    for usage in usages:
        for evt in usage:
            for metric in metric_list:
                if "Uops" not in metric:
                    if CONFIG["UK_TYPE"] == "K" and evt["eventId"] == EVT_ID_INTERVAL:
                        continue
                    elif CONFIG["UK_TYPE"] == "U" and evt["eventId"] != EVT_ID_INTERVAL:
                        continue
                sum_per_metric[metric] += evt[metric]

    for metric in sum_per_metric:
        if "RDCAS" in metric:
            sum_per_metric["RDCAS"] += sum_per_metric[metric]
        elif "WRCAS" in metric:
            sum_per_metric["WRCAS"] += sum_per_metric[metric]

    for cas in ["RDCAS_0_0","WRCAS_0_0","RDCAS_0_1","WRCAS_0_1","RDCAS_1_0","WRCAS_1_0","RDCAS_1_1","WRCAS_1_1"]:
        sum_per_metric.pop(cas, None)

    return sum_per_metric

def get_syscall_sum(usages, eid, retval, metric_list):
    sum_per_metric = dict()
    count = 0
    for metric in metric_list:
        if "RDCAS" in metric:
            sum_per_metric["RDCAS"] = 0
        elif "WRCAS" in metric:
            sum_per_metric["WRCAS"] = 0
        sum_per_metric[metric] = 0

    for usage in usages:
        for evt in usage:
            if evt["eventId"] == eid and evt["returnValue"] == retval:
                count += 1
                for metric in metric_list:
                    sum_per_metric[metric] += evt[metric]
                    
    for metric in sum_per_metric:
        if "RDCAS" in metric:
            sum_per_metric["RDCAS"] += sum_per_metric[metric]
        elif "WRCAS" in metric:
            sum_per_metric["WRCAS"] += sum_per_metric[metric]

    for cas in ["RDCAS_0_0","WRCAS_0_0","RDCAS_0_1","WRCAS_0_1","RDCAS_1_0","WRCAS_1_0","RDCAS_1_1","WRCAS_1_1"]:
        sum_per_metric.pop(cas, None)

    return sum_per_metric, count

syscall_table = {
    0: ('read', 'fs', ['pathname']),
    1: ('write', 'fs', ['pathname']),
    2: ('open', 'fs', []),
    3: ('close', 'fs', ['pathname']),
    4: ('stat', 'fs', ['pathname']),
    5: ('fstat', 'fs', ['pathname']),
    6: ('lstat', 'fs', ['pathname']),
    7: ('poll', 'fs', []),
    8: ('lseek', 'fs', ['whence', 'pathname']),
    9: ('mmap', 'arch', ['prot', 'flags']),
    10: ('mprotect', 'mm', ['prot']),
    11: ('munmap', 'mm', []),
    12: ('brk', 'mm', []),
    13: ('rt_sigaction', 'kernel', ['signum']),
    14: ('rt_sigprocmask', 'kernel', ['how']),
    15: ('rt_sigreturn', 'arch', []),
    16: ('ioctl', 'fs', []),
    17: ('pread64', 'fs', ['pathname']),
    18: ('pwrite64', 'fs', ['pathname']),
    19: ('readv', 'fs', ['iovcnt', 'pathname']),
    20: ('writev', 'fs', ['pathname']),
    21: ('access', 'fs', ['pathname', 'mode']),
    22: ('pipe', 'fs', []),
    23: ('select', 'fs', []),
    24: ('sched_yield', 'kernel', []),
    25: ('mremap', 'mm', []),
    26: ('msync', 'mm', ['flags']),
    27: ('mincore', 'mm', []),
    28: ('madvise', 'mm', ['advice']),
    29: ('shmget', 'ipc', []),
    30: ('shmat', 'ipc', []),
    31: ('shmctl', 'ipc', []),
    32: ('dup', 'fs', []),
    33: ('dup2', 'fs', []),
    34: ('pause', 'kernel', []),
    35: ('nanosleep', 'kernel', []),
    36: ('getitimer', 'kernel', []),
    37: ('alarm', 'kernel', []),
    38: ('setitimer', 'kernel', []),
    39: ('getpid', 'kernel', []),
    40: ('sendfile', 'fs', []),
    41: ('socket', 'net', ['domain', 'type', 'protocol']),
    42: ('connect', 'net', []),
    43: ('accept', 'net', []),
    44: ('sendto', 'net', ['flags']),
    45: ('recvfrom', 'net', ['flags']),
    46: ('sendmsg', 'net', ['flags']),
    47: ('recvmsg', 'net', ['flags']),
    48: ('shutdown', 'net', ['how']),
    49: ('bind', 'net', []),
    50: ('listen', 'net', ['backlog']),
    51: ('getsockname', 'net', []),
    52: ('getpeername', 'net', []),
    53: ('socketpair', 'net', ['domain', 'type', 'protocol']),
    54: ('setsockopt', 'net', ['level', 'optname']),
    55: ('getsockopt', 'net', ['level', 'optname']),
    56: ('clone', 'kernel', ['flags']),
    57: ('fork', 'kernel', []),
    58: ('vfork', 'kernel', []),
    59: ('execve', 'fs', []),
    60: ('exit', 'kernel', []),
    61: ('wait4', 'kernel', ['options']),
    62: ('kill', 'kernel', ['sig']),
    63: ('uname', 'kernel', []),
    64: ('semget', 'ipc', []),
    65: ('semop', 'ipc', []),
    66: ('semctl', 'ipc', []),
    67: ('shmdt', 'ipc', []),
    68: ('msgget', 'ipc', []),
    69: ('msgsnd', 'ipc', []),
    70: ('msgrcv', 'ipc', []),
    71: ('msgctl', 'ipc', []),
    72: ('fcntl', 'fs', ['cmd', 'pathname']),
    73: ('flock', 'fs', ['operation']),
    74: ('fsync', 'fs', ['pathname']),
    75: ('fdatasync', 'fs', ['pathname']),
    76: ('truncate', 'fs', []),
    77: ('ftruncate', 'fs', []),
    78: ('getdents', 'fs', []),
    79: ('getcwd', 'fs', ['size']),
    80: ('chdir', 'fs', ['path']),
    81: ('fchdir', 'fs', []),
    82: ('rename', 'fs', []),
    83: ('mkdir', 'fs', ['pathname', 'mode']),
    84: ('rmdir', 'fs', ['pathname']),
    85: ('creat', 'fs', []),
    86: ('link', 'fs', []),
    87: ('unlink', 'fs', ['pathname']),
    88: ('symlink', 'fs', []),
    89: ('readlink', 'fs', ['pathname', 'bufsiz']),
    90: ('chmod', 'fs', ['pathname', 'mode']),
    91: ('fchmod', 'fs', []),
    92: ('chown', 'fs', []),
    93: ('fchown', 'fs', []),
    94: ('lchown', 'fs', []),
    95: ('umask', 'kernel', []),
    96: ('gettimeofday', 'kernel', []),
    97: ('getrlimit', 'kernel', []),
    98: ('getrusage', 'kernel', ['who']),
    99: ('sysinfo', 'kernel', []),
    100: ('times', 'kernel', []),
    101: ('ptrace', 'kernel', []),
    102: ('getuid', 'kernel', []),
    103: ('syslog', 'kernel', []),
    104: ('getgid', 'kernel', []),
    105: ('setuid', 'kernel', []),
    106: ('setgid', 'kernel', []),
    107: ('geteuid', 'kernel', []),
    108: ('getegid', 'kernel', []),
    109: ('setpgid', 'kernel', []),
    110: ('getppid', 'kernel', []),
    111: ('getpgrp', 'kernel', []),
    112: ('setsid', 'kernel', []),
    113: ('setreuid', 'kernel', []),
    114: ('setregid', 'kernel', []),
    115: ('getgroups', 'kernel', []),
    116: ('setgroups', 'kernel', []),
    117: ('setresuid', 'kernel', []),
    118: ('getresuid', 'kernel', []),
    119: ('setresgid', 'kernel', []),
    120: ('getresgid', 'kernel', []),
    121: ('getpgid', 'kernel', []),
    122: ('setfsuid', 'kernel', []),
    123: ('setfsgid', 'kernel', []),
    124: ('getsid', 'kernel', []),
    125: ('capget', 'kernel', []),
    126: ('capset', 'kernel', []),
    127: ('rt_sigpending', 'kernel', []),
    128: ('rt_sigtimedwait', 'kernel', []),
    129: ('rt_sigqueueinfo', 'kernel', []),
    130: ('rt_sigsuspend', 'kernel', []),
    131: ('sigaltstack', 'kernel', []),
    132: ('utime', 'fs', []),
    133: ('mknod', 'fs', []),
    134: ('uselib', 'fs', []),
    135: ('personality', 'kernel', []),
    136: ('ustat', 'fs', []),
    137: ('statfs', 'fs', ['path']),
    138: ('fstatfs', 'fs', []),
    139: ('sysfs', 'fs', []),
    140: ('getpriority', 'kernel', []),
    141: ('setpriority', 'kernel', []),
    142: ('sched_setparam', 'kernel', []),
    143: ('sched_getparam', 'kernel', []),
    144: ('sched_setscheduler', 'kernel', []),
    145: ('sched_getscheduler', 'kernel', []),
    146: ('sched_get_priority_max', 'kernel', []),
    147: ('sched_get_priority_min', 'kernel', []),
    148: ('sched_rr_get_interval', 'kernel', []),
    149: ('mlock', 'mm', []),
    150: ('munlock', 'mm', []),
    151: ('mlockall', 'mm', []),
    152: ('munlockall', 'mm', []),
    153: ('vhangup', 'fs', []),
    154: ('modify_ldt', 'arch', []),
    155: ('pivot_root', 'fs', []),
    156: ('_sysctl', 'NOT_IMPLEMENTED', []),
    157: ('prctl', 'kernel', ['option']),
    158: ('arch_prctl', 'arch', ['option']),
    159: ('adjtimex', 'kernel', []),
    160: ('setrlimit', 'kernel', []),
    161: ('chroot', 'fs', []),
    162: ('sync', 'fs', []),
    163: ('acct', 'kernel', []),
    164: ('settimeofday', 'kernel', []),
    165: ('mount', 'fs', []),
    166: ('umount2', 'NOT_IMPLEMENTED', []),
    167: ('swapon', 'mm', []),
    168: ('swapoff', 'mm', []),
    169: ('reboot', 'kernel', []),
    170: ('sethostname', 'kernel', []),
    171: ('setdomainname', 'kernel', []),
    172: ('iopl', 'arch', []),
    173: ('ioperm', 'arch', []),
    174: ('create_module', 'NOT_IMPLEMENTED', []),
    175: ('init_module', 'kernel', []),
    176: ('delete_module', 'kernel', []),
    177: ('get_kernel_syms', 'NOT_IMPLEMENTED', []),
    178: ('query_module', 'NOT_IMPLEMENTED', []),
    179: ('quotactl', 'fs', []),
    180: ('nfsservctl', 'NOT_IMPLEMENTED', []),
    181: ('getpmsg', 'NOT_IMPLEMENTED', []),
    182: ('putpmsg', 'NOT_IMPLEMENTED', []),
    183: ('afs_syscall', 'NOT_IMPLEMENTED', []),
    184: ('tuxcall', 'NOT_IMPLEMENTED', []),
    185: ('security', 'NOT_IMPLEMENTED', []),
    186: ('gettid', 'kernel', []),
    187: ('readahead', 'mm', ['pathname']),
    188: ('setxattr', 'fs', []),
    189: ('lsetxattr', 'fs', []),
    190: ('fsetxattr', 'fs', []),
    191: ('getxattr', 'fs', []),
    192: ('lgetxattr', 'fs', []),
    193: ('fgetxattr', 'fs', []),
    194: ('listxattr', 'fs', []),
    195: ('llistxattr', 'fs', []),
    196: ('flistxattr', 'fs', []),
    197: ('removexattr', 'fs', []),
    198: ('lremovexattr', 'fs', []),
    199: ('fremovexattr', 'fs', []),
    200: ('tkill', 'kernel', []),
    201: ('time', 'kernel', []),
    202: ('futex', 'kernel', []),
    203: ('sched_setaffinity', 'kernel', []),
    204: ('sched_getaffinity', 'kernel', ['cpusetsize']),
    205: ('set_thread_area', 'arch', []),
    206: ('io_setup', 'fs', []),
    207: ('io_destroy', 'fs', []),
    208: ('io_getevents', 'fs', ['min_nr', 'nr']),
    209: ('io_submit', 'fs', ['nr']),
    210: ('io_cancel', 'fs', []),
    211: ('get_thread_area', 'arch', []),
    212: ('lookup_dcookie', 'NOT_IMPLEMENTED', []),
    213: ('epoll_create', 'fs', []),
    214: ('epoll_ctl_old', 'NOT_IMPLEMENTED', []),
    215: ('epoll_wait_old', 'NOT_IMPLEMENTED', []),
    216: ('remap_file_pages', 'mm', []),
    217: ('getdents64', 'fs', []),
    218: ('set_tid_address', 'kernel', []),
    219: ('restart_syscall', 'kernel', []),
    220: ('semtimedop', 'ipc', []),
    221: ('fadvise64', 'mm', ['advice', 'pathname']),
    222: ('timer_create', 'kernel', []),
    223: ('timer_settime', 'kernel', []),
    224: ('timer_gettime', 'kernel', []),
    225: ('timer_getoverrun', 'kernel', []),
    226: ('timer_delete', 'kernel', []),
    227: ('clock_settime', 'kernel', []),
    228: ('clock_gettime', 'kernel', []),
    229: ('clock_getres', 'kernel', []),
    230: ('clock_nanosleep', 'kernel', ['flags']),
    231: ('exit_group', 'kernel', []),
    232: ('epoll_wait', 'fs', ['maxevents']),
    233: ('epoll_ctl', 'fs', ['op', 'pathname']),
    234: ('tgkill', 'kernel', ['sig']),
    235: ('utimes', 'fs', []),
    236: ('vserver', 'NOT_IMPLEMENTED', []),
    237: ('mbind', 'mm', []),
    238: ('set_mempolicy', 'mm', []),
    239: ('get_mempolicy', 'mm', []),
    240: ('mq_open', 'ipc', []),
    241: ('mq_unlink', 'ipc', []),
    242: ('mq_timedsend', 'ipc', []),
    243: ('mq_timedreceive', 'ipc', []),
    244: ('mq_notify', 'ipc', []),
    245: ('mq_getsetattr', 'ipc', []),
    246: ('kexec_load', 'kernel', []),
    247: ('waitid', 'kernel', []),
    248: ('add_key', 'security', []),
    249: ('request_key', 'security', []),
    250: ('keyctl', 'security', ['operation']),
    251: ('ioprio_set', 'block', []),
    252: ('ioprio_get', 'block', []),
    253: ('inotify_init', 'fs', []),
    254: ('inotify_add_watch', 'fs', []),
    255: ('inotify_rm_watch', 'fs', []),
    256: ('migrate_pages', 'mm', []),
    257: ('openat', 'fs', ['pathname', 'flags']),
    258: ('mkdirat', 'fs', []),
    259: ('mknodat', 'fs', []),
    260: ('fchownat', 'fs', []),
    261: ('futimesat', 'fs', []),
    262: ('newfstatat', 'fs', ['pathname', 'flags']),
    263: ('unlinkat', 'fs', ['pathname', 'flags']),
    264: ('renameat', 'fs', []),
    265: ('linkat', 'fs', []),
    266: ('symlinkat', 'fs', []),
    267: ('readlinkat', 'fs', []),
    268: ('fchmodat', 'fs', []),
    269: ('faccessat', 'fs', ['pathname', 'flags']),
    270: ('pselect6', 'fs', []),
    271: ('ppoll', 'fs', ['sigmask', 'sigsetsize']),
    272: ('unshare', 'kernel', []),
    273: ('set_robust_list', 'kernel', []),
    274: ('get_robust_list', 'kernel', []),
    275: ('splice', 'fs', []),
    276: ('tee', 'fs', []),
    277: ('sync_file_range', 'fs', []),
    278: ('vmsplice', 'fs', []),
    279: ('move_pages', 'mm', []),
    280: ('utimensat', 'fs', []),
    281: ('epoll_pwait', 'fs', ['maxevents', 'timeout']),
    282: ('signalfd', 'fs', []),
    283: ('timerfd_create', 'fs', ['flags']),
    284: ('eventfd', 'fs', []),
    285: ('fallocate', 'fs', ['mode', 'pathname']),
    286: ('timerfd_settime', 'fs', ['flags']),
    287: ('timerfd_gettime', 'fs', []),
    288: ('accept4', 'net', ['flags']),
    289: ('signalfd4', 'fs', []),
    290: ('eventfd2', 'fs', []),
    291: ('epoll_create1', 'fs', []),
    292: ('dup3', 'fs', []),
    293: ('pipe2', 'fs', []),
    294: ('inotify_init1', 'fs', []),
    295: ('preadv', 'fs', []),
    296: ('pwritev', 'fs', []),
    297: ('rt_tgsigqueueinfo', 'kernel', []),
    298: ('perf_event_open', 'kernel', []),
    299: ('recvmmsg', 'net', []),
    300: ('fanotify_init', 'fs', []),
    301: ('fanotify_mark', 'fs', []),
    302: ('prlimit64', 'kernel', ['resource']),
    303: ('name_to_handle_at', 'fs', []),
    304: ('open_by_handle_at', 'fs', []),
    305: ('clock_adjtime', 'kernel', []),
    306: ('syncfs', 'fs', []),
    307: ('sendmmsg', 'net', []),
    308: ('setns', 'kernel', []),
    309: ('getcpu', 'kernel', []),
    310: ('process_vm_readv', 'mm', []),
    311: ('process_vm_writev', 'mm', []),
    312: ('kcmp', 'kernel', []),
    313: ('finit_module', 'kernel', []),
    314: ('sched_setattr', 'kernel', []),
    315: ('sched_getattr', 'kernel', []),
    316: ('renameat2', 'fs', []),
    317: ('seccomp', 'kernel', []),
    318: ('getrandom', 'drivers', []),
    319: ('memfd_create', 'mm', []),
    320: ('kexec_file_load', 'kernel', []),
    321: ('bpf', 'kernel', []),
    322: ('execveat', 'fs', []),
    323: ('userfaultfd', 'fs', []),
    324: ('membarrier', 'kernel', []),
    325: ('mlock2', 'mm', []),
    326: ('copy_file_range', 'fs', []),
    327: ('preadv2', 'fs', []),
    328: ('pwritev2', 'fs', []),
    329: ('pkey_mprotect', 'mm', []),
    330: ('pkey_alloc', 'mm', []),
    331: ('pkey_free', 'mm', []),
    332: ('statx', 'fs', []),
    333: ('io_pgetevents', 'fs', []),
    334: ('rseq', 'kernel', []),
    424: ('pidfd_send_signal', 'kernel', []),
    425: ('io_uring_setup', 'fs', []),
    426: ('io_uring_enter', 'fs', []),
    427: ('io_uring_register', 'fs', []),
    428: ('open_tree', 'fs', []),
    429: ('move_mount', 'fs', []),
    430: ('fsopen', 'fs', []),
    431: ('fsconfig', 'fs', []),
    432: ('fsmount', 'fs', []),
    433: ('fspick', 'fs', []),
    434: ('pidfd_open', 'kernel', []),
    435: ('clone3', 'kernel', []),
    436: ('close_range', 'fs', []),
    437: ('openat2', 'fs', []),
    438: ('pidfd_getfd', 'kernel', []),
    439: ('faccessat2', 'fs', []),
    440: ('process_madvise', 'mm', []),
    441: ('epoll_pwait2', 'fs', []),
    442: ('mount_setattr', 'fs', []),
    444: ('landlock_create_ruleset', 'NOT_IMPLEMENTED', []),
    445: ('landlock_add_rule', 'NOT_IMPLEMENTED', []),
    446: ('landlock_restrict_self', 'NOT_IMPLEMENTED', []),
}
