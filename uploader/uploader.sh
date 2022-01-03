#!/bin/bash

DIR="$( cd "$( dirname "$0" )" && pwd -P)"

function _exit(){
    exit 0
}
trap '_exit' INT

COMMON_CONF=$DIR/common.conf
. $COMMON_CONF
if [ ! -f $COMMON_CONF ]; then
    echo "Can't find common.conf in $COMMON_CONF"
    exit 1
fi

DONE_DIR=$DIR/$DATA_COLLECTOR_DB_NAME

mkdir -p $DONE_DIR
mkdir -p $UPLOADER_REQUEST

function parse_raw(){
    parse_path=$1
    python3 $DIR/raw_parser.py -i $parse_path -t $RECORD_TIME_SEC > $parse_path.json
    return 0
}

function import_mongo(){
    import_file=$1

    mongo --host "$DATA_COLLECTOR_DB_IP:$DATA_COLLECTOR_DB_PORT" --authenticationDatabase admin --username $DB_AUTH_USERNAME --password $DB_AUTH_PASSWORD --eval "db[\"$collection_name\"].drop()" $DATA_COLLECTOR_DB_NAME >/dev/null  # drop if exist
    mongoimport --host "$DATA_COLLECTOR_DB_IP:$DATA_COLLECTOR_DB_PORT" --authenticationDatabase admin --username $DB_AUTH_USERNAME --password $DB_AUTH_PASSWORD --db ${DATA_COLLECTOR_DB_NAME} --collection $collection_name --file $import_file --jsonArray 
    return 0
}

while true; do
    
    for result_file_path in $UPLOADER_REQUEST/*;do
        if [[ "$result_file_path" == "$UPLOADER_REQUEST/*" ]];then continue; fi

        collection_name=$(basename $result_file_path) \
        && new_location=$DONE_DIR/$collection_name \
        && mv $result_file_path $new_location \
        && parse_raw $new_location \
        && import_mongo $new_location.json &
        sleep 1s
    done

    sleep 5s
done
