#!/usr/bin/env python
#  Name: epics-update.py
#  Abs:  A tool to update EPICS packages
#
#  Example:
#    epics-update ?
#
#  Requested features to be added:
#
#==============================================================
import sys
import os
import socket
import subprocess
import argparse
import readline
import shutil
import tempfile
import textwrap
import Repo
import gitRepo
import svnRepo
import Releaser 
from git_utils import *
from svn_utils import *
from site_utils import *
from version_utils import *
from eco_version import eco_tools_version

from repo_defaults import *

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
            if macroName + "_MODULE_VERSION" in newMacroVersions:
                # newMacroVersions contains full XXX_MODULE_VERSION patterns
                macroName = macroName + "_MODULE_VERSION"
            if macroName in newMacroVersions:
                newVersion = newMacroVersions[macroName]
                if newVersion != oldVersion:
                    print "Old: %s" %  line,
                    line = string.replace( line, oldVersion, newMacroVersions[macroName] )
                    print "New: %s" %  line,
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

        # Parse the macro match
        originalLine   = match.group(0)
        commentedOut   = match.group(1).startswith('#')
        macroName      = match.group(2)
        oldVersionPath = match.group(3)

        # Is this macro related to the base version
        #isMacroBaseRelated = False
        #if macroName in [ "EPICS_BASE", "EPICS_BASE_VER", "EPICS_MODULES", "MODULES_SITE_TOP" ]:
        #	isMacroBaseRelated = True

        if macroName in newMacroVersions:
            pkgName = macroNameToPkgName(macroName)
            if not pkgName:
                continue
            if pkgName == 'base':
                if 'BASE_MODULE_VERSION' in oldMacroVersions:
                    newVersionPath = "$(EPICS_SITE_TOP)/base/$(BASE_MODULE_VERSION)"
                else:
                    newVersionPath = "$(EPICS_SITE_TOP)/base/%s" % ( newMacroVersions[macroName] )
                #print '1. newVersionPath = %s' % newVersionPath
            elif using_MODULE_VERSION.get( macroName, False ):
                newVersionPath = "$(EPICS_MODULES)/%s/$(%s_MODULE_VERSION)" % ( pkgName, macroName )
                #print '2. newVersionPath = %s' % newVersionPath
            else:
                newVersionPath = "$(EPICS_MODULES)/%s/%s" % ( pkgName, newMacroVersions[macroName] )
                #print '3. newVersionPath = %s' % newVersionPath
            if macroName in definedModules:
                # We've already defined this macroName
                if not commentedOut:
                    # Comment out subsequent definitions
                    print "Old: %s" %  line,
                    line = string.replace( line, originalLine, '#' + originalLine )
                    print "New: %s" %  line,
                    modified = True
            else:
                definedModules[macroName] = newVersionPath
                if commentedOut:
                    # Uncomment the line
                    print "Old: %s" %  line,
                    line = string.strip( line, '# ' )
                    print "New: %s" %  line,
                    modified = True
                if oldVersionPath != newVersionPath:
                    print "Old: %s" %  line,
                    line = string.replace( line, oldVersionPath, newVersionPath )
                    print "New: %s" %  line,
                    modified = True

        if not "BASE" in newMacroVersions:
            lineCache += line
            continue

        # Handle BASE related macros
        #if not isMacroBaseRelated:
        if macroName in [ "EPICS_BASE", "EPICS_BASE_VER", "EPICS_MODULES", "MODULES_SITE_TOP" ]:
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
            oldLine = line
            line = string.replace( line, oldBaseVersion, newBaseVersion )
            if newBaseVersion in line:
                print "Old: %s" %  oldLine,
                print "New: %s" %  line,
                modified = True
                lineCache += line
                continue

            if	   "EPICS_BASE_VER" in oldVersionPath \
                or "BASE_MODULE_VERSION" in oldVersionPath:
                lineCache += line
                continue

        # Handle fixing unusual paths
        if macroName == "EPICS_BASE_VER":
            oldLine = line
            #line = string.replace( line, oldBaseVersion, newBaseVersion )
            #line = string.replace( line, oldVersionPath, baseDirName )
            if True or newBaseVersion in line:
                print "Old: %s" %  oldLine,
                print "New: %s" %  line,
            modified = True

        if macroName == "EPICS_BASE":
            if   "BASE_MODULE_VERSION" in oldVersionPath:
                newVersionPath = "$(EPICS_SITE_TOP)/base/$(BASE_MODULE_VERSION)"
            elif "EPICS_BASE_VER" in oldVersionPath:
                newVersionPath = "$(EPICS_SITE_TOP)/base/$(EPICS_BASE_VER)"
            else:
                newVersionPath = "$(EPICS_SITE_TOP)/base/%s" % baseDirName 
            if oldVersionPath != newVersionPath:
                print "Old: %s" %  line,
                line = string.replace( line, oldVersionPath, newVersionPath )
                print "New: %s" %  line,
                modified = True

        if macroName == "EPICS_MODULES" or macroName == "MODULES_SITE_TOP":
            if   "BASE_MODULE_VERSION" in oldVersionPath:
                newVersionPath = "$(EPICS_SITE_TOP)/$(BASE_MODULE_VERSION)/modules"
            else:
                newVersionPath = "$(EPICS_SITE_TOP)/%s/modules" % newBaseVersion
            if oldVersionPath != newVersionPath:
                print "Old: %s" %  line,
                line = string.replace( line, oldVersionPath, newVersionPath )
                print "New: %s" %  line,
                modified = True

        lineCache += line
        continue

    in_file.close()
    if not modified:
        if verbose:
            print("%s, No change" %  filePath)
        return 0

    # Replace prior version w/ updates
    try:
        os.remove( filePath )
        out_file = open( filePath, 'w' )
        out_file.writelines( lineCache )
        out_file.close()
    except OSError as e:
        sys.stderr.write( 'Could not remove "%s": %s\n' % ( filePath, e.strerror ) )
        return 0
    except IOError as e:
        sys.stderr.write( 'Could not replace "%s": %s\n' % ( filePath, e.strerror ) )
        return 0
    print("%s, UPDATED" %  filePath)
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
        print("update_pkg_dependency: Invalid topDir: %s" % topDir)
        return 0
    if verbose:
        print("update_pkg_dependency: %s" % topDir)

    # Get current pkgSpecs
    oldPkgDependents = getEpicsPkgDependents( topDir, debug=debug )
    oldMacroVersions = {}
    for pkgName in oldPkgDependents:
        pkgSpec = pkgName + "/" + oldPkgDependents[pkgName]
        if verbose:
            print("OLD: %s" % pkgSpec)
        oldMacroVersions.update( pkgSpecToMacroVersions( pkgSpec ) )
    if len(oldMacroVersions) == 0:
        print("update_pkg_dependency error: No pkgSpecs found under topDir:\n%s" % topDir)
        return 0

    # Convert the list of pkgSpecs into a list of macroVersions
    # Each macroVersion is a tuple of ( macroName, version )
    newMacroVersions = {}
    for pkgSpec in pkgSpecs:
        if verbose:
            print("NEW: %s" % pkgSpec)
        newMacroVersions.update( pkgSpecToMacroVersions( pkgSpec ) )
    if len(newMacroVersions) == 0:
        print("update_pkg_dependency error: No valid converions for pkgSpecs:")
        print(pkgSpecs)
        return 0

    # Remove macros from newMacroVersions if they're already in oldMacroVersions
    # This helps avoid trying to fix commented out macros in configure/RELEASE
    # when they've already been defined in RELEASE.local.
    for macroName in oldMacroVersions.keys():
        if macroName not in newMacroVersions:
            continue
        if oldMacroVersions[macroName] == newMacroVersions[macroName]:
            del newMacroVersions[macroName]

    count = 0

    for fileName in [	os.path.join( "configure", "RELEASE.local" ),
                        "RELEASE_SITE",
                        os.path.join( "configure", "RELEASE" ) ]:
        # If we already updated package specs in RELEASE.local,
        # skip RELEASE to avoid duplicate macro defines
        if count > 0 and fileName == os.path.join( "configure", "RELEASE" ):
            continue
        filePath = os.path.join( topDir, fileName )
        if os.access( filePath, os.R_OK ):
            count += update_pkg_dep_file( filePath, oldMacroVersions, newMacroVersions, verbose )
    return count

def update_stable( topDir='.', debug=False ):
    curDep = getEpicsPkgDependents( topDir, debug=debug )
    if 'base' not in curDep:
        print "Error: unable to determine base version"
        return 0
    epicsSiteTop = determine_epics_site_top()
    modulesStableVersionPath = os.path.join( epicsSiteTop, curDep['base'], 'modules', 'MODULES_STABLE_VERSION' )
    if not os.path.isfile( modulesStableVersionPath ):
        print "Error: unable to find %s" % modulesStableVersionPath 
        return 0

    macroDict = {}
    stableVersions = getMacrosFromFile( modulesStableVersionPath, macroDict, debug=debug )

# TODO: Check for conflicts vs MODULE_STABLE_VERSION
#	updateVersions = {}
#	for dep in curDep:
#		if dep == 'base':
#			continue
#		if dep in stableVersions:
#			stableVerPath = os.path.join( epicsSiteTop, curDep['base'], 'modules', dep, stableVersions[dep] )
#			stableVerDep  = getEpicsPkgDependents( stableVerPath, debug=debug )
#			for sDep in stableVerDep:
#				if sDep in stableVersions and stableVerDep[sDep] != stableVersions[sDep]:
#					print "Error: %s depends on %s, but MODULES_STABLE_VERSION has %s" % ( dep, sDep, stableVersions[sDep] )
#					return -1
#				updateVersions[sDep] = stableVerDep[sDep]
#			updateVersions[dep] = stableVersions[dep]
#	for dep in updateVersions:
#		print "Need to update %s to %s" % ( dep, updateVersions[dep] )
    
    count = 0

    for fileName in [	os.path.join( "configure", "RELEASE" ),
                        os.path.join( "configure", "RELEASE.local" ) ]:
        filePath = os.path.join( topDir, fileName )
        if os.access( filePath, os.R_OK ):
            oldMacroVersions = getMacrosFromFile( filePath, {}, debug=debug )
            count += update_pkg_dep_file( filePath, oldMacroVersions, stableVersions, verbose=debug )

    return count

def process_options(argv):
    if argv is None:
        argv = sys.argv[1:]
    description =	'epics-update supports various ways of updating EPICS packages.\n'
    epilog_fmt  =	'\nExamples:\n' \
                    'epics-update --RELEASE_SITE\n' \
                    'epics-update -p asyn/R4.31-1.0.0 -p busy/R1.6.1-0.2.5\n'
    epilog = textwrap.dedent( epilog_fmt )
    parser = argparse.ArgumentParser( description=description, formatter_class=argparse.RawDescriptionHelpFormatter, epilog=epilog )
    parser.add_argument( '-p', '--package',   dest='packages', action='append', \
                        help='EPICS module-name/release-version. Ex: asyn/R4.30-1.0.1', default=[] )
    parser.add_argument( '-f', '--input_file_path', action='store', help='Read list of module releases from this file' )
    parser.add_argument( '-r', '--RELEASE_SITE', action='store_true',  help='Update RELEASE_SITE' )
    parser.add_argument( '-s', '--stable',   action='store_true', help='Update module dependencies to latest stable versions.' )
    parser.add_argument( '-t', '--top',      action='store',  default='.', help='Top of release area.' )
    parser.add_argument( '-v', '--verbose',  action="store_true", help='show more verbose output.' )
    parser.add_argument( '--version',  		 action="version", version=eco_tools_version )

    options = parser.parse_args( )

    return options 

def main(argv=None):
    options = process_options(argv)

    if (options.input_file_path):
        try:
            in_file = open(options.input_file_path, 'r')
        except IOError, e:
            sys.stderr.write('Could not open "%s": %s\n' % (options.input_file_path, e.strerror))
            return None

        # Read in pairs (package release) one per line
        for line in in_file:
            # Remove comments
            line = line.partition('#')[0]

            # Add anything that looks like a module release specification
            modulePath = line.strip()
            (module, release) = os.path.split( modulePath )
            if module and release:
                options.packages += [ modulePath ]
                if options.verbose:
                    print 'Adding: %s' % modulePath

            # repeat above for all lines in file

        in_file.close()

    count = 0
    if options.RELEASE_SITE:
        curDir = os.getcwd()
        os.chdir( options.top )
        if options.verbose:
            print "Updating %s/RELEASE_SITE ..." % options.top
        inputs = assemble_release_site_inputs( batch=True )
        export_release_site_file( inputs, debug=options.verbose )
        os.chdir( curDir )
        count += 1

    if options.stable:
        count += update_stable( debug=options.verbose )

    if len( options.packages ) > 0:
        count += update_pkg_dependency( options.top, options.packages, verbose=options.verbose )

    print "Done: Updated %d RELEASE file%s." % ( count, "" if count == 1 else "s" )
    return 0

if __name__ == '__main__':
    status = main()
    sys.exit(status)
