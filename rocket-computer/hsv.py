# Color computations

######################################################################
#
# RGB: r,g,b values are from 0 to 255
# HSV
#   h = [0,360], s = [0,1], v = [0,1]
#   if s == 0, then h = -1 (undefined)
######################################################################

        
# Create string representation of rgb values
def rgb2string(r, g, b):
    return "#%.2x" % r + "%.2x" % g + "%.2x" % b

# Extract r g b values from string
def string2rgb(s):
    if s[0] == '#':
        s = s[1:]
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return (r, g, b)

# Convert number in range [0.0,1.0] to [0,255]
def bit8(x):
    return int(round(255.0 * x))

# Convert number in range [0,255] to [0.0, 1.0]
def norm8(x):
    return x/255.0

# Return rgb value as (r,g,b)
def hsv2rgb(h, s, v):
    if s == 0:
        return (0,0,0)
    sector = h / 60.0
    i = int(sector)
    f = sector - i
    p = bit8(v * (1.0 - s))
    q = bit8(v * (1.0 - s*f))
    t = bit8(v * (1.0 - s * (1-f)))
    v8 = bit8(v)
    if i == 0:
        return (v8, t, p)
    elif i == 1:
        return (q, v8, p)
    elif i == 2:
        return (p, v8, t)
    elif i == 3:
        return (p, q, v8)
    elif i == 4:
        return (t, p, v8)
    else:
        return (v8, p, q)
        
# Convert hsv to rgb and then to string
def hsv2string(h,s,v):
    return rgb2string(*hsv2rgb(h,s,v))

# Convert rgb to hsv
def rgb2hsv(r, g, b):
    nr = norm8(r)
    ng = norm8(g)
    nb = norm8(b)
    nmin = min(nr, ng, nb)
    nmax = max(nr, ng, nb)
    v = nmax
    delta = nmax - nmin
    if nmax != 0:
        s = delta / nmax
    else:
        s = 0
        h = -1
        return (h, s, v)  # Undefined case
    if nmax == nr:
        sector = (ng - nb) / delta
    elif nmax == ng:
        sector = 2.0 + (nb - nr) / delta
    else:
        sector = 4.0 + (nr - ng) / delta
    h = sector * 60.0
    if h < 0.0:
        h = h + 360
    return (h, s, v)
    
def rgbstring2hsv(s):
    (r, g, b) = string2rgb(s)
    return rgb2hsv(r, g, b)

# Blend two RGB string colors according to weight (between 0.0 and 1.0)
# Based on average of hsv values
def hsvblend(c1, c2, wt1):
    (h1, s1, v1) = rgbstring2hsv(c1)
    (h2, s2, v2) = rgbstring2hsv(c2)
    wt2 = 1.0 - wt1
    h = int(wt1 * h1 + wt2 * h2)
    s = int(wt1 * s1 + wt2 * s2)
    v = int(wt1 * v1 + wt2 * v2)
    return hsv2string(h, s, v)

# Blend two RGB string colors according to weight (between 0.0 and 1.0)
# Based on average of rgb values
def rgbblend(c1, c2, wt1):
    (r1, g1, b1) = string2rgb(c1)
    (r2, g2, b2) = string2rgb(c2)
    wt2 = 1.0 - wt1
    r = int(wt1 * r1 + wt2 * r2)
    g = int(wt1 * g1 + wt2 * g2)
    b = int(wt1 * b1 + wt2 * b2)
    return rgb2string(r, g, b)

# Blend two RGB string colors according to weight (between 0.0 and 1.0)
# Based on average of rgb values
def blend(c1, c2, wt1):
    return rgbblend(c1, c2, wt1)


# Linear interpolation: Mapping for [0,1] to [0,1]
# Give piecewise linear function as list of points:
# [(0,0), (x1,y1), (x2,y2), ..., (1,1)]
def interpolate(x, interp = [(0,0),(1,1)]):
    (x0, y0) = interp[0]
    (xend, yend) = interp[-1]
    if x <= x0:
        return y0
    if x >= xend:
        return yend
    (xlast, ylast) = (x0, y0)
    (xnext, ynext) = interp[1]
    i = 1
    while (x > xnext):
        (xlast, ylast) = (xnext, ynext)
        (xnext, ynext) = interp[i]
        i = i + 1
    yval = ylast + (ynext-ylast)*(x-xlast)/(xnext-xlast)
    return yval

# Convert list of hues into piecewise linear interpolation
def htointerp(hlist):
    n = len(hlist)
    hmax = hlist[-1]
    return [(i/float(n-1),float(hlist[i])/hmax) for i in range(0,n)]

# Hue values for standard colors
hred = 0
horange = 30
hyellow = 60
hgreen = 120
hsky = 185
hblue = 240
hindigo = 266
hviolet = 274

hroygbiv = [hred, horange, hyellow, hgreen, hblue, hindigo, hviolet]
hroygsbv = [hred, horange, hyellow, hgreen, hsky, hblue, hviolet]
hroygbv = [hred, horange, hyellow, hgreen, hblue, hviolet]

# Piecewise linear function based on spacing out ROYGBIV
roygbivinterp = htointerp(hroygbiv)

# Piecewise linear function based on spacing out ROYGBV
# no indigo
roygbvinterp = htointerp(hroygbv)

# Piecewise linear function based on spacing out ROYGSBV
# no indigo, add "sky blue"
roygsbvinterp = htointerp(hroygsbv)

# Custom spacing based on trial and error
myinterp = [(0,0), (0.25, 0.15), (0.45, 0.25), (0.60, 0.50),
            (0.75, 0.70), (0.90, 0.85), (1,1)]

standardinterp = roygsbvinterp

# Generate list of n rgb strings for rainbow, using mapping of spectrum
# Include possible piecewise linear interpolation
# Granularity g gives option of having g repeated copies of each color
def spectrum(n, s=1, v=1, interp = [], granularity = 1):
    global standardinterp
    global hlist
    if len(interp) == 0:
        interp = standardinterp
    ncolors = int((n + granularity - 1)/granularity)
    xdelta = 0 if ncolors <= 1 else 1.0/(ncolors-1)
    hlist = [274 * interpolate(int(i/granularity) * xdelta, interp) for i in range(0,n)]
    return [hsv2string(h, s, v) for h in hlist]

def valueToColor(x, xmin = 0.0, xmax = 1.0, s=1, v=1, interp = []):
    x = max(x, xmin)
    x = min(x, xmax)
    if len(interp) == 0:
        interp = standardinterp
    xnorm = (x - xmin)/(xmax-xmin)
    h = 274*xnorm
    return hsv2string(h, s, v)
        
    
    
