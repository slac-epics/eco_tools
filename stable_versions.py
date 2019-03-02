import argparse
from repo_defaults import *
from site_utils import *
from version_utils import *

def update_stable( top='.', debug=False ):
    curDep = getEpicsPkgDependents( top, debug=debug )
    if 'base' not in curDep:
        print "Error: unable to determine base version"
        return -1
    epicsSiteTop = determine_epics_site_top()
    modulesStableVersionPath = os.path.join( epicsSiteTop, curDep['base'], 'modules', 'MODULES_STABLE_VERSION' )
    if not os.path.isfile( modulesStableVersionPath ):
        print "Error: unable to find %s" % modulesStableVersionPath 
        return -1

    stableVersions = getVersionsFromFile( modulesStableVersionPath )

    updateVersions = {}
    for dep in curDep:
        if dep == 'base':
            continue
        if dep in stableVersions:
            stableVerPath = os.path.join( epicsSiteTop, curDep['base'], 'modules', dep, stableVersions[dep] )
            stableVerDep  = getEpicsPkgDependents( stableVerPath, debug=debug )
            for sDep in stableVerDep:
                if sDep in stableVersions and stableVerDep[sDep] != stableVersions[sDep]:
                    print "Error: %s depends on %s, but MODULES_STABLE_VERSION has %s" % ( dep, sDep, stableVersions[sDep] )
                    return -1
                updateVersions[sDep] = stableVerDep[sDep]
            updateVersions[dep] = stableVersions[dep]
    for dep in updateVersions:
        print "Need to update %s to %s" % ( dep, updateVersions[dep] )

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument( '-s', '--stable', action='store_true', help='Update module dependencies to latest stable versions.' )
    parser.add_argument( '-d', '--debug', action='store_true', help='Update module dependencies to latest stable versions.' )
    options = parser.parse_args()


    if options.stable:
        update_stable( debug=options.debug )
    return 0

if __name__ == '__main__':
    status = main()
    sys.exit(status)
