'''This file facilitates translating EPICS package names, typically modules, to
a list of macro names used for that package at SLAC. 1:N
It also translates a macro name to the name of the package it's used for. 1:1
'''
import os
import string
from repo_defaults import *

_macroNameToPkgName  = {}
_pkgNameToMacroNames = {}

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
            print	"pkgNameAddMacroName Error: Pkg %s Macro %s already mapped to %s" % \
                    ( pkgName, macroName, _macroNameToPkgName[macroName] )

# Automatically populate most of our macro names for packages
# by converting the git directory name to uppercase
if os.path.isdir( DEF_GIT_MODULES_PATH ):
    for d in os.listdir( DEF_GIT_MODULES_PATH ):
        if not '.git' in d:
            continue
        pkgName = string.replace( d, '.git', '' )
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
pkgNameAddMacroName( 'BergozBCM-RF-asyn','BERGOZBCM_RF_ASYN' )
pkgNameAddMacroName( 'Bk9000_MBT',		'BK9000_MBT' )
pkgNameAddMacroName( 'Bx9000_MBT',		'BX9000' )
pkgNameAddMacroName( 'Bx9000_MBT',		'BX9000_MBT' )
pkgNameAddMacroName( 'Bx9000_MBT',		'BX9000MBT' )
pkgNameAddMacroName( 'diagTimer',		'DIAG_TIMER' )
pkgNameAddMacroName( 'etherPSC',		'EPSC' )
pkgNameAddMacroName( 'ethercat',		'ECASYN' )
pkgNameAddMacroName( 'gtr',				'GTR_VERSION' )
pkgNameAddMacroName( 'ip231-asyn',		'IP231_ASYN' )
pkgNameAddMacroName( 'ip330-asyn',		'IP330_ASYN' )
pkgNameAddMacroName( 'ip440',			'XY2440' )
pkgNameAddMacroName( 'ip440-asyn',		'IP440_ASYN' )
pkgNameAddMacroName( 'ip445',			'XY2445' )
pkgNameAddMacroName( 'ip445-asyn',		'IP445_ASYN' )
pkgNameAddMacroName( 'LeCroy_ENET',		'LECROY' )
pkgNameAddMacroName( 'normativeTypesCPP','NORMATIVETYPES' )
pkgNameAddMacroName( 'PSCD_Camac',		'PSCDCAMAC' )
pkgNameAddMacroName( 'pvAccessCPP',		'PVACCESS' )
pkgNameAddMacroName( 'pvAccessCPP',		'pvAccessCPP' )
pkgNameAddMacroName( 'pvaSrv',			'PVASRV' )
pkgNameAddMacroName( 'pvCommonCPP',		'PVCOMMON' )
pkgNameAddMacroName( 'pvCommonCPP',		'pvCommonCPP' )
pkgNameAddMacroName( 'pvDatabaseCPP',	'PVDATABASE' )
pkgNameAddMacroName( 'pvDataCPP',		'PVDATA' )
pkgNameAddMacroName( 'pvDataCPP',		'pvDataCPP' )
pkgNameAddMacroName( 'pvIOCCPP',		'PVIOC' )
pkgNameAddMacroName( 'seq',				'SNCSEQ' )
pkgNameAddMacroName( 'sscan',			'SSCAN' )
pkgNameAddMacroName( 'sSubRecord',		'SSUBRECORD' )
pkgNameAddMacroName( 'timingApi',		'TIMING_API' )
pkgNameAddMacroName( 'VHQx0x',			'VHQX0X' )
pkgNameAddMacroName( 'VHSx0x',			'VHSX0X' )
pkgNameAddMacroName( 'vmeCardRecord',	'VME_CARD_RECORD' )

