#!/usr/local/bin/python3
# Support for GUI to visualize rocket telemetry data

from tkinter import *
import math
import sys
import getopt

import recorder

def usage(prog):
    print("Usage: %s [-h] [-L] [-v VERB] [-p PORT] [-b BAUD] [-t TRIES] [-s SID] [-k BSIZE] [-y YMAX]" % prog)
    print("  -h      Print this message")
    print("  -L      Disable logging")
    print("  -v VERB Set verbosity")
    print("  -p PORT Specify serial port on /dev")
    print("  -b BAUD Set serial interface baud rate")
    print("  -t TRY  Specify number of tries in opening serial port")
    print("  -k BUF  Buffer with up to BUF samples")

# Useful widgets
class TextTracker:
    parent = None
    canvas = None
    minField = None
    curField = None
    maxField = None
    minValue = None
    maxValue = None
    pad = 20
    tagWidth = 15
    labelWidth = 100
    labelHeight = 25

    def __init__(self, parent, title):
        offset = self.pad + self.tagWidth + self.labelWidth
        width = offset + self.pad
        self.parent = parent
        self.canvas = Canvas(self.parent, width=width, height=4.0*self.labelHeight)
        self.canvas.pack(side=TOP)
        outline = self.canvas.create_rectangle((0,0), (width, 4.0*self.labelHeight), fill="white", outline = "")
        self.title = self.canvas.create_text((width/2, 0.5*self.labelHeight), text=title, fill="black")
        self.minLabel = self.canvas.create_text((self.pad,1.5*self.labelHeight), text="MIN:", anchor="w", fill="blue")
        self.minField = self.canvas.create_text((offset, 1.5*self.labelHeight), text="---", anchor="e", fill="black")
        self.curLabel = self.canvas.create_text((self.pad,2.5*self.labelHeight), text="CUR:", anchor="w", fill="red")
        self.curField = self.canvas.create_text((offset, 2.5*self.labelHeight), text="---", anchor="e", fill="black")
        self.maxLabel = self.canvas.create_text((self.pad,3.5*self.labelHeight), text="MAX:", anchor="w", fill="blue")
        self.maxField = self.canvas.create_text((offset, 3.5*self.labelHeight), text="---", anchor="e", fill="black")

    def reset(self):
        self.minValue = None
        self.maxValue = None
        self.canvas.itemconfigure(self.minField, text="---")
        self.canvas.itemconfigure(self.maxField, text="---")
        self.canvas.update()

    def update(self, value):
        svalue = "%.2f" % value
        if self.minValue is None or self.minValue > value:
            self.minValue = value
            self.canvas.itemconfigure(self.minField, text = svalue)
        self.canvas.itemconfigure(self.curField, text = svalue)
        if self.maxValue is None or self.maxValue < value:
            self.maxValue = value
            self.canvas.itemconfigure(self.maxField, text = svalue)
        self.canvas.update()

# Intermediate values for rounding numbers
roundingList = [1.0, 2.0, 5.0, 10.0]
def roundRange(val, lower = True):
    if lower and val >= 0:
        return 0.0
    if not lower and val <= 0.0:
        return 0.0
    neg = val < 0
    val = abs(val)
    rval = 1.0
    while (val >= 10.0):
        rval *= 10
        val = val / 10.0
    # val is now in [0.0, 10.0)
    for bound in self.roundingList:
        if val < bound:
            rval *= bound
            break
    return -rval if neg else rval

class Grapher:
    parent = None
    canvas = None
    width = None
    height = None
    yMax = 100.0
    yMin =   0.0
    dataPoints = []  # Each point is t, v, object
    axisParts = []

# Configuration parameters
    duration = 60.0
    radius = 3
    margin = 50
    titleY = 15

    def __init__(self, parent, title, width, height, yMin, yMax):
        self.width = width
        self.height = height
        self.yMin = yMin
        self.yMax = yMax
        self.canvas = Canvas(self.parent, width = width, height = height, background = "white")
        self.canvas.pack(side=LEFT)
        self.title = self.canvas.create_text((width/2, self.titleY), text=title, fill="black")
        self.dataPoints = []
        self.axisParts = []
        self.canvas.update()

    def getXpos(self, t, rawTime = False):
        tmin = self.dataPoints[0][0] if len(self.dataPoints) > 0 else t
        if rawTime:
            tmin = 0
        return self.margin + (self.width-self.margin) * (t-tmin)/self.duration

    def getYpos(self, y):
        if y < self.yMin or y > self.yMax:
            return None
        return (self.height-self.margin) * (self.yMax - y)/(self.yMax-self.yMin)

    def makeCircle(self, t, y):
        xpos = self.getXpos(t)
        ypos = self.getYpos(y)
        if ypos is None:
            return None
        return self.canvas.create_oval((xpos-self.radius, ypos-self.radius), (xpos+self.radius,ypos+self.radius), fill="red", outline="")

    def addAxes(self):
        xleft = self.getXpos(0, True)
        xright = self.getXpos(self.duration, True)
        ybottom = self.getYpos(self.yMin)
        ytop = self.getYpos(self.yMax)
        xaxis = self.canvas.create_line((xleft, ybottom), (xright, ybottom), fill="black")
        dtext = "%.1f" % self.duration
        xlabel = self.canvas.create_text((xright, ybottom+self.margin/2), anchor = "e", text= dtext, fill="black")
        yaxis = self.canvas.create_line((xleft, ybottom), (xleft, ytop), fill="black")
        ytext = "%.1f" % self.yMax
        ylabel = self.canvas.create_text((xleft-self.margin/2, 0), anchor = "n", text= ytext, fill="black")
        self.axisParts = [xaxis, xlabel, yaxis, ylabel]


    def addPoint(self, t, y):
        circ = self.makeCircle(t, y)
        if circ is None:
            return
        if len(self.dataPoints) == 0:
            self.addAxes()
        self.dataPoints.append((t,y,circ))
        self.canvas.update()
        
    def reset(self):
        for p in self.dataPoints:
            self.canvas.delete(p[2])
        self.dataPoints = []
        for obj in self.axisParts:
            self.canvas.delete(obj)
        self.axisParts = []
        self.canvas.update()

class Station:
    sampler = None
    formatter = None
    tk = None
    canvas = None
    timeTracker = None
    accelerationTracker = None
    altitudeTracker = None
    altitudeGrapher = None
    terminating = False
    minTime = None

    # Configuration parameters (default = HDMI 1080p)
    screenWidth = 1750
    screenHeight =950
    controlHeight = 80
    width = None
    height = None

    def __init__(self, sampler, formatter, yMax):
        self.sampler = sampler
        self.formatter = formatter
        self.tk = Tk()
        self.width = self.screenWidth
        self.height = self.screenHeight - self.controlHeight
        self.controlFrame = Frame(self.tk)
        self.controlFrame.pack(side=TOP, fill=BOTH, expand=YES)
        self.quitButton = Button(self.controlFrame, text = "Quit", height=2, width = 5, command = self.quit)
        self.quitButton.pack(side=LEFT)
        self.resetButton = Button(self.controlFrame, text = "Reset", height=2, width = 5, command = self.reset)
        self.resetButton.pack(side=LEFT)
        self.canvas = Canvas(self.tk, width=self.width, height=self.height, background="#ffffff")
        self.canvas = Canvas(self.tk, background="#ffffff")
        self.canvas.pack(side=LEFT, expand=YES)
        self.dataFrame = Frame(self.canvas)
        self.dataFrame.pack(side=TOP, fill=BOTH, expand=YES)
        self.altitudeGrapher = Grapher(self.dataFrame, "Altitude", 0.7*self.width, self.height, 0.0, yMax)
        self.trackerFrame = Frame(self.canvas)
        self.trackerFrame.pack(side=LEFT)
        self.timeTracker = TextTracker(self.trackerFrame, "Time")
        self.accelerationTracker = TextTracker(self.trackerFrame, "Acceleration")
        self.accelerationXTracker = TextTracker(self.trackerFrame, "Upward Acceleration")
        self.altitudeTracker = TextTracker(self.trackerFrame, "Altitude")
        self.terminating = False
        self.tk.update()
  
    def update(self):
        if self.terminating:
            return False
        tup = self.sampler.getNextSampleTuple()
        if tup is None:
            return True
        r = self.formatter.formatSample(tup)
        if r is None:
            return True
        self.timeTracker.update(r.timeStamp)
        self.accelerationTracker.update(r.acceleration())
        self.accelerationXTracker.update(r.accelerationX)
        self.altitudeTracker.update(r.altitude)
        self.altitudeGrapher.addPoint(r.timeStamp, r.altitude)
        self.tk.update()
        return True
        
    def run(self, maxCount = None):
        count = 0
        done = False
        while not done and (maxCount is None or count < maxCount):
            count += 1
            done = not self.update()

    def quit(self):
        self.terminating = True
        self.sampler.terminate()
        self.tk.after(200)
        sys.exit(0)

    def reset(self):
        self.timeTracker.reset()
        self.accelerationTracker.reset()
        self.altitudeTracker.reset()
        self.altitudeGrapher.reset()


def run(name, args):
    port = None
    baud = 115200
    retries = 10
    verbosity = 1
    senderId = None
    logName = recorder.logFileName()
    bufSize = 12
    yMax = 100.0

    optList, args = getopt.getopt(args, "hLv:p:b:t:s:k:y:")
    for (opt, val) in optList:
        if opt == '-h':
            usage(name)
            return
        elif opt == '-v':
            verbosity = int(val)
        elif opt == '-p':
            try:
                pnum = int(val)
                port = recorder.devPrefix + str(pnum)
            except:
                port = val
        elif opt == '-b':
            baud = int(val)
        elif opt == '-t':
            retries = int(val)
        elif opt == '-s':
            senderId = val
        elif opt == '-k':
            bufSize = int(val)
        elif opt == '-y':
            yMax = float(val)
        elif opt == '-L':
            logName = None

    if port is None:
        plist = recorder.findPorts()
        if len(plist) == 0:
            print("Can't find any devices starting with names '%s'" % recorder.devPrefix)
            return
        elif len(plist) == 1:
            port = plist[0]
        elif len(plist) == 2:
            print("Ambiguous port.  Candidates are:")
            for p in plist:
                print("  %s" % p)
            return

    if logName is not None:
        print("Writing to log file %s" % logName)

    sampler = recorder.Sampler(port, baud, senderId, verbosity, retries) if bufSize == 0 else recorder.BufferedSampler(port, baud, senderId, verbosity, retries, bufSize)
    formatter = recorder.Formatter(sampler, logName)
    station = Station(sampler, formatter, yMax)
    station.run()

    
if __name__ == "__main__":
    run(sys.argv[0], sys.argv[1:])
    sys.exit(0)
    
