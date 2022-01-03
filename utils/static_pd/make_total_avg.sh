
#!/bin/bash

INPUT_DIR=$1
GET_AVG_CMD="python3 ./get_total_avg.py"
INTERVAL_THRESHOLDS_FOR_MODEL=$2

if [ -z $1 ] || [  -z $2  ]; then
    echo "Invalid argument"
    echo "Need: (1)Input dir (2)interval thresholds for model data"
    exit 
fi

function processing_recursively(){
    for f in $(ls -R $OUTPUT_DIR ); do
        if [[ ${f: -1} == ":" ]];then
            CUR_DIR=${f%:}
        else
            CUR_FILE=$CUR_DIR/$f
            if [ ! -d $CUR_FILE ]; then
                if [[ $f == *"PtrnUsage"* ]];  then
                    if [[ $f == "total"* ]];then
                        continue
                    fi
                    $GET_AVG_CMD -i $CUR_FILE --interval $INTERVAL_THRESHOLDS_FOR_MODEL > ${CUR_DIR}/total_${INTERVAL_THRESHOLDS_FOR_MODEL}_$f
                fi
            fi
        fi
    done
}

processing_recursively