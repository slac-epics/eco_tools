'''
Utilities for supporting cram'''

import os
import subprocess
import json
from git_utils     import *
from repo_defaults import *

def createCramPackageInfo(packageName, apptype):
    '''Create .cram/packageinfo'''
    # Add .cram/packageinfo
    packageInfo = {}
    packageInfo['name'] = packageName
    packageInfo['type'] = apptype

    if not os.path.exists('.cram'):
        os.makedirs('.cram', 0775 )
    packageInfofile = os.path.join('.cram', 'packageinfo')
    with open(packageInfofile, 'w') as pkginfof:
        json.dump(packageInfo, pkginfof)

    subprocess.check_call(['git', 'add', '.cram/packageinfo'])
    
def determineCramAppType():
    '''Ask the user the cram type of the package'''
    # Ask the use the package type - Code from cram describe.
    appTypes = {
        'HIOC': 'A hard IOC using a st.cmd',
        'SIOC': 'A soft IOC using a hashbang',
        'HLA': 'A High level application',
        'Tools': 'Scripts typically in the tools/scripts folder',
        'Matlab': 'Matlab applications'
    }
    apptype = subprocess.check_output(['zenity', '--width=600', '--height=400',
                                    '--list',
                                    '--title', "Choose the type of software application",
                                    '--column="Type"', '--column="Description"']
                                    + list(reduce(lambda x, y: x + y, appTypes.items()))
                                    ).strip()
    return apptype

def getCramReleaseDir( url=None, refName=None ):
    packageInfo = None
    packageInfoFile = '.cram/packageinfo'
    if url:
        if not refName:
            print "getCramReleaseDir error: No refName for url", url
            return None
        packageInfoContent = gitGetRemoteFile( url, refName, packageInfoFile )
        if packageInfoContent:
            packageInfo = json.loads( packageInfoContent )
    else:
        if os.path.isfile( packageInfoFile ):
            try:
                with open( packageInfoFile, 'r' ) as pkgInfoFp:
                    packageInfo = json.load( pkgInfoFp )
            except:
                pass
    if not packageInfo:
        return None

    facilityConfigFile = None
    if os.path.isfile( DEF_LCLS_CRAM_USER ):
        facilityConfigFile = DEF_LCLS_CRAM_USER
    elif os.path.isfile( DEF_LCLS_CRAM_CFG ):
        facilityConfigFile = DEF_LCLS_CRAM_CFG
    if not facilityConfigFile:
        return None
    
    facilityConfigDict = None
    try:
        with open( facilityConfigFile, 'r' ) as facilityFp:
            facilityConfig = json.load( facilityFp )
            facilityConfigDict = {}
            for facility in facilityConfig:
                facilityConfigDict[ facility['name'] ] = facility
    except:
        pass
    if not facilityConfigDict:
        return None

    releaseDir = None
    try:
        releaseDir = facilityConfigDict['Dev'][ packageInfo['type'] ]['releaseFolder']
        releaseDir += '/'
        releaseDir += packageInfo['name']
    except:
        pass
    return releaseDir
