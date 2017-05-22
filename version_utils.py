#!/usr/bin/env python
import os
import re
import sys
import dircache
import fileinput
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

# Raw string regular expression patterns
numberRawStr        = r"(\d+)"
releaseRawStr       = r"(|[a-zA-Z0-9_-]*-)R(\d+)[-_.](\d+)(.*)"
macroNameRawStr     = r"^\s*([a-zA-Z0-9_]*)\s*=\s*(\S*)\s*$"
moduleVersionRawStr = r"^\s*([a-zA-Z0-9_]*)_MODULE_VERSION\s*=\s*(\S*)\s*$"
epicsBaseVerRawStr  = r"^\s*([A-Za-z0-9_-]*BASE[A-Za-z0-9_-]*VER[SION]*)\s*=\s*(\S*)\s*$"
epicsModulesRawStr  = r"^\s*EPICS_MODULES\s*=\s*(\S*\s*)$"
modulesSiteTopRawStr= r"^\s*MODULES_SITE_TOP\s*=\s*(\S*\s*)$"
versionRawStr       = r"^\s*([A-Za-z0-9_-]*VERSION)\s*=\s*(\S*)\s*$"

# Pre-compile regular expressions for speed
numberRegExp        = re.compile( numberRawStr )
releaseRegExp       = re.compile( releaseRawStr )
macroNameRegExp     = re.compile( macroNameRawStr )
moduleVersionRegExp = re.compile( moduleVersionRawStr )
epicsBaseVerRegExp  = re.compile( epicsBaseVerRawStr )
epicsModulesRegExp  = re.compile( epicsModulesRawStr )
modulesSiteTopRegExp= re.compile( modulesSiteTopRawStr )
versionRegExp       = re.compile( versionRawStr )

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
    '''isPCDSPackage does a simple startswith /reg or /afs/slac/g/pcds check
    More tests can be added if needed.'''
    if path.startswith( '/reg' ) or path.startswith( '/afs/slac/g/pcds' ):
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
    else:
        print >> out_file, 'BASE_MODULE_VERSION=%s'%inputs['EPICS_BASE_VER']
    print >> out_file, 'EPICS_SITE_TOP=%s'    % inputs['EPICS_SITE_TOP'] 
    if 'BASE_SITE_TOP' in inputs:
        print >> out_file, 'BASE_SITE_TOP=%s'     % inputs['BASE_SITE_TOP']
    if VersionToRelNumber(inputs['EPICS_BASE_VER'], debug=debug) < 3.141205:
        print >> out_file, 'MODULES_SITE_TOP=%s'  % inputs['EPICS_MODULES']
    if VersionToRelNumber(inputs['EPICS_BASE_VER'], debug=debug) >= 3.141205:
        print >> out_file, 'EPICS_MODULES=%s'     % inputs['EPICS_MODULES']
    if 'IOC_SITE_TOP' in inputs:
        print >> out_file, 'IOC_SITE_TOP=%s'      % inputs['IOC_SITE_TOP']
    if VersionToRelNumber(inputs['EPICS_BASE_VER'], debug=debug) < 3.141205:
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
        package_site_top = '/afs/slac/g/lcls/package'
    if not os.path.isdir( package_site_top ):
        package_site_top = '/afs/slac/g/pcds/package'
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
            pspkg_root = '/afs/slac/g/lcls/pkg_mgr'
        if not os.path.isdir( pspkg_root ):
            pspkg_root = '/afs/slac/g/pcds/pkg_mgr'
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

def getEpicsPkgDependents( topDir, debug=False, verbose=False ):
    pkgDependents    = {}
    #if not module.startswith( "screens" ):
    if True:
        # Get the base and dependent modules from RELEASE files
        releaseFiles = []
        releaseFiles += [ os.path.join( topDir, "..", "..", "RELEASE_SITE" ) ]
        releaseFiles += [ os.path.join( topDir, "RELEASE_SITE" ) ]
        releaseFiles += [ os.path.join( topDir, "configure", "RELEASE" ) ]
        releaseFiles += [ os.path.join( topDir, "configure", "RELEASE.local" ) ]
        for releaseFile in releaseFiles:
            if debug:
                print "Checking release file: %s" % ( releaseFile )
            if not os.path.isfile( releaseFile ):
                continue
            for line in fileinput.input( releaseFile ):
                line = line.strip()
                if line.startswith( '#' ) or len(line) == 0:
                    continue
                for regExp in [ versionRegExp, epicsBaseVerRegExp ]:
                    m = regExp.search( line )
                    if m and m.group(1) and m.group(2):
                        macroName = m.group(1).replace( '_MODULE_VERSION', '' )
                        if macroName in macroNameToPkgName:
                            pkgName = macroNameToPkgName[macroName]
                            pkgDependents[ pkgName ] = m.group(2)
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

