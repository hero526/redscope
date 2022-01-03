
#!/bin/bash
DIR="$( cd "$( dirname "$0" )" && pwd -P)"

MONGO_IP="XXX.XXX.XXX.XXX" # Collector Database(MongoDB) IP

DB_NAME=U-FINAL-STAP_HOTH_24_1024_SSD
UK_TYPE=${DB_NAME::1}
UK_TYPE="U"

# DB_NAME=1-U-STAP_HOTH_24_1024_SSD
# UK_TYPE=${DB_NAME:2:1}

ITERATATON=1
RECORD_SIZE=(1)
OP_COUNT=(1000000)
RECORD_COUNT=1000000
CLIENTS=(40)
DB_TYPE=(memcached) # mongo memcached)

OP_TYPE=(insert) # select delete) 

INTERVAL=(140 120 70 52 40 34)
INTERVAL=(3000 800 500 340 220)
INTERVAL=(10 12 20 30)
INTERVAL=(3000 800 500 340 220 140 120 70 52 40)
INTERVAL=(120) # 800 500 340 220 140 120 70 52)
METRIC="ActualCycle,RetiredInst,RDCAS_0_0,WRCAS_0_0,RDCAS_0_1,WRCAS_0_1,RDCAS_1_0,WRCAS_1_0,RDCAS_1_1,WRCAS_1_1"

TRIM_SEC=3

REAL_PTRN_PRINT="t"
REAL_PTRN_PRINT="false"

OUTPUT_DIR="${DIR}/results/${DB_NAME}"

rm -rf $OUTPUT_DIR
mkdir -p $OUTPUT_DIR

echo "CONFIG = { 'UK_TYPE':'$UK_TYPE' }" > $DIR/src/config.py

function get_running_worker_count(){
    echo $(ps -ef | grep "[p]ython3 $DIR/src/main.py" | wc -l)
}

function wait_until_my_turn(){
    num_cpu_core=$(grep -c ^processor /proc/cpuinfo)
    while true; do
        if [ $(get_running_worker_count) -lt $num_cpu_core ]; then
            return
        fi
        sleep 1s
    done
}

function sort_and_remove_dup_line(){
    for f in $(ls -R $OUTPUT_DIR ); do
        if [[ $f == /* ]];then
            CUR_DIR=${f%:}
        else
            CUR_FILE=$CUR_DIR/$f
            if [ ! -d $CUR_FILE ]; then
                sed '$!N; /^\(.*\)\n\1$/!P; D' $CUR_FILE > $CUR_FILE.before
                mv $CUR_FILE.before $CUR_FILE

                if [[ $f == *"PtrnUsage"* ]]; then
                    csvsort -c 12,6 -r $CUR_FILE > $CUR_FILE.before 
                    mv $CUR_FILE.before $CUR_FILE
                elif [[ $f == *"UsageSum"* ]]; then
                    csvsort -c 6 -r $CUR_FILE > $CUR_FILE.before
                    mv $CUR_FILE.before $CUR_FILE
                fi
            fi
        fi
    done
}

function killall_worker(){
    kill -9 $(ps -ef | grep "[p]ython3 $DIR/src/main.py" | awk '{print $2}')
    exit 0
}

trap 'killall_worker' INT

for DB in $DB_NAME; do
    for op_type in ${OP_TYPE[@]}; do
        for client in ${CLIENTS[@]}; do
            for interval in ${INTERVAL[@]}; do 
                for record_size in ${RECORD_SIZE[@]}; do
                    for op_count in ${OP_COUNT[@]}; do
                        for iter in $(seq 1 $ITERATATON); do
                            for db_type in ${DB_TYPE[@]}; do
                                # wait_until_my_turn
                                col=${db_type}_${op_type}_${RECORD_COUNT}_${record_size}_${client}_${interval}_${op_count}_i${iter}
                                python3 $DIR/src/main.py -d ${DB} -c ${col} -m ${METRIC} --output-dir ${OUTPUT_DIR} -o ${db_type} --ip $MONGO_IP -r $REAL_PTRN_PRINT --trim $TRIM_SEC &
                                if [ $? -ne 0 ];then
                                    echo "src/main.py didn't succeed. exit!"
                                    #exit
                                fi
                            done
                            wait
                        done
                    done
                done
            done
        done
    done
done
wait 

sort_and_remove_dup_line
rm $DIR/${UK_TYPE}_db_sum.csv
for db_type in ${DB_TYPE[@]}; do
    cat $OUTPUT_DIR/$db_type/${db_type}UsageSum.csv >> $DIR/${UK_TYPE}_db_sum.csv
done

echo "[End Static PD]"
exit
