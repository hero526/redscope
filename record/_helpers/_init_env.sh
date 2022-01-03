. $COMMON_CONF
. $CONTAINER_UTILS_DIR/_db_start_stop_checker.sh
. $HELEPERS_DIR/_helper_global.sh
. $HELEPERS_DIR/_helper_hwpmc.sh

wait_db_termination all
unset_counter
init_counter
drop_host_cache