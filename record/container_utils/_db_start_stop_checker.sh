# DB_NODE. ROOT PRIVILEGE.

function getuid_byname(){
    _target_db=$1
    docker_runner="docker exec $_target_db "
    yb_uid=""
    if [ "$_target_db" == "couch" ];then
        db_uid=$($docker_runner id -u couchdb)
    elif [ "$_target_db" == "memcached" ];then
        db_uid=$($docker_runner id -u memcache)
    elif [ "$_target_db" == "mongo" ];then
        db_uid=$($docker_runner id -u mongodb)
    else
        db_uid=$($docker_runner id -u $_target_db)
    fi

    echo $db_uid
}

function container_manager(){
    cmd=$1
    container_name=$2
    
    if [ $cmd == "start" ];then
        docker-compose -f $NOSQL_DB_COMPOSE up -d $container_name >/dev/null 2>&1 \
        && return 0
    elif [ $cmd == "stop" ];then
        if [ $container_name == "all" ];then
            docker-compose -f $NOSQL_DB_COMPOSE down -v >/dev/null 2>&1 \
            && return 0
        else
            docker stop $container_name >/dev/null 2>/dev/null;
            docker rm -v $container_name >/dev/null 2>&1 \
            && return 0
        fi
    fi

    return 1
}

function wait_db_start(){
    _target_db=$1
    echo -en "\033[0;31m""$_target_db container "
    
	IP=$(eval echo \$${_target_db^^}_IP)
	PORT=$(eval echo \$${_target_db^^}_PORT)

    if ! container_manager start $_target_db ;then
        echo -e "failed to start""\033[0m"
        return 1
    fi

    sleep 1
    set +x
    wait_until "\$(check_port_open $IP $PORT)" \
    && echo -e "started""\033[0m"; return 0

    echo -e "start failed""\033[0m"
    return 1
}

function wait_db_termination(){
    _target_db=$1
    echo -en "\033[0;31m""$_target_db container "

    IP=$(eval echo \$${_target_db^^}_IP)
	PORT=$(eval echo \$${_target_db^^}_PORT)

    if ! container_manager stop $_target_db ;then
        echo -e "failed to terminated""\033[0m"
        return 1
    fi

    sleep 1
    wait_until "! \$(check_port_open $IP $PORT)" \
    && echo -e "terminated""\033[0m"; return 0

    echo -e "termination failed""\033[0m"
    return 1
}
