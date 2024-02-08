#!/usr/local/bin/python3
# Support for GUI to visualize acceleration

from tkinter import *
import math
import sys
import getopt

import recorder
import hsv

def usage(prog):
    print("Usage: %s [-h] [-v VERB] [-n RECT] [-m [x|a]] [-p PORT] [-b BAUD] [-t TRIES] [-s SID] [-k BSIZE]" % prog)
    print("  -h      Print this message")
    print("  -v VERB Set verbosity")
    print("  -n RECT Set number of rectangles")
    print("  -m MODE Set mode: a=altitude, x=X-acceleration")
    print("  -p PORT Specify serial port on /dev")
    print("  -b BAUD Set serial interface baud rate")
    print("  -t TRY  Specify number of tries in opening serial port")
    print("  -k BUF  Buffer with up to BUF samples")


devPrefix = "/dev/cu.usbmodem"

class ShowMode:
    acceleration, altitude, both = range(3)

class Beater:
    sampler = None
    formatter = None
    tk = None
    canvas = None
    objects = []
    objectColors = []
    averageAltitude = 0.0
    mode = None

    # Configuration parameters (default = HDMI 1080p)
    width = 1920
    height = 1080
    # Rectangle sizes are normalized to [0,1] in both dimensions
    center = (0.5, 0.5)
    minSize = 0.05
    maxSize = 0.5
    accelKwd = 'acceleration-X'
    accelMin = -1.5
    accelMax = 1.5
    altKwd = 'altitude'
    altMin = -0.5
    altMax = 0.5
    rectangleCount = 5


    def __init__(self, sampler, formatter, mode, count):
        self.sampler = sampler
        self.formatter = formatter
        self.mode = mode
        self.rectangleCount = count
        self.tk = Tk()
        self.frame = Frame(self.tk)
        self.frame.pack(fill=BOTH, expand=YES)
        self.canvas = Canvas(self.frame, width=self.width, height=self.height, background="#ffffff")
        self.canvas.pack(fill=BOTH, expand=YES)
        self.addRectangles()
        self.averageAltitude = self.findAltitude()

        
    def findAltitude(self):
        value = None
        for t in range(10):
            tup = self.sampler.getNextSampleTuple()
            if tup is None:
                continue
            r = self.formatter.formatSample(tup)
            if r is not None and r.accept():
                return r.altitude
        print("WARNING: Could not determine altitude")
        return 0
        

    # Index of rectangle in object list
    # Rectangles numbered from 0 to self.rectangleCount-1
    # Put smallest ones at end of list
    def objectIndex(self, cindex):
        return self.rectangleCount - cindex - 1
  
    def rectangleCoordinates(self, index):
        norm = float(self.rectangleCount-1-index)/float(self.rectangleCount-1)
        hsize = (norm * (self.maxSize-self.minSize) + self.minSize)
        lx = self.width*(self.center[0] - hsize)
        ly = self.height*(self.center[0] - hsize)
        rx = self.width*(self.center[0] + hsize)
        ry = self.height*(self.center[0] + hsize)
        return (lx,ly,rx,ry)

    def addRectangles(self):
        self.objects = [0] * self.rectangleCount
        self.objectColors = ["#ff0000"] * self.rectangleCount
        for i in range(len(self.objects)):
            lx, ly, rx, ry = self.rectangleCoordinates(i)
            color = hsv.valueToColor(i, xmax= len(self.objects)-1)
            self.objectColors[i] = color
            self.objects[i] = self.canvas.create_rectangle((lx, ly), (rx, ry), fill=color, outline="")
#            print("Adding object %d rectangle (%.2f, %.2f, %.2f, %.2f).  Color = %s" % (self.objects[i], lx, ly, rx, ry, color))
        self.tk.update()

    def updateRectangles(self, color):
#        print("Updating color = %s" % color)
        nobj = len(self.objects)
        for i in range(nobj-1):
            self.objectColors[i] = self.objectColors[i+1]
        self.objectColors[nobj-1] = color
        for i in range(nobj):
#            print("Setting color of item %d to %s" % (self.objects[i], self.objectColors[i]))
            self.canvas.itemconfigure(self.objects[i], fill = self.objectColors[i])
#        print("Rectangles updated")
        
    def update(self):
        tup = self.sampler.getNextSampleTuple()
        if tup is None:
            return
        r = self.formatter.formatSample(tup)
        if r is None:
            return
        if self.mode == ShowMode.acceleration:
            value = r.accelerationX
            vmin = self.accelMin
            vmax = self.accelMax
        else:
            value = r.altitude
            vmin = self.altMin
            vmax = self.altMax
        color = hsv.valueToColor(value, vmin, vmax)
        self.updateRectangles(color)
        self.canvas.update()
#        if self.mode != ShowMode.acceleration:
#            print("Altitude = %.2f, Average altitude = %.2f" % (value, self.averageAltitude))
#        if self.mode != ShowMode.acceleration:
#            self.averageAltitude = 0.1 * value + 0.9 * self.averageAltitude

    def run(self, maxCount = None):
        count = 0
        while maxCount is None or count < maxCount:
            self.update()
            count += 1
        
def run(name, args):
    port = None
    baud = 115200
    retries = 10
    verbosity = 1
    senderId = None
    mode = ShowMode.acceleration
    count = 20
    bufSize = 1
    

    optList, args = getopt.getopt(args, "hv:p:b:t:s:m:n:k:")
    for (opt, val) in optList:
        if opt == '-h':
            usage(name)
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
        elif opt == '-n':
            count = int(val)
        elif opt == '-k':
            bufSize = int(val)
        elif opt == '-m':
            if len(val) != 1 or val not in "ax":
                print("Mode must be 'a' or 'x'")
                return
            mode = ShowMode.altitude if val == 'a' else ShowMode.acceleration

    if port is None:
        plist = recorder.findPorts()
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

    sampler = recorder.Sampler(port, baud, senderId, verbosity, retries) if bufSize == 0 else recorder.BufferedSampler(port, baud, senderId, verbosity, retries, bufSize) 
    formatter = recorder.Formatter(sampler)
    beater = Beater(sampler, formatter, mode, count)
    beater.run(1000)

    
if __name__ == "__main__":
    run(sys.argv[0], sys.argv[1:])
    sys.exit(0)
    
