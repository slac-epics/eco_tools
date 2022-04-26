#!/usr/bin/env python
'''This script import a PCDS EPICS IOC from svn to a git repo.'''
import sys
import argparse
import os.path
import re
import shutil
import tempfile
import subprocess
from cvs2git_utils import *
from repo_defaults import *

cvs_modules2Location = parseCVSModulesTxt()

def importCVS( gitRepoPath, packageName ):
    '''Import history into a git repo using cvs2git.'''

    tmpPath = tempfile.mkdtemp()
    if 'CVSROOT' not in os.environ:
        os.environ['CVSROOT'] = DEF_CVS_ROOT
    if packageName in cvs_modules2Location:
        packageLocation = os.path.join(os.environ['CVSROOT'], cvs_modules2Location[packageName])
    else:
        packageLocation = os.path.join(os.environ['CVSROOT'], packageName)
    print "Importing CVS package from ", packageLocation
    gitRepoPath = importHistoryFromCVS( tmpPath, gitRepoPath, packageLocation )
    return gitRepoPath

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='''This script creates a git repo for each specified CVS package ....
The trunk and one tags branch are derived from the package name.
Additional paths for both branches and tags may be added if desired either way.
''')
    parser.add_argument( '-f', '--filename', action='store',  help='Filename containing list of CVS packages')
    parser.add_argument( '-c', '--cvsPkg',  action='store',  help='Example: cvsToGit -c tools/edm/display/xray ' )
    parser.add_argument( '-T', '--trunk',    action='store',  help='CVS trunk path  to import. (relative to env CTRL_REPO)', default=None )
    parser.add_argument( '-b', '--branches', action='append', help='CVS branch(es)  to import. (relative to env CTRL_REPO)', default=[] )
    parser.add_argument( '-t', '--tags',     action='append', help='CVS tag paths   to import. (relative to env CTRL_REPO)', default=[] )
    parser.add_argument( '-v', '--verbose',  action="store_true", help='show more verbose output.' )
    parser.add_argument( '-n', '--name',     help='name of git repo.' )
    parser.add_argument( '-U', '--URL',      help='URL of git repo. Def GIT_TOP/slac/PACKAGE.git' )

    args = parser.parse_args( )

    if args.cvsPkg and args.trunk:
        print 'Please specify either a CVS package specification or a trunk path, not both.'    
        sys.exit()

    if args.filename:
        try:
            cvsPkgs = []
            with open( args.filename, "r" ) as f:
                cvsPkgs = f.readlines()
            for cvsPkg in cvsPkgs:
                sys.stdout.flush()
                sys.stderr.flush()
                cvsPkg = cvsPkg.strip(' 	/\n')
                # Skip comments
                if cvsPkg.startswith( '#' ):
                    continue
                gitUrl = os.path.join( gitEpicsRoot, cvsPkg + '.git' )
                if os.path.isdir( gitUrl ):
                    print( "%s: Already imported" % cvsPkg )
                    continue
                importCVS( gitUrl, cvsPkg )
        except Exception as e:
            print( "Error opening %s: %s" % ( args.filename, e ) )
    elif args.cvsPkg:
        gitUrl = args.URL
        # name=args.name, trunk=args.trunk, branches=args.branches, tags=args.tags, gitUrl=args.URL, verbose=args.verbose 
        importCVS( gitUrl, args.cvsPkg )
#	elif args.trunk is not None or len(args.branches) > 0:
#		if not args.name:
#			print 'Please provide a name for git repo'
#			sys.exit()
#		if  args.trunk is None:
#			args.trunk = args.branches[0]
#		importTrunk( args.trunk, args.name, args.URL, args.branches[1:], args.tags, args.verbose )
    else:
        parser.print_help()
        print 'Please provide a cvsPkg name, or one or more branches to import'
        sys.exit() 

    print "Done."

