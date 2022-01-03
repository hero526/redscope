#!/bin/bash
# CONTROLLER. ROOT PRIVILEGE.

. $COMMON_CONF

NUM_CLIENTS=$1
DB_TYPE=$2
IP=$3
PORT=$4
DB_NAME=$5
OP_TYPE=$6
OP_COUNT=$7
RECORD_SIZE=$8
REUSE_CONNECTION=$9
OPERATION_INTERVAL_OPT_MILLI_SEC=${10}
COLLECTION_NAME=${11}
PUBLISHER_PORT=$(echo "($$ % 500) + 30000" | bc)

function hangup_handler(){
    exit 0
}
trap 'hangup_handler' HUP

mkdir -p $CLIENT_DIR/key_val_pickles
echo -1 >/tmp/dr_state
if ! ls -l $CLIENT_DIR/key_val_pickles/${NUM_CLIENTS}_${OP_COUNT}_${DUP_SELECT_RANGE}_* >/dev/null 2>&1 ;then
    echo -n "Creating key val..... "
    $CLIENT_DIR/key_val_generator.py $NUM_CLIENTS $OP_COUNT $DUP_SELECT_RANGE $CLIENT_DIR
    if [ $? -eq 0 ]; then
        echo "All Created"
    else
        echo "Failed to create key val"
        exit 1
    fi
fi

if [ $OP_TYPE == "idle" ]; then
    sleep ${OP_COUNT}s
    exit
else
    $CLIENT_DIR/client_publisher.py $PUBLISHER_PORT $NUM_CLIENTS $OP_COUNT $DATA_COLLECTOR_DB_NAME $COLLECTION_NAME $DATA_COLLECTOR_DB_IP $DATA_COLLECTOR_DB_PORT &
    sleep 1s
    
    node_num=0
    for client_no in $(seq 1 $NUM_CLIENTS); do
        node=$(echo "$node_num % ${#CLIENT_IPS[@]}" | bc)
        cmd="/home/$CLIENT_USER/client_subscriber.py $PUBLISHER_PORT $DB_TYPE $IP $PORT $client_no $NUM_CLIENTS $DB_NAME $OP_TYPE $OP_COUNT $DUP_SELECT_RANGE $RECORD_SIZE $REUSE_CONNECTION $OPERATION_INTERVAL_OPT_MILLI_SEC $CLIENT_DIR"
        if [[ "${CLIENT_IPS[$node]}" == "127.0.0.1" || "${CLIENT_IPS[$node]}" == "$(hostname -I)" ]];then
            $cmd &
        else
            ssh $CLIENT_USER@${CLIENT_IPS[$node]} $cmd &
        fi
        let node_num=$node_num+1
    done

    wait
fi
