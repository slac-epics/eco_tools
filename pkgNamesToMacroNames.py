'''This file facilitates translating EPICS package names, typically modules, to
a list of macro names used for that package at SLAC. 1:N
It also translates a macro name to the name of the package it's used for. 1:1
'''
import os
import string
from repo_defaults import *

_macroNameToPkgName  = {}
_pkgNameToMacroNames = {}

# These macroNames are never mapped to pkgNames
_macroNameToPkgName[ 'ALARM_CONFIGS_TOP' ] = None
_macroNameToPkgName[ 'BASE_SITE_TOP' ] = None
_macroNameToPkgName[ 'CONFIG' ] = None
_macroNameToPkgName[ 'CONFIG_SITE_TOP' ] = None
_macroNameToPkgName[ 'EPICS_BASE_VER' ] = None
_macroNameToPkgName[ 'EPICS_EXTENSIONS' ] = None
_macroNameToPkgName[ 'EPICS_MODULES' ] = None
_macroNameToPkgName[ 'EPICS_SITE_TOP' ] = None
_macroNameToPkgName[ 'EVR_MODULE' ] = None
_macroNameToPkgName[ 'IOC_SITE_TOP' ] = None
_macroNameToPkgName[ 'LINUX_KERNEL_MODULES' ] = None
_macroNameToPkgName[ 'MAKE_TEST_IOC_APP' ] = None
_macroNameToPkgName[ 'MY_MODULES' ] = None
_macroNameToPkgName[ 'PACKAGE_SITE_TOP' ] = None
_macroNameToPkgName[ 'PSPKG_ROOT' ] = None
_macroNameToPkgName[ 'RULES' ] = None
_macroNameToPkgName[ 'TEMPLATE_TOP' ] = None
_macroNameToPkgName[ 'TOOLS_SITE_TOP' ] = None
_macroNameToPkgName[ 'TOP' ] = None

def macroNameToPkgName( macroName ):
    if macroName in _macroNameToPkgName:
        pkgName = _macroNameToPkgName[ macroName ]
    else:
        pkgName = macroName.lower()
    return pkgName

def pkgNameGetMacroNames( pkgName ):
    if pkgName in _pkgNameToMacroNames:
        macroNames = _pkgNameToMacroNames[ pkgName ]
        if not pkgName.upper() in macroNames:
            macroNames.append( pkgName.upper() )
    else:
        macroNames = [ pkgName.upper() ]
    return macroNames

def pkgNameAddMacroName( pkgName, macroName ):
    if not pkgName in _pkgNameToMacroNames:
        _pkgNameToMacroNames[pkgName] = [ macroName ]
    else:
        macroNames = _pkgNameToMacroNames[pkgName]
        if not macroName in macroNames:
            macroNames.append( macroName )
            _pkgNameToMacroNames[pkgName] = macroNames

    if not macroName in _macroNameToPkgName:
        _macroNameToPkgName[macroName]	= pkgName
    else:
        if _macroNameToPkgName[macroName] != pkgName:
            if _macroNameToPkgName[macroName] is None:
                print("pkgNameAddMacroName Error: Pkg %s Macro %s is not a valid pkgName" % \
                        ( pkgName, macroName ))
            else:
                print("pkgNameAddMacroName Error: Pkg %s Macro %s already mapped to %s" % \
                        ( pkgName, macroName, _macroNameToPkgName[macroName] ))

# Automatically populate most of our macro names for packages
# by converting the git directory name to uppercase
if os.path.isdir( DEF_GIT_MODULES_PATH ):
    for d in os.listdir( DEF_GIT_MODULES_PATH ):
        if not '.git' in d:
            continue
        pkgName = d.replace( '.git', '' )
        pkgNameAddMacroName( pkgName, pkgName.upper() )
else:
    # For systems w/o AFS
    pkgNameAddMacroName( 'ADCore',			'ADCORE' )
    pkgNameAddMacroName( 'ADProsilica',		'ADPROSILICA' )
    pkgNameAddMacroName( 'ADSimDetector',	'ADSIMDETECTOR' )
    pkgNameAddMacroName( 'ADStream',		'ADSTREAM' )
    pkgNameAddMacroName( 'ADSupport',		'ADSUPPORT' )
    pkgNameAddMacroName( 'aravisGigE',		'ARAVISGIGE' )
    pkgNameAddMacroName( 'ffmpegServer',	'FFMPEGSERVER' )
    pkgNameAddMacroName( 'iocAdmin',		'IOCADMIN' )

# Add special cases
pkgNameAddMacroName( 'areaDetector',	'AREA_DETECTOR' )
pkgNameAddMacroName( 'base',			'BASE' )
pkgNameAddMacroName( 'base',			'BASE_MODULE_VERSION' )
pkgNameAddMacroName( 'base',			'EPICS_BASE' )
pkgNameAddMacroName( 'BergozBCM-RF-asyn','BERGOZBCM_RF_ASYN' )
pkgNameAddMacroName( 'Bk9000_MBT',		'BK9000_MBT' )
pkgNameAddMacroName( 'bldClient',		'BLD_CLIENT' )	# TODO: We should flag these non-standard macro names
pkgNameAddMacroName( 'Bx9000_MBT',		'BX9000' )	# TODO: We should flag these non-standard macro names
pkgNameAddMacroName( 'Bx9000_MBT',		'BX9000_MBT' )
pkgNameAddMacroName( 'Bx9000_MBT',		'BX9000MBT' )	# TODO: We should flag these non-standard macro names
pkgNameAddMacroName( 'Camcom',			'CAMCOM' )
pkgNameAddMacroName( 'caSnooper',		'CASNOOPER' )
pkgNameAddMacroName( 'cexpsh',			'CEXP' )
pkgNameAddMacroName( 'ChannelWatcher',	'CHANNELWATCHER' )
pkgNameAddMacroName( 'diagTimer',		'DIAG_TIMER' )
pkgNameAddMacroName( 'etherPSC',		'EPSC' )
pkgNameAddMacroName( 'ethercat',		'ECASYN' )
pkgNameAddMacroName( 'fwdCliS',			'FWDCLIS' )
pkgNameAddMacroName( 'gtr',				'GTR_VERSION' )
pkgNameAddMacroName( 'ip231-asyn',		'IP231_ASYN' )
pkgNameAddMacroName( 'ip330-asyn',		'IP330_ASYN' )
pkgNameAddMacroName( 'ip440',			'XY2440' )
pkgNameAddMacroName( 'ip440-asyn',		'IP440_ASYN' )
pkgNameAddMacroName( 'ip445',			'XY2445' )
pkgNameAddMacroName( 'ip445-asyn',		'IP445_ASYN' )
pkgNameAddMacroName( 'LeCroy_ENET',		'LECROY' )
pkgNameAddMacroName( 'normativeTypesCPP','NORMATIVE' )	# TODO: We should flag these non-standard macro names
pkgNameAddMacroName( 'normativeTypesCPP','NORMATIVETYPES' )	# TODO: We should flag these non-standard macro names
pkgNameAddMacroName( 'procServ',		'PROCSERV' )
pkgNameAddMacroName( 'PSCD_Camac',		'PSCDCAMAC' )
pkgNameAddMacroName( 'pvAccessCPP',		'PVACCESS' )	# TODO: We should flag these non-standard macro names
pkgNameAddMacroName( 'pvAccessCPP',		'pvAccessCPP' )	# TODO: We should flag these non-standard macro names
pkgNameAddMacroName( 'pvaClientCPP',	'PVACLIENT' )	# TODO: We should flag these non-standard macro names
pkgNameAddMacroName( 'pvaSrv',			'PVASRV' )
pkgNameAddMacroName( 'pvCommonCPP',		'PVCOMMONCPP' )
pkgNameAddMacroName( 'pvCommonCPP',		'PVCOMMON' )	# TODO: We should flag these non-standard macro names
pkgNameAddMacroName( 'pvCommonCPP',		'pvCommonCPP' )	# TODO: We should flag these non-standard macro names
pkgNameAddMacroName( 'pvDatabaseCPP',	'PVDATABASECPP' )
pkgNameAddMacroName( 'pvDatabaseCPP',	'PVDATABASE' )	# TODO: We should flag these non-standard macro names
pkgNameAddMacroName( 'pvDataCPP',		'PVDATACPP' )
pkgNameAddMacroName( 'pvDataCPP',		'PVDATA' )	# TODO: We should flag these non-standard macro names
pkgNameAddMacroName( 'pvDataCPP',		'pvDataCPP' )	# TODO: We should flag these non-standard macro names
pkgNameAddMacroName( 'pvIOCCPP',		'PVIOC' )
pkgNameAddMacroName( 'seq',				'SNCSEQ' )
pkgNameAddMacroName( 'sscan',			'SSCAN' )
pkgNameAddMacroName( 'sSubRecord',		'SSUBRECORD' )
pkgNameAddMacroName( 'streamdevice',	'STREAMDEVICE' )
pkgNameAddMacroName( 'streamdevice',	'STREAM' )	# TODO: We should flag these non-standard macro names
pkgNameAddMacroName( 'StripTool',		'STRIPTOOL' )
pkgNameAddMacroName( 'timingApi',		'TIMING_API' )
pkgNameAddMacroName( 'VHQx0x',			'VHQX0X' )
pkgNameAddMacroName( 'VHSx0x',			'VHSX0X' )
pkgNameAddMacroName( 'VisualDCT',		'VISUALDCT' )
pkgNameAddMacroName( 'vmeCardRecord',	'VME_CARD_RECORD' )

