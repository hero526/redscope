#!/usr/bin/env python3
import sys, os
import csv
from argparse import ArgumentParser

IDX_DB_TYPE=0
IDX_OP_TYPE=1
IDX_RECORD_COUNT=2
IDX_RECORD_SIZE=3
IDX_CLIENT=4
IDX_INTERVAL=5
IDX_OP_COUNT=6
IDX_ITERATION=7
IDX_ARRIVAL_RATE=8
IDX_REQ=9
IDX_NON_IRREGULAR_REQ=10
IDX_METRIC=11

IDX_TO_PRINT=[
    IDX_DB_TYPE,
    IDX_OP_TYPE,
    IDX_RECORD_COUNT,
    IDX_RECORD_SIZE,
    IDX_CLIENT,
    IDX_OP_COUNT,
    IDX_ITERATION
]

IDX_PTRN_START = IDX_METRIC + 1

def validate_file(f_path):
    if not os.path.exists(f_path):
        raise Exception(f"Invalid Input({f_path})")

    f = open(f_path, 'r', encoding='utf-8')
    inputs = list(csv.reader(f))
    f.close()

    return inputs

if __name__ == "__main__":
    parser =  ArgumentParser()
    parser.add_argument("-i", "--input-file", dest="file", required=True, type=validate_file, help="input-file")
    parser.add_argument("--interval", dest="interval_thresholds", required=True, type=int, help="interval_thresholds")
    args = parser.parse_args()

    inputs = args.file
    interval_thresholds = args.interval_thresholds

    header = inputs[0]
    inputs = inputs[1:]

    header_ptrn = header[IDX_PTRN_START:]
    len_ptrn = len(header_ptrn)
    
    header_to_print = []
    for i in IDX_TO_PRINT:
        header_to_print.append(header[i])
    header_to_print.append(header[IDX_METRIC])
    header_to_print.extend(header_ptrn)
    header_str_to_print= ""
    for value in header_to_print:
        header_str_to_print += f",{value}"
    header_str_to_print = header_str_to_print[1:] # remove ,

    sum_per_expr_condition = dict()
    counter_per_expr_condition = dict()

    for line in inputs:
        expr_condition = ""
        metric = line[IDX_METRIC]
        ptrn_value = line[IDX_PTRN_START:]
        num_sample = int(line[IDX_NON_IRREGULAR_REQ])
        interval = int(line[IDX_INTERVAL])
        if interval < interval_thresholds:
            continue

        for idx in IDX_TO_PRINT:
            expr_condition += f',{line[idx]}'
        expr_condition = expr_condition[1:] # remove ,

        if sum_per_expr_condition.get(expr_condition) is None:
            sum_per_expr_condition[expr_condition] = dict()
            counter_per_expr_condition[expr_condition] = 0

        if sum_per_expr_condition[expr_condition].get(metric) is None:
            sum_per_expr_condition[expr_condition][metric] = [0] * len_ptrn

        counter_per_expr_condition[expr_condition] += num_sample

        for i in range(len(ptrn_value)):
            try:
                value = float(ptrn_value[i])
            except:
                value = 0
            sum_per_expr_condition[expr_condition][metric][i] += value * num_sample


    # print result
    print(header_str_to_print)
    for expr_condition in sum_per_expr_condition.keys():
        count = counter_per_expr_condition[expr_condition]
        metric_count = len(sum_per_expr_condition[expr_condition].keys())
        count = count/metric_count
        for metric, ptrn_value in sum_per_expr_condition[expr_condition].items():
            print(f"{expr_condition},{metric}", end="")
            for i in range(len(ptrn_value)):
                value = ptrn_value[i] / count
                print(f",{value}", end="")
            print()
    
