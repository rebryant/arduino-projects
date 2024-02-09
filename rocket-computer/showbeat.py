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
    acceleration, altitude = range(2)
    symbols = ['x', 'a']
    names = ["Acceleration", "Altitude"]

    def parse(self, symbol):
        for mode in range(2):
            if self.symbols[mode] == symbol:
                return mode
        return None

    def change(self, mode):
        if mode == self.acceleration:
            return self.altitude
        elif mode == self.altitude:
            return self.acceleration
        else:
            return None


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
    screenWidth = 1800
    screenHeight =1000
    controlHeight = 80
    width = None
    height = None
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
    rectangleCount = 50


    def __init__(self, sampler, formatter, mode, count):
        self.sampler = sampler
        self.formatter = formatter
        self.mode = mode
        self.rectangleCount = count
        self.width = self.screenWidth
        self.height = self.screenHeight - self.controlHeight
        self.tk = Tk()
        self.controlFrame = Frame(self.tk)
        self.controlFrame.pack(side=TOP, fill=BOTH, expand=YES)
        self.quitButton = Button(self.controlFrame, text = "Quit", height=2, width = 5, command = self.quit)
        self.quitButton.pack(side=LEFT)
        self.accelButton = Button(self.controlFrame, text = "Accel", height=2, width = 5, command = self.doAcceleration)
        self.accelButton.pack(side=LEFT)
        self.altButton = Button(self.controlFrame, text = "Alt", height=2, width = 5, command = self.doAltitude)
        self.altButton.pack(side=LEFT)

        
        self.dataFrame = Frame(self.tk)
        self.dataFrame.pack(side=BOTTOM, fill=BOTH, expand=YES)
        self.canvas = Canvas(self.dataFrame, width=self.width, height=self.height, background="#ffffff")
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
        self.objectColors = ["#ffffff"] * self.rectangleCount
        for i in range(len(self.objects)):
            lx, ly, rx, ry = self.rectangleCoordinates(i)
            self.objects[i] = self.canvas.create_rectangle((lx, ly), (rx, ry), fill=self.objectColors[i], outline="")
        self.tk.update()

    def clearColors(self):
        nobj = len(self.objects)
        for i in range(nobj):
            self.objectColors[i] = "#ffffff"
            self.canvas.itemconfigure(self.objects[i], fill = self.objectColors[i])
        self.tk.update()
        

    def updateRectangles(self, color):
        nobj = len(self.objects)
        for i in range(nobj-1):
            self.objectColors[i] = self.objectColors[i+1]
        self.objectColors[nobj-1] = color
        for i in range(nobj):
            self.canvas.itemconfigure(self.objects[i], fill = self.objectColors[i])
        
    def update(self):
        tup = self.sampler.getNextSampleTuple()
        if tup is None:
            return True
        r = self.formatter.formatSample(tup)
        if r is None:
            return True
        if self.mode == ShowMode.acceleration:
            value = r.accelerationX
            vmin = self.accelMin
            vmax = self.accelMax
        else:
            value = r.altitude - self.averageAltitude
            vmin = self.altMin
            vmax = self.altMax
        color = hsv.valueToColor(value, vmin, vmax)
        try:
            self.updateRectangles(color)
            self.canvas.update()
            return True
        except TclError:
            print("Encountered error when exiting")
            return False

    def run(self, maxCount = None):
        count = 0
        done = False
        while not done and (maxCount is None or count < maxCount):
            count += 1
            done = not self.update()
        
    def quit(self):
        self.sampler.terminate()
        self.tk.destroy()
        sys.exit(0)

    def doAcceleration(self):
        sm = ShowMode()
        self.mode = sm.acceleration
        print("Switching to mode %s" % sm.names[self.mode])
        self.clearColors()

    def doAltitude(self):
        sm = ShowMode()
        self.mode = sm.altitude
        self.averageAltitude = self.findAltitude()
        print("Switching to mode %s.  Altitude = %.2f" % (sm.names[self.mode], self.averageAltitude))
        self.clearColors()

def run(name, args):
    port = None
    baud = 115200
    retries = 10
    verbosity = 1
    senderId = None
    mode = ShowMode.acceleration
    count = 50
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
            sm = ShowMode()
            mode = sm.parse(val)
            if mode is None:
                print("Mode must be 'a' or 'x'")
                return

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
    beater.run()

    
if __name__ == "__main__":
    run(sys.argv[0], sys.argv[1:])
    sys.exit(0)
    
