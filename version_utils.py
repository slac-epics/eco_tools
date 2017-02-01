#!/usr/bin/python
import os
import re
from repo_defaults import *
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

def getEnv( envVar ):
    result = os.getenv( envVar )
    if not result:
        result = '?'
    return result

def determine_epics_base_ver():
    # First look for EPICS_BASE_VER in the environment
    epics_base_ver = getEnv('EPICS_BASE_VER')
    # Then EPICS_VER
    if epics_base_ver == '?':
        epics_base_ver = getEnv('EPICS_VER')
    # Then BASE_MODULE_VERSION
    if epics_base_ver == '?':
        epics_base_ver = getEnv('BASE_MODULE_VERSION')
    if epics_base_ver == '?':
        # If we have EPICS_BASE, work back from there
        epics_base = getEnv('EPICS_BASE')
        if epics_base == '?':
            epics_base_ver = 'unknown'
        else:
            epics_base_ver = os.path.basename( epics_base )
    return epics_base_ver

def determine_epics_site_top():
    # First look for EPICS_TOP in the environment
    epics_site_top = getEnv('EPICS_TOP')
    # Then EPICS_SITE_TOP
    if epics_site_top == '?':
        epics_site_top = getEnv('EPICS_SITE_TOP')
    if epics_site_top == '?':
        # If we have EPICS_BASE, work back from there
        epics_base = getEnv('EPICS_BASE')
        if epics_base != '?':
            epics_base_top = os.path.dirname( epics_base )
            epics_site_top = os.path.dirname( epics_base_top )
            if epics_base.startswith( 'base-' ):
                epics_ver = epics_base.replace( 'base-', '' )
                epics_site_top = os.path.join( epics_site_top, epics_ver )
            if epics_base.startswith( 'R3.14.12-' ):
                epics_site_top = os.path.join( epics_site_top, '3.14' )
    if epics_site_top == '?':
        if os.path.isdir(    DEF_EPICS_TOP_PCDS ):
            epics_site_top = DEF_EPICS_TOP_PCDS 
        elif os.path.isdir(  DEF_EPICS_TOP_LCLS ):
            epics_site_top = DEF_EPICS_TOP_LCLS
        elif os.path.isdir(  DEF_EPICS_TOP_AFS ):
            epics_site_top = DEF_EPICS_TOP_AFS
    if epics_site_top == '?':
        epics_site_top = 'unknown'
    return epics_site_top

