'''
Utilities for svn repos'''

import os
import sys
import subprocess
import fileinput

def svnGetWorkingBranch( ):
    '''See if the current directory is the top of an svn working directory.
    Returns a 3-tuple of [ url, branch, tag ], [ None, None, None ] on error.
    For a valid svn working dir, url must be a valid string, branch is typically
    the last component of the working dir path.  tag is either None or the same
    as branch if path matches the svn tags naming scheme.'''
    try:
        svnInfo = subprocess.check_output( [ 'svn', 'info', '.' ], stderr=subprocess.STDOUT )
        for line in svnInfo.splitlines():
            if line is None:
                break
            if line.startswith( "URL:" ):
                svn_url = line.split()[1]
                svn_tag = None
                ( parent_dir, svn_branch ) = os.path.split( svn_url )
                while parent_dir:
                    ( parent_dir, dir_name ) = os.path.split( parent_dir )
                    if dir_name == 'tags':
                        svn_tag = svn_branch
                        break
                return ( svn_url, svn_branch, svn_tag )

    except subprocess.CalledProcessError:
        pass

    return ( None, None, None )

def svnPathExists( svnPath, revision=None ):
    try:
        if revision:
            contents = subprocess.check_output( [ 'svn', 'ls', '%s@%s' % ( svnPath, revision) ], stderr = subprocess.STDOUT )
        else:
            contents = subprocess.check_output( [ 'svn', 'ls', svnPath ], stderr = subprocess.STDOUT )
        return True
    except RuntimeError:
        return False
    except subprocess.CalledProcessError:
        return False
