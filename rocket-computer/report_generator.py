#!/usr/local/bin/python3

# Generate Latex file containing results from set of rocket launches

def usage(name):
    print("Usage %s: [-h] [-t TITLE] [-o OUTFILE] R1 R2 ..." % name)

import sys
import getopt

import analyze

# Generate list of evaluators
evals = []
highlights = []

def skipline(count, outfile):
    for i in range(count):
        outfile.write("\n")

colorNames = []
  
colorList = [
  ("midblue", 0, 0.592157, 0.662745),
  ("medgreen", 0.15, 0.6, 0.15),
  ("darkturquoise", 0, 0.239216, 0.298039),
  ("darkestpurple", 0.396078, 0.113725, 0.196078),
  ("redpurple", 0.835294, 0, 0.196078),
  ("bluegray", 0.141176, 0.313725, 0.603922),
  ("darkgreen", 0.152941, 0.576471, 0.172549),
  ("redorange", 0.878431, 0.235294, 0.192157),
  ("midgreen", 0.560784, 0.6, 0.243137),
  ("clearorange", 0.917647, 0.462745, 0),

  ("clearpurple", 0.67451, 0.0784314, 0.352941),
  ("browngreen", 0.333333, 0.313725, 0.145098),
  ("midred", 0.80,0.3,0.3),

  ("darkbrown", 0.305882, 0.211765, 0.160784),
  ("greypurple", 0.294118, 0.219608, 0.298039),
]

def addColors(outfile):
    global colorNames
    for name, r, g, b in colorList: 
        colorNames.append(name)
        outfile.write("\\definecolor{%s}{rgb}{%.3f, %.3f, %.3f}\n" % (name, r, g, b))

def beginDocument(title, outfile):
    outfile.write("\\documentclass{easychair}\n")
    outfile.write("\\usepackage{tikz}\n")
    outfile.write("\\usepackage{pgfplots}\n")
    outfile.write("\\usepackage{booktabs}\n")
    outfile.write("\\authorrunning{}\n")
    outfile.write("\\titlerunning{}\n")
    skipline(1, outfile)
    addColors(outfile)
    skipline(1, outfile)
    outfile.write("\\begin{document}\n")
    outfile.write("\\begin{center}\n")
    outfile.write("\\bf \\LARGE %s\n" % title)
    outfile.write("\\end{center}\n")
    skipline(1, outfile)

def finishDocument(outfile):
    outfile.write("\\end{document}\n")

def generateSection(e, h, outfile):
    outfile.write("\n")
    outfile.write("\\begin{center}\n")
    e.tabularizeHighlights(h, outfile)
    outfile.write("\\end{center}\n")


def processFlight(root, outfile):
    global evals, highlights
    e = analyze.Evaluator(root)
    if e.root is None:
        if outfile != sys.stdout:
            print("Failed to process flight %s" % root)
        return
    evals.append(e)
    h = e.highlights()
    highlights.append(h)
    generateSection(e, h, outfile)
    skipline(1, outfile)
    if outfile != sys.stdout:
        print("Processed flight %s" % root)
    
def startGraph(outfile):
    skipline(1, outfile)
    outfile.write("\\begin{center}\n")
    outfile.write("\\begin{tikzpicture}\n")
    outfile.write("\\begin{axis}[mark options ={scale=0.75}, height=16cm,width=16cm,grid=both, grid style={black!10},\n")
    outfile.write("              legend cell align={left}, xlabel={Time (seconds)}, ymin = 0, ylabel={Altitude (meters)}]\n")

def finishGraph(outfile):
    outfile.write("\\end{axis}\n")
    outfile.write("\\end{tikzpicture}\n")
    outfile.write("\\end{center}\n")
    skipline(1, outfile)

def buildGraph(outfile):
    endThrustString = "\\addplot [only marks, color=red, mark options={scale=1.0}, mark=square*] coordinates {"
    deployString = "\\addplot [only marks, color=red, mark options={scale=2.0}, mark=diamond*] coordinates {"
    legendString = "\\legend{"
    
    startGraph(outfile)
    nextColor = 0
    for (e, h) in zip(evals, highlights):
        outfile.write("\\addplot [only marks, color=%s]\n" % colorNames[nextColor])
        nextColor += 1
        e.plotData(outfile);
        outfile.write("    ;\n")
        legendString += " %s," % e.root
        endThrustString += " (%.2f,%.2f)" % e.getCoordinate('thr-end', h)
        deployString += " (%.2f,%.2f)" % e.getCoordinate('deploy', h)
    endThrustString += "};\n"
    outfile.write(endThrustString)
    deployString += "};\n"
    outfile.write(deployString)
    legendString += " End Thrust, Deploy Parachute }\n"
    outfile.write(legendString)
    finishGraph(outfile)

def generate(title, roots, outfile):
    beginDocument(title, outfile)
    for r in roots:
        processFlight(r, outfile)
    buildGraph(outfile)
    finishDocument(outfile)
        
def stripExtension(name):
    fields = name.split(".")
    if len(fields) > 1:
        fields = fields[:-1]
    return ".".join(fields)

def run(name, args):
    title = "Rockets"
    roots = []
    outfile = sys.stdout
    optList, args = getopt.getopt(args, "ht:o:")
    for (opt, val) in optList:
        if opt == '-h':
            usage(name)
            return
        elif opt == '-t':
            title = val
        elif opt == '-o':
            try:
                outfile = open(val, "w")
            except:
                print("Couldn't open output file '%s'" % val)
                return
    roots = [stripExtension(a) for a in args]
    generate(title, roots, outfile)
    
if __name__ == "__main__":
    run(sys.argv[0], sys.argv[1:])
    sys.exit(0)
