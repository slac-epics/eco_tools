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

svnRepoEnvVar       = 'CTRL_REPO'
svnRepoBranchPath   = 'branches/merge/epics/modules'
svnRepoTagsPath     = 'epics/tags/modules'
svnRepoTrunkPath    = 'trunk/pcds/epics/modules'
gitModuleDir        = "/afs/slac.stanford.edu/g/cd/swe/git/repos/package/epics/modules"
moduleDestDir       = "/afs/slac.stanford.edu/g/cd/swe/git/repos/package/epics/modules/from-svn"
authorsFile         = "/afs/slac.stanford.edu/g/cd/swe/git/repos/package/epics/modules/authors.txt"
svnRepoRoot         = 'file:///afs/slac/g/pcds/vol2/svn/pcds'
if svnRepoEnvVar in os.environ:
    svnRepoRoot = os.environ[svnRepoEnvVar]

def importModule( module, name=None, trunk=None, branches=[], tags=[], verbose=False ):
    if  trunk is None: 
        trunk = os.path.join( svnRepoTrunkPath, module, "current" )
    print "Importing svn module %s from %s" % ( module, trunk )
    svn_tags  = [ os.path.join( svnRepoTagsPath, module ) ]
    svn_tags += tags
    if name is None:
        name = module
    importTrunk( trunk, name, moduleDestDir, branches=branches, tags=svn_tags, verbose=verbose )

 # TODO: In both svnIocToGit.py and svnModuleToGit.py.  Move to git_utils.py
def importTrunk( trunk, name, gitRoot, branches=[], tags=[], verbose=False ):
    # Create a tmp folder to work in
    tpath = tempfile.mkdtemp()
    tmpGitRepoPath = os.path.join( tpath, name )
    svnGitRepoPath = os.path.join( gitRoot, name + '.git' )
    if os.path.isdir( svnGitRepoPath ):
        print "svn import of repo already exists:", svnGitRepoPath
        return

    if trunk.startswith( svnRepoRoot ):
        print "Error: trunk path should not include base svn repo path: %s" % trunk
        return

    # Create the git svn clone command
    git_cmd = [ "git","svn","clone",
                    "--authors-file",   authorsFile,
                    "--trunk", trunk ]
    for b in branches:
        if b.startswith( svnRepoRoot ):
            print "Error: branch path should not include base svn repo path: %s" % b
            return
        git_cmd.extend( [ "--branches", b ] )

    for t in tags:
        if t.startswith( svnRepoRoot ):
            print "Error: tags path should not include base svn repo path: %s" % t
            return
        git_cmd.extend( [ "--tags", t ] )

    print "Import svn trunk %s\n   to %s:" % ( trunk, svnGitRepoPath )
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

    # Create a bare upstream repo for the new git repository, cloned from our tmp repo
    subprocess.check_call([ "git", "clone", "--bare", tmpGitRepoPath, svnGitRepoPath ])
    shutil.rmtree(tpath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='''This script creates a git repo for each specified svn module....
If you specify a module, the trunk and one tags branch are derived from the module name.
If you do NOT specify a module, you must specify a package name and either a single trunk path, or at least one branch to import.
Additional paths for both branches and tags may be added if desired either way.
''')
    parser.add_argument( '-m', '--module',   action='store',  help='svn module name to import. (trunk from trunk/pcds/epics/modules/MODULE_NAME/current, tags from epics/tags/modules/MODULE_NAME)' )
    parser.add_argument( '-T', '--trunk',    action='store',  help='svn trunk path  to import. (relative to env CTRL_REPO)', default=None )
    parser.add_argument( '-b', '--branches', action='append', help='svn branch(es)  to import. (relative to env CTRL_REPO)', default=[] )
    parser.add_argument( '-t', '--tags',     action='append', help='svn tag paths   to import. (relative to env CTRL_REPO)', default=[] )
    parser.add_argument( '-v', '--verbose',  action="store_true", help='show more verbose output.' )
    parser.add_argument( '-n', '--name',     help='name of git repo.' )

    args = parser.parse_args( )

    if args.module and args.trunk:
        print 'Please specify either a module name or a trunk path, not both.'    
        sys.exit()

    if args.module:
        importModule( args.module, name=args.name, trunk=args.trunk, branches=args.branches,
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
        print 'Please provide a module name, or one or more branches to import'
        sys.exit() 

    print "Done."

