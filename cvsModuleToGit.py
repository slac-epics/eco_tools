#!/usr/bin/env python
'''This script import an LCLS module from CVS to a git repo.'''

import argparse
import os.path
import shutil
import tempfile
from cvs_utils import *
from git_utils import *

gitDefaultDirFormat = "/afs/slac/g/cd/swe/git/repos/package/{}/from-cvs"
cvsRoot = "/afs/slac/g/lcls/cvs"
cvs_modules2Location = parseCVSModulesTxt( cvsRoot )
git_modules2Location = parseGitModulesTxt()

# Dictionary to store the cvs path and git path for each kind of import
# To add a new type add the entry in here with the proper paths and add
# the proper definition of moduleType for the importModule function.
moduleTypePaths = {
    'epics_module': {'cvs': 'epics/site/src', 'git': 'epics/modules'},
    'kernel_module': {'cvs': 'linuxKernel_Modules', 'git': 'linux/drivers/kernel'}
}


def importModule( module, module_type, gitFolder=None, repoPath=None ):
    tp = moduleTypePaths[module_type]
    if repoPath is None:
        if module in cvs_modules2Location:
            repoPath = os.path.join( cvsRoot, cvs_modules2Location[module] )
        else:
            repoPath = os.path.join( cvsRoot, tp['cvs'], module )
    if gitFolder is None:
        if module in git_modules2Location:
            gitFolder = git_modules2Location[module]
        else:
            gitFolder = os.path.join( gitDefaultDirFormat.format(tp['git']), module + ".git" )
    if os.path.isdir( gitFolder ):
        print "cvs import of repo already exists:", gitFolder
        return
    print "Importing CVS module %s from %s\n   to %s" % ( module, repoPath, gitFolder )
 
    # Import the CVS history using a tmp folder
    tpath = tempfile.mkdtemp()
    importHistoryFromCVS( tpath, gitFolder, repoPath, module=module )
    shutil.rmtree(tpath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='''This script creates a git repo for each specified CVS module....
''')
    parser.add_argument( '-m', '--module', action='append', required=True, help='Module name to import.' )
    parser.add_argument( '-k', '--kernel', action='store_true', default=False, required=False, help='Indicates if this is a Kernel Module.' )
    parser.add_argument( '--repoPath',  action='store', default=None, help='CVS repo path to import.' )
    parser.add_argument( '--gitFolder', action='store', default=None, help='Folder to create git repo in.' )

    args = parser.parse_args( )

    # TODO: Need to do a better job of handling differences in LCLS vs PCDS env
    if 'TOOLS' not in os.environ:
        if os.path.exists( '/afs/slac/g/lcls/tools' ):
            os.environ['TOOLS'] = '/afs/slac/g/lcls/tools'

    moduleType = 'epics_module'
    if args.kernel:
        moduleType = 'kernel_module'

    for m in args.module:
        importModule( m, moduleType, repoPath=args.repoPath, gitFolder=args.gitFolder )

    print "Done."

