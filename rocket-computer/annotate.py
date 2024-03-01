#!/usr/local/bin/python3

# Annotate rocket video with telemetry data

import cv2
import scipy.io
import numpy as np
import ffmpeg
import os
import sys
import getopt
import glob

import analyze

def usage(name):
    print("Usage: %s [-h] [-k] [-v VERB] -i IVFILE.AVI -d DFILE.csv [-o OVFILE.mp4]" % name)

def getRoot(fname):
    fields = fname.split(".")
    if len(fields) > 1:
        fields = fields[:-1]
    return ".".join(fields)

def getExtension(fname):
    fields = fname.split(".")
    if len(fields) > 1:
        return fields[-1]
    return ""
    

class Sound:
    # Process audio data
    # Use to detect launch starting point

    # Name of audio file
    audioName = None
    # Verbosity level
    verbLevel = 1
    # Keep intermediate files
    keep = False

    # General parameters
    # audio sample rate
    rate = 8000
    # RMS level for launch
    threshold = 20000.0
    # Required duration (seconds)
    duration = 1.0
    # Sample interval
    tdelta = 0.01
    
    def __init__(self, aname, verbLevel = 1, keep = False):
        self.audioName = aname
        self.verbLevel = verbLevel
        self.keep = keep

    def readWav(self):
        try:
            self.rate, val = scipy.io.wavfile.read(self.audioName)
        except Exception as ex:
            print("Couldn't read WAV file '%s' (%s)" % (self.audioName, str(ex)))
            return None
        return val

    # Construct array of RMS values for array
    # Each for a sample of duration tdelta
    def rmsValues(self, val):
        rms = []
        scount = int(self.tdelta * self.rate)
        pos = 0
        while pos + scount <= len(val):
            r = np.sqrt(np.sum(np.square(val[pos:pos+scount], dtype=float))/float(scount))
            rms.append(r)
            pos += scount
        return rms

    def findLaunchTime(self, rms):
        need = self.duration / self.tdelta
        indices = [i for i in range(len(rms)) if rms[i] > self.threshold]
        firstI = indices[0]
        lastI = indices[0]
        for i in indices[1:]:
            if i == lastI+1:
                lastI = i
            else:
                firstI = i
                lastI = i
            if lastI-firstI+1 >= need:
                return firstI * self.tdelta
        return None

    # Run entire chain on audio file
    def launchTime(self):
        val = self.readWav()
        if val is None:
            return -1.0
        if self.verbLevel >= 2:
            print("Read %d samples from %s" % (len(val), self.audioName))
        rms = self.rmsValues(val)
        if self.verbLevel >= 2:
            print("Got %d RMS values" % (len(rms)))
        t = self.findLaunchTime(rms)
        if t is None:
            return -1.0
        if self.verbLevel >= 1:
            print("Got launch time %.3f" % t)
        return t
    
        
# Annotate image
class Image:
    imageName = None
    image = None
    verbLevel = 1
    width = None
    height = None

    # Positioning parameters (all in fractions of image height/width)
    altitudeLeftPos = 0
    altitudeBottomPos = 0
    accelerationLeftPos = 0.10
    accelerationBottomPos = 0

    barHeight = 0.5
    barWidth = 0.075
    upColor = (0,0,127)
    peakColor = (127,0,0)
    labelColor = (0,150,150)
    leftPad = 3
    bottomPad = 8

    def __init__(self, imageName, verbLevel = 1):
        self.imageName = imageName
        self.verbLevel = verbLevel
        try:
            self.image = cv2.imread(imageName)
            self.width = np.shape(self.image)[0]
            self.height = np.shape(self.image)[0]
        except Exception as ex:
            if self.verbLevel > 0:
                print("Couldn't read image file '%s' (%s)" % (self.imageName, str(ex)))
            self.image = None

    def showAltitude(self, altitude, limitAltitude, peakAltitude = None, deltaAltitude=10.0):
        if self.image is None:
            return
        altitude = max(0, min(altitude, limitAltitude))
        if peakAltitude is not None:
            peakAltitude = max(0, min(peakAltitude, limitAltitude))
        left = int(self.width*self.altitudeLeftPos)
        right = int(self.width*(self.altitudeLeftPos+self.barWidth))
        # Background
        upper = int(self.height*(1.0-self.altitudeBottomPos-self.barHeight))
        lower = int(self.height*(1.0-self.altitudeBottomPos))
        cv2.rectangle(self.image, (left,upper), (right,lower), (255,255,255), -1)
        # current altitude
        aheight = altitude/limitAltitude * self.barHeight
        aupper = int(self.height*(1.0-self.altitudeBottomPos-aheight))
        if aheight > 0:
            cv2.rectangle(self.image, (left,aupper), (right,lower), self.upColor, -1)
        # peak altitude
        if peakAltitude is not None and peakAltitude > altitude:
            pheight = peakAltitude/limitAltitude * self.barHeight
            pupper = int(self.height*(1.0-self.altitudeBottomPos-pheight))
            cv2.rectangle(self.image, (left,pupper), (right,aupper), self.peakColor, -1)
        # Tick marks and labels
        alt = 0.0
        while alt <= limitAltitude:
            height = alt/limitAltitude * self.barHeight
            h = int(self.height*(1.0-self.altitudeBottomPos-height))
            cv2.line(self.image, (left,h), (right,h), (0,0,0), 2)
            if alt < limitAltitude:
                astring = "%dm" % int(alt)
                pstring = "%dm" % limitAltitude
                astring = " " * (len(pstring)-len(astring)) + astring
                cv2.putText(self.image, astring, (left+self.leftPad, h-self.bottomPad), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.labelColor, 1, cv2.LINE_AA)
            alt += deltaAltitude

    def showAcceleration(self, acceleration, limitAcceleration, peakAcceleration = None, deltaAcceleration=1.0):
        if self.image is None:
            return
        acceleration = max(0, min(acceleration, limitAcceleration))
        if peakAcceleration is not None:
            peakAcceleration = max(0, min(peakAcceleration, limitAcceleration))
        left = int(self.width*self.accelerationLeftPos)
        right = int(self.width*(self.accelerationLeftPos+self.barWidth))
        # Background
        upper = int(self.height*(1.0-self.accelerationBottomPos-self.barHeight))
        lower = int(self.height*(1.0-self.accelerationBottomPos))
        cv2.rectangle(self.image, (left,upper), (right,lower), (255,255,255), -1)
        # current acceleration
        aheight = max(0.0, acceleration/limitAcceleration * self.barHeight)
        aupper = int(self.height*(1.0-self.accelerationBottomPos-aheight))
        if aheight > 0:
            cv2.rectangle(self.image, (left,aupper), (right,lower), self.upColor, -1)
        # peak acceleration
        if peakAcceleration is not None and peakAcceleration > acceleration:
            pheight = max(0.0, peakAcceleration/limitAcceleration * self.barHeight)
            pupper = int(self.height*(1.0-self.accelerationBottomPos-pheight))
            cv2.rectangle(self.image, (left,pupper), (right,aupper), self.peakColor, -1)
        # Tick marks and labels
        acc = 0.0
        while acc <= limitAcceleration:
            height = acc/limitAcceleration * self.barHeight
            h = int(self.height*(1.0-self.accelerationBottomPos-height))
            cv2.line(self.image, (left,h), (right,h), (0,0,0), 2)
            if acc < limitAcceleration:
                astring = "%dg" % int(acc)
                pstring = "%dg" % limitAcceleration
                astring = " " * (len(pstring)-len(astring)) + astring
                cv2.putText(self.image, astring, (left+self.leftPad, h-self.bottomPad), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.labelColor, 1, cv2.LINE_AA)
            acc += deltaAcceleration

    def write(self, name = None):
        if self.image is None:
            return
        if name is None:
            name = self.imageName
        if not cv2.imwrite(name, self.image):
            if self.verboseLevel > 0:
                print("Failed to write image %s" % name)
        
        
class Video:

    videoName = None
    audioName = None
    frameDir = "frames"
    # Parameters
    fps = 30
    frameCount = 0
    videoLaunchTime = 0
    videoDuration = 0.0
    dataLaunchTime = 0
    dataDuration = 0.0
    evaluator = None
    verbLevel = 1
    keep = False
    tmpNames = []

        
    def __init__(self, vname, dname, verbLevel=1, keep = False):
        self.videoName = vname
        self.verbLevel = verbLevel
        self.keep = keep
        self.tmpNames = []
        vroot = getRoot(vname)
        self.frameDir = vroot + "-frames"
        # Get info about video
        vprobe = ffmpeg.probe(vname)['streams'][0]
        self.fps = int(vprobe['r_frame_rate'].split('/')[0])
        self.frameCount = int(vprobe['nb_frames'])
        self.videoDuration = float(self.frameCount)/self.fps
        # Get launch time for video
        if not self.buildWav():
            raise Exception("Program Failure")
        sound = Sound(self.audioName, self.verbLevel, self.keep)
        self.videoLaunchTime = sound.launchTime()
        self.report(1, "Video file %s:  frames = %d, fps = %d, launch = %.2f, duration = %.2f" % (self.videoName, self.frameCount, self.fps, self.videoLaunchTime, self.videoDuration))
        droot = getRoot(dname)
        self.evaluator = analyze.Evaluator(droot)
        r = self.evaluator.findLaunch()
        self.dataLaunchTime = 0.0 if r < 0 else self.evaluator.getFloatField(r, "time")
        self.dataDuration = self.evaluator.getFinalTime()
        self.report(1, "Data file %s: Launch Time %.2f, duration = %.2f" % (dname, self.dataLaunchTime, self.dataDuration))
        

    def quiet(self):
        return self.verbLevel <= 3

    # Get soundtrack from video file and save as .WAV file
    def buildWav(self):
        self.audioName = getRoot(self.videoName) + ".WAV"
        self.tmpNames.append(self.audioName)
        if os.path.exists(self.audioName):
            os.remove(self.audioName)
        try:
            ffmpeg.input(self.videoName).audio.output(self.audioName).run(quiet=self.quiet())
            self.report(3, "Extracted audio file %s" % self.audioName)
        except Exception as ex:
            print("Couldn't get audio from video file '%s' (%s)" % (self.videoName, str(ex)))
            return False
        return True

    def imageName(self, index = None):
        if index is None:
            return self.frameDir + "/image-%04d.png"
        else:
            return self.frameDir + ("/image-%.4d.png" % (index+1))

    def generateFrames(self):
        self.deleteFrames()
        os.mkdir(self.frameDir)
        # Get frames
        ffmpeg.input(self.videoName).output(self.imageName()).run(quiet=self.quiet())
        self.report(2, "Stored %d images in %s" % (self.frameCount, self.frameDir))

    def labelFrames(self):
        rawAltitudes = self.evaluator.getAltitudes()
        rawAccelerations = self.evaluator.getAccelerations()
        maxAltitude = max(rawAltitudes)
        limitAltitude = 100
        while limitAltitude < maxAltitude:
            limitAltitude += 100
        deltaAltitude = limitAltitude / 10
        maxAcceleration = max(rawAccelerations)
        limitAcceleration = 10
        while limitAcceleration < maxAcceleration:
            limitAcceleration += 10
        deltaAcceleration = limitAcceleration / 10
        # Video starting point WRT data
        tdelta = 1.0/self.fps
        tstart = self.dataLaunchTime - self.videoLaunchTime
        timedAltitudes = self.evaluator.valueSequence(rawAltitudes, tstart, self.videoDuration, tdelta)
        soFarAltitude = 0.0
        timedAccelerations = self.evaluator.valueSequence(rawAccelerations, tstart, self.videoDuration, tdelta)
        soFarAcceleration = 0.0
        for i in range(self.frameCount):
            name = self.imageName(i)
            im = Image(name, self.verbLevel)
            altitude = timedAltitudes[i]
            soFarAltitude = max(soFarAltitude, altitude)
            im.showAltitude(altitude, limitAltitude, soFarAltitude, deltaAltitude)
            acceleration = timedAccelerations[i]
            soFarAcceleration = max(soFarAcceleration, acceleration)
            im.showAcceleration(acceleration, limitAcceleration, soFarAcceleration, deltaAcceleration)
            im.write()
            self.report(3, "Annotated image %s.  altitude = %.2f, acceleration = %.2f" % (name, altitude, acceleration))
        self.report(1, "Annotated %d images" % self.frameCount)

    def deleteFrames(self):
        if os.path.exists(self.frameDir):
            flist = glob.glob(self.frameDir + "/*.png")
            for fname in flist:
                os.remove(fname)
            try:
                os.rmdir(self.frameDir)
            except:
                self.report(2, "Couldn't delete directory %s" % self.frameDir)
                return
            self.report(2, "Deleted %d files from directory %s" % (len(flist), self.frameDir))
                
    def generateVideo(self, outName):
        # Merge images into silent video
        tname = getRoot(self.videoName) + "-tmp.mp4"
        if os.path.exists(tname):
            os.remove(tname)
        self.tmpNames.append(tname)
        self.report(2, "Merging images into video file %s" % tname)
        ffmpeg.input(self.imageName(), framerate=self.fps).output(tname, r=self.fps, format='mp4', pix_fmt='yuv420p').run(quiet=self.quiet())
        self.report(2, "Merging sound file %s with video file %s to create file %s" % (self.audioName, tname, outName))
        video = ffmpeg.input(tname).video
        audio = ffmpeg.input(self.audioName).audio
        if os.path.exists(outName):
            os.remove(outName)
        ffmpeg.output(video, audio, outName).run(quiet=self.quiet())
        self.report(1, "Generated video file %s" % outName)

    def clean(self):
        if self.keep:
            return
        self.deleteFrames()
        for name in self.tmpNames:
            try:
                os.remove(name)
                self.report(3, "Deleted file %s" % name)
            except Exception as ex:
                self.report(3, "Couldn't delete file %s (%s)" % (name, str(ex)))

    def report(self, level, msg):
        if self.verbLevel >= level:
            print(msg)
    
    def run(self, outName):
        self.generateFrames()
        self.labelFrames()
        self.generateVideo(outName)
        self.clean()



def run(name, args):
    verbLevel = 1
    inVideoName = None
    inDataName = None
    outVideoName = None
    keep = False
    optList, args = getopt.getopt(args, "hkv:i:d:o:")
    for (opt, val) in optList:
        if opt == '-h':
            usage(name)
            return
        if opt == '-k':
            keep = True
        elif opt == '-v':
            verbLevel = int(val)
        elif opt == '-i':
            inVideoName = val
        elif opt == '-d':
            inDataName = val
        elif opt == '-o':
            outVideoName = val
        else:
            print("Uknown option '%s'" % opt)
            usage(name)
            return
    if inVideoName is None:
        print("Require input video file")
        usage(name)
        return
    if not os.path.exists(inVideoName):
        print("Error: File '%s' does not exist" % inVideoName)
        return
    if inDataName is None:
        print("require input data file")
        usage(name)
        return
    if not os.path.exists(inDataName):
        print("Error: File '%s' does not exist" % inDataName)
        return
    if outVideoName is None:
        outVideoName = getRoot(inVideoName) + "-new.mp4"
    v = Video(inVideoName, inDataName, verbLevel, keep)
    v.run(outVideoName)

if __name__ == "__main__":
    run(sys.argv[0], sys.argv[1:])
    sys.exit(0)
    

    
    

    
