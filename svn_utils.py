'''
Utilities for svn repos'''

import os
import sys
import subprocess
import fileinput
from repo_defaults import *

def svnPathExists( svnPath, revision=None, debug=False ):
    try:
        if revision:
            repoCmd = [ 'svn', 'ls', '%s@%s' % ( svnPath, revision) ]
        else:
            repoCmd = [ 'svn', 'ls', svnPath ]
        if debug:
            print("svnPathExists check_output: %s" % ' '.join( repoCmd ))
        contents = subprocess.check_output( repoCmd, stderr = subprocess.STDOUT )
        # No need to check contents
        # If no exception, the path exists
        return True
    except RuntimeError:
        return False
    except subprocess.CalledProcessError:
        return False

def svnGetRemoteTags( pathToSvnRepo, verbose=False ):
    tags = []
    tagsPath = pathToSvnRepo.replace("trunk/pcds/epics/modules","epics/tags/modules")
    tagsPath = tagsPath.replace( "trunk", "tags" )
    tagsPath = tagsPath.replace( "/current", "" )
    try:
        tags = subprocess.check_output(["svn", "ls", tagsPath ] ).splitlines()
        tags = [ tag.replace("/", "") for tag in tags ]
    except:
        pass
    tags = sorted(tags)
    if verbose:
        print("svnGetRemoteTags: Found %d tags in %s" % ( len(tags), pathToSvnRepo ))
    return tags

def svnGetWorkingBranch( debug=False ):
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

    except OSError as e:
        if debug:
            print(e)
        pass
    except subprocess.CalledProcessError as e:
        if debug:
            print(e)
        pass
    return ( repo_url, repo_branch, repo_tag )

def svnFindPackageRelease( packagePath, tag, debug = False, verbose = False ):
    '''Search known svn package paths for the package.
    Returns a tuple: (repo_url, repo_path, repo_tag)
    Returns (None, None, None) on error'''
    if verbose:
        print("svnFindPackageRelease: Looking for packagePath=%s, tag=%s" % (packagePath, tag))
    (repo_url, repo_path, repo_tag) = (None, None, None)
    svn_paths   = []
    if tag:
        # Our svn tags all start w/ "R"
        # For compatibility w/ pkg_mgr, provide missing R if needed
        if not tag.startswith( "R" ):
            tag = "R" + tag
        svn_paths  += [ DEF_SVN_TAGS ]
        svn_paths  += [ os.path.join( DEF_SVN_TAGS, 'modules' ) ]
        svn_paths  += [ os.path.join( DEF_SVN_TAGS, 'extensions' ) ]
        svn_paths  += [ os.path.join( DEF_SVN_TAGS, 'ioc' ) ]
        svn_paths  += [ os.path.join( DEF_SVN_TAGS, 'ioc', 'common' ) ]
    else:
        tag = 'current'
        svn_paths  += [ os.path.join( DEF_SVN_REPO, DEF_SVN_STUB2 ) ]
        svn_paths  += [ os.path.join( DEF_SVN_REPO, DEF_SVN_STUB2, 'modules' ) ]
        svn_paths  += [ os.path.join( DEF_SVN_REPO, DEF_SVN_STUB2, 'extensions' ) ]
        svn_paths  += [ os.path.join( DEF_SVN_REPO, DEF_SVN_STUB1 ) ]
        svn_paths  += [ os.path.join( DEF_SVN_REPO, DEF_SVN_STUB1, 'ioc' ) ]
        svn_paths  += [ os.path.join( DEF_SVN_REPO, DEF_SVN_STUB1, 'ioc', 'common' ) ]
        svn_paths  += [ os.path.join( DEF_SVN_REPO, DEF_SVN_STUB1, 'modules' ) ]
        svn_paths  += [ os.path.join( DEF_SVN_REPO, DEF_SVN_STUB1, 'extensions' ) ]

    for path in svn_paths:
        url = os.path.join( path, packagePath, tag )
        if svnPathExists( url, debug=debug ):
            (repo_url, repo_path, repo_tag) = ( url, path, tag )
            break
    if verbose:
        if repo_url:
            print("svnFindPackageRelease found %s/%s: url=%s, repo_path=%s, tag=%s" % (packagePath, tag, repo_url, repo_path, repo_tag))
        else:
            print("svnFindPackageRelease Error: Cannot find %s/%s" % (packagePath, tag))
    return (repo_url, repo_path, repo_tag)

