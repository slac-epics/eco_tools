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

# from cram_utils import *
from repo_defaults import *
from git_utils import *
from gitRepo   import *
from svn_utils import *
from svnRepo   import *

CVS_ROOT_TOP = '/afs/slac/g/lcls/cvs'
GIT_REPO_MODULES = DEF_GIT_REPOS + '/package/epics/modules'

# __all__ = ['export_release_site_file', 'assemble_cvs_inputs_from_term']

def getEnv( envVar ):
    result = os.getenv( envVar )
    if not result:
        result = '?'
    return result

def parseCVSModulesTxt():
    '''Parse the CVS modules file and return a dict of packageName -> location'''
    package2Location = {}
    cvsModulesTxtFile = os.path.join(os.environ['CVSROOT'], 'CVSROOT', 'modules')
    if not os.path.exists(cvsModulesTxtFile):
        print "Cannot determine CVS modules from modules file."
        return package2Location
    
    with open(cvsModulesTxtFile, 'r') as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        parts = line.split()
        if(len(parts) < 2):
            print "Error parsing ", cvsModulesTxtFile, "Cannot break", line, "into columns with enough fields using spaces/tabs"
            continue
        packageName = parts[0]
        packageLocation = parts[1]
        package2Location[packageName] = packageLocation
    return package2Location
        
cvs_modules2Location = parseCVSModulesTxt()

def build_modules( options ):
    releases = find_releases( options )
    for release in releases:
        build_release( release )
 
def find_releases( options ):
    releases = []
    for package in options.package:
        releases += [ find_release_repo( package, options ) ]
    return releases

def find_release_repo( module, options ):
    repo = None
    ( module_name, release_name ) = os.path.split( module )
    (git_url, git_tag) = gitFindPackageRelease( module_name, release_name, verbose = options.verbose )
    if git_url is not None:
        repo = gitRepo( git_url, None, git_tag )
    if repo is None:
        (svn_url, svn_branch, svn_tag) = svnFindPackageRelease( module_name, release_name, debug = True, verbose = options.verbose )
        if options.verbose:
            print "find_release_repo: Found svn_url=%s, svn_path=%s, svn_tag=%s" % ( svn_url, svn_branch, svn_tag )
        if svn_url is not None:
            repo = svnRepo( svn_url, svn_branch, svn_tag )
    return repo

def build_release( release ):
    curDir = os.getcwd()
    release.CheckOutRelease( release.GetWorkingBranch(), tagName, destinationPath )

def checkOutModule(packageName, tag, destinationPath):
    '''Checkout the module from GIT/CVS. 
    We first check to see if GIT has the module; if so, we clone the repo from git and do a headless checkout for the selected tag.
    Otherwise, we issue a command to CVS.
    '''

    if tag == '':
        print "Checkout %s to sandbox directory %s" % ( packageName, destinationPath )
    else:
        print "Checkout %s, tag %s, to directory %s" % ( packageName, tag, destinationPath )
    confirmResp = raw_input( 'Proceed (Y/n)?' )
    if len(confirmResp) != 0 and confirmResp != "Y" and confirmResp != "y":
        print "Aborting....."
        sys.exit(0)

    if os.path.exists(destinationPath):
        print 'Directory already exists!  Aborting.....'
        sys.exit(0)

    parent_dir = os.path.dirname( destinationPath )
    if len(parent_dir) > 0 and parent_dir != '.' and not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    # See if we can find it in with the git repos
    pathToGitRepo = determinePathToGitRepo(packageName)

    if pathToGitRepo:
        if pathToGitRepo.startswith("svn:///"):
            pathToSVNRepo =  pathToGitRepo.replace("svn:///", "file:///")
            if ( tag == 'MAIN_TRUNK' or tag == 'current' ):
                cmd=[ 'svn', 'checkout', pathToSVNRepo, destinationPath ]
            else:
                cmd=[ 'svn', 'checkout', '--revision', tag, pathToSVNRepo, destinationPath ]
            print cmd
            subprocess.check_call(cmd)
            os.chdir(destinationPath)
        else:
            print packageName, "is a git package.\nCloning the repository at", pathToGitRepo
            if os.path.exists(destinationPath):
                print "The folder", os.path.abspath(destinationPath), "already exists. If you intended to update the checkout, please do a git pull to pull in the latest changes."
                print "Aborting....."
                sys.exit(1)
            cmd=['git', 'clone', '--recursive', pathToGitRepo, destinationPath]
            print cmd
            subprocess.check_call(cmd)
            os.chdir(destinationPath)
            if (tag != ''):
                # Do a headless checkout to the specified tag
                cmd=['git', 'checkout', tag]
                print cmd
                subprocess.check_call(cmd)
            #else: TODO Checkout a default branch if one isn't already selected.
            # 1. current release branch
            # 2. master
            # 3. github-master
            # 4. lcls-trunk
            # 5. pcds-trunk
    else:
        if (tag == 'MAIN_TRUNK'):
            cmd='cvs checkout -P -d ' + destinationPath + ' ' + packageName    
            print cmd
        else:
            cmd='cvs checkout -P -r '+ tag +' -d '+ destinationPath +' ' + packageName    
            print cmd
        os.system(cmd)
        os.chdir(destinationPath)

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
    parser.add_argument( '-p', '--package',   action='append', \
                        help='EPICS module-name/release-version. Ex: asyn/R4.30-1.0.1', default=[] )
    parser.add_argument( '-b', '--base',     action='store',  help='Use to set EPICS_BASE in RELEASE_SITE' )
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
                options.package += [ modulePath ]
                if options.verbose:
                    print 'Adding: %s' % modulePath

            # repeat above for all lines in file

        in_file.close()

    if len( options.package ) == 0:
        print 'Error: No module/release packages specified!'
        return -1

    build_modules( options )

    return 0

if __name__ == '__main__':
    status = main()
    sys.exit(status)
