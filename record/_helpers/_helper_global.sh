#!/bin/bash

function check_install_package(){
    command=$1
    package=$2

    dpkg -S `which $command` >/dev/null 2>/dev/null
    if [ $? -ne 0 ];then
        echo "Installing $package"
        sudo apt install $package >/dev/null 2>/dev/null && echo "$2 installed"
    fi
    return 0
}

function get_remote_pids(){
    runner=$1
    process_name=$2

    ssh $runner "ps -ef | grep $process_name | grep -v grep | awk '{print \$2}'" 2>/dev/null
}

function kill_remote_process(){
    runner=$1
    process_name=$2
    if [ -z $3 ];then
        signal=2
    else
        signal=$3
    fi
    ssh $runner "pkill -$signal -ef $process_name >/dev/null"
}

function check_port_open(){
	IP=$1
	PORT=$2
	bash -c "cat < /dev/null > /dev/tcp/$IP/$PORT" >/dev/null 2>&1
	if [ $? -eq 0 ];then
		true
	else
		false
	fi
}

function wait_until(){
    condition=$1
    if [ ! -z $2 ];then
        wait_sec=$2
    else
        wait_sec=$SKIP_WAIT_SEC
    fi
    if [ $wait_sec -eq 0 ];then
        wait_sec=36000
    fi
    
    until eval $condition; do
        echo "Waiting for $condition"
        sleep 1
        let timeout=$timeout+1
        if [ $timeout -gt $wait_sec ]; then
            echo -e "\033[0;31m""TIMEOUT""\033[0m"
            return 1
        fi
    done
    return 0
}

function drop_host_cache(){
    # DROP CACHES
    sudo su - -c "echo 3 > /proc/sys/vm/drop_caches; sync;"
}
