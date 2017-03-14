'''
Utilities for cvs repos'''

import os
import sys
import subprocess
import fileinput
from repo_defaults import *

def cvsPathExists( cvsPath, revision=None, debug=False ):
    try:
        if revision:
            repoCmd = [ 'cvs', 'ls', '%s@%s' % ( cvsPath, revision) ]
        else:
            repoCmd = [ 'cvs', 'ls', cvsPath ]
        if debug:
            print "cvsPathExists check_output: %s" % ' '.join( repoCmd )
        contents = subprocess.check_output( repoCmd, stderr = subprocess.STDOUT )
        # No need to check contents
        # If no exception, the path exists
        return True
    except RuntimeError:
        return False
    except subprocess.CalledProcessError:
        return False

def cvsGetWorkingBranch( debug=False ):
    '''See if the current directory is the top of an cvs working directory.
    Returns a 3-tuple of [ url, branch, tag ], [ None, None, None ] on error.
    For a valid cvs working dir, url must be a valid string, branch is typically
    the last component of the working dir path.  tag is either None or the same
    as branch if path matches the cvs tags naming scheme.'''
    repo_url    = None
    repo_branch = None
    repo_tag    = None
    try:
        repoCmd = [ 'cvs', 'info', '.' ]
        statusInfo = subprocess.check_output( repoCmd, stderr=subprocess.STDOUT )
        statusLines = statusInfo.splitlines()
        for line in statusLines:
            if line is None:
                break
            if line.startswith( "URL:" ):
                repo_url = line.split()[1]
                repo_tag = None
                ( parent_dir, repo_branch ) = os.path.split( repo_url )
                while parent_dir:
                    ( parent_dir, dir_name ) = os.path.split( parent_dir )
                    if dir_name == 'tags':
                        repo_tag = repo_branch
                        break
                break

    except OSError, e:
        if debug:
            print e
        pass
    except subprocess.CalledProcessError, e:
        if debug:
            print e
        pass
    return ( repo_url, repo_branch, repo_tag )

def cvsFindPackageRelease( packageSpec, tag, debug = False, verbose = False ):
    (repo_url, repo_path, repo_tag) = (None, None, None)
    if verbose:
        print "cvsFindPackageRelease: Need to find packageSpec=%s, tag=%s" % (packageSpec, tag)

    if verbose:
        if repo_url:
            print "cvsFindPackageRelease found %s/%s: url=%s, repo_path=%s, tag=%s" % (packageSpec, tag, repo_url, repo_path, repo_tag)
        else:
            print "cvsFindPackageRelease Error: Cannot find %s/%s" % (packageSpec, tag)
    return (repo_url, repo_path, repo_tag)

def parseCVSModulesTxt( cvsRepoRoot=None ):
    '''Parse the CVS modules file and return a dict of packageName -> location'''
    package2Location = {}
    if  cvsRepoRoot is None:
        cvsRepoRoot = os.environ['CVSROOT']
    cvsModulesTxtFile = os.path.join( cvsRepoRoot, 'CVSROOT', 'modules')
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
        # TODO: Support other CVS module features
        # Spear CVS repo uses these CVS module features
        # Example: If CVSROOT/modules contains
        # foo   path/to/foo &bar
        # bar   -d subDir/bar path/to/bar
        # Then:
        # % cvs co foo
        # is equivalent to
        # % cvs co path/to/foo MAIN_TRUNK
        # % cd MAIN_TRUNK
        # % cvs co path/to/bar subDir/bar
        # We could change function to return a triple
        # return ( package2Location, dirName, submodules )
        
        packageName = parts[0]
        packageLocation = parts[1]
        package2Location[packageName] = packageLocation
    return package2Location

