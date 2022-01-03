#!/bin/bash
SOURCE_DB_IP=XXX.XXX.XXX.XXX
DEST_DB_IP=XXX.XXX.XXX.XXX
TARGET_LIST=(smaller_proxima6_c1 smaller_proxima3_c1 buf100_proxima6_c1)
# mongoimport --host "$DATA_COLLECTOR_DB_IP:$DATA_COLLECTOR_DB_PORT" --authenticationDatabase admin --username $DB_AUTH_USERNAME --password $DB_AUTH_PASSWORD --db $DATA_COLLECTOR_DB_NAME --collection $i --file $DIR/result/$i --jsonArray

for db_name in ${TARGET_LIST[@]};do
    ITERATION=(1 2 3 4 5)
    if [ $db_name == "buf100_proxima6_c1" ];then
        ITERATION=(6 7 8 9 10)
    fi
    for iter in ${ITERATION[@]}; do
        db=${db_name}_${iter}

        collection_list=$(mongo --host "$SOURCE_DB_IP" --authenticationDatabase admin --username $DB_AUTH_USERNAME --password $DB_AUTH_PASSWORD --eval "db.getCollectionNames()" ${db})
        collection_list=`echo $collection_list | sed -E 's|[^\[]* ||' | sed -E 's|[,\["]||g'`
        collection_list=`echo ${collection_list%\]}`
        IFS=' ' read -r -a collection_list <<< "$collection_list"

        for collection in ${collection_list[@]}; do
            if [[ "$collection" == "filtered"* ]]; then    
                continue
            fi
            
            new_iter=$iter
            if [ $new_iter -gt 5 ];then 
                let new_iter-=5
            fi

	    mongodump --host $SOURCE_DB_IP --authenticationDatabase admin --username $DB_AUTH_USERNAME --password $DB_AUTH_PASSWORD -d $db -c $collection -o dumpfiles
        done
        mongorestore --authenticationDatabase admin --username $DB_AUTH_USERNAME --password $DB_AUTH_PASSWORD -d db_runner_${new_iter} dumpfiles/$db

	systemctl stop mongod
	systemctl start mongod
    done
done




# mongodump -d some_database -c some_collection

# zip some_database.zip some_database/* -r

# mongorestore -d some_other_db -c some_or_other_collection dump/some_collection.bson

