#!/usr/bin/env python3

import os, sys, json, re
from argparse import ArgumentParser
from ctypes import *
from enum import Enum
from itertools import count
import signal

syscalls = {
    "read": (0, [{'int': 'fd'}, {'char*': 'buf'}, {'size_t': 'count'}]),
    "write": (1, [{'int': 'fd'}, {'char*': 'buf'}, {'size_t': 'count'}]),
    "open": (2, [{'const char*': 'pathname'}, {'int': 'flags'}, {'mode_t': 'mode'}]),
    "close": (3, [{'int': 'fd'}]),
    "stat": (4, [{'const char*': 'pathname'}, {'struct stat*': 'statbuf'}]),
    "fstat": (5, [{'int': 'fd'}, {'struct stat*': 'statbuf'}]),
    "lstat": (6, [{'const char*': 'pathname'}, {'struct stat*': 'statbuf'}]),
    "poll": (7, [{'struct pollfd*': 'fds'}, {'unsigned int': 'nfds'}, {'int': 'timeout'}]),
    "lseek": (8, [{'int': 'fd'}, {'off_t': 'offset'}, {'unsigned int': 'whence'}]),
    "mmap": (9, [{'void*': 'addr'}, {'size_t': 'length'}, {'int': 'prot'}, {'int': 'flags'}, {'int': 'fd'}, {'off_t': 'off'}]),
    "mprotect": (10, [{'void*': 'addr'}, {'size_t': 'len'}, {'int': 'prot'}]),
    "munmap": (11, [{'void*': 'addr'}, {'size_t': 'length'}]),
    "brk": (12, [{'void*': 'addr'}]),
    "rt_sigaction": (13, [{'int': 'signum'}, {'const struct sigaction*': 'act'}, {'struct sigaction*': 'oldact'}, {'size_t': 'sigsetsize'}]),
    "rt_sigprocmask": (14, [{'int': 'how'}, {'sigset_t*': 'set'}, {'sigset_t*': 'oldset'}, {'size_t': 'sigsetsize'}]),
    "rt_sigreturn": (15, []),
    "ioctl": (16, [{'int': 'fd'}, {'unsigned long': 'request'}, {'unsigned long': 'arg'}]),
    "pread64": (17, [{'int': 'fd'}, {'char*': 'buf'}, {'size_t': 'count'}, {'off_t': 'offset'}]),
    "pwrite64": (18, [{'int': 'fd'}, {'const char*': 'buf'}, {'size_t': 'count'}, {'off_t': 'offset'}]),
    "readv": (19, [{'int': 'fd'}, {'const struct iovec*': 'iov'}, {'int': 'iovcnt'}]),
    "writev": (20, [{'int': 'fd'}, {'const struct iovec*': 'iov'}, {'int': 'iovcnt'}]),
    "access": (21, [{'const char*': 'pathname'}, {'int': 'mode'}]),
    "pipe": (22, [{'int[2]': 'pipefd'}]),
    "select": (23, [{'int': 'nfds'}, {'fd_set*': 'readfds'}, {'fd_set*': 'writefds'}, {'fd_set*': 'exceptfds'}, {'struct timeval*': 'timeout'}]),
    "sched_yield": (24, []),
    "mremap": (25, [{'void*': 'old_address'}, {'size_t': 'old_size'}, {'size_t': 'new_size'}, {'int': 'flags'}, {'void*': 'new_address'}]),
    "msync": (26, [{'void*': 'addr'}, {'size_t': 'length'}, {'int': 'flags'}]),
    "mincore": (27, [{'void*': 'addr'}, {'size_t': 'length'}, {'unsigned char*': 'vec'}]),
    "madvise": (28, [{'void*': 'addr'}, {'size_t': 'length'}, {'int': 'advice'}]),
    "shmget": (29, [{'key_t': 'key'}, {'size_t': 'size'}, {'int': 'shmflg'}]),
    "shmat": (30, [{'int': 'shmid'}, {'const void*': 'shmaddr'}, {'int': 'shmflg'}]),
    "shmctl": (31, [{'int': 'shmid'}, {'int': 'cmd'}, {'struct shmid_ds*': 'buf'}]),
    "dup": (32, [{'int': 'oldfd'}]),
    "dup2": (33, [{'int': 'oldfd'}, {'int': 'newfd'}]),
    "pause": (34, []),
    "nanosleep": (35, [{'const struct timespec*': 'req'}, {'struct timespec*': 'rem'}]),
    "getitimer": (36, [{'int': 'which'}, {'struct itimerval*': 'curr_value'}]),
    "alarm": (37, [{'unsigned int': 'seconds'}]),
    "setitimer": (38, [{'int': 'which'}, {'struct itimerval*': 'new_value'}, {'struct itimerval*': 'old_value'}]),
    "getpid": (39, []),
    "sendfile": (40, [{'int': 'out_fd'}, {'int': 'in_fd'}, {'off_t*': 'offset'}, {'size_t': 'count'}]),
    "socket": (41, [{'int': 'domain'}, {'int': 'type'}, {'int': 'protocol'}]),
    "connect": (42, [{'int': 'sockfd'}, {'struct sockaddr*': 'addr'}, {'int': 'addrlen'}]),
    "accept": (43, [{'int': 'sockfd'}, {'struct sockaddr*': 'addr'}, {'int*': 'addrlen'}]),
    "sendto": (44, [{'int': 'sockfd'}, {'recvfrom*': 'buf'}, {'size_t': 'len'}, {'int': 'flags'}, {'struct sockaddr*': 'dest_addr'}, {'int': 'addrlen'}]),
    "recvfrom": (45, [{'int': 'sockfd'}, {'recvfrom*': 'buf'}, {'size_t': 'len'}, {'int': 'flags'}, {'struct sockaddr*': 'src_addr'}, {'int*': 'addrlen'}]),
    "sendmsg": (46, [{'int': 'sockfd'}, {'struct msghdr*': 'msg'}, {'int': 'flags'}]),
    "recvmsg": (47, [{'int': 'sockfd'}, {'struct msghdr*': 'msg'}, {'int': 'flags'}]),
    "shutdown": (48, [{'int': 'sockfd'}, {'int': 'how'}]),
    "bind": (49, [{'int': 'sockfd'}, {'struct sockaddr*': 'addr'}, {'int': 'addrlen'}]),
    "listen": (50, [{'int': 'sockfd'}, {'int': 'backlog'}]),
    "getsockname": (51, [{'int': 'sockfd'}, {'struct sockaddr*': 'addr'}, {'int*': 'addrlen'}]),
    "getpeername": (52, [{'int': 'sockfd'}, {'struct sockaddr*': 'addr'}, {'int*': 'addrlen'}]),
    "socketpair": (53, [{'int': 'domain'}, {'int': 'type'}, {'int': 'protocol'}, {'int[2]': 'sv'}]),
    "setsockopt": (54, [{'int': 'sockfd'}, {'int': 'level'}, {'int': 'optname'}, {'const void*': 'optval'}, {'int': 'optlen'}]),
    "getsockopt": (55, [{'int': 'sockfd'}, {'int': 'level'}, {'int': 'optname'}, {'char*': 'optval'}, {'int*': 'optlen'}]),
    "clone": (56, [{'unsigned long': 'flags'}, {'void*': 'stack'}, {'int*': 'parent_tid'}, {'int*': 'child_tid'}, {'unsigned long': 'tls'}]),
    "fork": (57, []),
    "vfork": (58, []),
    "execve": (59, [{'const char*': 'pathname'}, {'const char*const*': 'argv'}, {'const char*const*': 'envp'}]),
    "exit": (60, [{'int': 'status'}]),
    "wait4": (61, [{'pid_t': 'pid'}, {'int*': 'wstatus'}, {'int': 'options'}, {'struct rusage*': 'rusage'}]),
    "kill": (62, [{'pid_t': 'pid'}, {'int': 'sig'}]),
    "uname": (63, [{'struct utsname*': 'buf'}]),
    "semget": (64, [{'key_t': 'key'}, {'int': 'nsems'}, {'int': 'semflg'}]),
    "semop": (65, [{'int': 'semid'}, {'struct sembuf*': 'sops'}, {'size_t': 'nsops'}]),
    "semctl": (66, [{'int': 'semid'}, {'int': 'semnum'}, {'int': 'cmd'}, {'unsigned long': 'arg'}]),
    "shmdt": (67, [{'const void*': 'shmaddr'}]),
    "msgget": (68, [{'key_t': 'key'}, {'int': 'msgflg'}]),
    "msgsnd": (69, [{'int': 'msqid'}, {'struct msgbuf*': 'msgp'}, {'size_t': 'msgsz'}, {'int': 'msgflg'}]),
    "msgrcv": (70, [{'int': 'msqid'}, {'struct msgbuf*': 'msgp'}, {'size_t': 'msgsz'}, {'long': 'msgtyp'}, {'int': 'msgflg'}]),
    "msgctl": (71, [{'int': 'msqid'}, {'int': 'cmd'}, {'struct msqid_ds*': 'buf'}]),
    "fcntl": (72, [{'int': 'fd'}, {'int': 'cmd'}, {'unsigned long': 'arg'}]),
    "flock": (73, [{'int': 'fd'}, {'int': 'operation'}]),
    "fsync": (74, [{'int': 'fd'}]),
    "fdatasync": (75, [{'int': 'fd'}]),
    "truncate": (76, [{'const char*': 'path'}, {'off_t': 'length'}]),
    "ftruncate": (77, [{'int': 'fd'}, {'off_t': 'length'}]),
    "getdents": (78, [{'int': 'fd'}, {'struct linux_dirent*': 'dirp'}, {'unsigned int': 'count'}]),
    "getcwd": (79, [{'char*': 'buf'}, {'size_t': 'size'}]),
    "chdir": (80, [{'const char*': 'path'}]),
    "fchdir": (81, [{'int': 'fd'}]),
    "rename": (82, [{'const char*': 'oldpath'}, {'const char*': 'newpath'}]),
    "mkdir": (83, [{'const char*': 'pathname'}, {'mode_t': 'mode'}]),
    "rmdir": (84, [{'const char*': 'pathname'}]),
    "creat": (85, [{'const char*': 'pathname'}, {'mode_t': 'mode'}]),
    "link": (86, [{'const char*': 'oldpath'}, {'const char*': 'newpath'}]),
    "unlink": (87, [{'const char*': 'pathname'}]),
    "symlink": (88, [{'const char*': 'target'}, {'const char*': 'linkpath'}]),
    "readlink": (89, [{'const char*': 'pathname'}, {'char*': 'buf'}, {'size_t': 'bufsiz'}]),
    "chmod": (90, [{'const char*': 'pathname'}, {'mode_t': 'mode'}]),
    "fchmod": (91, [{'int': 'fd'}, {'mode_t': 'mode'}]),
    "chown": (92, [{'const char*': 'pathname'}, {'uid_t': 'owner'}, {'gid_t': 'group'}]),
    "fchown": (93, [{'int': 'fd'}, {'uid_t': 'owner'}, {'gid_t': 'group'}]),
    "lchown": (94, [{'const char*': 'pathname'}, {'uid_t': 'owner'}, {'gid_t': 'group'}]),
    "umask": (95, [{'mode_t': 'mask'}]),
    "gettimeofday": (96, [{'struct timeval*': 'tv'}, {'struct timezone*': 'tz'}]),
    "getrlimit": (97, [{'int': 'resource'}, {'struct rlimit*': 'rlim'}]),
    "getrusage": (98, [{'int': 'who'}, {'struct rusage*': 'usage'}]),
    "sysinfo": (99, [{'struct sysinfo*': 'info'}]),
    "times": (100, [{'struct tms*': 'buf'}]),
    "ptrace": (101, [{'long': 'request'}, {'pid_t': 'pid'}, {'void*': 'addr'}, {'void*': 'data'}]),
    "getuid": (102, []),
    "syslog": (103, [{'int': 'type'}, {'char*': 'bufp'}, {'int': 'len'}]),
    "getgid": (104, []),
    "setuid": (105, [{'uid_t': 'uid'}]),
    "setgid": (106, [{'gid_t': 'gid'}]),
    "geteuid": (107, []),
    "getegid": (108, []),
    "setpgid": (109, [{'pid_t': 'pid'}, {'pid_t': 'pgid'}]),
    "getppid": (110, []),
    "getpgrp": (111, []),
    "setsid": (112, []),
    "setreuid": (113, [{'uid_t': 'ruid'}, {'uid_t': 'euid'}]),
    "setregid": (114, [{'gid_t': 'rgid'}, {'gid_t': 'egid'}]),
    "getgroups": (115, [{'int': 'size'}, {'gid_t*': 'list'}]),
    "setgroups": (116, [{'int': 'size'}, {'gid_t*': 'list'}]),
    "setresuid": (117, [{'uid_t': 'ruid'}, {'uid_t': 'euid'}, {'uid_t': 'suid'}]),
    "getresuid": (118, [{'uid_t*': 'ruid'}, {'uid_t*': 'euid'}, {'uid_t*': 'suid'}]),
    "setresgid": (119, [{'gid_t': 'rgid'}, {'gid_t': 'egid'}, {'gid_t': 'sgid'}]),
    "getresgid": (120, [{'gid_t*': 'rgid'}, {'gid_t*': 'egid'}, {'gid_t*': 'sgid'}]),
    "getpgid": (121, [{'pid_t': 'pid'}]),
    "setfsuid": (122, [{'uid_t': 'fsuid'}]),
    "setfsgid": (123, [{'gid_t': 'fsgid'}]),
    "getsid": (124, [{'pid_t': 'pid'}]),
    "capget": (125, [{'cap_user_header_t': 'hdrp'}, {'cap_user_data_t': 'datap'}]),
    "capset": (126, [{'cap_user_header_t': 'hdrp'}, {'const cap_user_data_t': 'datap'}]),
    "rt_sigpending": (127, [{'sigset_t*': 'set'}, {'size_t': 'sigsetsize'}]),
    "rt_sigtimedwait": (128, [{'const sigset_t*': 'set'}, {'siginfo_t*': 'info'}, {'const struct timespec*': 'timeout'}, {'size_t': 'sigsetsize'}]),
    "rt_sigqueueinfo": (129, [{'pid_t': 'tgid'}, {'int': 'sig'}, {'siginfo_t*': 'info'}]),
    "rt_sigsuspend": (130, [{'sigset_t*': 'mask'}, {'size_t': 'sigsetsize'}]),
    "sigaltstack": (131, [{'const stack_t*': 'ss'}, {'stack_t*': 'old_ss'}]),
    "utime": (132, [{'const char*': 'filename'}, {'const struct utimbuf*': 'times'}]),
    "mknod": (133, [{'const char*': 'pathname'}, {'mode_t': 'mode'}, {'dev_t': 'dev'}]),
    "personality": (135, [{'unsigned long': 'persona'}]),
    "ustat": (136, [{'dev_t': 'dev'}, {'struct ustat*': 'ubuf'}]),
    "statfs": (137, [{'const char*': 'path'}, {'struct statfs*': 'buf'}]),
    "fstatfs": (138, [{'int': 'fd'}, {'struct statfs*': 'buf'}]),
    "sysfs": (139, [{'int': 'option'}]),
    "getpriority": (140, [{'int': 'which'}, {'int': 'who'}]),
    "setpriority": (141, [{'int': 'which'}, {'int': 'who'}, {'int': 'prio'}]),
    "sched_setparam": (142, [{'pid_t': 'pid'}, {'struct sched_param*': 'param'}]),
    "sched_getparam": (143, [{'pid_t': 'pid'}, {'struct sched_param*': 'param'}]),
    "sched_setscheduler": (144, [{'pid_t': 'pid'}, {'int': 'policy'}, {'struct sched_param*': 'param'}]),
    "sched_getscheduler": (145, [{'pid_t': 'pid'}]),
    "sched_get_priority_max": (146, [{'int': 'policy'}]),
    "sched_get_priority_min": (147, [{'int': 'policy'}]),
    "sched_rr_get_interval": (148, [{'pid_t': 'pid'}, {'struct timespec*': 'tp'}]),
    "mlock": (149, [{'const void*': 'addr'}, {'size_t': 'len'}]),
    "munlock": (150, [{'const void*': 'addr'}, {'size_t': 'len'}]),
    "mlockall": (151, [{'int': 'flags'}]),
    "munlockall": (152, []),
    "vhangup": (153, []),
    "modify_ldt": (154, [{'int': 'func'}, {'void*': 'ptr'}, {'unsigned long': 'bytecount'}]),
    "pivot_root": (155, [{'const char*': 'new_root'}, {'const char*': 'put_old'}]),
    "prctl": (157, [{'int': 'option'}, {'unsigned long': 'arg2'}, {'unsigned long': 'arg3'}, {'unsigned long': 'arg4'}, {'unsigned long': 'arg5'}]),
    "arch_prctl": (158, [{'int': 'option'}, {'unsigned long': 'addr'}]),
    "adjtimex": (159, [{'struct timex*': 'buf'}]),
    "setrlimit": (160, [{'int': 'resource'}, {'const struct rlimit*': 'rlim'}]),
    "chroot": (161, [{'const char*': 'path'}]),
    "sync": (162, []),
    "acct": (163, [{'const char*': 'filename'}]),
    "settimeofday": (164, [{'const struct timeval*': 'tv'}, {'const struct timezone*': 'tz'}]),
    "mount": (165, [{'const char*': 'source'}, {'const char*': 'target'}, {'const char*': 'filesystemtype'}, {'unsigned long': 'mountflags'}, {'const void*': 'data'}]),
    "swapon": (167, [{'const char*': 'path'}, {'int': 'swapflags'}]),
    "swapoff": (168, [{'const char*': 'path'}]),
    "reboot": (169, [{'int': 'magic'}, {'int': 'magic2'}, {'int': 'cmd'}, {'void*': 'arg'}]),
    "sethostname": (170, [{'const char*': 'name'}, {'size_t': 'len'}]),
    "setdomainname": (171, [{'const char*': 'name'}, {'size_t': 'len'}]),
    "iopl": (172, [{'int': 'level'}]),
    "ioperm": (173, [{'unsigned long': 'from'}, {'unsigned long': 'num'}, {'int': 'turn_on'}]),
    "init_module": (175, [{'void*': 'module_image'}, {'unsigned long': 'len'}, {'const char*': 'param_values'}]),
    "delete_module": (176, [{'const char*': 'name'}, {'int': 'flags'}]),
    "quotactl": (179, [{'int': 'cmd'}, {'const char*': 'special'}, {'int': 'id'}, {'void*': 'addr'}]),
    "gettid": (186, []),
    "readahead": (187, [{'int': 'fd'}, {'off_t': 'offset'}, {'size_t': 'count'}]),
    "setxattr": (188, [{'const char*': 'path'}, {'const char*': 'name'}, {'const void*': 'value'}, {'size_t': 'size'}, {'int': 'flags'}]),
    "lsetxattr": (189, [{'const char*': 'path'}, {'const char*': 'name'}, {'const void*': 'value'}, {'size_t': 'size'}, {'int': 'flags'}]),
    "fsetxattr": (190, [{'int': 'fd'}, {'const char*': 'name'}, {'const void*': 'value'}, {'size_t': 'size'}, {'int': 'flags'}]),
    "getxattr": (191, [{'const char*': 'path'}, {'const char*': 'name'}, {'void*': 'value'}, {'size_t': 'size'}]),
    "lgetxattr": (192, [{'const char*': 'path'}, {'const char*': 'name'}, {'void*': 'value'}, {'size_t': 'size'}]),
    "fgetxattr": (193, [{'int': 'fd'}, {'const char*': 'name'}, {'void*': 'value'}, {'size_t': 'size'}]),
    "listxattr": (194, [{'const char*': 'path'}, {'char*': 'list'}, {'size_t': 'size'}]),
    "llistxattr": (195, [{'const char*': 'path'}, {'char*': 'list'}, {'size_t': 'size'}]),
    "flistxattr": (196, [{'int': 'fd'}, {'char*': 'list'}, {'size_t': 'size'}]),
    "removexattr": (197, [{'const char*': 'path'}, {'const char*': 'name'}]),
    "lremovexattr": (198, [{'const char*': 'path'}, {'const char*': 'name'}]),
    "fremovexattr": (199, [{'int': 'fd'}, {'const char*': 'name'}]),
    "tkill": (200, [{'int': 'tid'}, {'int': 'sig'}]),
    "time": (201, [{'time_t*': 'tloc'}]),
    "futex": (202, [{'int*': 'uaddr'}, {'int': 'futex_op'}, {'int': 'val'}, {'const struct timespec*': 'timeout'}, {'int*': 'uaddr2'}, {'int': 'val3'}]),
    "sched_setaffinity": (203, [{'pid_t': 'pid'}, {'size_t': 'cpusetsize'}, {'unsigned long*': 'mask'}]),
    "sched_getaffinity": (204, [{'pid_t': 'pid'}, {'size_t': 'cpusetsize'}, {'unsigned long*': 'mask'}]),
    "io_setup": (206, [{'unsigned int': 'nr_events'}, {'io_context_t*': 'ctx_idp'}]),
    "io_destroy": (207, [{'io_context_t': 'ctx_id'}]),
    "io_getevents": (208, [{'io_context_t': 'ctx_id'}, {'long': 'min_nr'}, {'long': 'nr'}, {'struct io_event*': 'events'}, {'struct timespec*': 'timeout'}]),
    "io_submit": (209, [{'io_context_t': 'ctx_id'}, {'long': 'nr'}, {'struct iocb**': 'iocbpp'}]),
    "io_cancel": (210, [{'io_context_t': 'ctx_id'}, {'struct iocb*': 'iocb'}, {'struct io_event*': 'result'}]),
    "lookup_dcookie": (212, [{'u64': 'cookie'}, {'char*': 'buffer'}, {'size_t': 'len'}]),
    "epoll_create": (213, [{'int': 'size'}]),
    "remap_file_pages": (216, [{'void*': 'addr'}, {'size_t': 'size'}, {'int': 'prot'}, {'size_t': 'pgoff'}, {'int': 'flags'}]),
    "getdents64": (217, [{'unsigned int': 'fd'}, {'struct linux_dirent64*': 'dirp'}, {'unsigned int': 'count'}]),
    "set_tid_address": (218, [{'int*': 'tidptr'}]),
    "restart_syscall": (219, []),
    "semtimedop": (220, [{'int': 'semid'}, {'struct sembuf*': 'sops'}, {'size_t': 'nsops'}, {'const struct timespec*': 'timeout'}]),
    "fadvise64": (221, [{'int': 'fd'}, {'off_t': 'offset'}, {'size_t': 'len'}, {'int': 'advice'}]),
    "timer_create": (222, [{'const clockid_t': 'clockid'}, {'struct sigevent*': 'sevp'}, {'timer_t*': 'timer_id'}]),
    "timer_settime": (223, [{'timer_t': 'timer_id'}, {'int': 'flags'}, {'const struct itimerspec*': 'new_value'}, {'struct itimerspec*': 'old_value'}]),
    "timer_gettime": (224, [{'timer_t': 'timer_id'}, {'struct itimerspec*': 'curr_value'}]),
    "timer_getoverrun": (225, [{'timer_t': 'timer_id'}]),
    "timer_delete": (226, [{'timer_t': 'timer_id'}]),
    "clock_settime": (227, [{'const clockid_t': 'clockid'}, {'const struct timespec*': 'tp'}]),
    "clock_gettime": (228, [{'const clockid_t': 'clockid'}, {'struct timespec*': 'tp'}]),
    "clock_getres": (229, [{'const clockid_t': 'clockid'}, {'struct timespec*': 'res'}]),
    "clock_nanosleep": (230, [{'const clockid_t': 'clockid'}, {'int': 'flags'}, {'const struct timespec*': 'request'}, {'struct timespec*': 'remain'}]),
    "exit_group": (231, [{'int': 'status'}]),
    "epoll_wait": (232, [{'int': 'epfd'}, {'struct epoll_event*': 'events'}, {'int': 'maxevents'}, {'int': 'timeout'}]),
    "epoll_ctl": (233, [{'int': 'epfd'}, {'int': 'op'}, {'int': 'fd'}, {'struct epoll_event*': 'event'}]),
    "tgkill": (234, [{'int': 'tgid'}, {'int': 'tid'}, {'int': 'sig'}]),
    "utimes": (235, [{'char*': 'filename'}, {'struct timeval*': 'times'}]),
    "mbind": (237, [{'void*': 'addr'}, {'unsigned long': 'len'}, {'int': 'mode'}, {'const unsigned long*': 'nodemask'}, {'unsigned long': 'maxnode'}, {'unsigned int': 'flags'}]),
    "set_mempolicy": (238, [{'int': 'mode'}, {'const unsigned long*': 'nodemask'}, {'unsigned long': 'maxnode'}]),
    "get_mempolicy": (239, [{'int*': 'mode'}, {'unsigned long*': 'nodemask'}, {'unsigned long': 'maxnode'}, {'void*': 'addr'}, {'unsigned long': 'flags'}]),
    "mq_open": (240, [{'const char*': 'name'}, {'int': 'oflag'}, {'mode_t': 'mode'}, {'struct mq_attr*': 'attr'}]),
    "mq_unlink": (241, [{'const char*': 'name'}]),
    "mq_timedsend": (242, [{'mqd_t': 'mqdes'}, {'const char*': 'msg_ptr'}, {'size_t': 'msg_len'}, {'unsigned int': 'msg_prio'}, {'const struct timespec*': 'abs_timeout'}]),
    "mq_timedreceive": (243, [{'mqd_t': 'mqdes'}, {'char*': 'msg_ptr'}, {'size_t': 'msg_len'}, {'unsigned int*': 'msg_prio'}, {'const struct timespec*': 'abs_timeout'}]),
    "mq_notify": (244, [{'mqd_t': 'mqdes'}, {'const struct sigevent*': 'sevp'}]),
    "mq_getsetattr": (245, [{'mqd_t': 'mqdes'}, {'const struct mq_attr*': 'newattr'}, {'struct mq_attr*': 'oldattr'}]),
    "kexec_load": (246, [{'unsigned long': 'entry'}, {'unsigned long': 'nr_segments'}, {'struct kexec_segment*': 'segments'}, {'unsigned long': 'flags'}]),
    "waitid": (247, [{'int': 'idtype'}, {'pid_t': 'id'}, {'struct siginfo*': 'infop'}, {'int': 'options'}, {'struct rusage*': 'rusage'}]),
    "add_key": (248, [{'const char*': 'type'}, {'const char*': 'description'}, {'const void*': 'payload'}, {'size_t': 'plen'}, {'key_serial_t': 'keyring'}]),
    "request_key": (249, [{'const char*': 'type'}, {'const char*': 'description'}, {'const char*': 'callout_info'}, {'key_serial_t': 'dest_keyring'}]),
    "keyctl": (250, [{'int': 'operation'}, {'unsigned long': 'arg2'}, {'unsigned long': 'arg3'}, {'unsigned long': 'arg4'}, {'unsigned long': 'arg5'}]),
    "ioprio_set": (251, [{'int': 'which'}, {'int': 'who'}, {'int': 'ioprio'}]),
    "ioprio_get": (252, [{'int': 'which'}, {'int': 'who'}]),
    "inotify_init": (253, []),
    "inotify_add_watch": (254, [{'int': 'fd'}, {'u32': 'mask'}]),
    "inotify_rm_watch": (255, [{'int': 'fd'}, {'int': 'wd'}]),
    "migrate_pages": (256, [{'int': 'pid'}, {'unsigned long': 'maxnode'}, {'const unsigned long*': 'old_nodes'}, {'const unsigned long*': 'new_nodes'}]),
    "openat": (257, [{'int': 'dirfd'}, {'int': 'flags'}, {'mode_t': 'mode'}]),
    "mkdirat": (258, [{'int': 'dirfd'}, {'mode_t': 'mode'}]),
    "mknodat": (259, [{'int': 'dirfd'}, {'mode_t': 'mode'}, {'dev_t': 'dev'}]),
    "fchownat": (260, [{'int': 'dirfd'}, {'uid_t': 'owner'}, {'gid_t': 'group'}, {'int': 'flags'}]),
    "futimesat": (261, [{'int': 'dirfd'}, {'struct timeval*': 'times'}]),
    "newfstatat": (262, [{'int': 'dirfd'}, {'struct stat*': 'statbuf'}, {'int': 'flags'}]),
    "unlinkat": (263, [{'int': 'dirfd'}, {'int': 'flags'}]),
    "renameat": (264, [{'int': 'olddirfd'}, {'const char*': 'oldpath'}, {'int': 'newdirfd'}, {'const char*': 'newpath'}]),
    "linkat": (265, [{'int': 'olddirfd'}, {'const char*': 'oldpath'}, {'int': 'newdirfd'}, {'const char*': 'newpath'}, {'unsigned int': 'flags'}]),
    "symlinkat": (266, [{'const char*': 'target'}, {'int': 'newdirfd'}, {'const char*': 'linkpath'}]),
    "readlinkat": (267, [{'int': 'dirfd'}, {'char*': 'buf'}, {'int': 'bufsiz'}]),
    "fchmodat": (268, [{'int': 'dirfd'}, {'mode_t': 'mode'}, {'int': 'flags'}]),
    "faccessat": (269, [{'int': 'dirfd'}, {'int': 'mode'}, {'int': 'flags'}]),
    "pselect6": (270, [{'int': 'nfds'}, {'fd_set*': 'readfds'}, {'fd_set*': 'writefds'}, {'fd_set*': 'exceptfds'}, {'struct timespec*': 'timeout'}, {'void*': 'sigmask'}]),
    "ppoll": (271, [{'struct pollfd*': 'fds'}, {'unsigned int': 'nfds'}, {'struct timespec*': 'tmo_p'}, {'const sigset_t*': 'sigmask'}, {'size_t': 'sigsetsize'}]),
    "unshare": (272, [{'int': 'flags'}]),
    "set_robust_list": (273, [{'struct robust_list_head*': 'head'}, {'size_t': 'len'}]),
    "get_robust_list": (274, [{'int': 'pid'}, {'struct robust_list_head**': 'head_ptr'}, {'size_t*': 'len_ptr'}]),
    "splice": (275, [{'int': 'fd_in'}, {'off_t*': 'off_in'}, {'int': 'fd_out'}, {'off_t*': 'off_out'}, {'size_t': 'len'}, {'unsigned int': 'flags'}]),
    "tee": (276, [{'int': 'fd_in'}, {'int': 'fd_out'}, {'size_t': 'len'}, {'unsigned int': 'flags'}]),
    "sync_file_range": (277, [{'int': 'fd'}, {'off_t': 'offset'}, {'off_t': 'nbytes'}, {'unsigned int': 'flags'}]),
    "vmsplice": (278, [{'int': 'fd'}, {'const struct iovec*': 'iov'}, {'unsigned long': 'nr_segs'}, {'unsigned int': 'flags'}]),
    "move_pages": (279, [{'int': 'pid'}, {'unsigned long': 'count'}, {'const void**': 'pages'}, {'const int*': 'nodes'}, {'int*': 'status'}, {'int': 'flags'}]),
    "utimensat": (280, [{'int': 'dirfd'}, {'struct timespec*': 'times'}, {'int': 'flags'}]),
    "epoll_pwait": (281, [{'int': 'epfd'}, {'struct epoll_event*': 'events'}, {'int': 'maxevents'}, {'int': 'timeout'}, {'const sigset_t*': 'sigmask'}, {'size_t': 'sigsetsize'}]),
    "signalfd": (282, [{'int': 'fd'}, {'sigset_t*': 'mask'}, {'int': 'flags'}]),
    "timerfd_create": (283, [{'int': 'clockid'}, {'int': 'flags'}]),
    "eventfd": (284, [{'unsigned int': 'initval'}, {'int': 'flags'}]),
    "fallocate": (285, [{'int': 'fd'}, {'int': 'mode'}, {'off_t': 'offset'}, {'off_t': 'len'}]),
    "timerfd_settime": (286, [{'int': 'fd'}, {'int': 'flags'}, {'const struct itimerspec*': 'new_value'}, {'struct itimerspec*': 'old_value'}]),
    "timerfd_gettime": (287, [{'int': 'fd'}, {'struct itimerspec*': 'curr_value'}]),
    "accept4": (288, [{'int': 'sockfd'}, {'struct sockaddr*': 'addr'}, {'int*': 'addrlen'}, {'int': 'flags'}]),
    "signalfd4": (289, [{'int': 'fd'}, {'const sigset_t*': 'mask'}, {'size_t': 'sizemask'}, {'int': 'flags'}]),
    "eventfd2": (290, [{'unsigned int': 'initval'}, {'int': 'flags'}]),
    "epoll_create1": (291, [{'int': 'flags'}]),
    "dup3": (292, [{'int': 'oldfd'}, {'int': 'newfd'}, {'int': 'flags'}]),
    "pipe2": (293, [{'int*': 'pipefd'}, {'int': 'flags'}]),
    "inotify_init1": (294, [{'int': 'flags'}]),
    "preadv": (295, [{'int': 'fd'}, {'const struct iovec*': 'iov'}, {'unsigned long': 'iovcnt'}, {'unsigned long': 'pos_l'}, {'unsigned long': 'pos_h'}]),
    "pwritev": (296, [{'int': 'fd'}, {'const struct iovec*': 'iov'}, {'unsigned long': 'iovcnt'}, {'unsigned long': 'pos_l'}, {'unsigned long': 'pos_h'}]),
    "rt_tgsigqueueinfo": (297, [{'pid_t': 'tgid'}, {'pid_t': 'tid'}, {'int': 'sig'}, {'siginfo_t*': 'info'}]),
    "perf_event_open": (298, [{'struct perf_event_attr*': 'attr'}, {'pid_t': 'pid'}, {'int': 'cpu'}, {'int': 'group_fd'}, {'unsigned long': 'flags'}]),
    "recvmmsg": (299, [{'int': 'sockfd'}, {'struct mmsghdr*': 'msgvec'}, {'unsigned int': 'vlen'}, {'int': 'flags'}, {'struct timespec*': 'timeout'}]),
    "fanotify_init": (300, [{'unsigned int': 'flags'}, {'unsigned int': 'event_f_flags'}]),
    "fanotify_mark": (301, [{'int': 'fanotify_fd'}, {'unsigned int': 'flags'}, {'u64': 'mask'}, {'int': 'dirfd'}, {'const char*': 'pathname'}]),
    "prlimit64": (302, [{'pid_t': 'pid'}, {'int': 'resource'}, {'const struct rlimit64*': 'new_limit'}, {'struct rlimit64*': 'old_limit'}]),
    "name_to_handle_at": (303, [{'int': 'dirfd'}, {'struct file_handle*': 'handle'}, {'int*': 'mount_id'}, {'int': 'flags'}]),
    "open_by_handle_at": (304, [{'int': 'mount_fd'}, {'struct file_handle*': 'handle'}, {'int': 'flags'}]),
    "clock_adjtime": (305, [{'const clockid_t': 'clk_id'}, {'struct timex*': 'buf'}]),
    "syncfs": (306, [{'int': 'fd'}]),
    "sendmmsg": (307, [{'int': 'sockfd'}, {'struct mmsghdr*': 'msgvec'}, {'unsigned int': 'vlen'}, {'int': 'flags'}]),
    "setns": (308, [{'int': 'fd'}, {'int': 'nstype'}]),
    "getcpu": (309, [{'unsigned int*': 'cpu'}, {'unsigned int*': 'node'}, {'struct getcpu_cache*': 'tcache'}]),
    "process_vm_readv": (310, [{'pid_t': 'pid'}, {'const struct iovec*': 'local_iov'}, {'unsigned long': 'liovcnt'}, {'const struct iovec*': 'remote_iov'}, {'unsigned long': 'riovcnt'}, {'unsigned long': 'flags'}]),
    "process_vm_writev": (311, [{'pid_t': 'pid'}, {'const struct iovec*': 'local_iov'}, {'unsigned long': 'liovcnt'}, {'const struct iovec*': 'remote_iov'}, {'unsigned long': 'riovcnt'}, {'unsigned long': 'flags'}]),
    "kcmp": (312, [{'pid_t': 'pid1'}, {'pid_t': 'pid2'}, {'int': 'type'}, {'unsigned long': 'idx1'}, {'unsigned long': 'idx2'}]),
    "finit_module": (313, [{'int': 'fd'}, {'const char*': 'param_values'}, {'int': 'flags'}]),
    "sched_setattr": (314, [{'pid_t': 'pid'}, {'struct sched_attr*': 'attr'}, {'unsigned int': 'flags'}]),
    "sched_getattr": (315, [{'pid_t': 'pid'}, {'struct sched_attr*': 'attr'}, {'unsigned int': 'size'}, {'unsigned int': 'flags'}]),
    "renameat2": (316, [{'int': 'olddirfd'}, {'const char*': 'oldpath'}, {'int': 'newdirfd'}, {'const char*': 'newpath'}, {'unsigned int': 'flags'}]),
    "seccomp": (317, [{'unsigned int': 'operation'}, {'unsigned int': 'flags'}, {'const void*': 'args'}]),
    "getrandom": (318, [{'void*': 'buf'}, {'size_t': 'buflen'}, {'unsigned int': 'flags'}]),
    "memfd_create": (319, [{'const char*': 'name'}, {'unsigned int': 'flags'}]),
    "kexec_file_load": (320, [{'int': 'kernel_fd'}, {'int': 'initrd_fd'}, {'unsigned long': 'cmdline_len'}, {'const char*': 'cmdline'}, {'unsigned long': 'flags'}]),
    "bpf": (321, [{'int': 'cmd'}, {'union bpf_attr*': 'attr'}, {'unsigned int': 'size'}]),
    "stub_execveat": (322, [{'int': 'dirfd'}, {'const char*const*': 'argv'}, {'const char*const*': 'envp'}, {'int': 'flags'}]),
    "userfaultfd": (323, [{'int': 'flags'}]),
    "membarrier": (324, [{'int': 'cmd'}, {'int': 'flags'}]),
    "mlock2": (325, [{'const void*': 'addr'}, {'size_t': 'len'}, {'int': 'flags'}]),
    "copy_file_range": (326, [{'int': 'fd_in'}, {'off_t*': 'off_in'}, {'int': 'fd_out'}, {'off_t*': 'off_out'}, {'size_t': 'len'}, {'unsigned int': 'flags'}]),
    "preadv2": (327, [{'int': 'fd'}, {'const struct iovec*': 'iov'}, {'unsigned long': 'iovcnt'}, {'unsigned long': 'pos_l'}, {'unsigned long': 'pos_h'}, {'int': 'flags'}]),
    "pwritev2": (328, [{'int': 'fd'}, {'const struct iovec*': 'iov'}, {'unsigned long': 'iovcnt'}, {'unsigned long': 'pos_l'}, {'unsigned long': 'pos_h'}, {'int': 'flags'}]),
    "pkey_mprotect": (335, [{'void*': 'addr'}, {'size_t': 'len'}, {'int': 'prot'}, {'int': 'pkey'}]),
    "pkey_alloc": (330, [{'unsigned int': 'flags'}, {'unsigned long': 'access_rights'}]),
    "pkey_free": (331, [{'int': 'pkey'}]),
    "statx": (332, [{'int': 'dirfd'}, {'int': 'flags'}, {'unsigned int': 'mask'}, {'struct statx*': 'statxbuf'}]),
    "rread_timestamp": (445, [ {"unsigned long long*": "timestamp"} ]),
    "rread_tsc": (446, [ {"unsigned long long*": "tsc"} ]),
    "rread_pmc": (447, [ {"int": "counter"}, {"unsigned long long*": "value"} ]),
    "rread_msr": (448, [ {"unsigned int": "counter"}, {"unsigned long long*": "value"} ]),
    "rread_cas": (449, [ {'unsigned int': 'box'}, {'unsigned int': 'channel'},{'unsigned int': 'type'}, {'unsigned long long*': 'cas'} ]),

    "rread_timestamp_diff": (450, [ {"unsigned long long* diff_timestamp"} ]),
    "rread_tsc_diff": (451, [ {"unsigned long long*": "diff_tsc"} ]),
    "rread_pmc_diff": (452, [ {"int": "counter"}, {"unsigned long long*": "diff_value"} ]),
    "rread_msr_diff": (453, [ {"unsigned int": "counter"}, {"unsigned long long*": "diff_value"} ]),
    "rread_cas_diff": (454, [ {'unsigned int': 'box'}, {'unsigned int': 'channel'},{'unsigned int': 'type'}, {'unsigned long long*': 'diff_cas'} ]),
    
    "rread_putuser_timestamp_diff": (455, [ {"unsigned long long*": "diff_value"} ]),
    "rread_putuser_tsc_diff": (456, [ {"unsigned long long*": "diff_value"} ]),
    "rread_putuser_pmu_diff": (457, [ {"int": "counter"}, {"unsigned long long*": "diff_value"} ]),
    "rread_putuser_msr_diff": (458, [ {"unsigned int": "counter"}, {"unsigned long long*": "diff_value"} ]),
    "rread_putuser_cas_diff": (459, [ {"unsigned int": "box"}, {"unsigned int": "channel"}, {"unsigned int": "type"}, {"unsigned long long*": "diff_value"} ])
}

CPU_OFF_EVENT_ID=-10
INTERVAL_CPU_EVENT_ID=-11

TYPE_ENTER=0
TYPE_EXIT=1
TYPE_NON_RETURN=2
TYPE_CPU_ON=3
TYPE_CPU_OFF=4

_idx_info = ["RAW_TYPE", "EVENT_NAME", "TID", "PID", "PPID", "PNAME"]
_idx_resource = ["CPU", "TIMESTAMP", "CPU_CYCLE", "RETIRED_INSTRUCTIONS", "ACTUAL_CPU_CYCLE", "UOPS_LOADS", "UOPS_STORES","RDCAS_0_0", "WRCAS_0_0", "RDCAS_0_1", "WRCAS_0_1", "RDCAS_1_0", "WRCAS_1_0", "RDCAS_1_1", "WRCAS_1_1"]
_idx_start_resource =[]
_idx_end_resource =[]
for x in _idx_resource:
    _idx_start_resource.append("START_" + x)
    _idx_end_resource.append("END_" + x)

_idx_exit_only = ["RETVAL", "ARG_1", "ARG_2", "ARG_3", "ARG_4", "ARG_5", "ARG_6", "BUF_CONTENT", "PATH_NAME"]
_idx_cpu_only = ["IDLE"]

# sys_enter
_idx_sys_enter = _idx_start_resource.copy()
_idx_sys_enter.extend(_idx_info)
_idx_sys_enter.extend(_idx_end_resource)
_idx_sys_enter_name = "IDX_SYS_ENTER"
IDX_SYS_ENTER = Enum(_idx_sys_enter_name, zip(_idx_sys_enter, count()))

# cpu on/off
_idx_cpu_onoff = _idx_start_resource.copy()
_idx_cpu_onoff.extend(_idx_info)
_idx_cpu_onoff.extend(_idx_cpu_only)
_idx_cpu_onoff.extend(_idx_end_resource)
_idx_cpu_onoff_name = "IDX_CPU_ONOFF"
IDX_CPU_ONOFF = Enum(_idx_cpu_onoff_name, zip(_idx_cpu_onoff, count()))

# sys_exit
_idx_sys_exit = _idx_start_resource.copy()
_idx_sys_exit.extend(_idx_info)
_idx_sys_exit.extend(_idx_exit_only)
_idx_sys_exit.extend(_idx_end_resource)
_idx_sys_exit_name = "IDX_SYS_EXIT"
IDX_SYS_EXIT = Enum(_idx_sys_exit_name, zip(_idx_sys_exit, count()))

def validate_file(f):
    if not os.path.exists(f):
        print("[Error] Invalid Input(", f, ")\n", file=sys.stderr)
        exit()
    return f

def get_inputs(input_path):
    result = []
    input_f = None
    try:
        input_f = open(input_path, "r")
    except:
        raise Exception("[Error] Invalid Input")

    while True:
        line = input_f.readline()
        if not line:
            break

        line = line[:-1] # remove '\n'
        splited = line.split("ㅣ")
        if len(splited) <= 1:
            continue
        
        result.append(splited)

    input_f.close()
    return result

def print_json(result_data):
    print(json.dumps(result_data))

def parse_item(raw, raw_type):
    item = {
        "rawType": raw_type,
        "processId": None,
        "threadId": None,
        "parentProcessId": None,
        "processName": None,
        "eventId": None,
        "eventName": None,
        "returnValue": None,
        "args": None,
        
        "startIdle": None,
        "endIdle": None,

        "startCPU": None,
        "timestamp": None,
        "startCycle": None,
        "startRetiredInst": None,
        "startActualCycle": None,
        "startUopsLoads": None,
        "startUopsStores": None,

        "endCPU": None,
        "endTimestamp": None,
        "endCycle": None,
        "endRetiredInst": None,
        "endActualCycle": None,
        "endUopsLoads": None,
        "endUopsStores": None,

        "startRDCAS_0_0": None,
        "startWRCAS_0_0": None,
        "endRDCAS_0_0": None,
        "endWRCAS_0_0": None,

        "startRDCAS_0_1": None,
        "startWRCAS_0_1": None,
        "endRDCAS_0_1": None,
        "endWRCAS_0_1": None,

        "startRDCAS_1_0": None,
        "startWRCAS_1_0": None,
        "endRDCAS_1_0": None,
        "endWRCAS_1_0": None,

        "startRDCAS_1_1": None,
        "startWRCAS_1_1": None,
        "endRDCAS_1_1": None,
        "endWRCAS_1_1": None,

        "overheadEnterCycle": None,
        "overheadEnterRetiredInst": None,
        "overheadEnterActualCycle": None,
        "overheadEnterUopsLoads": None,
        "overheadEnterUopsStores": None,

        "overheadExitCycle": None,
        "overheadExitRetiredInst": None,
        "overheadExitActualCycle": None,
        "overheadExitUopsLoads": None,
        "overheadExitUopsStores": None,

        "overheadEnterRDCAS_0_0": None,
        "overheadEnterWRCAS_0_0": None,
        "overheadEnterRDCAS_0_1": None,
        "overheadEnterWRCAS_0_1": None,
        "overheadEnterRDCAS_1_0": None,
        "overheadEnterWRCAS_1_0": None,
        "overheadEnterRDCAS_1_1": None,
        "overheadEnterWRCAS_1_1": None,

        "overheadExitRDCAS_0_0": None,
        "overheadExitWRCAS_0_0": None,
        "overheadExitRDCAS_0_1": None,
        "overheadExitWRCAS_0_1": None,
        "overheadExitRDCAS_1_0": None,
        "overheadExitWRCAS_1_0": None,
        "overheadExitRDCAS_1_1": None,
        "overheadExitWRCAS_1_1": None
    }

    if raw_type == TYPE_ENTER:
        IDX = IDX_SYS_ENTER
    elif raw_type == TYPE_EXIT:
        IDX = IDX_SYS_EXIT
    elif raw_type == TYPE_CPU_OFF or raw_type == TYPE_CPU_ON:
        IDX = IDX_CPU_ONOFF
    else:
        raise Exception(f"No such raw type: {raw_type}")

    # Get and save common info
    item["eventName"] = raw[IDX.EVENT_NAME.value]
    item["threadId"] = int(raw[IDX.TID.value])
    item["processId"] = int(raw[IDX.PID.value])
    item["parentProcessId"] = int(raw[IDX.PPID.value])
    item["processName"] = raw[IDX.PNAME.value]
    item["eventId"] = get_syscall_no(item["eventName"])

    # Get start metrics
    start_cpu = int(raw[IDX.START_CPU.value])
    start_ts = float(parse_ts_unit(raw[IDX.START_TIMESTAMP.value]))
    start_cpu_cycle = int(raw[IDX.START_CPU_CYCLE.value])
    start_retired_inst = int(raw[IDX.START_RETIRED_INSTRUCTIONS.value])
    start_actual_cpu_cycle = int(raw[IDX.START_ACTUAL_CPU_CYCLE.value])
    start_uops_loads = int(raw[IDX.START_UOPS_LOADS.value])
    start_uops_stores = int(raw[IDX.START_UOPS_STORES.value])
    start_rdcas_values = dict()
    start_wrcas_values = dict()
    for e in IDX:
        if "RDCAS" in e.name and "START" in e.name:
            parsed_name = remove_prefix(e.name)
            start_rdcas_values[parsed_name] = int(raw[e.value])
        if "WRCAS" in e.name and "START" in e.name:
            parsed_name = remove_prefix(e.name)
            start_wrcas_values[parsed_name] = int(raw[e.value])

    # Get start metrics
    end_cpu = int(raw[IDX.END_CPU.value])
    end_ts = float(parse_ts_unit(raw[IDX.END_TIMESTAMP.value]))
    end_cpu_cycle = int(raw[IDX.END_CPU_CYCLE.value])
    end_retired_inst = int(raw[IDX.END_RETIRED_INSTRUCTIONS.value])
    end_actual_cpu_cycle = int(raw[IDX.END_ACTUAL_CPU_CYCLE.value])
    end_uops_loads = int(raw[IDX.END_UOPS_LOADS.value])
    end_uops_stores = int(raw[IDX.END_UOPS_STORES.value])
    end_rdcas_values = dict()
    end_wrcas_values = dict()
    for e in IDX:
        if "RDCAS" in e.name and "END" in e.name:
            parsed_name = remove_prefix(e.name)
            end_rdcas_values[parsed_name] = int(raw[e.value])
        if "WRCAS" in e.name and "END" in e.name:
            parsed_name = remove_prefix(e.name)
            end_wrcas_values[parsed_name] = int(raw[e.value])
    
    
    # save resource info
    if raw_type == TYPE_ENTER or raw_type == TYPE_CPU_OFF:
        item["startCPU"] = start_cpu
        item["timestamp"] = start_ts
        item["startCycle"] = start_cpu_cycle
        item["startRetiredInst"] = start_retired_inst
        item["startActualCycle"] = start_actual_cpu_cycle
        item["startUopsLoads"] = start_uops_loads
        item["startUopsStores"] = start_uops_stores
        for parsed_name, value in start_rdcas_values.items():
            item["start" + parsed_name] = value
        for parsed_name, value in start_wrcas_values.items():
            item["start" + parsed_name] = value

        item["overheadEnterCycle"] = end_cpu_cycle - start_cpu_cycle
        item["overheadEnterRetiredInst"] = end_retired_inst - start_retired_inst
        item["overheadEnterActualCycle"] = end_actual_cpu_cycle - start_actual_cpu_cycle
        item["overheadEnterUopsLoads"] = end_uops_loads - start_uops_loads
        item["overheadEnterUopsStores"] = end_uops_stores - start_uops_stores
        for parsed_name in start_rdcas_values.keys():
            item["overheadEnter" + parsed_name] = end_rdcas_values[parsed_name] - start_rdcas_values[parsed_name]
        for parsed_name in start_wrcas_values.keys():
            item["overheadEnter" + parsed_name] = end_wrcas_values[parsed_name] - start_wrcas_values[parsed_name]

    elif raw_type == TYPE_EXIT or raw_type == TYPE_CPU_ON:
        item["endCPU"] = end_cpu
        item["endTimestamp"] = end_ts
        item["endCycle"] = end_cpu_cycle
        item["endRetiredInst"] = end_retired_inst
        item["endActualCycle"] = end_actual_cpu_cycle
        item["endUopsLoads"] = end_uops_loads
        item["endUopsStores"] = end_uops_stores
        for parsed_name, value in end_rdcas_values.items():
            item["end"+parsed_name] = value
        for parsed_name, value in end_wrcas_values.items():
            item["end"+parsed_name] = value

        item["overheadExitCycle"] = end_cpu_cycle - start_cpu_cycle
        item["overheadExitRetiredInst"] = end_retired_inst - start_retired_inst
        item["overheadExitActualCycle"] = end_actual_cpu_cycle - start_actual_cpu_cycle
        item["overheadExitUopsLoads"] = end_uops_loads - start_uops_loads
        item["overheadExitUopsStores"] = end_uops_stores - start_uops_stores
        for parsed_name in start_rdcas_values.keys():
            item["overheadExit" + parsed_name] = end_rdcas_values[parsed_name] - start_rdcas_values[parsed_name]
        for parsed_name in start_wrcas_values.keys():
            item["overheadExit" + parsed_name] = end_wrcas_values[parsed_name] - start_wrcas_values[parsed_name]

    # Get and save arg and retval
    if raw_type == TYPE_EXIT:
        args = []
        for i in range(1, 7):
            exec(f"arg{i} = raw[IDX_SYS_EXIT.ARG_{i}.value]")
            exec(f"args.append(arg{i})")

        buf = raw[IDX_SYS_EXIT.BUF_CONTENT.value]
        if buf == "NULL" or len(buf) == 0:
            buf = None

        pathname = raw[IDX_SYS_EXIT.PATH_NAME.value]
        if pathname  == "NULL" or pathname == "DIFF_MNTNS":
            pathname = None

        retval = int(raw[IDX_SYS_EXIT.RETVAL.value])

        item["args"] = do_syscall_arg_type_casting(item["eventName"], args, buf, pathname)
        item["returnValue"] = retval

    if raw_type == TYPE_CPU_OFF:
        item["startIdle"] = True if int(raw[IDX_CPU_ONOFF.IDLE.value]) == 0 else False

    if raw_type == TYPE_CPU_ON:
        item["endIdle"] = True if int(raw[IDX_CPU_ONOFF.IDLE.value]) == 0 else False

    return item

def sort_by_ts(data):
    return data.sort(key = lambda x: x["endTimestamp"] if x["timestamp"] is None else x["timestamp"])

def do_postprocessing(inputs):
    results_tid = dict()
    results = []

    for raw in inputs:
        raw_type = int(raw[IDX_SYS_ENTER.RAW_TYPE.value])
        if raw_type == TYPE_NON_RETURN:
            raise Exception("Occur Non-return evt")
        item = parse_item(raw, raw_type)

        tid = item["threadId"]
        if tid not in results_tid:
            results_tid[tid] = []

        results_tid[tid].append(item)


    for tid, items in results_tid.items():
        sort_by_ts(items)
        if not all( (items[i]["endTimestamp"] if items[i]["timestamp"] is None else items[i]["timestamp"]) < (items[i+1]["endTimestamp"] if items[i+1]["timestamp"] is None else items[i+1]["timestamp"]) for i in range(len(items)-1) ):
            raise Exception("results_tid: Not Sorted")
        
        enter_event = None
        off_event = None
        for item in items:
            if item["rawType"] == TYPE_ENTER:
                if enter_event != -1 and enter_event is not None:
                    raise Exception("There's no matched EXIT_EVENT")
                enter_event = item

            elif item["rawType"] == TYPE_CPU_OFF:
                if off_event != -1 and off_event is not None:
                    raise Exception("There's no matched ON_EVENT")
                off_event = item

            elif item["rawType"] == TYPE_EXIT:
                exit_event = item
                if enter_event is None:
                    continue
                elif enter_event == -1:
                    raise Exception("There's no matched ENTER_EVENT")

                for name, value in enter_event.items():
                    if value is not None:
                        exit_event[name] = value
                enter_event = -1
                del exit_event["rawType"]
                results.append(exit_event)
                
            elif item["rawType"] == TYPE_CPU_ON:
                on_event = item
                if off_event is None:
                    continue
                elif off_event == -1:
                    raise Exception("There's no matched OFF_EVENT")

                for name, value in off_event.items():
                    if value is not None:
                        on_event[name] = value
                off_event = -1
                del on_event["rawType"]
                results.append(on_event)
            else:
                raise Exception(f"Unrecognized rawType: {item['rawType']}")

    return results

def get_syscall_no(evt_name):
    if evt_name == "":
        return None
    if evt_name == "CPU_ON" or evt_name == "CPU_OFF":
        return CPU_OFF_EVENT_ID

    return syscalls[evt_name][0]

def get_syscall_arg_format(evt_name):
    if evt_name == "":
        return None
    return syscalls[evt_name][1]

def parse_ts_unit(ts):
    return float(str(str(ts)[:-9])+"."+str(str(ts)[-9:]))

def do_syscall_arg_type_casting(evt_name, args, buf, pathname):
    arg_format_list = get_syscall_arg_format(evt_name)

    # remove dummy arg
    goal_arg_len = len(arg_format_list)
    args = args[:goal_arg_len]

    # parse each arg
    for idx in range(len(args)):
        arg_format = arg_format_list[idx]
        arg_name = list(arg_format.values())[0]
        data_type = list(arg_format.keys())[0]
        args[idx] = {"name": arg_name, "value": args[idx]}

        try:
            if args[idx]["value"] == "":
                pass
            elif data_type == "int":
                args[idx]["value"] = c_int(int(args[idx]["value"])).value
            elif data_type == "unsigned int":
                args[idx]["value"] = c_uint(int(args[idx]["value"])).value
            elif data_type == "long":
                args[idx]["value"] = int(args[idx]["value"])
            elif data_type == "unsigned long":
                args[idx]["value"] = c_ulong(int(args[idx]["value"])).value
            elif data_type == "size_t":
                args[idx]["value"] = c_size_t(int(args[idx]["value"])).value
            elif "*" in data_type:
                args[idx]["value"] = "0x"+"%X"%int(args[idx]["value"])
            else:
                pass

        except Exception:
            pass

    if buf is not None:
        args.append({"name":"parsed-buf", "value": buf})     
    if pathname is not None:
        args.append({"name":"parsed-pathname", "value": pathname})

    return args

def remove_prefix(name):
    parsed_name = ""
    for n in name.split("_")[1:]:
        parsed_name += "_" + n
    parsed_name = parsed_name[1:]

    return parsed_name


def trim_by_time_limit(data, time_limit):
    start_ts = data[0]["timestamp"]
    for idx in range(len(data)):
        evt = data[idx]
        duration = evt["timestamp"] - start_ts
        if duration >= time_limit:
            return data[:idx]

def sig_hup_handler(signum, frame):
    exit()

if __name__ == "__main__":
    signal.signal(signal.SIGHUP, sig_hup_handler)
    
    parser =  ArgumentParser()
    parser.add_argument('-i', "--input", dest="input", required=True, type=validate_file, help="Input file")
    parser.add_argument('-t', "--time", dest="time", type=int, help="time limit(s)")

    args = parser.parse_args()

    inputs = get_inputs(args.input)
    
    data = do_postprocessing(inputs)
    # sort_by_ts(data)
    # if args.time is not None:
        # data = trim_by_time_limit(data, args.time)
    sort_by_ts(data)
    print_json(data)
