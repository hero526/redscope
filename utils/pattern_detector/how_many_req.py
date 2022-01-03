import re
import sys

if len(sys.argv) < 2:
    print("put target e.g. redis_insert_1_1_8_pdict_pname_col.txt")
    exit(1)

data = sys.argv[1]
splitted_data = sys.argv[1].split('_')
target = '_'.join(splitted_data[0:2])

hint = "(1, 1, 'socket:[]', '192.168.122.200')"
rehint = "(1, 1, 'socket:\[\]', '192.168.122.200')"
answer = 0
found = 0

f = open(sys.argv[1], "r")

while True:
    line = f.readline()
    if not line: break

    if target in line:
        answer += int(line.split('_')[5])
        continue

    if hint in line:
        mult = int(line.split(' ')[0][1:-1])
        found += mult*len(re.findall(rehint, line))
        continue

f.close()

print(f"FOUND/ANSWER\n{found}/{answer}")

    
