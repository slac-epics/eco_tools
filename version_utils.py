#!/usr/bin/python
import re
#
# Purpose:
#
#   Utilities for analyzing version and release tags
#
# Copyright 2016 Stanford University
# Author: Bruce Hill <bhill@slac.stanford.edu>
#
# Released under the GPLv2 licence <http://www.gnu.org/licenses/gpl-2.0.html>
#

# Pre-compile regular expressions for speed
numberRegExp        = re.compile( r"(\d+)" )
releaseRegExp       = re.compile( r"([^0-9]*)R(\d+)[-_.](\d+)(.*)" )

def VersionToRelNumber( version, debug=False ):
    relNumber = 0.0
    try:
        ver = version
        if debug:
            print "VersionToRelNumber: %s" % ( ver )
        verMatch = releaseRegExp.search( ver )
        if verMatch:
            ver = verMatch.group(2) + '.' + verMatch.group(3) + verMatch.group(4)
        ver = ver.replace( '-', '.' )
        ver = ver.replace( '_', '.' )
        verNumbers = ver.split( '.' )
        scale = 1.0
        for n in verNumbers:
            m = numberRegExp.search( n )
            if m and m.group(1):
                relNumber += float(m.group(1)) / scale
            scale *= 100.0
    except:
        pass
    if debug:
        print "VersionToRelNumber: %s = %f" % ( version, relNumber )
    return relNumber

def isReleaseCandidate(release):
    match = releaseRegExp.search( release )
    if match:
        return True

