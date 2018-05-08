'''
Utilities for cvs repos'''

import os
import re
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

def cvsGetRemoteTags( packageName, verbose=False ):
    p1 = subprocess.Popen(['cvs', '-Q', 'rlog', '-h', packageName], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['awk', '-F"[.:]"', '/^\t/&&$(NF-1)!=0{print $1}'], stdin=p1.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
    output = p2.communicate()[0]

    plaintags = set()
    for line in output.split('\n'):
        line = line.strip()
        parts = line.split()
        if len(parts) < 1:
            continue
        plaintags.add(parts[0].split(":")[0])
    tags = sorted(plaintags)
    if verbose:
        print "cvsGetRemoteTags: Found %d tags in %s" % ( len(tags), packageName )
    return tags

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


def parseCVSModulesTxt( cvsRepoRoot=None, verbose=False ):
    '''Parse the CVS modules file and return a dict of packageName -> location'''
    package2Location = {}
    if  cvsRepoRoot is not None:
        os.environ['CVSROOT'] = cvsRepoRoot
    if 'CVSROOT' not in os.environ:
        if not os.path.exists( DEF_CVS_ROOT ):
            # CVS root not accessible.  Carry on quietly.
            return package2Location
        os.environ['CVSROOT'] = DEF_CVS_ROOT
    cvsModulesTxtFile = os.path.join( os.environ['CVSROOT'], 'CVSROOT', 'modules')
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

        # See if a directory path is specified
        dirPath = "."
        dirPathRegExp = re.compile( r"-d (\S+)" )
        dirPathMatch  = dirPathRegExp.search( line )
        if dirPathMatch:
            dirPath = dirPathMatch.group(1)
            line = line.replace( dirPathMatch.group(0), "" )

        # See if any submodules are specified
        subModules = []
        subModuleRegExp = re.compile( r"&(\S+)" )
        while True:
            subModuleMatch  = subModuleRegExp.search( line )
            if not subModuleMatch:
                break
            subModules.append( subModuleMatch.group(1) )
            line = line.replace( subModuleMatch.group(0), "" )

        # We should have at most 2 whitespace separated parts left: packageName packageLocation
        parts = line.split()
        if(len(parts) < 2):
            if verbose:
                print "Error parsing ", cvsModulesTxtFile, "Cannot break", line, "into columns with enough fields using spaces/tabs"
            continue

        packageName = parts[0]
        packageLocation = parts[1]
        package2Location[packageName] = packageLocation

    # Note: could return ( package2Location, dirPath, subModules ) if we intended to do something w/ dirPath or subModules
    return package2Location

