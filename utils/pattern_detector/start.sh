#!/bin/bash

for db_name in YC_KAMINO_8_16_HDD; do
    for target in mongo memcached redis; do
        for operation in "insert" "select" "delete"; do
            for client in 4 8 12 16 20 24; do
                for req_size in 1; do
                    python3 ./main.py -d $db_name -t $target -w $operation -s $req_size -c $client --clean
                done
            done
        done
    done
done
