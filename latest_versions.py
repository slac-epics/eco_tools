#!/bin/env python
import argparse
from pprint import *
from repo_defaults import *
from site_utils import *
from version_utils import *


def update_latest( top='.' ):
    pkgDep = getEpicsPkgDependents( top )
    if 'base' not in pkgDep:
        print "Error: unable to determine base version"
        return -1
    epicsSiteTop = determine_epics_site_top()
    epicsModules = os.path.join( epicsSiteTop, pkgDep['base'], 'modules' )
    pkgReleases = {}
    for pkg in pkgDep:
        pkgReleases[pkg] = getPkgReleaseList( epicsModules, pkg )
        print "%s releases: " % pkg
    pprint( pkgReleases )

    #latestVersions = getVersionsFromFile( modulesStableVersionPath )
    updateVersions = {}
    for dep in pkgDep:
        if dep == 'base':
            continue
        #if dep in stableVersions:
        #	updateVersions[dep] = stableVersions[dep]
    for dep in updateVersions:
        print "Need to update %s to %s\n" % ( dep, updateVersions[dep] )

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument( '-L', '--latest', action='store_true', help='Update module dependencies to latest versions.' )
    options = parser.parse_args()


    if options.latest:
        update_latest()
    return 0

if __name__ == '__main__':
    status = main()
    sys.exit(status)
