#!/usr/bin/env python
'''This script import a PCDS EPICS IOC from svn to a git repo.'''
import sys
import argparse
import os.path
import re
import shutil
import tempfile
import subprocess
from git_utils import *

svnRepoEnvVar       = 'CTRL_REPO'
svnRepoBranchPath   = 'branches/merge/epics'
svnRepoTagsPath     = 'epics/tags'
svnRepoTrunkPath    = 'epics/trunk'
gitEpicsRoot        = "/afs/slac.stanford.edu/g/cd/swe/git/repos/package/epics"
authorsFile         = "/afs/slac.stanford.edu/g/cd/swe/git/repos/package/epics/modules/authors.txt"
svnRepoRoot         = os.environ[svnRepoEnvVar]

def importIOC( iocSpec, name=None, trunk=None, branches=[], tags=[], verbose=False ):
    if  trunk is None: 
        trunk = os.path.join( svnRepoRoot, svnRepoTrunkPath, iocSpec, "current" )
    print "Importing svn IOC %s from %s" % ( iocSpec, trunk )
    svn_tags  = [ os.path.join( svnRepoRoot, svnRepoTagsPath, iocSpec ) ]
    svn_tags += tags
    if name is None:
        name = iocSpec
    importTrunk( trunk, name, branches=branches, tags=svn_tags, verbose=verbose )

def importTrunk( trunk, name, branches=[], tags=[], verbose=False ):
    # Create a tmp folder to work in
    tpath = tempfile.mkdtemp()
    tmpGitRepoPath = os.path.join( tpath, name )
    svnGitRepoPath = os.path.join( gitEpicsRoot, name + '.git' )
    if os.path.isdir( svnGitRepoPath ):
        print "svn import of repo already exists:", svnGitRepoPath
        return

    # Create the git svn clone command
    git_cmd = [ "git","svn","clone",
                    "--authors-file",   authorsFile,
                    "--trunk", trunk ]
    for b in branches:
        git_cmd.extend( [ "--branches", b ] )

    for t in tags:
        git_cmd.extend( [ "--tags", t ] )

    print "Import svn trunk %s to %s:" % ( trunk, svnGitRepoPath )
    git_cmd.extend( [ svnRepoRoot, tmpGitRepoPath ] )

    if verbose:
        print "git cmd:",
        for arg in git_cmd:
            print arg,
        print

    confirmResp = raw_input( 'Proceed (Y/n)?' )
    if len(confirmResp) != 0 and confirmResp != "Y" and confirmResp != "y":
        return

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
    subprocess.check_call([ "git", "clone", "--bare", tmpGitRepoPath, svnGitRepoPath ])
    shutil.rmtree(tpath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='''This script creates a git repo for each specified svn IOC ....
The trunk and one tags branch are derived from the IOC name.
Additional paths for both branches and tags may be added if desired either way.
''')
    parser.add_argument( '-i', '--iocSpec',  action='store',  help='svn ioc specification to import. (trunk is $CTRL_REPO/trunk/pcds/epics/ioc/IOC_SPEC/current)' )
    parser.add_argument( '-T', '--trunk',    action='store',  help='svn trunk path  to import. (relative to env CTRL_REPO)', default=None )
    parser.add_argument( '-b', '--branches', action='append', help='svn branch(es)  to import. (relative to env CTRL_REPO)', default=[] )
    parser.add_argument( '-t', '--tags',     action='append', help='svn tag paths   to import. (relative to env CTRL_REPO)', default=[] )
    parser.add_argument( '-v', '--verbose',  action="store_true", help='show more verbose output.' )
    parser.add_argument( '-n', '--name',     help='name of GitHub Repo.' )
    parser.add_argument( '-U', '--URL',      help='URL of GitHub Repo.' )

    args = parser.parse_args( )

    if args.iocSpec and args.trunk:
        print 'Please specify either a IOC specification or a trunk path, not both.'    
        sys.exit()

    if args.iocSpec:
        importIOC( args.iocSpec, name=args.name, trunk=args.trunk, branches=args.branches,
                      tags=args.tags, verbose=args.verbose )
    elif args.trunk is not None or len(args.branches) > 0:
        if not args.name:
            print 'Please provide a name for git repo'
            sys.exit()
        if  args.trunk is None:
            args.trunk = args.branches[0]
        importTrunk( args.trunk, args.name, args.branches[1:], args.tags, args.verbose )
    else:
        parser.print_help()
        print 'Please provide a iocSpec name, or one or more branches to import'
        sys.exit() 

    print "Done."

