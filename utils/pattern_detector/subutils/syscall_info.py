from config import Config

import logging
import re


ALL_DATA = 0
CLIENT_RELATED_RSRW = 1
NOT_RANDOM = 2
CONVERT_OPTIONS = [CLIENT_RELATED_RSRW, NOT_RANDOM]

CLIENT_RELATED_PATH_NAME = ["socket", "TCP", "UDP"]

def convert_sequence_to_tuple_events(data, opt=0):
    if opt == ALL_DATA:
        return convert_origin_sequence_to_tuple_events(data)
    elif opt == CLIENT_RELATED_RSRW or opt == NOT_RANDOM:
        return convert_regex_sequence_to_tuple_events(data, opt)
    
    raise Exception(f"Wrong opt {opt} in convert_sequence_to_tuple_events")

def convert_data_to_tuple_event(data):
    eventId = int(data["eventId"])

    if eventId < 0:
        return None
    
    # Make differences between negative return values.
    return_val = int(data["returnValue"])
    return_val = 1 if return_val >= 0 else return_val

    event = [return_val, eventId]

    for arg_name in syscall_table[eventId][2]:
        for arg in data["args"]:
            if arg["name"] == arg_name:
                item = arg["value"]
                if arg["name"] == "pathname":
                    if type(item) is str:
                        item = ''.join([i for i in item if not i.isdigit()])
                    else:
                        item = ''

                event.append(item)
                break

    for arg in data["args"]:
        if arg["name"] == "socketAddr":
            ip = arg["value"].split(':')[0]
            event.append(ip)

    return tuple(event)


def convert_all_sequence_to_tuple_events(data):
    sequence = []

    for x in data:
        if x['eventId'] == -11:
            event = (0, -11)
        else:
            event = convert_data_to_tuple_event(x)
        sequence.append(event)

    return sequence

# sequence = [(ret, id, arg1, arg2), (ret, id), ...]
def convert_origin_sequence_to_tuple_events(data):
    sequence = []

    for x in data:
        event = convert_data_to_tuple_event(x)
        if event == None:
            continue

        sequence.append(event)

    return sequence


def convert_regex_sequence_to_tuple_events(data, opt):
    sequence = [()]

    for x in data:
        event = convert_data_to_tuple_event(x)
        if event == None:
            continue

        if check_event_opt(event, opt): #and sequence[-1] != tuple(event):
            sequence.append(tuple(event))

    return sequence[1:]


def is_random(id):
    random_category = ["kernel", "mm", "arch"]
    # random_category = ["kernel", "mm"]
    if syscall_table[id][1] in random_category:
        return True

    return False
    

def check_client_related_rsrw(event):
    eventId = event[1]

    if rwrs_syscall_table.get(eventId) is None:
        return False

    # When client's ip address set
    if len(Config.CLIENT_IP) > 0:
        ip = get_ip_from_event_if_exist(event)
        if ip != "":
            if ip in Config.CLIENT_IP:
                return True
            else:
                return False

    if rwrs_syscall_table[eventId][1] == 'net':
        return True

    pathname = get_pathname_from_event_if_exist(event)
    if any(cond in pathname for cond in CLIENT_RELATED_PATH_NAME):
        return True
        
    return False

def get_ip_from_event_if_exist(event):
    could_ip = event[-1]
    pt = "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"

    if type(could_ip) is not str:
        return ""

    if re.search(pt, could_ip):
        return could_ip
    return ""


def get_pathname_from_event_if_exist(event):
    eventId = event[1]
    arg_names = syscall_table[eventId][2]
    if "pathname" in arg_names:
        return event[2 + arg_names.index("pathname")]
    return ""


def get_fd_from_all_data_if_exist(data):
    fd = None
    for arg in data['args']:
        if 'fd' in arg['name']:
            fd = int(arg['value'])
            break
    if fd == None:
        logging.warning(f"{data['eventName']} does not have fd argument")
    return fd

def client_related_pt_to_ranges(seq, all_data, opt=CLIENT_RELATED_RSRW):
    pt_ranges = []
    i = 0

    while True:
        if i >= len(all_data):
            break

        if seq[i][1] < 0 or rr_syscall_table.get(seq[i][1]) is None or not check_event_opt(seq[i], opt):
            i += 1
            continue

        start = i
        end = -1
        start_fd = get_fd_from_all_data_if_exist(all_data[i])
        if start_fd == None:
            continue

        checkpoint = [start]
        for j in range(start+1, len(seq)):
            if seq[j][1] < 0 or rwrs_syscall_table.get(seq[j][1]) is None or not check_event_opt(seq[j], opt):
                continue

            if rr_syscall_table.get(seq[j][1]) is not None:
                if len(checkpoint) == 2:
                    break
                continue
            
            end_fd = get_fd_from_all_data_if_exist(all_data[j])
            if end_fd == None:
                continue

            if start_fd == end_fd:
                end = j
                if len(checkpoint) == 2:
                    checkpoint[-1] = j
                else:
                    checkpoint.append(j)
                continue

            if len(checkpoint) == 2:
                break
        
        if end > 0:
            i = checkpoint[-1]+1
            pt_ranges.append(checkpoint)
        else:
            if all_data[start]['returnValue'] > 0:
                logging.warning(f"{all_data[start]['eventName']} (idx: {start} fd: {start_fd}, ip: {seq[start][-1]}) does not have matched write-send")
            i += 1

    return pt_ranges

def extract_regex_pt_to_ranges(seq, opt, pt):
    pt_ranges = []

    plen = len(pt)

    i = 0
    while True:
        if i >= len(seq):
            break
        
        if seq[i][1] < 0 or seq[i] != pt[0]:
            i += 1
            continue

        start = i
        cur = 0
        end = -1
        tmp_end = -1

        checkpoint = [start]
        for j in range(start+1, len(seq)):
            if seq[j][1] < 0 or not check_event_opt(seq[j], opt):
                continue

            # if seq[j] == pt[cur]:
    #             if cur == plen-1:
    #                 end = j
    #                 checkpoint[-1] = j
    #             continue

            if seq[j] != pt[cur]:
                if cur+1 < plen:
                    if seq[j] == pt[cur+1]:
                        checkpoint.append(j)
                        cur += 1
                        if cur == plen-1:
                            end = j
                            if checkpoint[-1] != end:
                                checkpoint.append(end)
                        break
                        
                break
        
        if end > 0:
            i = checkpoint[-1]+1
            pt_ranges.append(checkpoint)
        else:
            i += 1

    return pt_ranges
    
def check_event_opt(event, opt):
    if opt == ALL_DATA:
        return True

    if opt == CLIENT_RELATED_RSRW:
        return check_client_related_rsrw(event)
        
    elif opt == NOT_RANDOM:
        return not check_client_related_rsrw(event) and not is_random(event[1])

    return False


def get_thread_excution_time(all_data):
    for i in range(0, len(all_data), 1):
        fisrt_time = all_data[i]["timestamp"]
        if fisrt_time != -9999:
            break
    
    for i in range(len(all_data)-1, -1, -1):
        last_time = all_data[i]["endTimestamp"]
        if last_time != -9999:
            break

    return last_time - fisrt_time


def get_opt_from_event(event):
    if event[1] < 0:
        return ALL_DATA

    for opt in CONVERT_OPTIONS:
        if check_event_opt(event, opt):
            return opt



def pattern_to_name(pattern):
    result = []
    for event in pattern:
        no = event[1]
        info = syscall_table.get(no)
        if info is None:
            result.append("")
        else:
            result.append(info[0])
    return result
    

def pattern_to_cat(pattern):
    found_category = {
        "fs" : False,
        "mm" : False,
        "ipc": False,
        "net": False,
        "arch": False,
        "kernel": False,
        "security": False
    }
    for event in pattern:
        no = event[1]
        info = syscall_table.get(no)
        if info is not None:
            found_category[info[1]] = True

    return f'{found_category["fs"]}\t{found_category["mm"]}\t{found_category["ipc"]}\t{found_category["net"]}\t{found_category["arch"]}\t{found_category["kernel"]}\t{found_category["security"]}'

def pattern_to_verbose_str(pattern):
    pattern_verbose = []
    for event in pattern:
        return_val = str(event[0]) if event[0] < 0 else ""
        
        args = syscall_table[event[1]][2]
        args_verbose = ', '.join([f'[{args[i]}]{event[2:][i]}' for i in range(len(args))])

        event_verbose = [
            f'{pattern_to_name( ((0, event[1]),) )}',\
            f'({return_val}): ',\
            f"{args_verbose}"
        ]
        event_verbose_str = ''.join(event_verbose)
        pattern_verbose.append(event_verbose_str)

    return '@@@'.join(pattern_verbose)


rwrs_syscall_table = {
    0: ('read', 'fs', ['pathname']),
    1: ('write', 'fs', ['pathname']),
    17: ('pread64', 'fs', ['pathname']),
    18: ('pwrite64', 'fs', ['pathname']),
    19: ('readv', 'fs', ['iovcnt', 'pathname']),
    20: ('writev', 'fs', ['pathname']),
    40: ('sendfile', 'fs', []),
    44: ('sendto', 'net', ['flags']),
    45: ('recvfrom', 'net', ['flags']),
    46: ('sendmsg', 'net', ['flags']),
    47: ('recvmsg', 'net', ['flags']),
    89: ('readlink', 'fs', ['pathname', 'bufsiz']),
    187: ('readahead', 'mm', ['pathname']),
    242: ('mq_timedsend', 'ipc', []),
    243: ('mq_timedreceive', 'ipc', []),
    267: ('readlinkat', 'fs', []),
    295: ('preadv', 'fs', []),
    296: ('pwritev', 'fs', []),
    299: ('recvmmsg', 'net', []),
    307: ('sendmmsg', 'net', []),
    327: ('preadv2', 'fs', []),
    328: ('pwritev2', 'fs', []),
}

rr_syscall_table = {
    0: 'read',
    17: 'pread64',
    19: 'readv',
    45: 'recvfrom',
    47: 'recvmsg',
    89: 'readlink',
    187: 'readahead',
    243: 'mq_timedreceive',
    267: 'readlinkat',
    295: 'preadv',
    299: 'recvmmsg',
    310: 'process_vm_readv',
    327: 'preadv2'
}

ws_syscall_table = {
    1: 'write',
    18: 'pwrite64',
    20: 'writev',
    40: 'sendfile',
    44: 'sendto',
    46: 'sendmsg',
    242: 'mq_timedsend',
    296: 'pwritev',
    307: 'sendmmsg',
    328: 'pwritev2'
}

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
