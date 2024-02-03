#!/usr/bin/python3
# Support for GUI to visualize rocket telemetry data

import tkinter
import math
import sys
import getopt

import ground_recorder

class Grapher:
    sampler = None
    tk = None
    canvas = None
    keywords = []
    # Sequence of values for each keyword
    samples = {}
    minTime = 0.0
    maxTime = 0.0
    yMin = 0.0
    yMax = 0.0

    
    # Configuration parameters
    duration = 10
    width = 1000
    height = 400

    def __init__(self, tk, sampler, keywords):
        self.sampler = sampler
        self.tk = tk
        self.keywords = keywords
#        self.canvas = Tkinter.Canvas(self.tk)
#        self.canvas.config(width=self.width, height=self.height)
        # For each keyword, have list of (t,y) values
        self.samples = { k : [] for k in self.keywords}
        self.minTime = 0.0
        self.maxTime = 0.0
        self.yMin = 0.0
        self.yMax = 0.0

    def roundRange(self, val, lower = True):
        if lower and val >= 0:
            return 0.0
        if not lower and val <= 0:
            return 0.0
        neg = val < 0
        val = abs(val)
        rval = 1.0
        while (val >= 10.0):
            rval *= 10
            val = val / 10.0
        # val is now in [0.0, 10.0)
        if val <= 1.0:
            pass
        elif val <= 2.0:
            rval *= 2.0
        elif val <= 5.0:
            rval *= 5.0
        else:
            rval *= 10.0
        return -rval if neg else rval
    
    def normalizeSamples(self):
        tmax = 0.0
        for k in self.keywords:
            for (t,y) in self.samples[k]:
                tmax = max(t, tmax)
        self.maxTime = max(self.duration, math.ceil(tmax))
        self.minTime = self.maxTime - self.duration
        for k in self.keywords:
            nsamples = [(t,y) for (t,y) in self.samples[k] if t >= self.minTime]
            self.samples[k] = nsamples
        ymin = 1e6
        ymax = -1e6
        for k in self.keywords:
            for (t,y) in self.samples[k]:
                ymin = min(ymin, y)
                ymax = max(ymax, y)
        self.yMin = self.roundRange(ymin, lower=True)
        self.yMax = self.roundRange(ymax, lower=False)
        self.sampler.report(3, "Setting ranges %.1f .. %.1f, %.1f .. %.1f" % (self.minTime, self.maxTime, self.yMin, self.yMax))
        
    def display(self):
        self.normalizeSamples()
        if self.sampler.verbosity >= 3:
            self.sampler.report(3, "T left = %.1f" % self.minTime)
            for k in self.keywords:
                s = "  " + k + ":"
                for (t,y) in self.samples[k]:
                    s += " %.2f,%.1f" % (t,y)
                self.sampler.report(3, s)

    def addRecord(self, r):
        self.sampler.report(3, "Adding record with time stamp %.3f" % r.timeStamp)
        for k in self.keywords:
            y = r.getField(k)
            t = r.timeStamp
            if y is not None:
                self.samples[k].append((t,y))
        self.display()

class Display:
    sampler = None
    tk = None
    accelerationGrapher = None
    altitudeGrapher = None

    def __init__(self, sampler):
        self.sampler = sampler
#        self.tk = Tkinter.tk()
        self.accelerationGrapher = Grapher(self.tk, self.sampler, ["Acceleration", "X-Acceleration"])
#        self.accelerationGrapher.canvas.pack(side=Tkinter.TOP)
#        self.accelerationGrapher.canvas.update()
        self.altitudeGrapher = Grapher(self.tk, self.sampler, ["Altitude"])
#        self.altitudeGrapher.canvas.pack(side=Tkinter.BOTTOM)
#        self.altitudeGrapher.canvas.update()

    def run(self):
        while True:
            tup = self.sampler.getNextSampleTuple()
            if tup is None:
                print("Exiting")
                return
            r = ground_recorder.formatSample(tup, self.sampler)
            if r is None:
                break
            self.accelerationGrapher.addRecord(r)
            self.altitudeGrapher.addRecord(r)
        

def run(name, args):
    port = None
    baud = 115200
    retries = 10
    verbosity = 3
    senderId = None

    optList, args = getopt.getopt(args, "hv:p:b:t:s:")
    for (opt, val) in optList:
        if opt == '-h':
            ground_recorder.usage(name)
            return
        elif opt == '-v':
            verbosity = int(val)
        elif opt == '-p':
            try:
                pnum = int(val)
                port = devPrefix + str(pnum)
            except:
                port = val
        elif opt == '-b':
            baud = int(val)
        elif opt == '-t':
            retries = int(val)
        elif opt == '-s':
            senderId = val

    if port is None:
        plist = ground_recorder.findPorts()
        if len(plist) == 0:
            print("Can't find any devices starting with names '%s'" % devPrefix)
            return
        elif len(plist) == 1:
            port = plist[0]
        elif len(plist) == 2:
            print("Ambiguous port.  Candidates are:")
            for p in plist:
                print("  %s" % p)
            return

    sampler = ground_recorder.Sampler(port, baud, senderId, verbosity, retries)
    display = Display(sampler)
    display.run()

    
if __name__ == "__main__":
    run(sys.argv[0], sys.argv[1:])
    sys.exit(0)
    
