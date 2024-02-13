#!/usr/local/bin/python3

# Analyze properties of flight from CSV representation of its log.

import csv
import sys
import numpy as np


class Evaluator:
#    Array of dictionaries built from CSV reader.  One entry per sample
#    All entries are text
    entries = []
    events = ["launch", "thrust-end", "apogee", "landing"]
    headings = ["row", "time", "altitude", "acceleration", "acceleration-X"]
    formats = ["%d", "%.3f", "%.3f", "%.3f", "%.3f"]

    def __init__(self, cfile):
        self.entries = []
        creader = csv.DictReader(cfile)
        for row in creader:
            self.entries.append(row)

    def count(self):
        return len(self.entries)

    def getField(self, row, kw):
        return self.entries[row][kw]

    def getIntField(self, row, kw):
        return int(self.getField(row, kw))

    def getFloatField(self, row, kw):
        return float(self.getField(row, kw))

    def getTimes(self):
        return [self.getFloatField(r, "time") for r in range(self.count())]

    def getAltitudes(self):
        return [self.getFloatField(r, "altitude") for r in range(self.count())]

    def getAccelerations(self):
        return [self.getFloatField(r, "acceleration") for r in range(self.count())]

    def getAccelerationXs(self):
        return [self.getFloatField(r, "acceleration-X") for r in range(self.count())]
    
    def findLaunch(self):
        accelerations = self.getAccelerations()
        for r in range(self.count()):
            if accelerations[r] > 1.5:
                return r
        return -1

    def findThrustEnd(self):
        accelerationXs = self.getAccelerationXs()
        rstart = self.findLaunch()
        if rstart < 0:
            return rstart
        apos = accelerationXs[rstart] > 0
        for r in range(rstart, self.count()):
            accel = accelerationXs[r]
            if apos and accel < 0 or not apos and accel > 0:
                return r
        return -1
        

    def findApogee(self):
        altitudes = self.getAltitudes()
        bestHeight = max(altitudes)
        for r in range(self.count()):
            if altitudes[r] == bestHeight:
                return r
        return -1

    def findLanding(self):
        altitudes = self.getAltitudes()
        rstart = self.findApogee()
        if rstart < 0:
            return rstart
        for r in range(rstart, self.count()):
            if altitudes[r] < 1.0:
                return r
        return -1

    # Generate dictionary of dictionaries show interesting events
    def highlights(self):
        times = self.getTimes()
        altitudes = self.getAltitudes()
        accelerations = self.getAccelerations()
        accelerationXs = self.getAccelerationXs()
        rlaunch = self.findLaunch()
        rtend = self.findThrustEnd()
        rapogee = self.findApogee()
        rlanding = self.findLanding()
        rows = [rlaunch, rtend, rapogee, rlanding]
        result = {}
        tstart = times[0] if rlaunch < 0 else times[rlaunch]
        hstart = altitudes[0] if rlaunch < 0 else altitudes[rlaunch]
        for idx in range(len(rows)):
            event = self.events[idx]
            r = rows[idx]
            entry = { self.headings[0] : r }
            if r < 0:
                vals = [None] * 4
            else:
                vals = [times[r]-tstart, altitudes[r]-hstart, accelerations[r], accelerationXs[r]]
            for i in range(4):
                entry[self.headings[i+1]] = vals[i]
            result[event] = entry
        return result

    def estring(self, event, h):
        entry = h[event]
        return [event] + [(self.formats[i] % entry[self.headings[i]]) for i in range(len(self.headings))]

    def showHighlights(self, h):
        print("\t".join(["event"] + self.headings))
        for event in self.events:
            es = self.estring(event, h)
            print("\t".join(es))
            
        
            
def process(file):
    e = Evaluator(file)
    h = e.highlights()
    e.showHighlights(h)

            
def run(name, args):
    infile = sys.stdin
    if len(args) == 1 and args[0] == '-h' or len(args) > 1:
        print("Usage: %s [-h] [INFILE]" % name)
        return
    if len(args) == 1:
        try:
            infile = open(args[0], 'r')
        except:
            print("Couldn't open file '%s'" % args[0])
            return
    process(infile)


if __name__ == "__main__":
    run(sys.argv[0], sys.argv[1:])
    sys.exit(0)
    
