import os
import sys
import time

f = open('C:\\Users\\Nata\\Documents\\output.txt', 'w')
print(sys.argv[1], file=f)
pid = int(sys.argv[1])
print(pid, file=f)
while True:
    print('try kill', file=f)
    print(f'pid={pid}', file=f)
    try:
        print('start killing', file=f)
        os.kill(pid, 0)
        print('finish killing', file=f)
    except OSError:
        print('wake up', file=f)
        break
    else:
        print('wait', file=f)
print('after cycle', file=f)


os.system('\"' + sys.argv[2] + '\"')
print('update command line: ', sys.argv, file=f)
