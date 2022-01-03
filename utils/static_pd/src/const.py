DB_TYPE_MONGO="mongo"
DB_TYPE_MEMCACHED="memcached"
DB_TYPE_REDIS="redis"

MONGO_PTRN_CONN="Conn"
MONGO_PTRN_CONN_FLUSH="ConnFlush"
MONGO_PTRN_FLUSHER="Flusher"
MONGO_PTRN_MONGOD="Mongod"

FLUSH_PATH_NAME="/var/lib/mongodb/journal/WiredTigerLog"

MONGO_FLUSH_RETURN_BYTES=1152

MONGO_PNAME_CONN_1 = "conn"
MONGO_PNAME_CONN_2 = "listener"
MONGO_PNAME_FLUSHER = "WTJourn.Flusher"
MONGO_PNAME_MONGOD = "mongod"

TARGET_MONGO_PTRN_TYPE = [MONGO_PTRN_CONN, MONGO_PTRN_CONN_FLUSH, MONGO_PTRN_FLUSHER, MONGO_PTRN_MONGOD]

OP_TYPE_INSERT="insert"
OP_TYPE_SELECT="select"
OP_TYPE_DELETE="delete"
OP_TYPES = [OP_TYPE_INSERT, OP_TYPE_SELECT, OP_TYPE_DELETE]

EVT_ID_CPU_OFF = -10
EVT_ID_INTERVAL = -11

COLLECTION_FORMAT=["databaseType","operationType","recordCount","recordSize","client","interval(ms)","operationCount","iteration"]

ARRIVAL_RATE_DB_NAME="ARRIVAL_RATE"

COMMON_HEADER="database type,operation type,record count,record size,client,interval(ms),operation count,iteration,arrival rate"

CLIENT_IDX_NUM=4


PTRN_HEADER_REDIS=["EpollWait", "Interval(0)", "Read", "Interval(1)", "Read(-11)", "Interval(2)", "Write"]
PTRN_HEADER_MEMCACHED=["EpollWait", "Interval(0)", "Read", "Interval(1)", "Sendmsg"]
PTRN_HEADER_MONGO=["Recvmsg", "Interval(0)", "Recvmsg", "Interval(1)", "Sendmsg"]