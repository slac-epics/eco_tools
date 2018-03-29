#!/usr/bin/env python
import os
import re
import sys
import json
import dircache
import glob
import subprocess
from repo_defaults import *
from pkgNamesToMacroNames import *
#
# Purpose:
#
#   Utilities for analyzing version and release tags
#
# Copyright 2016,2017 Stanford University
# Author: Bruce Hill <bhill@slac.stanford.edu>
#
# Released under the GPLv2 licence <http://www.gnu.org/licenses/gpl-2.0.html>
#


# Pre-compile regular expressions for speed
numberRegExp        = re.compile( r"(\d+)" )
releaseRegExp       = re.compile( r"(|[a-zA-Z0-9_-]*-)R(\d+)[-_.](\d+)(.*)" )
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

def isPCDSPath(path):
    '''isPCDSPackage does a couple of simple path.startswith string comparisons
    More tests can be added if needed.'''
    if path.startswith( DEF_EPICS_TOP_PCDS ):
        return True
    if path.startswith( '/afs/slac/g/pcds' ): # /afs/slac symbolic link might be part of pcds pathnames
        return True
    if path.startswith( DEF_EPICS_TOP_PCDS ):
        return True
    return False

def get_base_versions( epics_site_top ):
    base_versions	= []
    base_candidates	= dircache.listdir( os.path.join( epics_site_top, 'base' ) )
    for base_candidate in base_candidates:
        if isBaseTop( os.path.join( epics_site_top, 'base', base_candidate ) ):
            base_versions.append( base_candidate )
    return base_versions

def getEnv( envVar ):
    result = os.getenv( envVar )
    if not result:
        result = '?'
    return result

def determine_epics_base_ver():
    '''Returns EPICS base version string, or None if unable to derive.'''
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
        if epics_base != '?':
            epics_base_ver = os.path.basename( epics_base )
        else:
            # Returns None if not found
            epics_base_ver = None
    return epics_base_ver

def determine_epics_site_top():
    '''Returns string w/ a directory name for EPICS site top, or None if unable to derive.'''
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
    if  epics_site_top == '?':
        epics_site_top = None
    return epics_site_top

def determine_epics_modules_top():
    # First look for EPICS_MODULES_TOP in the environment
    epics_modules_top = getEnv('EPICS_MODULES_TOP')
    if epics_modules_top == '?':
        epics_base_ver = determine_epics_base_ver()
        epics_site_top = determine_epics_site_top()
        if not epics_base_ver or not epics_site_top:
            print "determine_epics_modules_top Error: Unable to determine EPICS_MODULES_TOP!"
            return None
        if epics_base_ver.startswith( 'base-' ):
            epics_base_ver = epics_base_ver.replace( 'base-', '' )
        epics_modules_top = os.path.join( epics_site_top, epics_base_ver, 'modules' )
        if not os.path.isdir( epics_modules_top ):
            epics_modules_top = os.path.join( epics_site_top, 'modules' )
        if not os.path.isdir( epics_modules_top ):
            print "determine_epics_modules_top Error: Unable to determine valid EPICS_MODULES_TOP!"
            epics_modules_top = None
    return epics_modules_top

def determine_epics_host_arch():
    '''Returns string w/ EPICS host arch, or None if unable to derive.'''
    # First look for EPICS_HOST_ARCH in the environment
    epics_host_arch = getEnv('EPICS_HOST_ARCH')
    if epics_host_arch == '?':
        epics_site_top = determine_epics_site_top()
        epics_base_ver = determine_epics_base_ver()
        if epics_site_top is not None and epics_base_ver is not None:
            epicsHostArchPath	= os.path.join(	epics_site_top, 'base',
                                                epics_base_ver, 'startup', 'EpicsHostArch' )
            if os.path.isfile( epicsHostArchPath ):
                cmdOutput = subprocess.check_output( [ epicsHostArchPath ] ).splitlines()
                if len(cmdOutput) == 1:
                    epics_host_arch = cmdOutput[0]
    if  epics_host_arch == '?':
        epics_host_arch = None
    return epics_host_arch

def export_release_site_file( inputs, debug=False):
    """
    Use the contents of a dictionary of top level dirs to create a 
    RELEASE_SITE dir in a specified dir
    """

    #out_file = sys.stdout for testing 

    output_file_and_path = './RELEASE_SITE'
    try:
        out_file = open(output_file_and_path, 'w')
    except IOError, e:
        sys.stderr.write('Could not open "%s": %s\n' % (output_file_and_path, e.strerror))
        return None

    print >> out_file, '#=============================================================================='
    if VersionToRelNumber(inputs['EPICS_BASE_VER'], debug=debug) < 3.141205:
        print >> out_file, '#RELEASE Location of external products'
    else:
        print >> out_file, '# RELEASE_SITE Location of EPICS_SITE_TOP, EPICS_MODULES, and BASE_MODULE_VERSION'
    print >> out_file, '# Run "gnumake clean uninstall install" in the application'
    print >> out_file, '# top directory each time this file is changed.'
    print >> out_file, ''
    print >> out_file, '#=============================================================================='
    if VersionToRelNumber(inputs['EPICS_BASE_VER'], debug=debug) < 3.141205:
        print >> out_file, '# Define the top of the EPICS tree for your site.'
        print >> out_file, '# We will build some tools/scripts that allow us to'
        print >> out_file, '# change this easily when relocating software.'
        print >> out_file, '#=============================================================================='
        if doesPkgNeedMacro( 'BASE_MODULE_VERSION' ):
            print >> out_file, 'BASE_MODULE_VERSION=%s'%inputs['EPICS_BASE_VER']
    else:
        print >> out_file, 'BASE_MODULE_VERSION=%s'%inputs['EPICS_BASE_VER']
    print >> out_file, 'EPICS_SITE_TOP=%s'    % inputs['EPICS_SITE_TOP'] 
    if 'BASE_SITE_TOP' in inputs:
        print >> out_file, 'BASE_SITE_TOP=%s'     % inputs['BASE_SITE_TOP']
    if VersionToRelNumber(inputs['EPICS_BASE_VER'], debug=debug) < 3.141205 \
        or doesPkgNeedMacro( 'MODULES_SITE_TOP' ):
        print >> out_file, 'MODULES_SITE_TOP=%s'  % inputs['EPICS_MODULES']
    if VersionToRelNumber(inputs['EPICS_BASE_VER'], debug=debug) >= 3.141205 \
        or doesPkgNeedMacro( 'EPICS_MODULES' ):
        print >> out_file, 'EPICS_MODULES=%s'     % inputs['EPICS_MODULES']
    if 'IOC_SITE_TOP' in inputs:
        print >> out_file, 'IOC_SITE_TOP=%s'      % inputs['IOC_SITE_TOP']
    if VersionToRelNumber(inputs['EPICS_BASE_VER'], debug=debug) < 3.141205 \
        or doesPkgNeedMacro( 'EPICS_BASE_VER' ):
        print >> out_file, 'EPICS_BASE_VER=%s' %inputs['EPICS_BASE_VER']
    print >> out_file, 'PACKAGE_SITE_TOP=%s'  % inputs['PACKAGE_SITE_TOP']
    if 'PSPKG_ROOT' in inputs:
        print >> out_file, 'PSPKG_ROOT=%s'        % inputs['PSPKG_ROOT']
    if 'TOOLS_SITE_TOP' in inputs:
        print >> out_file, 'TOOLS_SITE_TOP=%s'    % inputs['TOOLS_SITE_TOP']
    if 'ALARM_CONFIGS_TOP' in inputs:
        print >> out_file, 'ALARM_CONFIGS_TOP=%s' % inputs['ALARM_CONFIGS_TOP']
    print >> out_file, '#=============================================================================='
    if out_file != sys.stdout:
        out_file.close()

def assemble_release_site_inputs( batch=False ):

    input_dict = {}

    epics_base_ver = determine_epics_base_ver()
    epics_site_top = determine_epics_site_top()

    if not epics_base_ver:
        # base_versions = get_base_versions( epics_site_top )
        print 'TODO: Provide list of available epics_base_ver options to choose from'
        epics_base_ver = 'unknown-base-ver'
    input_dict['EPICS_BASE_VER'] = epics_base_ver
    if not batch:
        prompt5 = 'Enter EPICS_BASE_VER or [RETURN] to use "' + epics_base_ver + '">'
        user_input = raw_input(prompt5).strip()
        if user_input:
            input_dict['EPICS_BASE_VER'] = user_input
    print 'Using EPICS_BASE_VER: ' + input_dict['EPICS_BASE_VER']

    # TODO: Substitute input_dict['EPICS_BASE_VER'] for any substrings below that match
    # the default epics_base_ver we got from the environment before prompting the user.
    # That way users can easily change the base version in one place

    if not epics_site_top:
        epics_site_top = 'unknown-epics-site-top'
    input_dict['EPICS_SITE_TOP'] = epics_site_top
    if not batch:
        prompt1 = 'Enter full path for EPICS_SITE_TOP or [RETURN] to use "' + epics_site_top + '">'
        user_input = raw_input(prompt1).strip()
        if user_input:
            input_dict['EPICS_SITE_TOP'] = user_input
    print 'Using EPICS_SITE_TOP: ' + input_dict['EPICS_SITE_TOP']

    input_dict['BASE_SITE_TOP'] = os.path.join( input_dict['EPICS_SITE_TOP'], 'base' )
    print 'Using BASE_SITE_TOP: ' + input_dict['BASE_SITE_TOP']

    epics_modules_ver = input_dict['EPICS_BASE_VER']
    if epics_modules_ver.startswith( 'base-' ):
        epics_modules_ver = epics_modules_ver.replace( 'base-', '' )

    epics_modules = getEnv('EPICS_MODULES_TOP')
    if os.path.isdir( epics_modules ):
        input_dict['EPICS_MODULES'] = epics_modules
    else:
        epics_modules = os.path.join( input_dict['EPICS_SITE_TOP'], epics_modules_ver, 'modules' )
        if not os.path.isdir( epics_modules ):
            epics_modules = os.path.join( epics_site_top, 'modules' )
        input_dict['EPICS_MODULES'] = epics_modules
    if not batch:
        prompt5 = 'Enter full path for EPICS_MODULES or [RETURN] to use "' + input_dict['EPICS_MODULES'] + '">'
        user_input = raw_input(prompt5).strip()
        if user_input:
            input_dict['EPICS_MODULES'] = user_input
    print 'Using EPICS_MODULES: ' + input_dict['EPICS_MODULES']

    ioc_site_top = os.path.join( input_dict['EPICS_SITE_TOP'], 'iocTop' )
    if os.path.isdir( ioc_site_top ):
        input_dict['IOC_SITE_TOP'] = ioc_site_top
        print 'Using IOC_SITE_TOP: ' + input_dict['IOC_SITE_TOP']

    package_site_top = getEnv('PACKAGE_TOP')
    if not os.path.isdir( package_site_top ):
        package_site_top = getEnv('PACKAGE_SITE_TOP')
    if not os.path.isdir( package_site_top ):
        package_site_top = '/reg/g/pcds/package'
    if not os.path.isdir( package_site_top ):
        package_site_top = '/afs/slac.stanford.edu/g/lcls/package'
    if not os.path.isdir( package_site_top ):
        package_site_top = '/afs/slac.stanford.edu/g/pcds/package'
    input_dict['PACKAGE_SITE_TOP'] = package_site_top
    if not batch:
        prompt6 = 'Enter full path for PACKAGE_SITE_TOP or [RETURN] to use "' + package_site_top + '">'
        user_input = raw_input(prompt6).strip()
        if user_input:
            input_dict['PACKAGE_SITE_TOP'] = user_input
    print 'Using PACKAGE_SITE_TOP: ' + input_dict['PACKAGE_SITE_TOP']

    if VersionToRelNumber(input_dict['EPICS_BASE_VER']) >= 3.141205:
        pspkg_root = getEnv('PSPKG_ROOT')
        if not os.path.isdir( pspkg_root ):
            pspkg_root = '/reg/g/pcds/pkg_mgr'
        if not os.path.isdir( pspkg_root ):
            pspkg_root = '/afs/slac.stanford.edu/g/lcls/pkg_mgr'
        if not os.path.isdir( pspkg_root ):
            pspkg_root = '/afs/slac.stanford.edu/g/pcds/pkg_mgr'
        print 'Using PSPKG_ROOT:', pspkg_root
        input_dict['PSPKG_ROOT'] = pspkg_root

    input_dict['TOOLS_SITE_TOP'] = ''
    input_dict['ALARM_CONFIGS_TOP'] = ''
    tools_site_top = getEnv('TOOLS')
    if os.path.isdir(tools_site_top):
        input_dict['TOOLS_SITE_TOP'] = tools_site_top
        if not batch:
            prompt6 = 'Enter full path for TOOLS_SITE_TOP or [RETURN] to use "' + tools_site_top + '">'
            user_input = raw_input(prompt6).strip()
            if user_input:
                input_dict['TOOLS_SITE_TOP'] = user_input
        if os.path.isdir( input_dict['TOOLS_SITE_TOP'] ):
            print 'Using TOOLS_SITE_TOP: ' + input_dict['TOOLS_SITE_TOP']

            alarm_configs_top = os.path.join( input_dict['TOOLS_SITE_TOP'], 'AlarmConfigsTop' )
            input_dict['ALARM_CONFIGS_TOP'] = alarm_configs_top
            if not batch:
                prompt6 = 'Enter full path for ALARM_CONFIGS_TOP or [RETURN] to use "' + alarm_configs_top + '">'
                user_input = raw_input(prompt6).strip()
                if user_input:
                    input_dict['ALARM_CONFIGS_TOP'] = user_input
            if os.path.isdir( input_dict['ALARM_CONFIGS_TOP'] ):
                print 'Using ALARM_CONFIGS_TOP: ' + input_dict['ALARM_CONFIGS_TOP']

    return input_dict

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
        print "getPkgReleaseList Error: top is not a directory: %s\n" % top
    pkgDir = os.path.join( top, pkgName )
    if not os.path.isdir( pkgDir ):
        print "getPkgReleaseList Error: %s is not a package under %s\n" % ( pkgName, top )

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

        for release in sorted( releaseSet.keys(), reverse = True ):
            releaseList += [ releaseSet[ release ] ]
    return releaseList

def getMacrosFromFile( filePath, macroDict, debug = False ):
    '''Find and return a dictionary of gnu make style macros
    found in a file.  Ex. macroDict['BASE_MODULE_VERSION'] = 'R3.15.5-1.0'
    '''
    if not os.path.isfile( filePath ):
        print "getMacrosFromFile Error: unable to open %s" % filePath 
        return -1
    if debug:
        print "getMacrosFromFile %s: %d versions on entry" % ( filePath, len(macroDict) )
    in_file = open( filePath, "r" )
    for line in in_file:
        line = line.strip()
        if line.startswith( '#' ) or len(line) == 0:
            continue
        if line.startswith( 'include' ) or line.startswith( '-include' ):
            includeFileRefs = line.split()[1:]
            includeFiles = []
            # Expand macros and glob include file references
            for ref in includeFileRefs:
                ref = expandMacros( ref, macroDict )
                includeFiles += glob.glob( ref )
            # Recursively call getMacrosFromFile for each includeFile
            for includeFile in includeFiles:
                macroDict = getMacrosFromFile( includeFile, macroDict, debug )
            continue

        for regExp in [ macroNameRegExp, versionRegExp, epicsBaseVerRegExp ]:
            macroMatch = regExp.search( line )
            if not macroMatch:
                continue
            macroName  = macroMatch.group(1)
            macroValue = macroMatch.group(2)
            if macroName and macroValue:
                if debug:
                    print "getMacrosFromFile: %s = %s" % ( macroName, macroValue )
                macroDict[ macroName ] = macroValue
                break

    # Expand macro values
    for macroName in macroDict:
        macroValue = macroDict[macroName]
        macroDict[macroName] = expandMacros( macroValue, macroDict )

    if debug:
        print "getMacrosFromFile %s: %d versions on exit" % ( filePath, len(macroDict) )
    return macroDict

def getEpicsPkgDependents( topDir, debug=False ):
    '''Find and return a dictionary of EPICS package (modules and base) versions
    found in a release file.  Ex. pkgDependents['base'] = 'R3.15.5-1.0'
    '''
    macroDict = {}
    macroDict['TOP'] = topDir
    # Get the base and dependent modules from RELEASE files
    releaseFiles = [ os.path.join( topDir, "configure", "RELEASE" ) ]
    #releaseFiles += [ os.path.join( topDir, "..", "..", "RELEASE_SITE" ) ]
    #releaseFiles += [ os.path.join( topDir, "RELEASE_SITE" ) ]
    #releaseFiles += [ os.path.join( topDir, "configure", "RELEASE.local" ) ]
    for releaseFile in releaseFiles:
        if debug:
            print "getEpicsPkgDependents: Checking release file: %s" % ( releaseFile )
        if not os.path.isfile( releaseFile ):
            continue
        macroDict = getMacrosFromFile( releaseFile, macroDict, debug=debug )
        #pkgDependents.update( releaseVersions )
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
                print "getEpicsPkgDependents: %s = %s" % ( pkgName, pkgVersion )
            pkgDependents[ pkgName ] = pkgVersion

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

def update_pkg_dep_file( filePath, oldMacroVersions, newMacroVersions, verbose=False ):
    """
    update_pkg_dep_file(
        filePath,		 	#  path to file
        oldMacroVersions,	#  dict of old macro versions: macroVersion[macroName] = version
        newMacroVersions,	#  dict of new macro versions: macroVersion[macroName] = version
        verbose=False		#  show progress )
    Update the specified package dependencies, (module or base versions).
    newMacroVersions can specify a subset of the old macroNames
    Checks and updates the specfied file if needed.
    Returns 1 if modified, else 0
    """
    using_MODULE_VERSION = {}
    definedModules = {}
    using_BASE_MODULE_VERSION = False
    using_EPICS_BASE_VER = False
    modified   = False
    lineCache  = []
    in_file = open( filePath, "r" )
    for line in in_file:
        strippedLine = line.strip()
        if len(strippedLine) == 0:
            lineCache += line
            continue

        # XXX_MODULE_VERSION = YYYYYYYYY
        match = moduleVersionRegExp.search( line )
        if match:
            macroName  = match.group(1)
            oldVersion = match.group(2)
            if macroName in newMacroVersions:
                newVersion = newMacroVersions[macroName]
                if newVersion != oldVersion:
                    line = string.replace( line, oldVersion, newMacroVersions[macroName] )
                    modified = True
                if macroName == "BASE":
                    using_BASE_MODULE_VERSION = True
                else:
                    using_MODULE_VERSION[macroName] = True
            lineCache += line
            continue

        # #* XXX = YYYYYYYYYYYYYYYYYYYYYYYYYYYY
        # Matches any macro definition, even if commented out
        match = condMacroRegExp.search( line )
        if not match:
            lineCache += line
            continue

        originalLine   = match.group(0)
        commentedOut   = match.group(1).startswith('#')
        macroName      = match.group(2)
        oldVersionPath = match.group(3)
        if macroName in newMacroVersions:
            pkgName = macroNameToPkgName(macroName)
            if not pkgName:
                continue
            if using_MODULE_VERSION.get( macroName, False ):
                newVersionPath = "$(EPICS_MODULES)/%s/$(%s_MODULE_VERSION)" % ( pkgName, macroName )
            else:
                newVersionPath = "$(EPICS_MODULES)/%s/%s" % ( pkgName, newMacroVersions[macroName] )
            if macroName in definedModules:
                # We've already defined this macroName
                if not commentedOut:
                    # Comment out subsequent definitions
                    line = string.replace( line, originalLine, '#' + originalLine )
                    modified = True
            else:
                definedModules[macroName] = newVersionPath
                if commentedOut:
                    # Uncomment the line
                    line = string.strip( line, '# ' )
                    modified = True
                if oldVersionPath != newVersionPath:
                    line = string.replace( line, oldVersionPath, newVersionPath )
                    modified = True

        if not "BASE" in newMacroVersions:
            lineCache += line
            continue

        # Handle BASE related macros
        if not macroName in [ "EPICS_BASE", "EPICS_BASE_VER", "EPICS_MODULES", "MODULES_SITE_TOP" ]:
            lineCache += line
            continue

        newBaseVersion = newMacroVersions["BASE"]
        oldBaseVersion = oldMacroVersions["BASE"]
        if oldBaseVersion == newBaseVersion:
            lineCache += line
            continue

        if VersionToRelNumber(newBaseVersion) < 3.141205:
            baseDirName = "base-%s" % newBaseVersion
        else:
            baseDirName = newBaseVersion

        if VersionToRelNumber(oldBaseVersion) >= 3.141205:
            # For these, just replace all old instances of base version w/ new version
            line = string.replace( line, oldBaseVersion, newBaseVersion )
            if newBaseVersion in line:
                modified = True
                lineCache += line
                continue

            if	   "EPICS_BASE_VER" in oldVersionPath \
                or "BASE_MODULE_VERSION" in oldVersionPath:
                lineCache += line
                continue

        # Handle fixing unusual paths
        if macroName == "EPICS_BASE_VER":
            line = string.replace( line, oldVersionPath, baseDirName )
            modified = True

        if macroName == "EPICS_BASE":
            if   "BASE_MODULE_VERSION" in oldVersionPath:
                newVersionPath = "$(EPICS_SITE_TOP)/base/$(BASE_MODULE_VERSION)"
            elif "EPICS_BASE_VER" in oldVersionPath:
                newVersionPath = "$(EPICS_SITE_TOP)/base/$(EPICS_BASE_VER)"
            else:
                newVersionPath = "$(EPICS_SITE_TOP)/base/%s" % baseDirName 
            if oldVersionPath != newVersionPath:
                line = string.replace( line, oldVersionPath, newVersionPath )
                modified = True

        if macroName == "EPICS_MODULES" or macroName == "MODULES_SITE_TOP":
            if   "BASE_MODULE_VERSION" in oldVersionPath:
                newVersionPath = "$(EPICS_SITE_TOP)/$(BASE_MODULE_VERSION)/modules"
            else:
                newVersionPath = "$(EPICS_SITE_TOP)/%s/modules" % newBaseVersion
            if oldVersionPath != newVersionPath:
                line = string.replace( line, oldVersionPath, newVersionPath )
                modified = True

        lineCache += line
        continue

    in_file.close()
    if not modified:
        if verbose:
            print "%s, No change" %  filePath
        return 0

    # Replace prior version w/ updates
    try:
        os.remove( filePath )
        out_file = open( filePath, 'w' )
        out_file.writelines( lineCache )
        out_file.close()
    except OSError, e:
        sys.stderr.write( 'Could not remove "%s": %s\n' % ( filePath, e.strerror ) )
        return 0
    except IOError, e:
        sys.stderr.write( 'Could not replace "%s": %s\n' % ( filePath, e.strerror ) )
        return 0
    print "%s, UPDATED" %  filePath
    return 1

def update_pkg_dependency( topDir, pkgSpecs, debug=False, verbose=False ):
    """
    update_pkg_dependency(
        topDir,			#  path to top directory of epics package
        pkgSpecs,       #  array of pkg specification strings: pkgPath/pkgVersion, ex asyn/R4.31
        verbose=False   #  show progress )
    Update the specified package dependencies, (module or base versions).
    Checks and updates as needed:
        TOP/RELEASE_SITE
        TOP/configure/RELEASE
        TOP/configure/RELEASE.local
    Returns count of how many files were updated.
    """
    # Check for a valid top directory
    if not os.path.isdir( topDir ):
        print "update_pkg_dependency: Invalid topDir: %s" % topDir
        return 0
    if verbose:
        print "update_pkg_dependency: %s" % topDir

    # Get current pkgSpecs
    oldPkgDependents = getEpicsPkgDependents( topDir, debug=debug )
    oldMacroVersions = {}
    for pkgName in oldPkgDependents:
        pkgSpec = pkgName + "/" + oldPkgDependents[pkgName]
        if verbose:
            print "OLD: %s" % pkgSpec
        oldMacroVersions.update( pkgSpecToMacroVersions( pkgSpec ) )
    if len(oldMacroVersions) == 0:
        print "update_pkg_dependency error: No pkgSpecs found under topDir:\n%s" % topDir
        return 0

    # Convert the list of pkgSpecs into a list of macroVersions
    # Each macroVersion is a tuple of ( macroName, version )
    newMacroVersions = {}
    for pkgSpec in pkgSpecs:
        if verbose:
            print "NEW: %s" % pkgSpec
        newMacroVersions.update( pkgSpecToMacroVersions( pkgSpec ) )
    if len(newMacroVersions) == 0:
        print "update_pkg_dependency error: No valid converions for pkgSpecs:"
        print pkgSpecs
        return 0

    count = 0

    for fileName in [	"RELEASE_SITE",
                        os.path.join( "configure", "RELEASE" ),
                        os.path.join( "configure", "RELEASE.local" ) ]:
        filePath = os.path.join( topDir, fileName )
        if os.access( filePath, os.R_OK ):
            count += update_pkg_dep_file( filePath, oldMacroVersions, newMacroVersions, verbose )
    return count

def get_cram_releaseDir( ):
    packageInfo = None
    packageInfoFile = '.cram/packageinfo'
    if os.path.isfile( packageInfoFile ):
        try:
            with open( packageInfoFile, 'r' ) as pkgInfoFp:
                packageInfo = json.load( pkgInfoFp )
        except:
            pass
    if not packageInfo:
        return None

    facilityConfigFile = None
    if os.path.isfile( DEF_LCLS_CRAM_USER ):
        facilityConfigFile = DEF_LCLS_CRAM_USER
    elif os.path.isfile( DEF_LCLS_CRAM_CFG ):
        facilityConfigFile = DEF_LCLS_CRAM_CFG
    if not facilityConfigFile:
        return None
    
    facilityConfigDict = None
    try:
        with open( facilityConfigFile, 'r' ) as facilityFp:
            facilityConfig = json.load( facilityFp )
            facilityConfigDict = {}
            for facility in facilityConfig:
                facilityConfigDict[ facility['name'] ] = facility
    except:
        pass
    if not facilityConfigDict:
        return None

    releaseDir = None
    try:
        releaseDir = facilityConfigDict['Dev'][ packageInfo['type'] ]['releaseFolder']
        releaseDir += '/'
        releaseDir += packageInfo['name']
    except:
        pass
    return releaseDir

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
