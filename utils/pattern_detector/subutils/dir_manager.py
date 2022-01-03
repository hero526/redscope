from subclasses.collector import MongoCTL

import os
import glob
from config import Config

def del_file(path):
    try:
        os.remove(path)
    except:
        pass

def del_files(path):
    tmp_files = glob.glob(path)
    for f in tmp_files:
        del_file(f)

def mkdirs(path):
    try:
        os.makedirs(path, exist_ok=True)
    except:
        pass

def clean(cfg):
    for db in cfg.dbs:
        del_files(f'{Config.RESULT_DIR}/*tmp')
        del_files(f'{Config.RESULT_DIR}/{db}/*tmp')
        del_file('record.log')

        mkdirs(f"{Config.RESULT_DIR}/{db}")

    if cfg.clean or cfg.delete:
        del_files(f'{Config.RESULT_DIR}/*.tsv')

    if cfg.clean:
        mongo_ctl_clean = MongoCTL()

        for db in cfg.dbs:
            del_file(f"{Config.RESULT_DIR}/{db}/idle_0_0_0_0.pickle")

            for target in cfg.targets:
                del_files(f"{Config.RESULT_DIR}/{db}/{target}.pickle")
        
                already_list = mongo_ctl_clean.get_collection_list(cfg.filtered_db_name, find=f"{db}_{target}", log=False)
                mongo_ctl_clean.drop_collections(cfg.filtered_db_name, already_list)
