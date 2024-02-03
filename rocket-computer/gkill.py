#!/usr/bin/python3

# Utility to kill runs of groundstation.py

import subprocess
import signal
import os
import sys

defaultPhrase = "ground_recorder.py"

def findProcesses(phrase):
    result = []
    p = subprocess.run(["ps", "-a"], stdout = subprocess.PIPE)
    lines = str(p.stdout).split("\\n")
    for line in lines:
        if line.find("Python3") and line.find(phrase) >= 0:
            try:
                pid = int(line.split()[0])
                result.append(pid)
            except:
                pass
    return result

def run(name, args):
    if len(args) == 1 and args == '-h':
        print("Usage: %s PROGS" % name)
        return
    phrases = args if len(args) > 0 else [defaultPhrase]
    pcount = 0
    for phrase in phrases:
        plist = findProcesses(phrase)
        for pid in plist:
            try:
                os.kill(pid, signal.SIGKILL)
                print("Killed PID %d" % pid)
                pcount += 1
            except:
                print("Couldn't kill PID %d" % pid)
    print("Killed %d processes" % pcount)

if __name__ == "__main__":
    run(sys.argv[0], sys.argv[1:])
    sys.exit(0)

            
        
    
                        
