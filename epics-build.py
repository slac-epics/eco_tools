#!/usr/bin/env python
#  Name: epics-build.py
#  Abs:  A tool to build one or more EPICS releases
#
#  Packages specified by -p or --package with syntax pkg-name/pkg-version
#  Example:
#    epics-build -p iocAdmin/R3.1.15-1.0.0 -m autosave/R5.6.2-2.2.0
#
#  Supports smart defaults and overrides for:
#		* EPICS_MODULES - path to top of EPICS modules directory
#		* EPICS_TOP or EPICS_SITE_TOP - path to top of EPICS release area
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
import json
import Repo
import gitRepo
import svnRepo
import Releaser 
from git_utils import *
from svn_utils import *

# from cram_utils import *
from repo_defaults import *

CVS_ROOT_TOP = '/afs/slac/g/lcls/cvs'
GIT_REPO_MODULES = DEF_GIT_REPOS + '/package/epics/modules'

# __all__ = ['export_release_site_file', 'assemble_cvs_inputs_from_term']

def getEnv( envVar ):
    result = os.getenv( envVar )
    if not result:
        result = '?'
    return result


def build_modules( options ):
    try:
        releases = find_releases( options )
        for release in releases:
            release.InstallPackage( installTop=options.top )
    except:
        print 'build_modules: Not all packages were installed!'
 
def find_releases( options ):
    releases = []
    for package in options.packages:
        release = Releaser.find_release( package, options.verbose )
        if release is not None:
            releases += [ release ]
    return releases

def determinePathToGitRepo(packageName):
    '''If the specified package is stored in GIT, then return the URL to the GIT repo. Otherwise, return None'''
    (git_url, git_tag) = gitGetRemoteTag( packageName, tag=None )
    return git_url

def process_options(argv):
    if argv is None:
        argv = sys.argv[1:]
    description = 'epics-build builds one or EPICS module releases.\n'
    epilog_fmt = '\nStandard EPICS modules can be specified w/ just the module basename.\n'\
            + 'Similarly, modules or packages listed in eco_modulelist (%s)\n'\
            + 'can be specified w/ just the module or package name.\n'\
            + 'Longer module repo paths will be checked against GIT_TOP (%s).\n' \
            + 'and also against svn tags top (%s).\n' \
            + 'and also cvs root (%s).\n' \
            + 'i.e. Repo searched for in $TOP/[module-path/]module-name/release-version'
    epilog = epilog_fmt % ( gitModulesTxtFile, DEF_GIT_REPOS, DEF_SVN_REPO, CVS_ROOT_TOP )
    parser = argparse.ArgumentParser( description=description, epilog=epilog )
    parser.add_argument( '-p', '--package',   dest='packages', action='append', \
                        help='EPICS module-name/release-version. Ex: asyn/R4.30-1.0.1', default=[] )
#	parser.add_argument( '-b', '--base',     action='store',  help='Use to set EPICS_BASE in RELEASE_SITE' )
    parser.add_argument( '-f', '--input_file_path', action='store', help='Read list of module releases from this file' )
    parser.add_argument( '-r', '--repo',     action='store',  help='repo url' )
    parser.add_argument( '-t', '--top',      action='store',  help='Top of release area.' )
    parser.add_argument( '-v', '--verbose',  action="store_true", help='show more verbose output.' )

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

    if len( options.packages ) == 0:
        print 'Error: No module/release packages specified!'
        return -1

    build_modules( options )

    return 0

if __name__ == '__main__':
    status = main()
    sys.exit(status)
