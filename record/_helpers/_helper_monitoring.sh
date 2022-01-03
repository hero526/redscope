# DB_NODE. ROOT PRIVILEGE.

. $HELEPERS_DIR/_helper_hwpmc.sh

function wait_systemtap_start(){
    result_file_path=$1
    target_db=$2
    raw_file_path="/tmp/raw_stap"

    stap_script_file_path=$SYSTEMTAP_SUBUTILS_DIR/stap_script/stap_script.stp
    stap_running_status="/tmp/stap_running"
    
    db_uid=$(getuid_byname $target_db)
    sed -i "s/global target_uid = [0-9]*$/global target_uid = $db_uid/g" $stap_script_file_path
    
    rm -f $result_file_path

    init_counter
    set_counter

    sleep 3s
    echo -1 | tee $stap_running_status >/dev/null

    sudo stap -b -s $RB_SIZE_MB -o $raw_file_path -DSTP_NO_OVERLOAD -D MAXSKIPPED=0 -D MAXTRYLOCK=1000000 -D MAXSTRINGLEN=10000 -D MINSTACKSPACE=8192 $stap_script_file_path 2>/dev/null &
    sleep 5s

    limit_time=30
    spend_time=0
    # num_of_cores=$(grep -c processor /proc/cpuinfo)
    while true; do
        if [ "$(cat $stap_running_status)" == "1" ];then
            echo -e "\033[0;33m"${MONITORING_ENGINE} monitoring started"\033[0m"
            return 0
        fi

        spend_time=$(( $spend_time + 2 ))
        if [ $spend_time -gt $limit_time ];then
            break
        fi
        sleep 2s
    done
    echo "SystemTap Initialization timeout"
    wait_systemtap_termination $result_file_path
    return 1
}

function wait_systemtap_termination(){
    result_file_path=$1
    raw_file_path="/tmp/raw_stap"
    stap_running_status="/tmp/stap_running"

    sudo killall -s INT stapio stap > /dev/null 2>/dev/null
    echo -e "\033[0;33m"${MONITORING_ENGINE} monitoring stopped "\033[0m"

    while true; do
        if [ "$(cat $stap_running_status)" == "0" ]; then
            break
        fi
        echo "Wait for systemTap logging before termination. wait 2s..."
        sleep 2s
    done

    unset_counter
    init_counter

    sleep 5s

    #stap-merge ${raw_file_path}* > $result_file_path.raw #2>/dev/null
    for result in `ls ${raw_file_path}_*`; do
        cat $result >> $result_file_path.raw
    done
    rm -rf ${raw_file_path}_*

    return 0
}

function wait_perf_start(){
    result_file_path=$1
    target_db=$2
    
    sleep 2s
    if [ $PERF_METRIC == cpu ];then
        echo -e "\033[0;33m"${MONITORING_ENGINE} start monitoring"\033[0m" \
        && sudo perf stat -x, -o ${result_file_path}.csv --per-core -a \
        -e cpu/event=0xC0,umask=0x00/$METRIC_SPACE,cpu/event=0x3C,umask=0x00/$METRIC_SPACE \
        -- sleep $RECORD_TIME_SEC >/dev/null 2>&1 \
        && echo -e "\033[0;33m"${MONITORING_ENGINE} monitoring stopped"\033[0m" &

    elif [ $PERF_METRIC == uops ];then
        echo -e "\033[0;33m"${MONITORING_ENGINE} start monitoring"\033[0m" \
        && sudo perf stat -x, -o ${result_file_path}.csv --per-core -a \
        -e cpu/event=0xD0,umask=0x81/$METRIC_SPACE,cpu/event=0xD0,umask=0x82/$METRIC_SPACE \
        -- sleep $RECORD_TIME_SEC >/dev/null 2>&1 \
        && echo -e "\033[0;33m"${MONITORING_ENGINE} monitoring stopped"\033[0m" &

    elif [ $PERF_METRIC == mem ];then
        echo -e "\033[0;33m"${MONITORING_ENGINE} start monitoring"\033[0m" \
        && sudo perf stat -x, -o ${result_file_path}.csv --per-core -a \
        -e uncore_imc_*/event=0x04,umask=0x03/,uncore_imc_*/event=0x04,umask=0x0c/ \
        -- sleep $RECORD_TIME_SEC >/dev/null 2>&1 \
        && echo -e "\033[0;33m"${MONITORING_ENGINE} monitoring stopped"\033[0m" &

    elif [ $PERF_METRIC == all ];then
        echo -e "\033[0;33m"${MONITORING_ENGINE} start monitoring"\033[0m" \
        && sudo perf stat -x, -o ${result_file_path}.csv --per-core -a \
        -e cpu/event=0xC0,umask=0x00/$METRIC_SPACE,cpu/event=0x3C,umask=0x00/$METRIC_SPACE,cpu/event=0xD0,umask=0x81/$METRIC_SPACE,cpu/event=0xD0,umask=0x82/$METRIC_SPACE,uncore_imc_*/event=0x04,umask=0x03/,uncore_imc_*/event=0x04,umask=0x0c/ \
        -- sleep $RECORD_TIME_SEC >/dev/null 2>&1 \
        && echo -e "\033[0;33m"${MONITORING_ENGINE} monitoring stopped"\033[0m" &

    else
        echo -e "\033[0;31m"Invalid $PERF_METRIC"\033[0;0m"
    fi

    return 0
}

function wait_perf_termination(){
    result_file_path=$1
    file=$(basename ${result_file_path})

    sleep 2s
    mongo --host "$DATA_COLLECTOR_DB_IP:$DATA_COLLECTOR_DB_PORT" --authenticationDatabase admin --username <user name> --password <user password> --eval "db[\"$file\"].drop()" $DATA_COLLECTOR_DB_NAME >/dev/null  # drop if exist
    mongoimport --host "$DATA_COLLECTOR_DB_IP:$DATA_COLLECTOR_DB_PORT" --authenticationDatabase admin --username <user name> --password <user password> --db $DATA_COLLECTOR_DB_NAME --collection $file \
    --type csv --file ${result_file_path}.csv --fields socket-d-core,thread,value,empty,eventName,eventMask,runtime,percent,opt1,opt2 \
    && echo "[Record Success]"
    return 0;
}

function wait_perfpid_start(){
    result_file_path=$1
    target_db=$2
    
    if [ $target_db == "redis" ];then
        pids=$(pgrep redis-server)
    elif [ $target_db == "memcached" ];then
        pids=$(pgrep memcached)
    elif [ $target_db == "mongo" ];then
        pids=$(pgrep mongod)
    fi

    sleep 2s

    if [ $PERF_METRIC == cpu ];then
        echo -e "\033[0;33m"${MONITORING_ENGINE} start monitoring"\033[0m" \
        && sudo perf stat -x, -o ${result_file_path}.csv --pid $pids  \
        -e cpu/event=0xC0,umask=0x00/$METRIC_SPACE,cpu/event=0x3C,umask=0x00/$METRIC_SPACE \
        -- sleep $RECORD_TIME_SEC >/dev/null 2>&1 \
        && echo -e "\033[0;33m"${MONITORING_ENGINE} monitoring stopped"\033[0m" &

    elif [ $PERF_METRIC == uops ];then
        echo -e "\033[0;33m"${MONITORING_ENGINE} start monitoring"\033[0m" \
        && sudo perf stat -x, -o ${result_file_path}.csv --pid $pids  \
        -e cpu/event=0xD0,umask=0x81/$METRIC_SPACE,cpu/event=0xD0,umask=0x82/$METRIC_SPACE \
        -- sleep $RECORD_TIME_SEC >/dev/null 2>&1 \
        && echo -e "\033[0;33m"${MONITORING_ENGINE} monitoring stopped"\033[0m" &

    elif [ $PERF_METRIC == all ];then
        echo -e "\033[0;33m"${MONITORING_ENGINE} start monitoring"\033[0m" \
        && sudo perf stat -x, -o ${result_file_path}.csv --pid $pids  \
        -e cpu/event=0xC0,umask=0x00/$METRIC_SPACE,cpu/event=0x3C,umask=0x00/$METRIC_SPACE,cpu/event=0xD0,umask=0x81/$METRIC_SPACE,cpu/event=0xD0,umask=0x82/$METRIC_SPACE \
        -- sleep $RECORD_TIME_SEC >/dev/null 2>&1 \
        && echo -e "\033[0;33m"${MONITORING_ENGINE} monitoring stopped"\033[0m" &

    elif [ $PERF_METRIC == both ];then
        echo -e "\033[0;33m"${MONITORING_ENGINE} start monitoring"\033[0m" \
        && sudo perf stat -x, -o ${result_file_path}.csv --pid $pids  \
        -e cpu/event=0xC0,umask=0x00/$METRIC_SPACE,cpu/event=0x3C,umask=0x00/$METRIC_SPACE,cpu/event=0xD0,umask=0x81/$METRIC_SPACE,cpu/event=0xD0,umask=0x82/$METRIC_SPACE \
        -- sleep $RECORD_TIME_SEC >/dev/null 2>&1 \
        && sudo perf stat -x, -o ${result_file_path}2.csv --per-core -a \
        -e uncore_imc_*/event=0x04,umask=0x03/,uncore_imc_*/event=0x04,umask=0x0c/ \
        -- sleep $RECORD_TIME_SEC >/dev/null 2>&1 \
        && cat ${result_file_path}2.csv >> ${result_file_path}.csv \
        && rm ${result_file_path}2.csv \
        && echo -e "\033[0;33m"${MONITORING_ENGINE} monitoring stopped"\033[0m" &

    else
        echo -e "\033[0;31m"Invalid $PERF_METRIC"\033[0;0m"
    fi

    return 0
}

function wait_perfpid_termination(){
    result_file_path=$1
    file=$(basename ${result_file_path})
    
    sleep 2s
    mongo --host "$DATA_COLLECTOR_DB_IP:$DATA_COLLECTOR_DB_PORT" --authenticationDatabase admin --username $DB_AUTH_USERNAME --password $DB_AUTH_PASSWORD --eval "db[\"$file\"].drop()" $DATA_COLLECTOR_DB_NAME >/dev/null  # drop if exist
    mongoimport --host "$DATA_COLLECTOR_DB_IP:$DATA_COLLECTOR_DB_PORT" --authenticationDatabase admin --username $DB_AUTH_USERNAME --password $DB_AUTH_PASSWORD --db $DATA_COLLECTOR_DB_NAME --collection $file \
    --type csv --file ${result_file_path}.csv --fields value,empty,eventName,eventMask,runtime,percent,opt1,opt2 \
    && echo "[Record Success]"
    return 0;
}
