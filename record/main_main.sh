#!/bin/bash

cp ../config/common.conf ../config/common.conf.bak

# cp ../config/ksystemtap_common.conf ../config/common.conf
# ./main.sh dbrunner memcached

cp ../config/usystemtap_common.conf ../config/common.conf
./main.sh dbrunner memcached

cp ../config/cpu_perfpid_common.conf ../config/common.conf
./main.sh dbrunner memcached

# cp ../config/uops_perfpid_common.conf ../config/common.conf
# ./main.sh dbrunner redis memcached mongo

# cp ../config/perfpid_common.conf ../config/common.conf
# ./main.sh dbrunner redis memcached mongo

# cp ../config/perf_common.conf ../config/common.conf
# ./main.sh dbrunner redis memcached mongo

cp ../config/common.conf.bak ../config/common.conf
