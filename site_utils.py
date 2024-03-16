#!/usr/bin/env python3

import os
from repo_defaults import *
from version_utils import *

#
# Purpose:
#
#   Site specific Utilities for determining EPICS release paths
#
# Copyright 2018 Stanford University
# Author: Bruce Hill <bhill@slac.stanford.edu>
#
# Released under the GPLv2 licence <http://www.gnu.org/licenses/gpl-2.0.html>
#

def isPCDSPath(path):
    '''isPCDSPackage does a couple of simple path.startswith string comparisons
    More tests can be added if needed.'''
    if path.startswith( DEF_EPICS_TOP_PCDS ):
        return True
    if path.startswith( DEF_EPICS_TOP_PCDS_OLD ):
        return True
    if path.startswith( '/afs/slac/g/pcds' ): # /afs/slac symbolic link might be part of pcds pathnames
        return True
    if path.startswith( DEF_EPICS_TOP_AFS ):
        return True
    return False

def getEnv( envVar ):
    result = os.getenv( envVar )
    if not result:
        result = '?'
    return result

def determine_epics_site_top():
    '''Returns string w/ a directory name for EPICS site top, or None if unable to derive.'''
    # First look for EPICS_TOP in the environment
    epics_site_top = getEnv('EPICS_TOP')
    # Then EPICS_SITE_TOP
    if epics_site_top == '?':
        epics_site_top = getEnv('EPICS_SITE_TOP')
    if epics_site_top == '?':
        # If we have EPICS_BASE, work back from there
        epics_base = getEnv('EPICS_BASE')
        if epics_base != '?':
            epics_base_top = os.path.dirname( epics_base )
            epics_site_top = os.path.dirname( epics_base_top )
            if epics_base.startswith( 'base-' ):
                epics_ver = epics_base.replace( 'base-', '' )
                epics_site_top = os.path.join( epics_site_top, epics_ver )
            if epics_base.startswith( 'R3.14.12-' ):
                epics_site_top = os.path.join( epics_site_top, '3.14' )
    if epics_site_top == '?':
        if os.path.isdir(    DEF_EPICS_TOP_PCDS ):
            epics_site_top = DEF_EPICS_TOP_PCDS 
        elif os.path.isdir(  DEF_EPICS_TOP_PCDS_OLD ):
            epics_site_top = DEF_EPICS_TOP_PCDS_OLD
        elif os.path.isdir(  DEF_EPICS_TOP_LCLS ):
            epics_site_top = DEF_EPICS_TOP_LCLS
        elif os.path.isdir(  DEF_EPICS_TOP_AFS ):
            epics_site_top = DEF_EPICS_TOP_AFS
    if  epics_site_top == '?':
        epics_site_top = None
    return epics_site_top

def determine_epics_modules_top():
    # First look for EPICS_MODULES_TOP in the environment
    epics_modules_top = getEnv('EPICS_MODULES_TOP')
    if epics_modules_top == '?':
        epics_base_ver = determine_epics_base_ver()
        epics_site_top = determine_epics_site_top()
        if not epics_base_ver or not epics_site_top:
            print("determine_epics_modules_top Error: Unable to determine EPICS_MODULES_TOP!")
            return None
        if epics_base_ver.startswith( 'base-' ):
            epics_base_ver = epics_base_ver.replace( 'base-', '' )
        if VersionToRelNumber(epics_base_ver) > 3.1412:
            epics_modules_top = os.path.join( epics_site_top, epics_base_ver, 'modules'	)
        else:
            epics_modules_top = os.path.join( epics_site_top, 'modules', 'R3-14-12' )
        if not os.path.isdir( epics_modules_top ):
            print("determine_epics_modules_top Error: %s is not a directory!" % epics_modules_top)
            epics_modules_top = None
    return epics_modules_top

def determine_epics_host_arch():
    '''Returns string w/ EPICS host arch, or None if unable to derive.'''
    # First look for EPICS_HOST_ARCH in the environment
    epics_host_arch = os.getenv('EPICS_HOST_ARCH')
    if not epics_host_arch:
        epics_site_top = determine_epics_site_top()
        epics_base_ver = determine_epics_base_ver()
        if epics_site_top is not None and epics_base_ver is not None:
            epicsHostArchPath	= os.path.join(	epics_site_top, 'base',
                                                epics_base_ver, 'startup', 'EpicsHostArch' )
            if os.path.isfile( epicsHostArchPath ):
                cmdOutput = subprocess.check_output( [ epicsHostArchPath ] ).splitlines()
                if len(cmdOutput) == 1:
                    epics_host_arch = str(cmdOutput[0])

    # Returns None if unable to derive
    return epics_host_arch

def export_release_site_file( inputs, debug=False):
    """
    Use the contents of a dictionary of top level dirs to create a 
    RELEASE_SITE dir in a specified dir
    """

    #out_file = sys.stdout for testing 

    output_file_and_path = './RELEASE_SITE'
    try:
        out_file = open(output_file_and_path, 'w')
    except IOError as e:
        sys.stderr.write('Could not open "%s": %s\n' % (output_file_and_path, e.strerror))
        return None

    print('#==============================================================================', file=out_file)
    if VersionToRelNumber(inputs['EPICS_BASE_VER'], debug=debug) < 3.141205:
        print('#RELEASE Location of external products', file=out_file)
    else:
        print('# RELEASE_SITE Location of EPICS_SITE_TOP, EPICS_MODULES, and BASE_MODULE_VERSION', file=out_file)
    print('# Run "gnumake clean uninstall install" in the application', file=out_file)
    print('# top directory each time this file is changed.', file=out_file)
    print('', file=out_file)
    print('#==============================================================================', file=out_file)
    if VersionToRelNumber(inputs['EPICS_BASE_VER'], debug=debug) < 3.141205:
        print('# Define the top of the EPICS tree for your site.', file=out_file)
        print('# We will build some tools/scripts that allow us to', file=out_file)
        print('# change this easily when relocating software.', file=out_file)
        print('#==============================================================================', file=out_file)
        if doesPkgNeedMacro( 'BASE_MODULE_VERSION' ):
            print('BASE_MODULE_VERSION=%s'%inputs['EPICS_BASE_VER'], file=out_file)
    else:
        print('BASE_MODULE_VERSION=%s'%inputs['EPICS_BASE_VER'], file=out_file)
    print('EPICS_SITE_TOP=%s'    % inputs['EPICS_SITE_TOP'], file=out_file) 
    if 'BASE_SITE_TOP' in inputs:
        print('BASE_SITE_TOP=%s'     % inputs['BASE_SITE_TOP'], file=out_file)
    if VersionToRelNumber(inputs['EPICS_BASE_VER'], debug=debug) < 3.141205 \
        or doesPkgNeedMacro( 'MODULES_SITE_TOP' ):
        print('MODULES_SITE_TOP=%s'  % inputs['EPICS_MODULES'], file=out_file)
    if VersionToRelNumber(inputs['EPICS_BASE_VER'], debug=debug) >= 3.141205 \
        or doesPkgNeedMacro( 'EPICS_MODULES' ):
        print('EPICS_MODULES=%s'     % inputs['EPICS_MODULES'], file=out_file)
    if 'IOC_SITE_TOP' in inputs:
        print('IOC_SITE_TOP=%s'      % inputs['IOC_SITE_TOP'], file=out_file)
    if VersionToRelNumber(inputs['EPICS_BASE_VER'], debug=debug) < 3.141205 \
        or doesPkgNeedMacro( 'EPICS_BASE_VER' ):
        print('EPICS_BASE_VER=%s' %inputs['EPICS_BASE_VER'], file=out_file)
    print('PACKAGE_SITE_TOP=%s'  % inputs['PACKAGE_SITE_TOP'], file=out_file)
    if 'MATLAB_PACKAGE_TOP' in inputs:
        print('MATLAB_PACKAGE_TOP=%s'        % inputs['MATLAB_PACKAGE_TOP'], file=out_file)
    if 'PSPKG_ROOT' in inputs:
        print('PSPKG_ROOT=%s'        % inputs['PSPKG_ROOT'], file=out_file)
    if 'TOOLS_SITE_TOP' in inputs:
        print('TOOLS_SITE_TOP=%s'    % inputs['TOOLS_SITE_TOP'], file=out_file)
    if 'ALARM_CONFIGS_TOP' in inputs:
        print('ALARM_CONFIGS_TOP=%s' % inputs['ALARM_CONFIGS_TOP'], file=out_file)
    print('#==============================================================================', file=out_file)
    if out_file != sys.stdout:
        out_file.close()

def assemble_release_site_inputs( batch=False ):

    input_dict = {}

    epics_base_ver = determine_epics_base_ver()
    epics_site_top = determine_epics_site_top()

    if epics_base_ver is None:
        # base_versions = get_base_versions( epics_site_top )
        print('TODO: Provide list of available epics_base_ver options to choose from')
        epics_base_ver = 'unknown-base-ver'
    input_dict['EPICS_BASE_VER'] = epics_base_ver
    if not batch:
        prompt5 = 'Enter EPICS_BASE_VER or [RETURN] to use "' + epics_base_ver + '">'
        user_input = input(prompt5).strip()
        if user_input:
            input_dict['EPICS_BASE_VER'] = user_input
    print('Using EPICS_BASE_VER: ' + input_dict['EPICS_BASE_VER'])

    # TODO: Substitute input_dict['EPICS_BASE_VER'] for any substrings below that match
    # the default epics_base_ver we got from the environment before prompting the user.
    # That way users can easily change the base version in one place

    if not epics_site_top:
        epics_site_top = 'unknown-epics-site-top'
    input_dict['EPICS_SITE_TOP'] = epics_site_top
    if not batch:
        prompt1 = 'Enter full path for EPICS_SITE_TOP or [RETURN] to use "' + epics_site_top + '">'
        user_input = input(prompt1).strip()
        if user_input:
            input_dict['EPICS_SITE_TOP'] = user_input
    print('Using EPICS_SITE_TOP: ' + input_dict['EPICS_SITE_TOP'])

    input_dict['BASE_SITE_TOP'] = os.path.join( input_dict['EPICS_SITE_TOP'], 'base' )
    print('Using BASE_SITE_TOP: ' + input_dict['BASE_SITE_TOP'])

    epics_modules_ver = input_dict['EPICS_BASE_VER']
    if epics_modules_ver.startswith( 'base-' ):
        epics_modules_ver = epics_modules_ver.replace( 'base-', '' )

    epics_modules = getEnv('EPICS_MODULES_TOP')
    if os.path.isdir( epics_modules ):
        input_dict['EPICS_MODULES'] = epics_modules
    else:
        epics_modules = os.path.join( input_dict['EPICS_SITE_TOP'], epics_modules_ver, 'modules' )
        if not os.path.isdir( epics_modules ):
            epics_modules = os.path.join( epics_site_top, 'modules' )
        input_dict['EPICS_MODULES'] = epics_modules
    if not batch:
        prompt5 = 'Enter full path for EPICS_MODULES or [RETURN] to use "' + input_dict['EPICS_MODULES'] + '">'
        user_input = input(prompt5).strip()
        if user_input:
            input_dict['EPICS_MODULES'] = user_input
    print('Using EPICS_MODULES: ' + input_dict['EPICS_MODULES'])

    ioc_site_top = os.path.join( input_dict['EPICS_SITE_TOP'], 'iocTop' )
    if os.path.isdir( ioc_site_top ):
        input_dict['IOC_SITE_TOP'] = ioc_site_top
        print('Using IOC_SITE_TOP: ' + input_dict['IOC_SITE_TOP'])

    package_site_top = getEnv('PACKAGE_TOP')
    if not os.path.isdir( package_site_top ):
        package_site_top = getEnv('PACKAGE_SITE_TOP')
    if not os.path.isdir( package_site_top ):
        package_site_top = '/cds/group/pcds/package'
    if not os.path.isdir( package_site_top ):
        package_site_top = '/afs/slac.stanford.edu/g/lcls/package'
    if not os.path.isdir( package_site_top ):
        package_site_top = '/afs/slac.stanford.edu/g/pcds/package'
    input_dict['PACKAGE_SITE_TOP'] = package_site_top
    if not batch:
        prompt6 = 'Enter full path for PACKAGE_SITE_TOP or [RETURN] to use "' + package_site_top + '">'
        user_input = input(prompt6).strip()
        if user_input:
            input_dict['PACKAGE_SITE_TOP'] = user_input
    print('Using PACKAGE_SITE_TOP: ' + input_dict['PACKAGE_SITE_TOP'])

    matlab_package_top = getEnv('MATLAB_PACKAGE_TOP')
    if not os.path.isdir( matlab_package_top ):
        matlab_root = getEnv('MATLAB_ROOT')
        if os.path.isdir( matlab_root ):
            matlab_package_top = os.path.split(matlab_root)[0]
    if not os.path.isdir( matlab_package_top ):
        matlab_package_top = '/usr/local/matlab'
    if not os.path.isdir( matlab_package_top ):
        matlab_package_top = '/reg/common/package/matlab'
    if not os.path.isdir( matlab_package_top ):
        matlab_package_top = '/afs/slac.stanford.edu/g/lcls/package/matlab'
    print('Using MATLAB_PACKAGE_TOP:', matlab_package_top)
    input_dict['MATLAB_PACKAGE_TOP'] = matlab_package_top

    if VersionToRelNumber(input_dict['EPICS_BASE_VER']) >= 3.141205:
        pspkg_root = getEnv('PSPKG_ROOT')
        if not os.path.isdir( pspkg_root ):
            pspkg_root = '/cds/group/pcds/pkg_mgr'
        if not os.path.isdir( pspkg_root ):
            pspkg_root = '/afs/slac.stanford.edu/g/lcls/pkg_mgr'
        if not os.path.isdir( pspkg_root ):
            pspkg_root = '/afs/slac.stanford.edu/g/pcds/pkg_mgr'
        print('Using PSPKG_ROOT:', pspkg_root)
        input_dict['PSPKG_ROOT'] = pspkg_root

    input_dict['TOOLS_SITE_TOP'] = ''
    input_dict['ALARM_CONFIGS_TOP'] = ''
    tools_site_top = getEnv('TOOLS')
    if os.path.isdir(tools_site_top):
        input_dict['TOOLS_SITE_TOP'] = tools_site_top
        if not batch:
            prompt6 = 'Enter full path for TOOLS_SITE_TOP or [RETURN] to use "' + tools_site_top + '">'
            user_input = input(prompt6).strip()
            if user_input:
                input_dict['TOOLS_SITE_TOP'] = user_input
        if os.path.isdir( input_dict['TOOLS_SITE_TOP'] ):
            print('Using TOOLS_SITE_TOP: ' + input_dict['TOOLS_SITE_TOP'])

            alarm_configs_top = os.path.join( input_dict['TOOLS_SITE_TOP'], 'AlarmConfigsTop' )
            input_dict['ALARM_CONFIGS_TOP'] = alarm_configs_top
            if not batch:
                prompt6 = 'Enter full path for ALARM_CONFIGS_TOP or [RETURN] to use "' + alarm_configs_top + '">'
                user_input = input(prompt6).strip()
                if user_input:
                    input_dict['ALARM_CONFIGS_TOP'] = user_input
            if os.path.isdir( input_dict['ALARM_CONFIGS_TOP'] ):
                print('Using ALARM_CONFIGS_TOP: ' + input_dict['ALARM_CONFIGS_TOP'])

    return input_dict
