'''This file facilitates translating EPICS package names, typically modules, to
a list of macro names used for that package at SLAC. 1:N
It also translates a macro name to the name of the package it's used for. 1:1
'''
import os
import string
from repo_defaults import *

macroNameToPkgName  = {}
pkgNameToMacroNames = {}

def pkgNameGetMacroNames( pkgName ):
    if pkgName in pkgNameToMacroNames:
        macroNames = pkgNameToMacroNames[ pkgName ]
        if not pkgName.upper() in macroNames:
            macroNames.append( pkgName.upper() )
    else:
        macroNames = [ pkgName.upper() ]
    return macroNames

def pkgNameAddMacroName( pkgName, macroName ):
    if not pkgName in pkgNameToMacroNames:
        pkgNameToMacroNames[pkgName] = [ macroName ]
    else:
        macroNames = pkgNameToMacroNames[pkgName]
        if not macroName in macroNames:
            macroNames.append( macroName )
            pkgNameToMacroNames[pkgName] = macroNames

    if not macroName in macroNameToPkgName:
        macroNameToPkgName[macroName]	= pkgName
    else:
        if macroNameToPkgName[macroName] != pkgName:
            print	"pkgNameAddMacroName Error: Pkg %s Macro %s already mapped to %s" % \
                    ( pkgName, macroName, macroNameToPkgName[macroName] )

if os.path.isdir( DEF_GIT_MODULES_PATH ):
    for d in os.listdir( DEF_GIT_MODULES_PATH ):
        if not '.git' in d:
            continue
        pkgName = string.replace( d, '.git', '' )
        pkgNameAddMacroName( pkgName, pkgName.upper() )

# Add special cases
pkgNameAddMacroName( 'areaDetector',	'AREA_DETECTOR' )
pkgNameAddMacroName( 'base',			'BASE' )
pkgNameAddMacroName( 'Bk9000_MBT',		'BK9000_MBT' )
pkgNameAddMacroName( 'Bx9000_MBT',		'BX9000' )
pkgNameAddMacroName( 'Bx9000_MBT',		'BX9000_MBT' )
pkgNameAddMacroName( 'diagTimer',		'DIAG_TIMER' )
pkgNameAddMacroName( 'etherPSC',		'EPSC' )
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
pkgNameAddMacroName( 'pvaSrv',			'PVASRV' )
pkgNameAddMacroName( 'pvCommonCPP',		'PVCOMMON' )
pkgNameAddMacroName( 'pvDatabaseCPP',	'PVDATABASE' )
pkgNameAddMacroName( 'pvDataCPP',		'PVDATA' )
pkgNameAddMacroName( 'pvIOCCPP',		'PVIOC' )
pkgNameAddMacroName( 'seq',				'SNCSEQ' )
pkgNameAddMacroName( 'sscan',			'SSCAN' )
pkgNameAddMacroName( 'sSubRecord',		'SSUBRECORD' )
pkgNameAddMacroName( 'VHQx0x',			'VHQX0X' )
pkgNameAddMacroName( 'VHSx0x',			'VHSX0X' )
pkgNameAddMacroName( 'vmeCardRecord',	'VME_CARD_RECORD' )

