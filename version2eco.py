#!/usr/bin/env python

import os
import sys
from version_utils import *



with open('./MODULES_STABLE_VERSION', 'r') as f:  
    lines = f.readlines()

epics_modules_top = determine_epics_modules_top()
moduleNames = os.listdir( epics_modules_top )
lowercaseModuleName2moduleName = {}

# Preload modules names that do not fit a pattern
lowercaseModuleName2moduleName['epsc'] = 'etherPSC'
lowercaseModuleName2moduleName['vme_card_record'] = 'vmeCardRecord'
lowercaseModuleName2moduleName['ip231_asyn'] = 'ip231-asyn'
lowercaseModuleName2moduleName['ip330_asyn'] = 'ip330-asyn'
lowercaseModuleName2moduleName['ip440_asyn'] = 'ip440-asyn'
lowercaseModuleName2moduleName['ip445_asyn'] = 'ip445-asyn'
lowercaseModuleName2moduleName['pscdcamac'] = 'PSCD_Camac'
lowercaseModuleName2moduleName['lecroy'] = 'LeCroy_ENET'
lowercaseModuleName2moduleName['caenv792'] = 'caenV792-asyn'
lowercaseModuleName2moduleName['area_detector'] = 'areaDetector'
lowercaseModuleName2moduleName['cexp'] = 'cexpsh'
lowercaseModuleName2moduleName['gtr_sis8300'] = 'sis8300'


for name in moduleNames:
    lowercaseModuleName2moduleName[name.lower()] = name

for line in lines:
    if line.startswith('#'):
        continue
    if '=' in line:
        parts = line.split('=')
        lhs=parts[0].replace('_MODULE_VERSION', '').replace('_VERSION', '').lower()
        if lhs not in lowercaseModuleName2moduleName:
            if "MAIN_TRUNK" not in lhs:
                print "Cannot determine module name for ", lhs
                sys.exit(1)
        lhsModuleName = lowercaseModuleName2moduleName[lhs]
        print "{0} {1}".format(lhsModuleName, parts[1].rstrip())


