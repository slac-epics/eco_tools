'''
Utilities for svn repos'''

import os
import sys
import subprocess
import fileinput
from repo_defaults import *

def svnPathExists( svnPath, revision=None, verbose=False ):
    try:
        if revision:
            repoCmd = [ 'svn', 'ls', '%s@%s' % ( svnPath, revision) ]
        else:
            repoCmd = [ 'svn', 'ls', svnPath ]
        if verbose:
            print "svnPathExists check_output: %s" % ' '.join( repoCmd )
        contents = subprocess.check_output( repoCmd, stderr = subprocess.STDOUT )
        # No need to check contents
        # If no exception, the path exists
        return True
    except RuntimeError:
        return False
    except subprocess.CalledProcessError:
        return False

def svnGetWorkingBranch( debug=False, verbose=False ):
    '''See if the current directory is the top of an svn working directory.
    Returns a 3-tuple of [ url, branch, tag ], [ None, None, None ] on error.
    For a valid svn working dir, url must be a valid string, branch is typically
    the last component of the working dir path.  tag is either None or the same
    as branch if path matches the svn tags naming scheme.'''
    repo_url    = None
    repo_branch = None
    repo_tag    = None
    try:
        repoCmd = [ 'svn', 'info', '.' ]
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
        if debug or verbose:
            print e
        pass
    except subprocess.CalledProcessError, e:
        if debug or verbose:
            print e
        pass
    return ( repo_url, repo_branch, repo_tag )

def svnFindPackageRelease( packageSpec, tag, debug = False, verbose = False ):
    (repo_url, repo_path, repo_tag) = (None, None, None)
    # Our svn tags all start w/ "R"
    # For compatibility w/ pkg_mgr, provide missing R if needed
    if not tag.startswith( "R" ):
        tag = "R" + tag
    if verbose:
        print "svnFindPackageRelease: Need to find packageSpec=%s, tag=%s\n" % (packageSpec, tag)

    svn_tag_paths  =  [ DEF_SVN_TAGS ]
    svn_tag_paths  += [ os.path.join( DEF_SVN_TAGS, 'modules' ) ]
    svn_tag_paths  += [ os.path.join( DEF_SVN_TAGS, 'extensions' ) ]
    svn_tag_paths  += [ os.path.join( DEF_SVN_TAGS, 'ioc/common' ) ]

    for path in svn_tag_paths:
        url = os.path.join( DEF_SVN_REPO, path, packageSpec, tag )
        if svnPathExists( url, verbose=verbose ):
            (repo_url, repo_path, repo_tag) = ( url, path, tag )
            break
    if verbose:
        if repo_url:
            print "svnFindPackageRelease: Found repo_url=%s, repo_path=%s, repo_tag=%s\n" % (repo_url, repo_path, repo_tag)
        else:
            print "svnFindPackageRelease Error: Cannot find %s/%s\n" % (packageSpec, tag)
    return (repo_url, repo_path, repo_tag)

