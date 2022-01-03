import pickle


fw = open("see.txt", "w")

pdict_pname_col = data
for col, pdict_pname in pdict_pname_col.items():
    for pname, pdict in pdict_pname.items():
        fw.write(f"{col}, {pname}\n")
        for pt, pt_obj in pdict.items():
            tmp = [e for e in pt if e[1] >= 0]
            fw.write(f"{'['+str(pt_obj.remain)+']':5s} {tuple(tmp)}\n")


fw.close()