#!/usr/bin/env python
'''This script import an LCLS module from CVS to a git repo.'''

import argparse
import os.path
import shutil
import tempfile
from git_utils import *

gitDefaultDirFormat = "/afs/slac/g/cd/swe/git/repos/package/{}/from-cvs"

# Dictionary to store the cvs path and git path for each kind of import
# To add a new type add the entry in here with the proper paths and add
# the proper definition of moduleType for the importModule function.
moduleTypePaths = {
    'epics_module': {'cvs': 'epics/site/src', 'git': 'epics/modules'},
    'kernel_module': {'cvs': 'linuxKernel_Modules', 'git': 'linux/drivers/kernel'}
}


def importModule( module, module_type ):
    tp = moduleTypePaths[module_type]

    CVSpackageLocation = os.path.join( os.environ['CVSROOT'], tp['cvs'], module )
    print "Importing CVS module %s from %s" % ( module, CVSpackageLocation )
 
    # Import the CVS history using a tmp folder
    tpath = tempfile.mkdtemp()
    modulesDir = gitDefaultDirFormat.format(tp['git'])
    importHistoryFromCVS(tpath, None, CVSpackageLocation, modulesDir=modulesDir, module=module )
    shutil.rmtree(tpath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='''This script creates a git repo for each specified CVS module....
''')
    parser.add_argument( '-m', '--module', action='append', required=True, help='CVS module name to import.' )
    parser.add_argument( '-k', '--kernel', action='store_true', default=False, required=False, help='Indicates if this is a Kernel Module.' )

    args = parser.parse_args( )

    # TODO: Need to do a better job of handling differences in LCLS vs PCDS env
    if 'TOOLS' not in os.environ:
        if os.path.exists( '/afs/slac/g/lcls/tools' ):
            os.environ['TOOLS'] = '/afs/slac/g/lcls/tools'

    moduleType = 'epics_module'
    if args.kernel:
        moduleType = 'kernel_module'

    for m in args.module:
        importModule( m , moduleType )

    print "Done."

