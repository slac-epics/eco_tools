#!/usr/bin/env python
'''This script import a PCDS EPICS module from svn to a git repo.'''
import sys
import argparse
import os.path
import re
import shutil
import tempfile
import subprocess
from git_utils import *

svnRepoEnvVar		= 'CTRL_REPO'
svnRepoBranchPath	= 'branches/merge/epics/modules'
svnRepoTagsPath		= 'epics/tags/modules'
svnRepoTrunkPath	= 'trunk/pcds/epics/modules'
moduleDestDir		= "/afs/slac/g/cd/swe/git/repos/package/epics/modules/from-svn"
authorsFile			= "/afs/slac/g/cd/swe/git/repos/package/epics/modules/authors.txt"
svnRepoRoot         = os.environ[svnRepoEnvVar]

def importModule( module, name=None, branches=[], tags=[], verbose=False ):
    svnPackageLocation = os.path.join( svnRepoRoot, svnRepoTrunkPath, module )
    print "Importing svn module %s from %s" % ( module, svnPackageLocation )
    svn_trunk  = os.path.join( svnRepoTrunkPath, module, "current" )
    svn_tags   = [ os.path.join( svnRepoTagsPath,	 module ) ]
    svn_tags += tags
    if name is None:
        name = module
    importTrunk( svn_trunk, name, branches=branches, tags=svn_tags )

def importTrunk( trunk, name, branches=[], tags=[], verbose=False ):
    # Create a tmp folder to work in
    tpath = tempfile.mkdtemp()
    tmpGitRepoPath = os.path.join( tpath, name )

    # Create the git svn clone command
    git_cmd = [	"git","svn","clone",
                    "--authors-file",   authorsFile,
                    "--trunk", trunk ]
    for b in branches:
        git_cmd.extend( [ "--branches", b ] )

    for t in tags:
        git_cmd.extend( [ "--tags", t ] )

    git_cmd.extend( [ svnRepoRoot, tmpGitRepoPath ] )

    if verbose:
        print "Running cmd:",
        for arg in git_cmd:
            print arg,
        print

    # Run git svn clone
    subprocess.check_call( git_cmd )
 
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
    newGitRepoPath = os.path.join( moduleDestDir, name + '.git' )
    subprocess.check_call([	"git", "clone", "--bare", tmpGitRepoPath, newGitRepoPath ])
    shutil.rmtree(tpath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='''This script creates a git repo for each specified svn module....
''')
    parser.add_argument( '-m', '--module',   action='store',  help='svn module name to import.' )
    parser.add_argument( '-b', '--branches', action='append', help='svn branch(es)  to import.', default=[] )
    parser.add_argument( '-t', '--tags',	 action='append', help='svn tag paths   to import.', default=[] )
    parser.add_argument( '-v', '--verbose',  action="store_true", help='show more verbose output.' )
    parser.add_argument( '-n', '--name',     help='name of GitHub Repo.' )

    args = parser.parse_args( )

    if args.module:
        importModule( args.module, name=args.name, branches=args.branches,
                      tags=args.tags, verbose=args.verbose )
    elif len(args.branches) > 0: 
        if not args.name:
            print 'Please provide a name for git repo'    
            sys.exit()
        trunk = args.branches[0]
        importTrunk( trunk, args.name, args.branches[1:], args.tags, args.verbose )
    else:
        print 'Please provide a module name, or one or more brances to import'
        sys.exit() 

    print "Done."

