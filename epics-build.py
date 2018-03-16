#!/usr/bin/env python
#  Name: epics-build.py
#  Abs:  A tool to build one or more EPICS releases
#
#  Packages specified by -p or --package with syntax pkg-name/pkg-version
#  Example:
#    epics-build -p iocAdmin/R3.1.15-1.0.0 -m autosave/R5.6.2-2.2.0
#
#  Supports smart defaults and overrides for:
#       * EPICS_MODULES - path to top of EPICS modules directory
#       * EPICS_TOP or EPICS_SITE_TOP - path to top of EPICS release area
#
#  Auth: 13-Dec-2016, Bruce Hill          (bhill)
#  Rev:  dd-mmm-yyyy, Reviewer's Name     (USERNAME)
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
import json
import Repo
import gitRepo
import svnRepo
import Releaser 
from git_utils import *
from svn_utils import *
from version_utils import *
from eco_version import eco_tools_version

# from cram_utils import *
from repo_defaults import *

# __all__ = ['export_release_site_file', 'assemble_cvs_inputs_from_term']

def getEnv( envVar ):
    result = os.getenv( envVar )
    if not result:
        result = '?'
    return result


def build_modules( options ):
    if options.top:
        if not os.path.isdir( options.top ):
            print "Invalid --top %s" % options.top
    try:
        releases = find_releases( options )
        for release in releases:
            release.InstallPackage( installTop=options.top, force=options.force )
    except:
        print sys.exc_value
        print 'build_modules: Not all packages were installed!'
 
def find_releases( options ):
    releases = []
    for package in options.packages:
        release = Releaser.find_release( package, options.verbose )
        if release is None:
            print "Error: Could not find packageSpec: %s" % package
        else:
            releases += [ release ]
    return releases

def buildDependencies( pkgTop, verbose=False ):
    # Check Dependendents
    print "Checking dependents for %s" % ( pkgTop )
    buildDep = getEpicsPkgDependents( pkgTop, verbose=verbose )
    for dep in buildDep:
        if dep == 'base':
            continue    # Just check module dependents
        package = "%s/%s" % ( dep, buildDep[dep] )
        release = Releaser.find_release( package, verbose=verbose )
        if release is None:
            print "Error: Could not find package %s" % package
            continue
        release.InstallPackage( )

def process_options(argv):
    if argv is None:
        argv = sys.argv[1:]
    description = 'epics-build builds one or EPICS module releases.\n'
    epilog_fmt = '\nStandard EPICS modules can be specified w/ just the module basename.\n'\
            + 'Similarly, modules or packages which are listed in the eco modulelist\n'\
            + '     %s\n'\
            + 'can be specified w/ just the module or package name.\n'\
            + '\nLonger module repo paths will be checked against GIT_TOP (%s).\n' \
            + 'and also against svn tags top (%s).\n' \
            + 'and also cvs root (%s).\n' \
            + 'i.e. Repo searched for in $TOP/[module-path/]module-name/release-version\n' \
            + '\nExamples:\n' \
            + 'epics-build -p history/R2.6.1\n' \
            + 'epics-build -p asyn/4.31-0.1.0 --top /afs/slac/g/lcls/epics/R3.15.5-1.0/modules\n'
    epilog = textwrap.dedent(epilog_fmt % ( gitModulesTxtFile, DEF_GIT_REPOS_URL, DEF_SVN_REPO, DEF_CVS_ROOT ))
    parser = argparse.ArgumentParser( description=description, formatter_class=argparse.RawDescriptionHelpFormatter, epilog=epilog )
    parser.add_argument( '-p', '--package',   dest='packages', action='append', \
                        help='EPICS module-name/release-version. Ex: asyn/R4.30-1.0.1', default=[] )
#   parser.add_argument( '-b', '--base',     action='store',  help='Use to set EPICS_BASE in RELEASE_SITE' )
    parser.add_argument( '-f', '--input_file_path', action='store', help='Read list of module releases from this file' )
    parser.add_argument( '-r', '--repo',     action='store',  help='repo url' )
    parser.add_argument( '-t', '--top',      action='store',  help='Top of release area.' )
    parser.add_argument( '--dep',            action='store',  help='Build dependencies for specified directory.' )
    parser.add_argument( '--force',          action='store_true',  help='Force rebuild.' )
    parser.add_argument( '-v', '--verbose',  action="store_true", help='show more verbose output.' )
    parser.add_argument( '--version',        action="version", version=eco_tools_version )

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

    if options.dep:
        buildDependencies( options.dep, verbose=options.verbose )
    elif len( options.packages ) == 0:
        print 'Error: No module/release packages specified!'
        return -1

    build_modules( options )

    return 0

if __name__ == '__main__':
    status = main()
    sys.exit(status)
