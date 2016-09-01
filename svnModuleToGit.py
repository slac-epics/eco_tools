#!/usr/bin/env python
'''This script import a PCDS EPICS module from svn to a git repo.'''

import argparse
import os.path
import re
import shutil
import tempfile
from git_utils import *

svnRepoEnvVar		= 'CTRL_REPO'
svnRepoBranchPath	= 'branches/merge/epics/modules'
svnRepoTagsPath		= 'epics/tags/modules'
svnRepoTrunkPath	= 'trunk/pcds/epics/modules'
moduleDestDir		= "/afs/slac/g/cd/swe/git/repos/package/epics/modules/from-svn"
authorsFile			= "/afs/slac/g/lcls/vol8/git-repos/authors.txt"

def importModule( module ):
    svnRepoRoot = os.environ[svnRepoEnvVar]
    svnPackageLocation = os.path.join( svnRepoRoot, svnRepoTrunkPath, module )
    print "Importing svn module %s from %s" % ( module, svnPackageLocation )
 
    tpath = tempfile.mkdtemp()
    # Run git svn clone
    tmpGitRepoPath = os.path.join( tpath, module )
    subprocess.check_call([	"git", "svn", "clone",
                            "--authors-file", authorsFile,
                            "--branches",	os.path.join( svnRepoBranchPath,module ),
                            "--tags",		os.path.join( svnRepoTagsPath,	module ),
                            "--trunk",		os.path.join( svnRepoTrunkPath,	module, "current" ),
                            svnRepoRoot,	tmpGitRepoPath ])
 
    # Make lightweight tags for each of the svn remote tags
    # No need to use git annotated tags here, as each of these
    # svn tags are svn's equivalent of annotated tags, with
    # a comment, the tagger, and the tag timestamp.
    curDir = os.getcwd()
    os.chdir(tmpGitRepoPath)
    output = subprocess.check_output([ "git", "branch", "-a" ])
    lines  = output.splitlines()
    for line in lines:
        remoteTag = re.search( r"remotes/tags/([^@]*)$", line )
        if remoteTag:
            subprocess.check_call([ "git", "tag", remoteTag.group(1), remoteTag.group(0) ])

    os.chdir(curDir)

    # Create a bare master repo for the new git repository, cloned from our tmp repo
    newGitRepoPath = os.path.join( moduleDestDir, module + '.git' )
    subprocess.check_call([	"git", "clone", "--bare", tmpGitRepoPath, newGitRepoPath ])
    shutil.rmtree(tpath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='''This script creates a git repo for each specified svn module....
''')
    parser.add_argument( '-m', '--module', action='append', required=True, help='svn module name to import.' )

    args = parser.parse_args( )
    for m in args.module:
        importModule( m )

    print "Done."

