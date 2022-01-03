# DB_NODE. ROOT PRIVILEGE.

function run(){
    mode=$1
    if [ $mode -eq 0 ];then # Default        
        ERROR_FILE=$RECORD_HOME/errors/dbrunner_errors.txt
    elif [ $mode -eq 1 ]; then # Idle
        ERROR_FILE=$RECORD_HOME/record/errors/idle_errors.txt
    else
        echo "Invalid mode: _runner.sh $mode "
        return 1
    fi

    monitoring_start_welldone=1
    monitoring_end_welldone=1
    monitoring_engine=${MONITORING_ENGINE,,}

    # Cleaning up
    drop_host_cache
    wait_db_termination all
    rm -f $result_file_path
    
    echo "**************************** $(basename ${result_file_path}) ********************************"
    ### START DB
    wait_db_start $target_db
    

    # DBRUNNER CMD Maker
    if [ $mode -eq 0 ]; then
        IP=$(eval echo \$${target_db^^}_IP)
        PORT=$(eval echo \$${target_db^^}_PORT)

        CONTROLLER="$CTRL_USER@$CTRL_IP"
        SSH_CONTROLLER="ssh $CONTROLLER "
        
        load_success=true
        run_success=true

        if [ $workload_type != "idle" ] && [ $workload_type != "insert" ] && [[ $record_count -gt 0 || $workload_type != "insert" ]];then
            if [ $record_count -lt $operation_count ];then
                record_count=$operation_count
            fi
            load_success=false

            echo -e "\n============== L O A D ($record_count) ================="
            client_cmd="bash $CLIENT_DIR/client.sh $num_client $target_db $IP $PORT $DB_NAME load $operation_count $record_size $reuse_connection $operation_interval_ms"
            $SSH_CONTROLLER "export COMMON_CONF=$COMMON_CONF; $client_cmd" &
            
            wait_until "[ \$(get_remote_pids $CONTROLLER client_subscriber.py | wc -l) -eq $num_client ]" 0 >/dev/null \
            && wait_until "[ \$(get_remote_pids $CONTROLLER client_publisher.py | wc -l) -eq 0 ]" 0 >/dev/null \
            && wait_until "[ \$(get_remote_pids $CONTROLLER client_subscriber.py | wc -l) -eq 0 ]" 0 >/dev/null \
            && load_success=true
            if ! $load_success;then
                kill_remote_process $CONTROLLER client_subscriber.py 1
                kill_remote_process $CONTROLLER client_publisher.py 1
            fi
            set +x
        fi
    fi

    if $LOAD_REBOOT && [[ ! " ${IN_MEMORY_DB[@]} " =~ " $target_db " ]] && ([ $workload_type == "select" ] || [ $workload_type == "delete" ]);then
        wait_db_termination $target_db
        wait_db_start $target_db
        sleep 3s
    fi
    

    # RUN

    if [ $mode -eq 0 ]; then
        if $load_success; then
            echo -e "\n============= R U N (${operation_count}) ================="
            run_success=false

            client_cmd="bash $CLIENT_DIR/client.sh $num_client $target_db $IP $PORT $DB_NAME $workload_type $operation_count $record_size $reuse_connection $operation_interval_ms $(basename $result_file_path)"
            $SSH_CONTROLLER "export COMMON_CONF=$COMMON_CONF; $client_cmd" &
            
            until [ $($SSH_CONTROLLER "cat /tmp/dr_state") == "-1" ] ; do
                sleep 1s
            done
            until [ $($SSH_CONTROLLER "cat /tmp/dr_state") == "1" ] ; do
                sleep .1s
            done
            
            ### START Monitoring Tool
            if [ $with_monitoring ];then
                if [[ $mode -eq 0 && $load_success ]];then
                    wait_${monitoring_engine}_start ${result_file_path} $target_db
                    monitoring_start_welldone=$?
                    if [ $monitoring_start_welldone -eq 0 ];then
                        kill_remote_process $CONTROLLER client_publisher.py 15
                        sleep $RECORD_TIME_SEC;
                        kill_remote_process $CONTROLLER client_publisher.py 15
                    else
                        echo -e "\033[0;33m"monitoring failed"\033[0m"
                    fi
                    
                    
                    wait_${monitoring_engine}_termination ${result_file_path}
                    monitoring_end_welldone=$?
                fi
            else
                # Actual record time
                sleep $RECORD_TIME_SEC;
            fi

            kill_remote_process $CONTROLLER client_subscriber.py 1
            kill_remote_process $CONTROLLER client_publisher.py 2

            wait_until "[ \$(get_remote_pids $CONTROLLER client_publisher.py | wc -l) -eq 0 ]" >/dev/null \
            && run_success=true
            if ! $run_success;then
                kill_remote_process $CONTROLLER client_publisher.py 1
            fi
        fi

    elif [ $mode -eq 1 ]; then
        echo -e "\n============= R U N (${idle_time}) ================="
        run_success=true
        wait_${monitoring_engine}_start ${result_file_path} $target_db
        monitoring_start_welldone=$?

        for ((i=0; i<$idle_time; i+=$IDLE_CHECK_STEP));do
            if [ $(ps -ef | grep $target_db | grep -v grep | wc -l) -eq 0 ];then
                run_success=false
                break
            fi
            sleep $IDLE_CHECK_STEP
        done

        wait_${monitoring_engine}_termination ${result_file_path}
        monitoring_end_welldone=$?
    fi

    sleep 2s
    # Cleaning up
    wait_db_termination $target_db
    drop_host_cache
    
    ## Get back owner of record directory
    sudo chown -R $RUAN_USER: $RECORD_HOME

    # Check result length
    if [ ${MONITORING_ENGINE} == "SYSTEMTAP" ];then
        result_len=$(cat $result_file_path.raw | wc -m)
        if [ $result_len -le 3 ]; then 
            echo "[RECORD ERROR]"
            echo "    ${result_file_path}.raw has error(len: $result_len)"
            monitoring_start_welldone=1
        fi
    fi

    # SUCCEED Case
    if [[ $monitoring_start_welldone -eq 0 && $monitoring_end_welldone -eq 0 && $run_success ]];then
        return 0
    fi

    return 1
}
