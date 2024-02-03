#!/usr/bin/python3

# Utility to kill runs of groundstation.py

import subprocess
import signal
import os
import sys

phrase = "ground_recorder.py"

def findProcesses():
    result = []
    p = subprocess.run(["ps", "-a"], stdout = subprocess.PIPE)
    lines = str(p.stdout).split("\\n")
    for line in lines:
        if line.find(phrase) >= 0:
            try:
                pid = int(line.split()[0])
                result.append(pid)
            except:
                pass
    return result

def run():
    pcount = 0
    plist = findProcesses()
    for pid in plist:
        try:
            os.kill(pid, signal.SIGKILL)
            print("Killed PID %d" % pid)
            pcount += 1
        except:
            print("Couldn't kill PID %d" % pid)
    print("Killed %d processes" % pcount)

if __name__ == "__main__":
    run()
    sys.exit(0)

            
        
    
                        
