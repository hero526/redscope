#!/bin/bash

SLACK_API="Slack API url"
SLACK_ERROR_API="Slack API url"

function send_start_slack_msg(){
    if $ENABLE_SLACK_ALARM ; then
        #Send start slack msg
        slack_msg="*[Start Experiments: ${DATA_COLLECTOR_DB_NAME}]*\n"
        slack_msg="${slack_msg}\t- _Iteration_\t${ITERATION}\n"
        slack_msg="${slack_msg}\t- _Request sizes_\t[ ${DBRUNNER_RECORD_SIZE_KBYTE[@]} ] \n"
        slack_msg="${slack_msg}\t- _Operation counts_\t[ ${OPERATION_COUNT[@]} ] \n"
        slack_msg="${slack_msg}\t- _Number of clients_\t[ ${NUM_CLIENT[@]} ] \n"
        slack_msg="${slack_msg}\t- _Workload type_\t[ ${WORKLOAD_TYPES[@]} ] \n"
        slack_msg="${slack_msg}\t- _Intervals_\t[ ${DBRUNNER_OPERATION_INTERVAL_MILLI_SEC[@]} ] \n"
        slack_msg="${slack_msg}\t- _Target databases_\t[ ${args[@]} ] \n"
        curl -X POST -H 'Content-type: application/json' --data "{\"text\":\"${slack_msg}\"}"  $SLACK_API >/dev/null 2>/dev/null
    fi
}
function send_end_slack_msg(){
    # curl -X POST -H 'Content-type: application/json' --data "{\"text\":\"*[End Experiments]* :partyparrot: \"}"  $SLACK_ERROR_API >/dev/null 2>/dev/null
    if $ENABLE_SLACK_ALARM ; then
        curl -X POST -H 'Content-type: application/json' --data "{\"text\":\"*[End Experiments]* :partyparrot: \"}"  $SLACK_API >/dev/null 2>/dev/null
    fi
}

function send_record_failed_slack_msg(){
    curl -X POST -H 'Content-type: application/json' --data "{\"text\":\"- _Record Failed_: (${DATA_COLLECTOR_DB_NAME}, ${result_file})\"}"  $SLACK_ERROR_API >/dev/null 2>/dev/null
}

function send_iteration_msg(){
    if $ENABLE_SLACK_ALARM ; then
        curl -X POST -H 'Content-type: application/json' --data "{\"text\":\"*[Iteration Done(${i}/${ITERATION})]* Elapsed time: $(($SECONDS / 60))m $(($SECONDS % 60))s \"}"  $SLACK_API >/dev/null 2>/dev/null
    fi
}

function send_wk_type_msg(){
    if $ENABLE_SLACK_ALARM ; then
        index_of ${wk_type} ${WORKLOAD_TYPES[@]} 
        idx=$?
        let diff=$end_time_for_wk_type-$start_time_for_wk_type
        curl -X POST -H 'Content-type: application/json' --data "{\"text\":\"*[Workload Type Done($(($idx+1))/${#WORKLOAD_TYPES[@]})]* Elapsed time: $(($diff / 60))m $(($diff % 60))s \"}"  $SLACK_API >/dev/null 2>/dev/null
    fi
}

function index_of(){
    target=$1
    array=($@)
    array=(${array[@]:1})
    idx=$(echo ${array[@]/$target//} | cut -d/ -f1 | wc -w | tr -d ' ')
    return $idx
}
