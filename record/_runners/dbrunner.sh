#!/bin/bash
# DB_NODE. ROOT PRIVILEGE.

function _exit(){
    exit 0
}
trap '_exit' INT

. $COMMON_CONF

. $HELEPERS_DIR/_helper_global.sh
. $HELEPERS_DIR/_helper_slack.sh

. $CONTAINER_UTILS_DIR/_db_start_stop_checker.sh
. $HELEPERS_DIR/_helper_monitoring.sh
. $RUNNERS_DIR/_runner.sh

with_monitoring=$1
target_db=$2
workload_type=$3
num_client=$4
operation_interval_ms=$5
operation_count=$6
record_count=$7
iter=$8
record_size=$9
reuse_connection=${10}

if  ! [[ $1 || $1 == "false" ]] ; then
    echo "Wrong record options $1 => the first arg must be true or false"
    exit
fi

if [ ! -d $RECORD_HOME/result/fin ];then
    sudo su - $CTRL_USER -c "mkdir -p $RECORD_HOME/result/fin"
fi

result_file=${target_db}_${workload_type}_${record_count}_${record_size}_${num_client}_${operation_interval_ms}_${operation_count}_i${iter}
result_file_path=$RECORD_HOME/result/$result_file

if [ $num_client -ne 0 ];then
    run 0
    result=$?
elif [ $num_client -eq 0 ];then
    idle_time=$operation_count
    run 1
    result=$?
else
    echo "Error! There is no workload_type type $workload_type in dbrunner.sh"
    result=1
    exit 1
fi

if [ $result -eq 0 ] && [ $with_monitoring ]; then
    if [[ $MONITORING_ENGINE != "PERF"* ]]; then
        echo "[Record Success]"
        # Backup raw files
        mkdir -p $RAW_BACKUP_DIR/$DATA_COLLECTOR_DB_NAME
        cp $result_file_path.raw $RAW_BACKUP_DIR/$DATA_COLLECTOR_DB_NAME

        if [ ! -z $UPLOADER_IP ];then
            scp $result_file_path.raw $UPLOADER_USER@$UPLOADER_IP:$UPLOADER_REQUEST/$result_file && mv $result_file_path.raw $RECORD_HOME/result/fin
        else
            python3 $SYSTEMTAP_SUBUTILS_DIR/stap_result_parser/raw_parser.py -i $result_file_path.raw -t ${RECORD_TIME_SEC} > $result_file_path.json

            mongo --host "$DATA_COLLECTOR_DB_IP:$DATA_COLLECTOR_DB_PORT" --authenticationDatabase admin --username $DB_AUTH_USERNAME --password $DB_AUTH_PASSWORD --eval "db[\"$result_file\"].drop()" $DATA_COLLECTOR_DB_NAME >/dev/null  # drop if exist
            mongoimport --host "$DATA_COLLECTOR_DB_IP:$DATA_COLLECTOR_DB_PORT" --authenticationDatabase admin --username $DB_AUTH_USERNAME --password $DB_AUTH_PASSWORD --db ${DATA_COLLECTOR_DB_NAME} --collection $result_file --file $result_file_path.json --jsonArray 
            mv $result_file_path* $RECORD_HOME/result/fin
        fi
    fi
else
    send_record_failed_slack_msg
fi

sudo chown -R $RUAN_USER: $RECORD_HOME
exit 0
