#!/usr/bin/env python3
'''This script import an LCLS EPICS module from CVS to a git repo.'''

import argparse
import os.path
from cvs_utils import *
from git_utils import *
import cvs2git_utils

cvsRoot = "/afs/slac.stanford.edu/g/spear/cvsrep"

# Dictionary to store the cvs path and git path for each kind of import
# To add a new type add the entry in here with the proper paths and add
# the proper definition of moduleType for the importModuleType function.
moduleTypePaths = {
    'epics_module': {'cvs': 'epics/modules', 'git': 'epics/modules'},
    'kernel_module': {'cvs': 'linuxKernel_Modules', 'git': 'linux/drivers/kernel'},
    'epics_extension': {'cvs': 'epics/extensions/src', 'git': 'epics/extensions'}
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='''This script creates a git repo for each specified CVS module....
''')
    parser.add_argument( '-m', '--module', action='append', required=True, help='Module name to import.' )
    parser.add_argument( '-e', '--extension', action='store_true', default=False, required=False, help='Indicates if this is a EPICS Extension.' )
    parser.add_argument( '--repoPath',  action='store', default=None, help='CVS repo path to import.' )
    parser.add_argument( '--gitFolder', action='store', default=None, help='Folder to create git repo in.' )

    args = parser.parse_args( )

    # TODO: Need to do a better job of handling differences in LCLS vs PCDS env
    if 'TOOLS' not in os.environ:
        if os.path.exists( '/afs/slac.stanford.edu/g/lcls/tools' ):
            os.environ['TOOLS'] = '/afs/slac.stanford.edu/g/lcls/tools'

    moduleType = 'epics_module'
    if args.extension:
        moduleType = 'epics_extension'

    for m in args.module:
        typePaths = moduleTypePaths[moduleType]
        cvs2git_utils.importModuleType( cvsRoot, m, typePaths, repoPath=args.repoPath, gitFolder=args.gitFolder, fromDir='from-spear' )

    print("Done.")

