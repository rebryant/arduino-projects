#!/usr/local/bin/python3

# Analyze properties of flight from CSV representation of its log.

import csv
import sys
import numpy as np

class Evaluator:
#    Array of dictionaries built from CSV reader.  One entry per sample
#    All entries are text
    root = None
    entries = []
    events = ["launch", "thr-max", "thr-end", "v-max", "apogee", "deploy", "land"]
    vevent = "v-max"
    headings = ["row", "time", "alt", "accel", "accel-X"]
    vheadings = ["row", "time", "alt", "accel", "accel-X", "velocity"]
    vheading = "velocity"
    formats = ["%d", "%.3f", "%.3f", "%.3f", "%.3f"]
    vformat = "%.3f"

    def __init__(self, root):
        self.root = root
        csvName = root + ".csv"
        try:
            cfile = open(csvName, "r")
        except:
            self.root = None
            print("Couldn't open file '%s'" % csvName)
            return
        self.entries = []
        creader = csv.DictReader(cfile)
        for row in creader:
            self.entries.append(row)
        cfile.close()
        self.rstart = self.findLaunch()
        self.tstart = self.getFloatField(self.rstart, "time")
        self.astart = self.getFloatField(self.rstart, "altitude")

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

    def getNormTimes(self, rstart, rend):
        times = self.getTimes()
        return [times[r]-self.tstart for r in range(rstart, rend+1)]

    def getNormAltitudes(self, rstart, rend):
        altitudes = self.getAltitudes()
        return [max(0, altitudes[r]-self.astart) for r in range(rstart, rend+1)]


    def findLaunch(self):
        accelerations = self.getAccelerations()
        for r in range(self.count()):
            if accelerations[r] > 1.5:
                return r
        return -1

    def findThrustMax(self):
        rend = self.findApogee()
        accelerations = self.getAccelerations()
        tmax = max(accelerations[0:rend+1])
        for r in range(rend+1):
            if accelerations[r] == tmax:
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

    def findDeploy(self):
        accelerations = self.getAccelerations()
        rstart = self.findApogee()
        if rstart < 0:
            return rstart
        for r in range(rstart, self.count()):
            if accelerations[r] > 1.0:
                return r
        return -1

    def findLand(self):
        altitudes = self.getAltitudes()
        rstart = self.findApogee()
        if rstart < 0:
            return rstart
        for r in range(rstart, self.count()):
            if altitudes[r] < 1.0:
                return r
        return -1

    def plotData(self, outfile):
        rend = self.findLand()
        times = self.getNormTimes(self.rstart, rend)
        altitudes = self.getNormAltitudes(self.rstart, rend)
        outfile.write("coordinates {");
        count = 0
        for (t, a) in zip(times, altitudes):
            outfile.write(" (%.2f, %.2f)" % (t, a))
            count += 1
            if count >= 10:
                outfile.write("\n      ")
                count = 0
        outfile.write("}\n")


    # Generate dictionary of dictionaries show interesting events
    def highlights(self):
        times = self.getTimes()
        altitudes = self.getAltitudes()
        accelerations = self.getAccelerations()
        accelerationXs = self.getAccelerationXs()
        rlaunch = self.findLaunch()
        rtmax = self.findThrustMax()
        rtend = self.findThrustEnd()

        rvmax, vmax = self.findMaxVelocity()
        rapogee = self.findApogee()
        rdeploy = self.findDeploy()
        rland = self.findLand()
        rows = [rlaunch, rtmax, rtend, rvmax, rapogee, rdeploy, rland]
        result = {}
        for idx in range(len(rows)):
            event = self.events[idx]
            r = rows[idx]
            entry = { self.headings[0] : r }
            if r < 0:
                vals = [-1] * 4
            else:
                vals = [times[r], altitudes[r], accelerations[r], accelerationXs[r]]
            for i in range(4):
                entry[self.headings[i+1]] = vals[i]
            if event == self.vevent:
                entry[self.vheading] = vmax
            result[event] = entry
        return result

    def getCoordinate(self, event, h):
        t = h[event]['time'] - self.tstart
        a = h[event]['alt'] - self.astart
        return (t, a)

    def estring(self, event, h):
        entry = h[event]
        ls = [event] + [(self.formats[i] % entry[self.headings[i]]) for i in range(len(self.headings))]
        if event == self.vevent:
            ls.append(self.vformat % entry[self.vheading])
        return ls

    def showHighlights(self, h):
        print("\t".join(["event"] + self.headings + [self.vheading]))
        for event in self.events:
            es = self.estring(event, h)
            print("\t".join(es))
            
    def tabularizeHighlights(self, h, outfile):
        outfile.write("\\begin{tabular}{lrrrr}\n")
        outfile.write("\\multicolumn{5}{l}{\\textbf{%s}} \\\\ \n" % self.root)
        outfile.write("\\toprule\n")
        outfile.write("Event & Time & Altitude & Acceleration & Velocity\\\\ \n")
        outfile.write(" &      ($s$) & ($m$) & ($g$) & $(m/s)$ \\\\ \n")
        outfile.write("\\midrule\n")

        # Launch
        accel = h['launch']['accel']
        outfile.write("Launch & 0.000 & 0.000 & %.3f &  \\\\ \n" % (accel))

        # Max Thrust
        accel = h['thr-max']['accel']
        alt = max(0.0,  h['thr-max']['alt']-self.astart)
        time = h['thr-max']['time'] - self.tstart
        outfile.write("Max Thrust & %.3f & %.3f & %.3f &  \\\\ \n" % (time, alt, accel))

        
        # End Thrust
        alt = h['thr-end']['alt']-self.astart
        time = h['thr-end']['time'] - self.tstart
        outfile.write("End Thrust & %.3f & %.3f &  &  \\\\ \n" % (time, alt))

        # Max velocity
        alt = h['v-max']['alt']-self.astart
        time = h['v-max']['time'] - self.tstart
        accel = -h['v-max']['accel']
        vel = h['v-max']['velocity']
        outfile.write("Max Velocity & %.3f & %.3f & %.3f & %.3f \\\\ \n" % (time, alt, accel, vel))
        
        # Apogee
        alt = h['apogee']['alt']-self.astart
        time = h['apogee']['time'] - self.tstart
        accel = -h['apogee']['accel']
        outfile.write("Apogee & %.3f & %.3f & %.3f &  \\\\ \n" % (time, alt, accel))

        # Deploy
        alt = h['deploy']['alt']-self.astart
        time = h['deploy']['time'] - self.tstart
        accel = -h['deploy']['accel']
        outfile.write("Parachute & %.3f & %.3f & %.3f &  \\\\ \n" % (time, alt, accel))


        # Landing
        time = h['land']['time'] - self.tstart
        outfile.write("Landing & %.3f & 0.000 &  &  \\\\ \n" % (time))

        outfile.write("\\bottomrule\n")
        outfile.write("\\end{tabular}\n")

    def deriv(self, coeffs):
        wcoeffs = [i * coeffs[i] for i in range(len(coeffs))]
        return wcoeffs[1:]

    def altitudeCurve(self, rstart, rend):
        times = self.getNormTimes(rstart, rend)
        altitudes = self.getNormAltitudes(rstart, rend)
        t = np.array(times)
        a = np.array(altitudes)
        coeffs = np.polynomial.polynomial.polyfit(t, a, 4)
        return list(coeffs)
        
    def velocityCurve(self, rstart, rend):
        acoeffs = self.altitudeCurve(rstart, rend)
        return self.deriv(acoeffs)

    def ceval(self, coeffs, t):
        pwr = 1.0
        val = 0.0
        nt = t - self.tstart
        for c in coeffs:
            val += pwr * c
            pwr *= nt
        return val + self.astart
        
    def findMaxVelocity(self):
        rstart = self.findLaunch()
        rend = self.findApogee()
        coeffs = self.velocityCurve(rstart, rend)
        rbest = -1
        vbest = -1.0
        for r in range(rstart, rend):
            t = self.getFloatField(r, 'time')
            velo = self.ceval(coeffs, t)
            if velo > vbest:
                vbest = velo
                rbest = r
        return (rbest, vbest)

def fit(e):
    h = e.highlights()
    elaunch = h['launch']
    eapogee = h['apogee']
    eland = h['land']
    rlaunch = elaunch['row']
    rapogee = eapogee['row']
    rland = eland['row']
    print("Launch:    r=%d, t=%.3f" % (elaunch['row'], elaunch['time']))
    print("Apogee:    r=%d, t=%.3f" % (eapogee['row'], eapogee['time']))    
    coeffs = e.altitudeCurve(rlaunch, rapogee)
    vcoeffs = e.velocityCurve(rlaunch, rapogee)
    print("Row\tTime\tRTime\tAlt\tCalt\tVelo")
    for r in range(rlaunch, rapogee+1):
        t = e.getFloatField(r, 'time')
        rt = t-e.tstart
        alt = e.getFloatField(r, 'altitude')
        calt = e.ceval(coeffs, t)
        velo = e.ceval(vcoeffs, t)
        print("%d\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f" % (r, t, rt, alt, calt, velo))
    print("Apogee:        r=%d, t=%.3f" % (eapogee['row'], eapogee['time']))
    print("Land:    r=%d, t=%.3f" % (eland['row'], eland['time']))    
    coeffs = e.altitudeCurve(rapogee, rland)
    vcoeffs = e.deriv(coeffs)
    print("Row\tTime\tAlt\tCalt\tVelo")
    for r in range(rapogee, rland+1):
        t = e.getFloatField(r, 'time')
        alt = e.getFloatField(r, 'altitude')
        calt = e.ceval(coeffs, t)
        velo = e.ceval(vcoeffs, t)
        print("%d\t%.3f\t%.3f\t%.3f\t%.3f" % (r, t, alt, calt, velo))


def process(file):
    e = Evaluator(file)
    h = e.highlights()
    e.showHighlights(h)
    print("")
    e.tabularizeHighlights(h, sys.stdout)
    print("")
    e.plotData(sys.stdout)
            
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
    
