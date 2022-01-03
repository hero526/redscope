#!/bin/bash

function print_usage(){
    echo "Usage: ./main_runner.sh dbrunner all"
    echo "       ./main_runner.sh dbrunner-idle all"
    echo "       ./main_runner.sh dbrunner ${DBRUNNER_TARGET_LIST[@]}"
    
    printf "Target list: "
    for target in ${TARGET_LIST[@]}; do
        printf "$target "
    done 
    printf "\n"

    return 0
}

function kill_runners(){
    for target in ${args[@]}; do
        IP=$(eval echo \$${target^^}_IP)
        kill_remote_process root@${IP} runner
        if [ $MONITORING_ENGINE == "SYSTEMTAP" ];then
            kill_remote_process root@${IP} "stap"
            kill_remote_process root@${IP} "stapio"
        fi
    done

    for ip in ${CLIENT_IPS[@]};do
        if [ $ip == "127.0.0.1" ];then
            pkill -1 -f key_val_generator.py
            pkill -1 -f client_subscriber.py
            pkill -1 -f client_publisher.py
            pkill -1 -f raw_parser.py
        else
            kill_remote_process $CLIENT_USER@$ip key_val_generator.py 1
            kill_remote_process $CLIENT_USER@$ip raw_parser.py 1
            kill_remote_process $CLIENT_USER@$ip client_subscriber.py 1
            kill_remote_process $CLIENT_USER@$ip client_publisher.py 1
        fi
    done

    if [ ! -z $UPLOADER_IP ];then
        wait_until "[ \$(ssh $UPLOADER_USER@$UPLOADER_IP ls -l $UPLOADER_REQUEST | wc -l) -eq 1 ]"
        sleep 1s
        wait_until "[ \$(get_remote_pids $UPLOADER_USER@$UPLOADER_IP raw_parser.py | wc -l) -eq 0 ]" 0
        sleep 1s
        wait_until "[ \$(get_remote_pids $UPLOADER_USER@$UPLOADER_IP mongoimport | wc -l) -eq 0 ]" 0
        kill_remote_process $UPLOADER_USER@$UPLOADER_IP uploader
    fi

    ssh root@${IP} "export COMMON_CONF=$COMMON_CONF; $HELEPERS_DIR/_init_env.sh"
    echo "Done!"
    exit 0
}


function get_already_collection_list(){
    tmp=$(mongo $DATA_COLLECTOR_DB_NAME --host "$DATA_COLLECTOR_DB_IP:$DATA_COLLECTOR_DB_PORT" --authenticationDatabase admin --username $DB_AUTH_USERNAME --password $DB_AUTH_PASSWORD --eval "db.getCollectionNames()" --quiet)
    tmp=${tmp#[}
    tmp=${tmp%]}
    list=(`echo $tmp | tr "," "\n"`)
    echo ${list[@]}
    return 0
}

function copy_files(){
    for server in ${args[@]}; do
        # BASE FILE, CONFIG FILE, SYSTEMTAP TAPSET, CHANGE OWNER
        IP=$(eval echo \$${server^^}_IP)
        ssh root@${IP} "export COMMON_CONF=$COMMON_CONF; $HELEPERS_DIR/_init_env.sh"

        if ! ssh root@$IP "stat $RUAN_HOME >/dev/null 2>&1" ;then
            ssh root@$IP "mkdir -p $(dirname $RUAN_HOME) >/dev/null 2>&1" \
            && echo -n "Clone ruan.. " \
            && ssh root@$IP "git clone ssh://git@XXX.XXX.XXX.XXX:XXXXX/XXXXX/ruan.git $RUAN_HOME >/dev/null 2>&1" \ # Clone ruan git
            && echo "Done!"
        fi

        scp -r $HELEPERS_DIR $RUNNERS_DIR $CONTAINER_UTILS_DIR $SYSTEMTAP_SUBUTILS_DIR root@$IP:$RECORD_HOME > /dev/null \
        && scp $SYSTEMTAP_SUBUTILS_DIR/stap_tapset/timestamp.stp $SYSTEMTAP_SUBUTILS_DIR/stap_tapset/task.stp root@$IP:$SYSTEMTAP_TAPSET_DIR/linux > /dev/null \
        && scp $COMMON_CONF root@$IP:$COMMON_CONF > /dev/null \
        && ssh root@$IP "chown -R $RUAN_USER: $RUAN_HOME" > /dev/null \
        && echo "Copied to $server" &
    done

    for client in ${CLIENT_IPS[@]}; do
        if [ $client != "127.0.0.1" ];then
            scp $CLIENT_DIR/client_subscriber.py $CLIENT_DIR/requirements.txt $CLIENT_USER@$client:/home/$CLIENT_USER/ > /dev/null \
            && ssh $CLIENT_USER@$client "pip3 install -r /home/$CLIENT_USER/requirements.txt" > /dev/null 2>&1 \
            && echo "Copied to $client for CLIENT" &
        fi
        if [ $client == "127.0.0.1" ];then
            cp $CLIENT_DIR/client_subscriber.py $CLIENT_DIR/requirements.txt /home/$CLIENT_USER/ > /dev/null \
            && pip3 install -r /home/$CLIENT_USER/requirements.txt >/dev/null 2>&1 \
            && echo "Copied to localhost for CLIENT" &
        fi
    done

    wait

    if [ ! -z $UPLOADER_IP ];then
        echo "Uploader detected! $UPLOADER_USER $UPLOADER_IP" \
        && scp -r $UPLOADER_DIR $UPLOADER_USER@$UPLOADER_IP:~ >/dev/null 2>&1 \
        && scp $COMMON_CONF $UPLOADER_USER@$UPLOADER_IP:$UPLOADER_HOME >/dev/null 2>&1 \
        && scp $SYSTEMTAP_SUBUTILS_DIR/stap_result_parser/raw_parser.py $UPLOADER_USER@$UPLOADER_IP:$UPLOADER_HOME >/dev/null 2>&1 \
        && ssh $UPLOADER_USER@$UPLOADER_IP "bash $UPLOADER_HOME/uploader.sh >/dev/null 2>/dev/null" &
    fi

    ssh root@${IP} "rm -rf $RECORD_HOME/result"
}
