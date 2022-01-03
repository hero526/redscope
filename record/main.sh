#!/bin/bash
# CONTROLLER. ROOT PRIVILEGE.

export DIR="$( cd "$( dirname "$0" )" && pwd -P)"
export COMMON_CONF=$DIR/../config/common.conf

if [ ! -f $COMMON_CONF ]; then
    echo "Can't find common.conf in $COMMON_CONF"
    exit 1
fi

. $COMMON_CONF
. $HELEPERS_DIR/_helper_global.sh
. $HELEPERS_DIR/_helper_main.sh
. $HELEPERS_DIR/_helper_slack.sh

# Checking root user
if [ $(id -u) -ne 0 ]; then
    echo "Please run with root user!"
    exit 0
fi

# Checking input argument
if [ $# -lt 2 ]; then 
    print_usage
    exit 0
fi

args=($@)
args=(${args[@]:1})

if [ $1 == "dbrunner" ] || [ $1 == "dbrunner-idle" ];then
    TARGET_CHECKLIST=(${DBRUNNER_TARGET_LIST[@]})
    record_script="dbrunner.sh true"

    if [ $1 == "dbrunner" ];then
        WORKLOAD_TYPES=(${DBRUNNER_WORKLOAD_TYPES[@]})
    elif [[ "$1" == *"idle"* ]];then
        WORKLOAD_TYPES=(idle)
        RECORD_NUM=0
        DBRUNNER_RECORD_SIZE_KBYTE=(0)
        DBRUNNER_OPERATION_INTERVAL_MILLI_SEC=(0)
    fi

    if [ $2 == "all" ]; then
        args=${DBRUNNER_TARGET_LIST[@]}
    fi
else
    echo "Wrong option $1"
    print_usage
    exit 0
fi

check_install_package mongo mongodb-clients
check_install_package rdmsr msr-tools

trap 'kill_runners' INT

COLLECTION_LIST=($(get_already_collection_list))

copy_files

send_start_slack_msg

# main loop
for ((i=1; i<=$ITERATION; i++)); do 
    SECONDS=0
    for req_size in ${DBRUNNER_RECORD_SIZE_KBYTE[@]}; do
        for op_count in ${OPERATION_COUNT[@]};do
            for num_cli in ${NUM_CLIENT[@]};do
                for wk_type in ${WORKLOAD_TYPES[@]};do
                    start_time_for_wk_type=$SECONDS
                    for interval in ${DBRUNNER_OPERATION_INTERVAL_MILLI_SEC[@]};do
                        for target_db in ${args[@]}; do
                            is_found=false
                            for target in ${TARGET_CHECKLIST[@]}; do
                                if [ $target_db == $target ];then
                                    is_found=true
                                    break
                                fi
                            done
                            
                            if [ $is_found == false ]; then
                                echo "(main) Invalid parameter: ${target_db}"
                            else
                                experiment=${target_db}_${wk_type}_${RECORD_NUM}_${req_size}_${num_cli}_${interval}_${op_count}_i${i}
                                if [[ " ${COLLECTION_LIST[@]} " =~ " \"$experiment\" " ]]; then
                                    echo -e "\e[32m" $experiment already exists "\e[0m"
                                    if $DO_NOT_RUN_DUPLICATED_EXPERIMENT;then
                                        continue
                                    fi
                                fi

                                IP=$(eval echo \$${target_db^^}_IP)
                                ssh root@${IP} "export COMMON_CONF=$COMMON_CONF; $RUNNERS_DIR/$record_script $target_db $wk_type $num_cli $interval $op_count $RECORD_NUM $i $req_size $DBRUNNER_REUSE_CONNECTION" &
                                runner_pid=$!
                                wait $runner_pid

                            fi
                        done
                    done
                    end_time_for_wk_type=$SECONDS
                    send_wk_type_msg
                done
            done
        done
    done
    send_iteration_msg
done

send_end_slack_msg
echo -n "End of experiment... "  && kill_runners

exit 0
