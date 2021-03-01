#!/usr/bin/env python
#  Name: epics-jenkins.py
#  Abs:  A tool to handle jenkins SCM polling jobs.
#
#  This script can be run by jenkins for any commits to the repo
#  and must determine which, if any, branches need to a build test
#  and which new releases, if any, need to be built.
#  Needs to support builds for multiple EPICS base releases.
#
#  Arguments:
#		?
#  Example:
#    epics-jenkins -p iocAdmin/R3.1.15-1.0.0
#
#  Supports smart defaults and overrides for:
#       * EPICS_MODULES - path to top of EPICS modules directory
#       * EPICS_TOP or EPICS_SITE_TOP - path to top of EPICS release area
#
#  Auth: 01-Dec-2020, Bruce Hill          (bhill)
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
import Repo
import gitRepo
import svnRepo
import Releaser
import json
from git_utils import *
from svn_utils import *
from version_utils import *
from eco_version import eco_tools_version

from repo_defaults import *

def build_modules( options ):
    status = 0
    if options.top:
        if not os.path.isdir( options.top ):
            print "Invalid --top %s" % options.top
    try:
        #TODO: remove hard coded install top
        test_installTop = "/var/lib/jenkins/jobs/" + options.packages[0] + "/testWorkspace"
        releases = find_releases_config( options )
        if len(releases) == 0:
            status = 1
        else:
            for release in releases:
                #result = release.InstallPackage( installTop=options.top, force=options.force, rmFailed=options.rmFailed )
                
                result = release.InstallPackage( installTop=test_installTop, force=options.force, rmFailed=options.rmFailed )
                if status == 0:
                    status = result
    except:
        print sys.exc_value
        print 'build_modules: Not all packages were installed!'
        return 1
    return status
 
def find_releases( options ):
    releases = []
    for package in options.packages:
        release = Releaser.find_release( package, verbose=options.verbose )
        if release is None:
            print "Error: Could not find packageSpec: %s" % package
        else:
            releases += [ release ]
    return releases

def find_releases_config( options ):
    jenkins_config = import_config(".")
    package_split = options.packages[0].split("/")
    package = package_split[0] + "/" + package_split[-1]
    release = Releaser.find_release( package, verbose=options.verbose )
    if release is None:
        print "Error: Could not find packageSpec: %s" % package
    else:
        return [release]
    return

def import_config(config_path):
    with open("/cds/home/l/lking/eco_tools/jenkins-config.json") as filename:
        jenkins_config = json.load(filename)
    return jenkins_config

def buildDependencies( pkgTop, verbose=False ):
    status = 0
    # Check Dependendents
    print "Checking dependents for %s" % ( pkgTop )
    buildDep = getEpicsPkgDependents( pkgTop )
    for dep in buildDep:
        if dep == 'base':
            continue    # Just check module dependents
        package = "%s/%s" % ( dep, buildDep[dep] )
        release = Releaser.find_release( package, verbose=verbose )
        if release is None:
            print "Error: Could not find package %s" % package
            continue
        result = release.InstallPackage( )
        if result != 0:
            status = 1
    return status

def process_options(argv):
    if argv is None:
        argv = sys.argv[1:]
    description = 'epics-jenkins builds one or EPICS module releases.\n'
    epilog_fmt = '\nStandard EPICS modules can be specified w/ just the module basename.\n'\
            + 'Similarly, modules or packages which are listed in the eco modulelist\n'\
            + '     %s\n'\
            + 'can be specified w/ just the module or package name.\n'\
            + '\nLonger module repo paths will be checked against GIT_TOP (%s).\n' \
            + 'and also against svn tags top (%s).\n' \
            + 'and also cvs root (%s).\n' \
            + 'i.e. Repo searched for in $TOP/[module-path/]module-name/release-version\n' \
            + '\nExamples:\n' \
            + 'epics-jenkins -p history/R2.6.1\n' \
            + 'epics-jenkins -p asyn/4.31-0.1.0 --top /afs/slac/g/lcls/epics/R3.15.5-1.0/modules\n'
    epilog = textwrap.dedent(epilog_fmt % ( gitModulesTxtFile, DEF_GIT_REPO_PATH, DEF_SVN_REPO, DEF_CVS_ROOT ))
    parser = argparse.ArgumentParser( description=description, formatter_class=argparse.RawDescriptionHelpFormatter, epilog=epilog )
    parser.add_argument( '-p', '--package',   dest='packages', action='append', \
                        help='EPICS module-name/release-version. Ex: asyn/R4.30-1.0.1', default=[] )
#   parser.add_argument( '-b', '--base',     action='store',  help='Use to set EPICS_BASE in RELEASE_SITE' )
    parser.add_argument( '-f', '--input_file_path', action='store', help='Read list of module releases from this file' )
    parser.add_argument( '-r', '--repo',     action='store',  help='repo url' )
    parser.add_argument( '-t', '--top',      action='store',  help='Top of release area.' )
    parser.add_argument( '--commit',         action='store',  help='Commit to checkout.' )
    parser.add_argument( '--priorCommit',    action='store',  help='Prior jenkins build commit.' )
    parser.add_argument( '--dep',            action='store',  help='Build dependencies for specified directory.' )
    parser.add_argument( '--force',          action='store_true',  help='Force rebuild.' )
    parser.add_argument( '--rmFailed',       action='store_true',  help='Remove failed builds.' )
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

    if options.commit:
        print 'epics-jenkins: commit to build %s' % options.commit
        if options.commit == options.priorCommit:
            print 'epics-jenkins: No change, nothing to build.'
            return 0

    if options.priorCommit:
        print 'epics-jenkins: priorCommit to build %s' % options.priorCommit

    if options.dep:
        result = buildDependencies( options.dep, verbose=options.verbose )
        if result != 0:
            return 0  
    elif len( options.packages ) == 0:
        print 'Error: No module/release packages specified!'
        return 0

    status = build_modules( options )
    if status:
        print 'epics-jenkins build error\n'
    return 0

if __name__ == '__main__':
    status = main()
    sys.exit(status)
