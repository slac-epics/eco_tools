#!/usr/bin/env python
'''This script generates a eco file for the EPICS shared module tree'''

import argparse
import moduleEcoNames2MakefileNames

def generateEcoFile(fileName):
    completeModules = [x[0] for x in moduleEcoNames2MakefileNames.moduleNames if x[1]]
    maxLengthOfModuleName = max([len(x) for x in completeModules])
    paddedModuleNames = [x.ljust(maxLengthOfModuleName) + " MAIN_TRUNK" for x in completeModules]
    with open(fileName, 'w') as f:
        f.write("\n".join(paddedModuleNames))
        


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='''This script generates a file containing a list of modules and intended for consumption by eco.
For each module defined completely in moduleEcoNames2MakefileNames, we generate a line containing the module's package name (CVS or GIT name) and the string "MAIN_TRUNK".
This script is typically the first step when generating a shared module tree. 
Once we have the modulelist.txt file, we can use eco to check out the modules themselves.''')
    parser.add_argument('ecoFileName', action='store', help='The full path to the file to be used by eco, this is typically EPICS_MODULES_TOP/moduleslist.txt')

    args = parser.parse_args() 
    generateEcoFile(args.ecoFileName)
    print "Done generating a module list file to", args.ecoFileName


