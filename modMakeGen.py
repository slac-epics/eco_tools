#!/usr/bin/env python
'''This script reads in a modulelist.txt file with the versions and then generates a MODULES_STABLE_VERSION'''

import argparse
import os.path
import moduleEcoNames2MakefileNames


def generateModulesStableVersionFile(modules_txt_path, modules_stable_version_path):
    moduleName2moduleMakeName = { x[0] : x[1] for x in moduleEcoNames2MakefileNames.moduleNames if x[1]}
    with open(modules_txt_path, 'r') as f:
        lines = f.readlines()
    with open(modules_stable_version_path, 'w') as g:
        for line in lines:
            li = line.strip()
            if not li:
                continue;
            if li.startswith('#'):
                g.write(li + "\n")
                continue;
            parts = li.split()
            if len(parts) != 2:
                print "Skipping incorrectly formatted line", li
                continue
            moduleName=parts[0]
            moduleVersion=parts[1]
            if moduleName not in moduleName2moduleMakeName:
                print "Cannot find module", moduleName, " defined in ", modules_txt_path, " in the list of standard modules defined in moduleEcoNames2MakefileNames"
                continue
            g.write(moduleName2moduleMakeName[moduleName] + "_MODULE_VERSION=" + moduleVersion + "\n")
            

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='''This script reads in a modulelist.txt file (typically generated with modTreeGen) and generates a MODULES_STABLE_VERSION.
The modulelist.txt file that serves as the input to this script typically contains a line for each module defined completely in moduleEcoNames2MakefileNames.
Each line contains the module's package name (CVS or GIT name) and the appropriate version.
This script is typically the final step when generating a shared module tree. 
The MODULES_STABLE_VERSION is the file that IOC engineers will include in their configure/RELEASE''')
    parser.add_argument('ecoFileName', action='store', help='The full path to the moduleslist.txt that was originally generated by modTreeGen. This is typically EPICS_MODULES_TOP/moduleslist.txt')

    args = parser.parse_args() 
    modules_txt_path = os.path.abspath(args.ecoFileName)
    modules_stable_version_path = os.path.join(os.path.dirname(modules_txt_path), 'MODULES_STABLE_VERSION')
    generateModulesStableVersionFile(modules_txt_path, modules_stable_version_path)
    print "Done generating the MODULES_STABLE_VERSION file to", modules_stable_version_path


