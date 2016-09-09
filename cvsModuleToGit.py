#!/usr/bin/env python
'''This script import an LCLS EPICS module from CVS to a git repo.'''

import argparse
import os.path
import shutil
import tempfile
from git_utils import *

defaultModulesDir = "/afs/slac/g/cd/swe/git/repos/package/epics/modules/from-cvs"

def importModule( module ):
    CVSpackageLocation = os.path.join( os.environ['CVSROOT'], 'epics/site/src', module )
    print "Importing CVS module %s from %s" % ( module, CVSpackageLocation )
 
    # Import the CVS history using a tmp folder
    tpath = tempfile.mkdtemp()
    importHistoryFromCVS(tpath, None, CVSpackageLocation, modulesDir=defaultModulesDir, module=module )
    shutil.rmtree(tpath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='''This script creates a git repo for each specified CVS module....
''')
    parser.add_argument( '-m', '--module', action='append', required=True, help='CVS module name to import.' )

    args = parser.parse_args( )
    for m in args.module:
        importModule( m )

    print "Done."

