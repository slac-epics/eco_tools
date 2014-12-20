#!/usr/bin/env python
#==============================================================
#
#  whatsAffected.py:  What are the modules that are affected if we make changes to one module
#
#==============================================================

import os
import os.path
import sys
import re
import subprocess
import argparse

def parseModulesTextFile(modules_txt_path):
    '''Parse the modules.txt file and return a dict mapping the name to the version'''
    moduleName2Version = {}
    with open(modules_txt_path, 'r') as f:
        lines = f.readlines()
    for line in lines:
        li = line.strip()
        if not li:
            continue;
        if li.startswith('#'):
            continue;
        parts = li.split()
        if len(parts) != 2:
            print "Skipping incorrectly formatted line", li
            continue
        moduleName=parts[0]
        moduleVersion=parts[1]
        moduleName2Version[moduleName] = moduleVersion
    return moduleName2Version


def moduleName(path):
    moduleName = os.path.basename(os.path.dirname(path))
    return moduleName

def versionName(path):
    versionName = os.path.basename(path)
    return versionName

def determineModuleDependenciesFromConfigureRelease(path_to_configure_release):
    # Determining the dependencies from the RELEASE file is a little complex as we have two pieces of information
    # We have a version line like so ASYN_MODULE_VERSION=asyn-R4-17-RC1-lcls1
    # and then we have the module line like so ASYN=$(EPICS_MODULES)/asyn/$(ASYN_MODULE_VERSION)
    # Typically, the version line comes before the module line
    # We use the string $(EPICS_MODULES)/ to determine the module name and the appropriate module version variable name ASYN_MODULE_VERSION
    # We use the string _MODULE_VERSION to maintain a dictionary of module name and module version.
    # After processing the complete RELEASE file, we add dependencies in the main dependencies dict
    versionpathswithinmodule = {}
    dependencies = []
    with open(path_to_configure_release, 'r') as releaseFile:
        for line in releaseFile.readlines():
            li = line.strip()
            if (re.match("(.*)(_MODULE_VERSION=)(.*)", li) and not li.startswith("#") and not li.startswith("BASE_MODULE_VERSION")):
                namepathpair = li.split('=')
                versionpathswithinmodule[namepathpair[0]] = namepathpair[1]
        
            if (re.match("(.*)(\$\(EPICS_MODULES\)/)(.*)", li) and not li.startswith("#") and not li.startswith("BASE_MODULE_VERSION")):
                modulepartialpath = li.replace('$(EPICS_MODULES)/', '').split('=')[1]
                # Occasionally, we get absolute paths like ASYN=$(EPICS_MODULES)/asyn/asyn-R4-17-RC1-lcls1
                # These we detect by the absence of the $( string
                if ('$(' in modulepartialpath):
                    modulepartialpathwithvar = modulepartialpath.replace('$(', '').replace(')', '')
                    # modulepartialpathwithvar should look like asyn/ASYN_MODULE_VERSION, event/EVENT_MODULE_VERSION etc
                    modulepathpair = modulepartialpathwithvar.split('/')
                    modulename = modulepathpair[0]
                    moduleversionvar = modulepathpair[1]
                    if(moduleversionvar not in versionpathswithinmodule):
                        raise Exception('Cannot determine value of version variable ' + moduleversionvar + ' when processing RELEASE file for ' + path)
                    moduleversionpath = [modulename, versionpathswithinmodule[moduleversionvar]]
                    # print '\t\tDepends on: ' + moduleversionpath
                    dependencies.append(moduleversionpath)
                else:
                    raise Exception('We cannot handle absolute paths in this utility as we need a way to determine the module name unambigiously')
    return dependencies
    

def assessImpact(modules_txt_path, module_being_changed):
    '''Determine the modules that depend on the module being changed'''
    moduleName2Version = parseModulesTextFile(modules_txt_path)
    module2Dependencies = {}
    for (moduleName, moduleVersion) in moduleName2Version.iteritems():
        path_to_configure_release = os.path.join(moduleName, moduleVersion, 'configure', 'RELEASE')
        dependencies = determineModuleDependenciesFromConfigureRelease(path_to_configure_release)
        module2Dependencies[moduleName] = [x[0] for x in dependencies]
    impacted_modules = [x[0] for x in module2Dependencies.iteritems() if module_being_changed in x[1]]
    if impacted_modules:
        print "The module", module_being_changed, "directly impacts these modules", ", ".join(sorted(impacted_modules))
        # Compute the impact recursively
        visited, stack = set(), [module_being_changed]
        while stack:
            moduleName = stack.pop()
            if moduleName not in visited:
                visited.add(moduleName)
                stack.extend([x[0] for x in module2Dependencies.iteritems() if moduleName in x[1]])
        print "The module", module_being_changed, "recursively impacts these modules", ", ".join(sorted(visited))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='''For the modules specified in the input moduleslist.txt file, determine their dependencies and use this to assess the impact of changing one module to a newer version''')
    parser.add_argument('ecoFileName', action='store', help='The file containing the modules and their versions (the one used by eco), this is typically EPICS_MODULES_TOP/moduleslist.txt')
    parser.add_argument('moduleName', action='store', help='The name (CVS or GIT name) of the module that you want to change')

    args = parser.parse_args() 
    modules_txt_path = os.path.abspath(args.ecoFileName)
    module_being_changed = args.moduleName
    assessImpact(modules_txt_path, module_being_changed)


