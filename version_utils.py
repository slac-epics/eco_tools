#!/usr/bin/env python
#from __future__ import print_function
import os
import re
import sys
import glob
#import pprint
import subprocess
from pkgNamesToMacroNames import *
#
# Purpose:
#
#   Utilities for analyzing version and release tags
#
# Copyright 2016,2017,2018 Stanford University
# Author: Bruce Hill <bhill@slac.stanford.edu>
#
# Released under the GPLv2 licence <http://www.gnu.org/licenses/gpl-2.0.html>
#

epics7_submodules = [ "normativeTypesCPP", "pvAccessCPP", "pvDataCPP", "pvDatabaseCPP", "pva2pva", "pvaClient" ]

# Pre-compile regular expressions for speed
numberRegExp        = re.compile( r"(\d+)" )
releaseRegExp       = re.compile( r"(|[a-zA-Z0-9_-]*[-_])R(\d+)[-_.](\d+)(.*)" )
macroNameRegExp     = re.compile( r"^\s*([a-zA-Z0-9_]*)\s*=\s*(\S*)\s*$" )
condMacroRegExp     = re.compile( r"^(#*)\s*([a-zA-Z0-9_]+)\s*=\s*(\S*)\s*$" )
macroRefRegExp      = re.compile( r"^(.*)\$\(([a-zA-Z0-9_]+)\)(.*)$" )
moduleVersionRegExp = re.compile( r"^\s*([a-zA-Z0-9_]+)_MODULE_VERSION\s*=\s*(\S*)\s*$" )
epicsBaseVerRegExp  = re.compile( r"^\s*([A-Za-z0-9_-]*BASE[A-Za-z0-9_-]*VER[SION]*)\s*=\s*(\S*)\s*$" )
epicsModulesRegExp  = re.compile( r"^\s*EPICS_MODULES\s*=\s*(\S*\s*)$" )
modulesSiteTopRegExp= re.compile( r"^\s*MODULES_SITE_TOP\s*=\s*(\S*\s*)$" )
versionRegExp       = re.compile( r"^\s*([A-Za-z0-9_-]*VERSION)\s*=\s*(\S*)\s*$" )

def VersionToRelNumber( version, debug=False ):
    relNumber = 0.0
    try:
        ver = version
        if debug:
            print(("VersionToRelNumber: %s" % ( ver )))
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
        print(("VersionToRelNumber: %s = %f" % ( version, relNumber )))
    return relNumber

def isReleaseCandidate(release):
    if release.endswith( "FAILED" ):
        return False
    match = releaseRegExp.search( release )
    if match:
        return True

def isBaseTop(path):
    '''isBaseTop does a simple check for startup/EpicsHostArch.
    More tests can be added if needed.'''
    if os.path.isfile( os.path.join( path, 'startup', 'EpicsHostArch' ) ):
        return True
    return False

def isEpicsPackage(path):
    '''isEpicsPackage does a simple check for configure/RELEASE.
    More tests can be added if needed.'''
    if os.path.isfile( os.path.join( path, 'configure', 'RELEASE' ) ):
        return True
    return False

def get_base_versions( epics_site_top ):
    base_versions	= []
    base_candidates	= os.listdir( os.path.join( epics_site_top, 'base' ) )
    for base_candidate in base_candidates:
        if isBaseTop( os.path.join( epics_site_top, 'base', base_candidate ) ):
            base_versions.append( base_candidate )
    return base_versions

def determine_epics_base_ver():
    '''Returns EPICS base version string, or None if unable to derive.'''
    # If we have EPICS_BASE, work back from there
    epics_base = os.getenv('EPICS_BASE')
    if epics_base:
        epics_base_ver = os.path.basename( os.path.normpath(epics_base) )
        return epics_base_ver

    # If not, look for EPICS_BASE_VER in the environment
    epics_base_ver = os.getenv('EPICS_BASE_VER')
    # Then EPICS_VER
    if not epics_base_ver:
        epics_base_ver = os.getenv('EPICS_VER')
    # Then BASE_MODULE_VERSION
    if not epics_base_ver:
        epics_base_ver = os.getenv('BASE_MODULE_VERSION')

    # Returns None if not found
    return epics_base_ver

def strContainsMacros( strWithMacros ):
    macroMatch = macroRefRegExp.search( strWithMacros )
    if macroMatch:
        return True
    return False

def expandMacros( strWithMacros, macroDict ):
    while True:
        macroMatch = macroRefRegExp.search( strWithMacros )
        if not macroMatch:
            break
        macroName = macroMatch.group(2)
        if not macroName in macroDict:
            # No need to expand other macros in the string once one has failed
            break
        # Expand this macro and continue
        strWithMacros = macroMatch.group(1) + macroDict[macroName] + macroMatch.group(3)

    return strWithMacros

def getPkgReleaseList( top, pkgName ):
    '''For a given top directory, add pkgName to top and look
    for EPICS releases in that directory.
    Returns a sorted list of releases, most recent first.'''
    # Loop through the directories looking for releases
    if not os.path.isdir( top ):
        print(("getPkgReleaseList Error: top is not a directory: %s\n" % top))
    pkgDir = os.path.join( top, pkgName )
    if not os.path.isdir( pkgDir ):
        print(("getPkgReleaseList Error: %s is not a package under %s\n" % ( pkgName, top )))

    releaseList = [ ]
    for dirPath, dirs, files in os.walk( pkgDir, topdown=True ):
        if len( dirs ) == 0:
            continue
        if '.git' in dirs:
            dirs.remove( '.git' )
        if '.svn' in dirs:
            dirs.remove( '.svn' )
        if 'CVS' in dirs:
            dirs.remove( 'CVS' )
        releases = [ ]
        dirs.sort()
        for dir in dirs[:]:
            # Remove from list so we don't search recursively
            dirs.remove( dir )
            if not isReleaseCandidate(dir):
                continue
            release = os.path.join( dirPath, dir )
            verPath = os.path.join( release, "configure", "RELEASE" )

            buildPath = os.path.join( release, "build" )
            if os.path.isfile( verPath ) or os.path.isdir( buildPath ):
                releases += [ release ]

        if len( releases ) == 0:
            continue;

        # Create the release set so we can order the releases by version number
        releaseSet  = { }
        for release in releases:
            ( reldir, ver ) = os.path.split( release )
            relNumber = VersionToRelNumber( ver )
            while relNumber in releaseSet:
                relNumber -= 1e-12
            releaseSet[ relNumber ] = release

        for release in sorted( list(releaseSet.keys()), reverse = True ):
            releaseList += [ releaseSet[ release ] ]
    return releaseList

def getMacrosFromFile( filePath, macroDict, debug = False, required = False ):
    '''Find and return a dictionary of gnu make style macros
    found in a file.  Ex. macroDict['BASE_MODULE_VERSION'] = 'R3.15.5-1.0'
    '''
    if not os.path.isfile( filePath ):
        if required:
            print(("getMacrosFromFile Error: unable to open %s" % filePath)) 
        return macroDict
    if debug:
        print(("getMacrosFromFile %s: %d versions on entry" % ( filePath, len(macroDict) )))
    in_file = open( filePath, "r" )
    for line in in_file:
        line = line.strip()
        if line.startswith( '#' ) or len(line) == 0:
            continue
        if line.startswith( 'include' ) or line.startswith( '-include' ):
            if line.startswith( '-include' ):
                required = False
            else:
                required = True
            includeFileRefs = line.split()[1:]
            includeFiles = []
            # Expand macros and glob include file references
            for ref in includeFileRefs:
                ref = expandMacros( ref, macroDict )
                includeFiles += glob.glob( ref )
            # Recursively call getMacrosFromFile for each includeFile
            for includeFile in includeFiles:
                macroDict = getMacrosFromFile( includeFile, macroDict, debug, required )
            continue

        for regExp in [ macroNameRegExp, versionRegExp, epicsBaseVerRegExp ]:
            macroMatch = regExp.search( line )
            if not macroMatch:
                continue
            macroName  = macroMatch.group(1)
            macroValue = macroMatch.group(2)
            if macroName and macroValue:
                if debug:
                    print(("getMacrosFromFile: %s = %s" % ( macroName, macroValue )))
                macroDict[ macroName ] = macroValue
                break

    # Expand macro values
    for macroName in macroDict:
        macroValue = macroDict[macroName]
        macroDict[macroName] = expandMacros( macroValue, macroDict )

    if debug:
        print(("getMacrosFromFile %s: %d versions on exit" % ( filePath, len(macroDict) )))
    return macroDict

def getEpicsPkgDependents( topDir, debug=False ):
    '''Find and return a dictionary of EPICS package (modules and base) versions
    found in a release file.  Ex. pkgDependents['base'] = 'R3.15.5-1.0'
    '''
    macroDict = {}
    macroDict['TOP'] = topDir
    # Get the base and dependent modules from RELEASE files
    releaseFile = os.path.join( topDir, "configure", "RELEASE" )
    if debug:
        print(("getEpicsPkgDependents: Checking release file: %s" % ( releaseFile )))
    if os.path.isfile( releaseFile ):
        macroDict = getMacrosFromFile( releaseFile, macroDict, debug=debug )

    pkgDependents = {}
    epicsModules = None
    if 'EPICS_MODULES' in macroDict:
        epicsModules = macroDict[ 'EPICS_MODULES' ]
    for macroName in macroDict:
        if macroName.endswith( '_MODULE_VERSION' ):
            continue
        macroValue = macroDict[macroName]
        pkgName    = macroNameToPkgName(macroName)
        if not pkgName:
            continue
        if pkgName == 'base':
            pkgVersion = os.path.split( macroValue )[-1]
        elif epicsModules and macroValue.startswith( epicsModules ):
            macroValue = macroValue.replace( epicsModules, '' )
            pkgVersion = os.path.split( macroValue )[-1]
        else:
            # Just show the last 4 levels of arbitrary paths:w
            pkgVersion = '/'.join( macroValue.split('/')[-3:] )
        if pkgName and pkgVersion:
            if debug:
                print(("getEpicsPkgDependents: %s = %s" % ( pkgName, pkgVersion )))
            pkgDependents[ pkgName ] = pkgVersion

    if "base" in pkgDependents:
        baseVersion = pkgDependents["base"]
        if VersionToRelNumber(baseVersion) >= 7:
            # Strip out epics7 submodules
            for m in epics7_submodules:
                if m in pkgDependents:
                    del pkgDependents[m]

    return pkgDependents

def pkgSpecToMacroVersions( pkgSpec, verbose=False ):
    """
    Convert the pkgSpec into a dictionary of macroVersions
    Each macroVersion entry maps macroName to version
    """
    macroVersions = {}
    ( pkgPath, pkgVersion ) = os.path.split( pkgSpec )
    pkgName = os.path.split( pkgPath )[1]
    macroNames = pkgNameGetMacroNames( pkgName )
    for macroName in macroNames:
        macroVersions[ macroName ] = pkgVersion
    return macroVersions

# Check if any file inside configure/ has included a ../../RELEASE_SITE file
def hasIncludeDotDotReleaseSite():
    if not os.path.isdir( 'configure' ):
        return False
    # Just check configure/RELEASE and configure/RELEASE.local
    for filename in [ 'RELEASE', 'RELEASE.local' ]:
        configFilePath = os.path.join( 'configure', filename )
        if not os.path.isfile( configFilePath ):
            continue
        configFile = open( configFilePath, 'r')
        for line in configFile:
            # Check included ../../RELEASE_SITE file unless it is commented
            if re.search('^[^\#]include(.*)/../../RELEASE_SITE', line):
                return True
    return False

def doesPkgNeedMacro( macroName ):
    '''
    Check if configure/RELEASE* files need a particular macro
    '''
    if not macroName or len(macroName) == 0:
        return False
    # TODO: Check all configure/RELEASE* files
    definesMacro = False
    needsMacro = False
    definesMacroRegExp = re.compile( '^%s\s*=\s*\S' % macroName )
    needsMacroRegExp   = re.compile( '\$\(' + macroName )
    for filename in [ 'RELEASE', 'RELEASE.local' ]:
        configFilePath = os.path.join( 'configure', filename )
        if not os.path.isfile( configFilePath ):
            continue
        configFile = open( configFilePath, 'r')
        for line in configFile:
            # Check if this macro is used
            if  needsMacroRegExp.search( line ):
                needsMacro = True
            # Check if this macro is defined
            if  definesMacroRegExp.search( line ):
                definesMacro = True

    if needsMacro and definesMacro:
        needsMacro = False
    return needsMacro

def ExpandPackagePath( topDir, pkgSpec, base=None, debug=False ):
    '''Takes a topDir directory path and looks for packages which match the pkgSpec.
    The pkgSpec can be "modules", "ioc", "ioc/common", "ioc/$AREA", "$MODULE_NAME",
    or "$MODULE_NAME/$MODULE_VERSION".
    Returns a list of release paths.
    Looks for file system paths which match one of the following:
        topDir/pkgSpec
        topDir/base/pkgSpec
        topDir/base/modules/pkgSpec
        topDir/modules/pkgSpec
    If that directory exists and satisfies the isReleaseCandidate() test,
    or any sub-directory of that directory satisfies IsReleaseCandidate(),
    it is added to a list of release paths which is returned.
    '''
    # See if "modules" is in both parts of the path
    if "modules" in topDir and "modules" in pkgSpec:
        topDir = os.path.dirname( topDir )

    # Create the path to package
    pkgPath = os.path.join( topDir, pkgSpec )

    if not os.path.isdir( pkgPath ) and base:
        if not base in topDir:
            topDir = os.path.join( topDir, base )
        if not "modules" in topDir and not "modules" in pkgSpec:
            topDir = os.path.join( topDir, "modules" )
        modPath = os.path.join( topDir, pkgSpec )
        if os.path.isdir( modPath ):
            pkgPath = modPath

    if not os.path.isdir( pkgPath ):
        if not "modules" in topDir and not "modules" in pkgSpec:
            topDir = os.path.join( topDir, "modules" )
        pkgPath = os.path.join( topDir, pkgSpec ) 

    # See if it exists
    if not os.path.isdir( pkgPath ):
        if debug:
            print(("ExpandPackagePath: %s not found" % ( pkgPath )))
        return []

    # See if this is a screens release
    screenArg   = False
    if "screens" in pkgPath:
        screenArg   = True

    if debug:
        print(("ExpandPackagePath: Expanding %s ..." % ( pkgPath )))

    selectedReleases = [ ]
    if isReleaseCandidate( os.path.split( pkgPath )[-1] ):
        selectedReleases += [ pkgPath ]
    else:
        for dirPath, dirs, files in os.walk( pkgPath, topdown=True ):
            if len( dirs ) == 0:
                continue
            if '.git' in dirs:
                dirs.remove( '.git' )
            if '.svn' in dirs:
                dirs.remove( '.svn' )
            if 'CVS' in dirs:
                dirs.remove( 'CVS' )

            # Loop through the directories looking for releases
            releases = [ ]
            dirs.sort()
            for dir in dirs[:]:
                if dirPath != pkgPath:
                    # Remove from list so we don't search recursively beyond one level
                    dirs.remove( dir )
                if not isReleaseCandidate(dir):
                    continue
                release = os.path.join( dirPath, dir )
                if screenArg:
                    verPath = os.path.join( release, "Makefile" )
                else:
                    verPath = os.path.join( release, "configure", "RELEASE" )

                buildPath = os.path.join( release, "build" )
                if os.path.isfile( verPath ) or os.path.isdir( buildPath ):
                    if debug:
                        print(("ExpandPackagePath: Found ", release))
                    releases += [ release ]

            if len( releases ) == 0:
                continue;

            # Create the release set so we can order the releases by version number
            releaseSet  = { }
            for release in releases:
                ( reldir, ver ) = os.path.split( release )
                relNumber = VersionToRelNumber( ver )
                while relNumber in releaseSet:
                    relNumber -= 1e-12
                releaseSet[ relNumber ] = release

            #if debug:
            #   print "ExpandPackagePath Module Releases: "
            #   pp.pprint( releaseSet )

            for release in sorted( list(releaseSet.keys()), reverse = True ):
                selectedReleases += [ releaseSet[ release ] ]

    if debug:
        print(("ExpandPackagePath Selected Releases: %s" % selectedReleases ))
    return selectedReleases

