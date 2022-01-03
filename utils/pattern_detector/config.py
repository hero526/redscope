import sys
import logging
import argparse
import itertools

class Config:
    COLLECTOR_USER_ID = "XXXXX" # Collector Database(MongoDB) Username
    COLLECTOR_USER_PW = "XXXXXXXX" # Collector Database(MongoDB) Password
    COLLECTOR_IP = "XXX.XXX.XXX.XXX" # Collector Database(MongoDB) IP address
    COLLECTOR_PORT = XXXXX # Collector Database port number
    CLIENT_IP = ["192.168.122.190", "192.168.122.191"] # TODO: maybe..? IMPLEMENTATION NOT COMPLETED

    RESULT_DIR = "results"

    def __init__(self):
        dbg_levels=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        corrleation_levels=["CONSTANT", "NEGATIVE", "NEGLIGIBLE", "POSITIVE", "OBVIOUS_POSITIVE", "STRONG_POSITIVE", "PERFECT_POSITIVE"]

        parser = argparse.ArgumentParser()
        parser.add_argument('-d', "--dbname",       dest="dbname", required=True, type=str, help="Data source")
        parser.add_argument('-t', "--target",       dest="targets", required=False, default="*", type=str, nargs='+', help="Target names")
        parser.add_argument('-w', "--workload",     dest="workloads", required=False, default="*", type=str, nargs='+', help="Workload types")
        parser.add_argument('-r', "--record",       dest="records", required=False, default="*", type=str, nargs='+', help="Record counts")
        parser.add_argument('-s', "--recordsize",   dest="rc_sizes", metavar='sizes', required=False, default="*", type=str, nargs='+', help="Record sizes")
        parser.add_argument('-c', "--client",       dest="clients", required=False, default="*", type=str, nargs='+', help="Client nums")
        parser.add_argument('-ms', "--intervalms", dest="intervalms", required=False, default="*", type=str, nargs='+', help="Request interval microseconds")

        parser.add_argument('-f', "--filter",       dest="filter_dbname", metavar='filterDB', required=False, type=str, default="", help="Filtering DB destination")
        parser.add_argument('-i', "--idle",         dest="idle_dbname", metavar='idleDB', required=False, type=str, default="", help="Idle DB source")

        parser.add_argument('-l', "--log",          dest="loglevel", metavar='level', required=False, type=str.upper, default="INFO", choices=dbg_levels, help="Set log level")
        parser.add_argument('-co', "--correlation", dest="correlation", required=False, type=str.upper, default="PERFECT_POSITIVE", choices=corrleation_levels, help="Threshold for Spearman correlation")
        # parser.add_argument('-ip', "--client-ip",   dest="client_ips", metavar='clientIP', required=False, type=str, nargs='+', default="", help="Client IP addresses")

        parser.add_argument("--delete",             dest="delete", required=False, default=False, type=type(True), nargs='?', help="Delete result files")
        parser.add_argument('--clean',              dest="clean", required=False, default=False, type=type(True), nargs='?', help="clean all and run")

        args = parser.parse_args()

        self.db_name = args.dbname

        if len(args.filter_dbname) == 0:
            self.filtered_db_name = f"FILTERED-{self.db_name}"
        else:
            self.filtered_db_name = args.filter_dbname
        
        if len(args.idle_dbname) == 0:
            self.idle_db_name = "IDLE_HOTH_8_32_SSD"
        else:
            self.idle_db_name = args.idle_dbname


        if args.targets == "*":
            self.dbs = ["riak", "couchbase", "elasticsearch", "mongo", "redis", "cassandra", "memcached", "neo4j", "mysql", "level", "rocks", "couch", "hbase"]
        else:
            self.dbs = args.targets
        
        if args.workloads == "*":
            self.workloads=["a", "b", "c", "d", "e", "f", "insert", "delete", "select"]
        else:
            self.workloads = args.workloads
        
        self.records = args.records
        self.rc_sizes = args.rc_sizes
        self.clients = args.clients
        self.intervalms = args.intervalms

        self.targets = []
        for x in list(itertools.product(self.workloads, self.records, self.rc_sizes, self.clients,  self.intervalms)):
            self.targets.append('_'.join(x))
        
        self.targets_with_db = []
        for x in list(itertools.product(self.dbs, self.targets)):
            self.targets_with_db.append('_'.join(x))

        self.spearman_threshold = args.correlation
        
        self.loglevel = getattr(logging, args.loglevel, None)
        self.clean = True if args.clean is None else False
        self.delete = True if args.delete is None else False

        
