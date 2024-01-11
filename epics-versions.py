#!/usr/bin/env python

import re
import sys
import optparse
import subprocess
import fileinput
import glob
import os
import pprint
import signal
import traceback
import subprocess

from repo_defaults import *
from site_utils import *
from version_utils import *
from pkgNamesToMacroNames import *
from eco_version import eco_tools_version

#
# Purpose:
#
#   This script searches for releases of EPICS modules and reports
#   which versions are available along with any dependencies.
#
#   However, in addition to EPICS modules, this script can show
#   version information for the following as well:
#
#       base                    - EPICS base
#       modules                 - All modules
#       modules/<mod_name>      - Module named mod_name
#       ioc/common/<ioc_name>   - common IOC named ioc_name
#       ioc/amo/<ioc_name>      - AMO IOC named ioc_name
#       ioc/sxr                 - All SXR IOC's
#       screens/edm/xpp         - XPP edm control room screens
#       screens                 - All control room screens
#       etc.
#
#   If a release has a configure/RELEASE file which specifies
#   BASE_MODULE_VERSION, it's value will be shown as the EPICS base version.
#
#   If the --verbose option is selected, all version macros
#   matching *_MODULE_VERSION in the configure/RELEASE file
#   will be shown.
#
#   Example:
#       epics-versions -v ioc/common/Leviton
#   Assuming the following directory is the latest release of ioc/common/Leviton:
#       $(EPICS_SITE_TOP)/ioc/common/Leviton/R1.1.0
#   Output would be:
#       ioc/common/Leviton      R1.1.0      Base    R3.14.9-0.3.0
#           AUTOSAVE_MODULE_VERSION         = R4.2.1.2-1.2.0
#           IOCADMIN_MODULE_VERSION         = R2.0.0-1.1.0
#           GENERALTIME_MODULE_VERSION      = R1.2.2.2-1.0.0
#           SNMP_MODULE_VERSION             = R1.1.0-1.5.0
#
#
# Copyright 2011,2012,2016,2017,2018,2019 Stanford University
# Photon Controls and Data Systems
# Author: Bruce Hill <bhill@slac.stanford.edu>
#
# Released under the GPLv2 licence <http://www.gnu.org/licenses/gpl-2.0.html>
#
debugScript         = False

# Create a pretty printer for nicer diagnostics
pp  = pprint.PrettyPrinter( indent=4 )

# Pre-compile regular expressions for speed
parentRegExp        = re.compile( r"RELEASE\s*=\s*(\S*)\s*$" )

class ValidateError( Exception ):
    pass

def debug_signal_handler(signal, frame):
    import pdb
    pdb.set_trace()
signal.signal(signal.SIGINT, debug_signal_handler)

def ReportReleases( pkgPath, pkgSpec, releases, opt ):
    if opt.debug:
        print("ReportReleases: ", pkgSpec)
    found = False
    priorModule = None
    for release in releases:
        reportedModule = ReportRelease( pkgPath, release, priorModule, opt )
        if reportedModule != None:
            found = True
            priorModule = reportedModule
    return found

def ReportDependents( module, pkgDependents, wide=False, recurse=True ):
    if "base" in pkgDependents and recurse:
        epicsModules = os.path.join( determine_epics_site_top(), pkgDependents['base'], "modules" )
        for depRoot in sorted( pkgDependents.keys() ):
            depVersion = pkgDependents[ depRoot ]
            subDeps = getEpicsPkgDependents( os.path.join( epicsModules, depRoot, depVersion ) )
            for subDep in subDeps:
                if subDep not in pkgDependents:
                    pkgDependents[subDep] = subDeps[subDep]
                elif pkgDependents[subDep] != subDeps[subDep]:
                    print( "Mismatch: %s depends on %s/%s" % ( module,  subDep, pkgDependents[subDep] ) )
                    print( "Mismatch: %s depends on %s/%s" % ( depRoot, subDep, subDeps[subDep] ) )

    for depRoot in sorted( pkgDependents.keys() ):
        if depRoot == "base":
            continue
        # Print dependent info w/o newline (trailing ,)
        depVersion = pkgDependents[ depRoot ]
        if opt.wide:
            # Don't print newline in wide mode 
            print(" %s/%s" % ( depRoot, depVersion ), end=' ')
        elif '/' in depVersion:
            print("%20s%18s %s" % ( '', depRoot, depVersion ))
        else:
            print("%20s%18s %19s/%s" % ( '', depRoot, depRoot, depVersion ))

def ReportRelease( pkgPath, release, priorModule, opt ):
    ''' Get the module and version from the release string. '''
    cmdList = [ "readlink", "-e", release ]
    cmdOutput = subprocess.check_output( cmdList ).splitlines()
    if len(cmdOutput) == 1:
        release = str(cmdOutput[0])
    ( relPath, moduleVersion ) = os.path.split( release )
    # Simplify the module path by removing the default module release
    # portion of the path
    cmdList = [ "readlink", "-e", pkgPath ]
    cmdOutput = subprocess.check_output( cmdList ).splitlines()
    if len(cmdOutput) == 1:
        pkgPath = str(cmdOutput[0])
    #relPath = relPath.replace( "slac.stanford.edu", "slac" )
    relPath = relPath.replace( pkgPath + "/", "" )

    # At most just show the last 3 directory levels
    relPath = '/'.join( relPath.split('/')[-3:] )
    module  = relPath
    if module == priorModule and not opt.showAll:
        return None

    pkgDependents	= getEpicsPkgDependents( release, debug=opt.debug )
    baseVer = "?"
    # We should always get a base version if there is one
    if 'base' in pkgDependents:
        baseVer = pkgDependents['base']
        #del pkgDependents['base']

    if module == 'base':
        baseVer = moduleVersion

    if baseVer != "?" and opt.debug:
        print("%s BaseVersion: %s" % ( pkgPath, baseVer ))

    buildPath = os.path.join( release, "build" )
    if os.path.isdir( buildPath ):
        baseVerPrompt = "Templated IOC"
    else:
        # See if they've restricted output to a specific base version
        if opt.base and opt.base != baseVer:
            return None
        if "screens" in release or module == "base":
            baseVerPrompt = ""
        elif opt.wide:
            baseVerPrompt = " base/" + baseVer
        else:
            baseVerPrompt = "%18s/%s" % ( "base", baseVer )

    # Print the module and version, along with base version if any
    if opt.wide:
        print("%s/%s %s" % ( module, moduleVersion, baseVerPrompt ), end=' ')
    #elif module.startswith('/'):
    #	print "%-37/%s" % ( release, baseVerPrompt )
    else:
        print("%18s/%-20s %s" % ( module, moduleVersion, baseVerPrompt ))

    # Show pkgDependents for --verbose
    if opt.verbose:
        ReportDependents( module, pkgDependents, wide=opt.wide )
    if opt.wide:
        print()

    if opt.verbose and os.path.isdir( buildPath ) :
        # Templated IOC
        # Show parent release for each ioc
        configFiles = glob.glob( os.path.join( release, "*.cfg" ) )
        for configFile in configFiles:
            for line in fileinput.input( configFile ):
                match = parentRegExp.search( line )
                if match:
                    iocName = os.path.basename(configFile).replace( '.cfg', '' )
                    parentRelease = match.group(1)
                    # Grab the last 4 directories
                    # i.e. ioc/common/gigECam/R1.20.5
                    parentName    = os.path.dirname( parentRelease )
                    parentRelease = os.path.basename( parentRelease )
                    for i in [0,1,2]:
                        (parentName, parentTail) = os.path.split( parentName )
                        if not parentName:
                            break
                        parentRelease = os.path.join( parentTail, parentRelease ) 
                    if opt.wide:
                        # Don't print newline in wide mode 
                        print(" %s/%s" % ( iocName, parentRelease ), end=' ')
                    else:
                        print("%-4s %20s/%s" % ( '', iocName, parentRelease ))
        if opt.wide:
            print()

    return module

def ExpandPackageForTopVariants( siteTop, package, opt ):
    if "modules" in siteTop or "modules" in package:
        # All modules already checked for
        return []
    topVariants = [ siteTop ]
    for topVariant in defEpicsTopVariants:
        topVariants.append( os.path.join( siteTop, topVariant ) )

    releases = []
    for topDir in topVariants:
        releases += ExpandPackagePath( topDir, package, base=opt.base, debug=opt.debug )
    return releases

def isEpicsTopVariant( topDir ):
    for topVariant in defEpicsTopVariants:
        if topDir.endswith( topVariant ):
            return True
    return False

def ExpandPackagesForTop( topDir, packages, opt ):
    '''Look for and report on each package under the specified top directory.'''
    topDirShown = False
    releases = []
    numReleasesForTop = 0
    for package in packages:
        # If the package is a valid directory path, assume it's a release dir
        # Note that relative paths are allowed, so package could be "." for $CWD
        if os.path.isdir( package ) and isEpicsPackage( package ):
            if not ReportRelease( topDir, package, None, opt ):
                print("%s: No releases found.\n" % ( package ))
            else:
                numReleasesForTop += 1
            continue
        elif package not in defEpicsTopVariants:
            releases += ExpandPackagePath( topDir, package, base=opt.base, debug=opt.debug )
        #elif isEpicsTopVariant( topDir ):
        elif topDir.endswith(package):
            for dirPath, dirs, files in os.walk( topDir, topdown=True ):
                if len( dirs ) == 0:
                    continue
                for dir in dirs[:]:
                    # Remove from list so we don't search recursively
                    dirs.remove( dir )
                    releases += ExpandPackagePath( topDir, dir, base=opt.base, debug=opt.debug )

        # validate the package specification
        if len(releases) == 0 or not os.path.isdir( releases[0] ):
            releases = ExpandPackageForTopVariants( topDir, package, opt )
        if len(releases) == 0 or not os.path.isdir( releases[0] ):
            continue
        if not opt.wide and topDirShown == False:
            print("Releases under %s/" % topDir)
            topDirShown = True

        # Report all releases for this package
        if not ReportReleases( topDir, package, releases, opt ):
            print("%s/%s: No releases found matching specification.\n" % ( topDir, package ))
        numReleasesForTop += len(releases)
        # Clear releases before checking next package
        releases = []

    return numReleasesForTop

# Entry point of the script. This is main()
try:
    parser = optparse.OptionParser( description = "Report on available package versions and dependencies",
                                    version = eco_tools_version,
                                    usage = "usage: %prog [options] PKG ...\n"
                                            "\tPKG can be one or more of:\n"
                                            "\t\tdirectoryPath\n"
                                            "\t\tbase\n"
                                            "\t\t<MODULE_NAME>\n"
                                            "\t\tmodules\n"
                                            "\t\tmodules/<MODULE_NAME>\n"
                                            "\t\tioc\n"
                                            "\t\tioc/<hutch>\n"
                                            "\t\tioc/<hutch>/<IOC_NAME>\n"
                                            "\t\tscreens/edm/<hutch>\n"
                                            "\t\tetc ...\n"
                                            "\tExamples:\n"
                                            "\tepics-versions -v ADCore\n"
                                            "\tepics-versions ADCore ADProsilica asyn busy\n"
                                            "\tepics-versions Magnet --top /afs/slac/g/lcls/epics/iocTop\n"
                                            "\tepics-versions IOCManager\n"
                                            "\tepics-versions -a iocAdmin\n"
                                            "\tepics-versions ioc/xpp\n"
                                            "\tWith no args, shows dependencies for current directory.\n"
                                            "\tepics-versions\n"
                                            "\tFor help: epics-versions --help" )
    parser.set_defaults(    verbose     = False,
                            revision    = "HEAD",
                            debug       = debugScript )

    parser.add_option(  "-a", "--all", dest="showAll", action="store_true",
                        help="display all revisions of each package" )

    parser.add_option(  "-v", "--verbose", dest="verbose", action="store_true",
                        help="show dependent modules" )

    parser.add_option(  "-d", "--debug", dest="debug", action="store_true",
                        help="display more info for debugging script" )

    parser.add_option(  "-b", "--base", dest="base",
                        help="Restrict output to packages for specified base version\n"
                             "ex. --base=R3.14.9-0.3.0" )

    parser.add_option(  "-w", "--wide", dest="wide", action="store_true",
                        help="Wide output, all package info on one line\n"   )

    parser.add_option(  "--top", dest="epicsTop", metavar="TOP",
                        default=None,
                        help="Top of EPICS release area\n"
                             "ex. --top=/afs/slac/g/lcls/epics/R3-14-12-4_1-1/modules\n"
                             "or  --top=/afs/slac/g/lcls/epics/iocTop\n"	)

    parser.add_option(  "--allTops", dest="allTops", action="store_true",
                        help="Search all accessible known EPICS release locations\n" )

    # Future options
    #add_option(    "--prefix", "path to the root of the release area"

    # Parse the command line arguments
    ( opt, args ) = parser.parse_args()

    # validate the arglist
    if not args or not args[0]:
        # If no arguments, show the current directory
        args = [ "." ]

    # If used to query a single directory, set verbose to show it's dependents
    if len(args) == 1 and os.path.isdir( args[0] ):
        opt.verbose = True

    # Determine EPICS_SITE_TOP and BASE version
    epics_site_top = determine_epics_site_top()
    if opt.base:
        epics_base_ver = opt.base
    else:
        epics_base_ver = determine_epics_base_ver()
        if not epics_base_ver:
            print("epics-versions: Unable to determine EPICS Base version.")
            print("Please define via at least one of these env variables:")
            print("  EPICS_BASE, EPICS_BASE_VER, EPICS_VER, BASE_MODULE_VERSION")
            epics_base_ver = 'unknown-base-ver'

    releaseCount = 0
    # See which epicsTop to search
    if not opt.epicsTop and os.path.isdir( epics_site_top ):
        # --top not specified, start from epics_site_top
        opt.epicsTop = os.path.join( epics_site_top, epics_base_ver, "modules" )
        # If opt.EpicsTop is invalid, look in environment
        if not os.path.isdir( opt.epicsTop ):
            opt.epicsTop = os.environ.get( "EPICS_MODULES_TOP" )
        if not opt.epicsTop or not os.path.isdir( opt.epicsTop ):
            opt.epicsTop = os.environ.get( "EPICS_MODULES" )
        if not opt.epicsTop or not os.path.isdir( opt.epicsTop ):
            if epics_site_top:
                opt.epicsTop = os.path.join( epics_site_top, 'modules' ) 
                if not os.path.isdir( opt.epicsTop ):
                    opt.epicsTop = None

    if opt.epicsTop:
        releaseCount += ExpandPackagesForTop( opt.epicsTop, args, opt )

    if releaseCount == 0 and epics_site_top:
        # See if we find any matches directly under epics_site_top
        releaseCount += ExpandPackagesForTop( epics_site_top, args, opt )

    # If we haven't found a default or --allTops, try any we can find
    if opt.allTops or releaseCount == 0:
        for site_top in [ DEF_EPICS_TOP_LCLS, DEF_EPICS_TOP_MCC, DEF_EPICS_TOP_PCDS, DEF_EPICS_TOP_AFS ]:
            # if site_top == epics_site_top:
                # Already shown
            # 	continue
            #releaseCount += ExpandPackagesForTop( site_top, args, opt )
            #continue
            for dirPath, dirs, files in os.walk( site_top, topdown=True ):
                if len( dirs ) == 0:
                    continue
                for dir in dirs[:]:
                    # Remove from list so we don't search recursively
                    dirs.remove( dir )
                    epicsTop = os.path.join( site_top, dir, 'modules' ) 
                    if not os.path.isdir( epicsTop ):
                        continue
                    if opt.epicsTop and epicsTop == opt.epicsTop:
                        # Already done this one
                        continue
                    releaseCount += ExpandPackagesForTop( epicsTop, args, opt )
            if not opt.allTops and releaseCount > 0:
                break

    if releaseCount == 0:
        errorMsg = "Unable to find any releases for these modules:"
        for module in args:
            errorMsg += " "
            errorMsg += module
        raise ValidateError(errorMsg)

    # All done!
    sys.exit(0)

except ValidateError:
    print("Error: %s\n" % sys.exc_info()[1]) 
    parser.print_usage()
    sys.exit(6)

except KeyboardInterrupt:
    print("\nERROR: interrupted by user.")
    sys.exit(2)

except SystemExit:
    raise

except:
    if debugScript:
        traceback.print_tb(sys.exc_info()[2])
    print("%s exited with ERROR:\n%s\n" % ( sys.argv[0], sys.exc_info()[1] ))
    sys.exit( 1 )
