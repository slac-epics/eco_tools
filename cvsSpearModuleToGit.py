#!/usr/bin/env python
'''This script import an LCLS EPICS module from CVS to a git repo.'''

import argparse
import os.path
import shutil
import tempfile
from cvs_utils import *
from git_utils import *

defaultModulesDir = "/afs/slac.stanford.edu/g/cd/swe/git/repos/package/epics/modules/from-spear"
cvsRoot = "/afs/slac.stanford.edu/g/spear/cvsrep"
cvs_modules2Location = parseCVSModulesTxt( cvsRoot )
git_modules2Location = parseGitModulesTxt()

def importModule( module, gitFolder=None, repoPath=None ):
    if  repoPath is None:
        if module in cvs_modules2Location:
            repoPath = os.path.join( cvsRoot, cvs_modules2Location[module] )
        else:
            repoPath = os.path.join( cvsRoot, 'epics/modules', module )
    if gitFolder is None:
        if module in git_modules2Location:
            gitFolder = git_modules2Location[module]
        else:
            gitFolder = defaultModulesDir
    print "Importing CVS module %s from %s\n   to %s" % ( module, repoPath, gitFolder )
 
    # Import the CVS history using a tmp folder
    tpath = tempfile.mkdtemp()
    importHistoryFromCVS(tpath, None, repoPath, gitFolder=gitFolder, module=module )
    shutil.rmtree(tpath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='''This script creates a git repo for each specified CVS module....
''')
    parser.add_argument( '-m', '--module', action='append', required=True, help='CVS module name to import.' )
    parser.add_argument( '--repoPath',  action='store', default=None, help='CVS repo path to import.' )
    parser.add_argument( '--gitFolder', action='store', default=None, help='Folder to create git repo in.' )

    args = parser.parse_args( )

    # TODO: Need to do a better job of handling differences in LCLS vs PCDS env
    if 'TOOLS' not in os.environ:
        if os.path.exists( '/afs/slac.stanford.edu/g/lcls/tools' ):
            os.environ['TOOLS'] = '/afs/slac.stanford.edu/g/lcls/tools'

    for m in args.module:
        importModule( m, repoPath=args.repoPath, gitFolder=args.gitFolder )

    print "Done."

