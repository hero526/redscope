#!/bin/bash

DIR="$( cd "$( dirname "$0" )" && pwd -P)"

filename=$1
for sysname in $(cat ./$filename); do
    python3 $DIR/args_parser.py $sysname "num+name+comment"
done