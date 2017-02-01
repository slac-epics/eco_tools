#!/usr/bin/python
import re
import sys
import optparse
import commands
import fileinput
import glob
import os
import pprint
import signal
import traceback

from version_utils import *

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
# Copyright 2011,2012,2016 Stanford University
# Photon Controls and Data Systems
# Author: Bruce Hill <bhill@slac.stanford.edu>
#
# Released under the GPLv2 licence <http://www.gnu.org/licenses/gpl-2.0.html>
#
DEF_EPICS_TOP_PCDS  = "/reg/g/pcds/package/epics"
DEF_EPICS_TOP_AFS   = "/afs/slac/g/pcds/package/epics"
DEF_EPICS_TOP_LCLS  = "/afs/slac/g/lcls/epics"
DEF_EPICS_TOP_MCC   = "/usr/local/lcls/epics"
debugScript         = False


# Create a pretty printer for nicer diagnostics
pp  = pprint.PrettyPrinter( indent=4 )

# Pre-compile regular expressions for speed
baseVersionRegExp   = re.compile( r"^\s*([A-Za-z0-9_-]*BASE[A-Za-z0-9_-]*VER[SION]*)\s*=\s*(\S*)\s*$" )
versionRegExp       = re.compile( r"^\s*([A-Za-z0-9_-]*VERSION)\s*=\s*(\S*)\s*$" )
parentRegExp        = re.compile( r"RELEASE\s*=\s*(\S*)\s*$" )

class ValidateError( Exception ):
    pass

def debug_signal_handler(signal, frame):
    import pdb
    pdb.set_trace()
signal.signal(signal.SIGINT, debug_signal_handler)

def ExpandModulePath( topDir, module, opt ):
    # See if "modules" is in both parts of the path
    if "modules" in topDir and "modules" in module:
        topDir = os.path.dirname( topDir )

    # Create the path to module
    modPath = os.path.join( topDir, module )

    # See if it exists
    if not os.path.isdir( modPath ):
        if opt.debug:
            print "ExpandModulePath: %s not found" % ( modPath )
        return []

    # See if this is a screens release
    screenArg   = False
    if "screens" in modPath:
        screenArg   = True

    if opt.debug:
        print "ExpandModulePath: Expanding %s ..." % ( modPath )

    selectedReleases = [ ]
    for dirPath, dirs, files in os.walk( modPath, topdown=True ):
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
            # Remove from list so we don't search recursively
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
                if opt.debug:
                    print "ExpandModulePath: Found ", release
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

        #if opt.debug:
        #   print "ExpandModulePath Module Releases: "
        #   pp.pprint( releaseSet )

        for release in sorted( releaseSet.keys(), reverse = True ):
            selectedReleases += [ releaseSet[ release ] ]

    if opt.debug:
        print "ExpandModulePath Selected Releases: "
        pp.pprint( selectedReleases )
    return selectedReleases

def ReportReleases( moduleTop, module, releases, opt ):
    if opt.debug:
        print "ReportReleases: ", module
    found = False
    priorModule = None
    for release in releases:
        reportedModule = ReportRelease( moduleTop, module, release, priorModule, opt )
        if reportedModule != None:
            found = True
            priorModule = reportedModule
    return found

def ReportRelease( moduleTop, module, release, priorModule, opt ):

    # Get the module and version from the release string
    ( relPath, moduleVersion ) = os.path.split( release )
    module = relPath.replace( moduleTop, "" )
    module = module.lstrip( "/" )
    if opt.debug:
        print "ReportRelease: %s, priorModule = %s" % ( module, priorModule )
    if module == priorModule and not opt.showAll:
        return None

    moduleDependents    = {}
    baseDependents      = {}
    if not module.startswith( "screens" ):
        # Get the base and dependent modules from RELEASE files
        releaseFiles = []
        releaseFiles += [ os.path.join( release, "..", "..", "RELEASE_SITE" ) ]
        releaseFiles += [ os.path.join( release, "RELEASE_SITE" ) ]
        releaseFiles += [ os.path.join( release, "configure", "RELEASE" ) ]
        releaseFiles += [ os.path.join( release, "configure", "RELEASE.local" ) ]
        for releaseFile in releaseFiles:
            if opt.debug:
                print "Checking release file: %s" % ( releaseFile )
            if not os.path.isfile( releaseFile ):
                continue
            for line in fileinput.input( releaseFile ):
                m = versionRegExp.search( line )
                if m and m.group(1) and m.group(2):
                    moduleDependents[ m.group(1) ] = m.group(2)
                m = baseVersionRegExp.search( line )
                if m and m.group(1) and m.group(2):
                    baseDependents[ m.group(1) ] = m.group(2)

    baseVer = "?"
    baseVerMacros = [ "BASE_MODULE_VERSION", "BASE_VERSION", "EPICS_BASE_VER", "EPICS_BASE_VERSION" ]
    for baseMacro in baseVerMacros:
        # For the BASE macro's, remove them from moduleDependents
        if baseMacro in moduleDependents:
            del moduleDependents[ baseMacro ]

        if not baseMacro in baseDependents:
            continue

        # Skip any defined by other macros
        baseMacroValue = baseDependents[ baseMacro ]
        if '$' in baseMacroValue:
            continue

        # Found a base version!
        baseVer = baseMacroValue

    if module == 'base':
        baseVer = moduleVersion

    if baseVer != "?" and opt.debug:
        print "%s BaseVersion: %s" % ( moduleTop, baseVer )

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
            baseVerPrompt = " BASE=" + baseVer
        else:
            baseVerPrompt = "%-18s = %s" % ( "BASE", baseVer )

    # Print the module and version, along with base version if any
    if opt.wide:
        print "%s %s" % ( release, baseVerPrompt ),
    else:
        print "%-24s %-18s %s" % ( module, moduleVersion, baseVerPrompt )

    # Show moduleDependents for --verbose
    if opt.verbose:
        for dep in sorted( moduleDependents.keys() ):
            # Print dependent info w/o newline (trailing ,)
            depRoot = dep.replace( "_MODULE_VERSION", "" )
            if opt.wide:
                # Don't print newline in wide mode 
                print " %s=%s" % ( depRoot, moduleDependents[ dep ] ),
            else:
                print "%-24s %-18s %-18s = %s" % ( "", "", depRoot, moduleDependents[ dep ] )
    if opt.wide:
        print

    if os.path.isdir( buildPath ):
        # Templated IOC
        # Show parent release for each ioc
        configFiles = glob.glob( os.path.join( release, "*.cfg" ) )
        for configFile in configFiles:
            for line in fileinput.input( configFile ):
                match = parentRegExp.search( line )
                if match:
                    iocName = os.path.basename(configFile).replace( '.cfg', '' )
                    parentRelease = match.group(1)
                    print "%-4s %-20s %s" % ( '', iocName, parentRelease )

    return module

def ExpandPackageForTopVariants( siteTop, package, opt ):
    if "modules" in siteTop or "modules" in package:
        # All modules already checked for
        return []
    topVariants = []
    topVariants += [ os.path.join( siteTop, "extensions" ) ]
    topVariants += [ os.path.join( siteTop, "iocTop" ) ]
    topVariants += [ os.path.join( siteTop, "ioc" ) ]
    topVariants += [ os.path.join( siteTop, "ioc", "common" ) ]
    topVariants += [ os.path.join( siteTop, "ioc", "amo" ) ]
    topVariants += [ os.path.join( siteTop, "ioc", "sxr" ) ]
    topVariants += [ os.path.join( siteTop, "ioc", "xpp" ) ]
    topVariants += [ os.path.join( siteTop, "ioc", "cxi" ) ]
    topVariants += [ os.path.join( siteTop, "ioc", "mec" ) ]
    topVariants += [ os.path.join( siteTop, "ioc", "mfx" ) ]
    topVariants += [ os.path.join( siteTop, "ioc", "xcs" ) ]
    topVariants += [ os.path.join( siteTop, "ioc", "xrt" ) ]
    topVariants += [ os.path.join( siteTop, "ioc", "tst" ) ]
    topVariants += [ os.path.join( siteTop, "ioc", "fee" ) ]
    topVariants += [ os.path.join( siteTop, "ioc", "las" ) ]
    topVariants += [ os.path.join( siteTop, "screens" ) ]
    topVariants += [ os.path.join( siteTop, "screens", "edm" ) ]
    releases = []
    for topDir in topVariants:
        releases += ExpandModulePath( topDir, package, opt )
    return releases

def ExpandPackagesForTop( topDir, packages, opt ):
    '''Look for and report on each package under the specified top directory.'''
    topDirShown = False
    releases = []
    numReleasesForTop = 0
    for package in packages:
        if package != "modules":
            releases += ExpandModulePath( topDir, package, opt )
        elif topDir.endswith("modules"):
            for dirPath, dirs, files in os.walk( topDir, topdown=True ):
                if len( dirs ) == 0:
                    continue
                for dir in dirs[:]:
                    # Remove from list so we don't search recursively
                    dirs.remove( dir )
                    releases += ExpandModulePath( topDir, dir, opt )

        # validate the package specification
        if len(releases) == 0 or not os.path.isdir( releases[0] ):
            releases = ExpandPackageForTopVariants( topDir, package, opt )
        if len(releases) == 0 or not os.path.isdir( releases[0] ):
            continue
        if not opt.wide and topDirShown == False:
            print "Releases under %s:" % topDir
            topDirShown = True

        # Report all releases for this package
        if not ReportReleases( topDir, package, releases, opt ):
            print "%s/%s: No releases found matching specification.\n" % ( topDir, package )
        numReleasesForTop += len(releases)
        # Clear releases before checking next package
        releases = []

    return numReleasesForTop

# Entry point of the script. This is main()
try:
    parser = optparse.OptionParser( description = "Report on available package versions and dependencies",
                                    usage = "usage: %prog [options] MODULE ...\n"
                                            "\tMODULE can be one or more of:\n"
                                            "\t\tbase\n"
                                            "\t\tmodules\n"
                                            "\t\tmodules/<MODULE_NAME>\n"
                                            "\t\tioc\n"
                                            "\t\tioc/<hutch>\n"
                                            "\t\tioc/<hutch>/<IOC_NAME>\n"
                                            "\t\tscreens/edm/<hutch>\n"
                                            "\t\tetc ...\n"
                                            "\tEx: %prog ioc/xpp\n"
                                            "\tFor help: %prog --help" )
    parser.set_defaults(    verbose     = False,
                            revision    = "HEAD",
                            debug       = debugScript )

    parser.add_option(  "-a", "--all", dest="showAll", action="store_true",
                        help="display all revisions of each module" )

    parser.add_option(  "-v", "--verbose", dest="verbose", action="store_true",
                        help="show dependent modules" )

    parser.add_option(  "-d", "--debug", dest="debug", action="store_true",
                        help="display more info for debugging script" )

    parser.add_option(  "-b", "--base", dest="base",
                        help="Restrict output to modules for specified base version\n"
                             "ex. --base=R3.14.9-0.3.0" )

    parser.add_option(  "-w", "--wide", dest="wide", action="store_true",
                        help="Wide output, all module info on one line\n"   )

    parser.add_option(  "--top", dest="epicsTop", metavar="TOP",
                        default=None,
                        help="Top of EPICS release area\n"
                             "ex. --top=/afs/slac/g/pcds/package/epics" )

    parser.add_option(  "--allTops", dest="allTops", action="store_true",
                        help="Search all accessible known EPICS module release locations\n" )

    # Future options
    #add_option(    "--prefix", "path to the root of the release area"

    # Parse the command line arguments
    ( opt, args ) = parser.parse_args()

    # validate the arglist
    if not args or not args[0]:
        raise ValidateError, "No valid modules specified."

    # Determine EPICS_SITE_TOP and BASE version
    epics_site_top = determine_epics_site_top()
    if opt.base:
        epics_base_ver = opt.base
    else:
        epics_base_ver = determine_epics_base_ver()

    releaseCount = 0
    if epics_site_top:
        # See if we find any matches directly under epics_site_top
        releaseCount += ExpandPackagesForTop( epics_site_top, args, opt )

    # See which epicsTop to search
    if not opt.epicsTop:
        # --top not specified, look for EPICS_MODULES_TOP in environment
        opt.epicsTop = os.path.join( epics_site_top, epics_base_ver, "modules" )
        if not opt.epicsTop or not os.path.isdir( opt.epicsTop ):
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

    # If we haven't found a default or --allTops, try any we can find
    if opt.allTops or not opt.epicsTop:
        for site_top in [ DEF_EPICS_TOP_LCLS, DEF_EPICS_TOP_MCC, DEF_EPICS_TOP_PCDS, DEF_EPICS_TOP_AFS ]:
            # if site_top == epics_site_top:
                # Already shown
            # 	continue
            #releaseCount += ExpandPackagesForTop( site_top, args, opt )
            #continue
            # Move to ExpandModulePath()?
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

    if releaseCount == 0:
        errorMsg = "Unable to find any releases for these modules:"
        for module in args:
            errorMsg += " "
            errorMsg += module
        raise ValidateError, errorMsg

    # All done!
    sys.exit(0)

except ValidateError:
    print "Error: %s\n" % sys.exc_value 
    parser.print_usage()
    sys.exit(6)

except KeyboardInterrupt:
    print "\nERROR: interrupted by user."
    sys.exit(2)

except SystemExit:
    raise

except:
    if debugScript:
        traceback.print_tb(sys.exc_traceback)
    print "%s exited with ERROR:\n%s\n" % ( sys.argv[0], sys.exc_value )
    sys.exit( 1 )
