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
from repo_defaults import *

svnRepoEnvVar       = 'CTRL_REPO'
svnRepoBranchPath   = 'branches/merge/epics'
svnRepoTagsPath     = 'epics/tags'
svnRepoTrunkPath    = 'epics/trunk'
gitEpicsRoot        = "/afs/slac.stanford.edu/g/cd/swe/git/repos/package/epics"
authorsFile         = "/afs/slac.stanford.edu/g/cd/swe/git/repos/package/epics/modules/authors.txt"
svnRepoRoot         = 'file:///afs/slac/g/pcds/vol2/svn/pcds'
if svnRepoEnvVar in os.environ:
    svnRepoRoot = os.environ[svnRepoEnvVar]

def importIOC( iocSpec, name=None, trunk=None, branches=[], tags=[], gitUrl=None, batch=False, verbose=False ):
    if  trunk is None: 
        trunk = os.path.join( svnRepoTrunkPath, iocSpec, "current" )
        if not svnPathExists( os.path.join(svnRepoRoot, trunk) ):
            trunk = os.path.join( svnRepoTrunkPath, iocSpec )
    if not svnPathExists( os.path.join(svnRepoRoot, trunk) ):
        print( "Error: trunk path does not exist: %s" % os.path.join(svnRepoRoot, trunk) )
        return
    print "Importing svn IOC %s from %s" % ( iocSpec, trunk )
    svn_tags  = [ os.path.join( svnRepoTagsPath, iocSpec ) ]
    svn_tags += tags
    if name is None:
        name = iocSpec
    if not gitUrl:
        gitUrl = os.path.join( gitEpicsRoot, name + '.git' )
    importTrunk( trunk, name, gitUrl, branches=branches, tags=svn_tags,
                batch=batch, verbose=verbose )

 # TODO: In both svnIocToGit.py and svnModuleToGit.py.  Move to git_utils.py
def importTrunk( trunk, name, gitUrl, branches=[], tags=[], verbose=False, batch=False ):
    # Create a tmp folder to work in
    tpath = tempfile.mkdtemp()
    tmpGitRepoPath = os.path.join( tpath, name )
    if os.path.isdir( gitUrl ):
        print "svn import of repo already exists:", gitUrl
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

    print "Import svn trunk %s\n   to %s:" % ( trunk, gitUrl )
    git_cmd.extend( [ svnRepoRoot, tmpGitRepoPath ] )

    if verbose:
        print "git cmd:",
        for arg in git_cmd:
            print arg,
        print

    if not batch:
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
    subprocess.check_call([ "git", "clone", "--bare",
                            "--template=%s/templates" % DEF_GIT_MODULES_PATH,
                            tmpGitRepoPath, gitUrl ])
    shutil.rmtree(tpath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='''This script creates a git repo for each specified svn IOC ....
The trunk and one tags branch are derived from the IOC name.
Additional paths for both branches and tags may be added if desired either way.
''')
    parser.add_argument( '-f', '--filename', action='store',  help='Filename containing list of iocSpecs')
    parser.add_argument( '-i', '--iocSpec',  action='store',  help='Example: svnIocToGit -i ioc/common/NewportAgilis (trunk imported from SVN_REPO/epics/trunk/IOC_SPEC/current, tags from SVN_REPO/epics/tags/IOC_SPEC)' )
    parser.add_argument( '-T', '--trunk',    action='store',  help='svn trunk path  to import. (relative to env CTRL_REPO)', default=None )
    parser.add_argument( '-b', '--branches', action='append', help='svn branch(es)  to import. (relative to env CTRL_REPO)', default=[] )
    parser.add_argument( '-t', '--tags',     action='append', help='svn tag paths   to import. (relative to env CTRL_REPO)', default=[] )
    parser.add_argument( '-v', '--verbose',  action="store_true", help='show more verbose output.' )
    parser.add_argument( '-n', '--name',     help='name of git repo.' )
    parser.add_argument( '-U', '--URL',      help='URL of git repo. Def GIT_TOP/package/epics/IOC_SPEC' )

    args = parser.parse_args( )

    if args.iocSpec and args.trunk:
        print 'Please specify either a IOC specification or a trunk path, not both.'    
        sys.exit()

    if args.filename:
        try:
            iocSpecs = []
            with open( args.filename, "r" ) as f:
                iocSpecs = f.readlines()
            for iocSpec in iocSpecs:
                iocSpec = iocSpec.strip(' 	/\n')
                # Skip comments
                if iocSpec.startswith( '#' ):
                    continue
                gitUrl = os.path.join( gitEpicsRoot, iocSpec + '.git' )
                if os.path.isdir( gitUrl ):
                    print( "%s: Already imported" % iocSpec )
                    continue
                importIOC( iocSpec, verbose=args.verbose, batch=True )
        except Exception as e:
            print( "Error opening %s: %s" % ( args.filename, e ) )
    elif args.iocSpec:
        importIOC( args.iocSpec, name=args.name, trunk=args.trunk, branches=args.branches,
                      tags=args.tags, gitUrl=args.URL, verbose=args.verbose )
    elif args.trunk is not None or len(args.branches) > 0:
        if not args.name:
            print 'Please provide a name for git repo'
            sys.exit()
        if  args.trunk is None:
            args.trunk = args.branches[0]
        importTrunk( args.trunk, args.name, args.URL, args.branches[1:], args.tags, args.verbose )
    else:
        parser.print_help()
        print 'Please provide a iocSpec name, or one or more branches to import'
        sys.exit() 

    print "Done."

