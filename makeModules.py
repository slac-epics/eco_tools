#!/usr/bin/env python3
#==============================================================
#
#  makeModules.py:  A tool to automate the builds of modules. 
#  Typically, you'd set up your EPICS environment and run makeModules.py in the EPICS_MODULES_TOP folder
#  makeModules.py walks the directory and for each directory where there is a configure directory, it 
#  1) Determines the dependencies of this module and adds it to a global dependency list.
#      This is done by processing lines containing $(EPICS_MODULES) and _MODULE_VERSION in configure/RELEASE
#  2) Creates the overall build order for all of the modules based on the dependency list.
#  3) Changes into each version of each module folder and runs make.
#  4) Stops the whole build process if there is an error building a single module. 
#
#
#  Name: makeModules.py
#
#  Facility:  SLAC/LCLS
#
#  Auth: 04-Nov-2011, Murali Shankar      (mshankar)
#  Rev:  dd-mmm-yyyy, Reviewer's Name     (USERNAME)
#
#  Requested features to be added:
#--------------------------------------------------------------
#  Mod:
#  04-Nov-2011, Murali Shankar
#    Initial version
#==============================================================

import os
import os.path
import sys
import re
import sets
import subprocess


def moduleName(path):
    moduleName = os.path.basename(os.path.dirname(path))
    return moduleName

def versionName(path):
    versionName = os.path.basename(path)
    return versionName

paths = set([])
dependencies = dict([])

for path, dirnames, filenames in os.walk('.'):
#    print 'ls %r' % path
# We look for folders named configure that have a file named RELEASE
    if ('configure' in dirnames and 'RELEASE' in os.listdir(os.path.join(path, 'configure'))):
        print('Module: ' + repr(moduleName(path)) + ' Version: ' + repr(versionName(path)))
        thismoduleversion = moduleName(path) + '/' + versionName(path)
        paths.add(thismoduleversion)
        dependencies[thismoduleversion] = set([])
# We stop at the highest configure/RELEASE
        del dirnames[:]
# Determining the dependencies from the RELEASE file is a little complex as we have two pieces of information
# We have a version line like so ASYN_MODULE_VERSION=asyn-R4-17-RC1-lcls1
# and then we have the module line like so ASYN=$(EPICS_MODULES)/asyn/$(ASYN_MODULE_VERSION)
# Typically, the version line comes before the module line
# We use the string $(EPICS_MODULES)/ to determine the module name and the appropriate module version variable name ASYN_MODULE_VERSION
# We use the string _MODULE_VERSION to maintain a dictionary of module name and module version.
# After processing the complete RELEASE file, we add dependencies in the main dependencies dict
        versionpathswithinmodule = dict([])
        releaseFile = open(os.path.join(path, 'configure', 'RELEASE'), 'r')
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
                    moduleversionpath = modulename + '/' + versionpathswithinmodule[moduleversionvar]
                    print('\t\tDepends on: ' + moduleversionpath)
                    dependencies[thismoduleversion].add(moduleversionpath)
                else:
# Here we had an absolute path like asyn/asyn-R4-17-RC1-lcls1; so no lookup or processing is needed
                    moduleversionpath = modulepartialpath
                    print('\t\tDepends on: ' + moduleversionpath)
                    dependencies[thismoduleversion].add(moduleversionpath)



# Now paths should have a list of all the directories that we need to run make on and dict should have the dependency list
# Quick assertion - make sure every dependency exists as a path 
for module in dependencies:
    deps = dependencies[module]
    for dep in deps:
        if(dep not in paths):
           raise Exception('Dependency ' + dep + ' from module ' + module + ' is not present in the list of expanded paths')

# If we get this far, things are reasonably consistent with our world.
# We use dependencies to sort paths into a build order
# We use a list 'currentlyworkingon' to address circular dependencies
currentlyworkingon = set([])
buildorder = list([])

def addDependenciesToBuildOrder(module):
    deps = dependencies[module]
    if(len(deps) != 0):
        for dep in deps:
            if(dep not in currentlyworkingon):
                currentlyworkingon.add(dep)
                addDependenciesToBuildOrder(dep)
                currentlyworkingon.remove(dep)
    if(module not in buildorder):
        buildorder.append(module)


for module in paths:
    currentlyworkingon.add(module)
    addDependenciesToBuildOrder(module)
    currentlyworkingon.remove(module)


# Now buildorder should have the build order.
# Quick assertion, make sure every items in paths is in build order
for path in paths:
    if(path not in buildorder):
        raise Exception('Path ' + path + ' is not in the final build order')

# Now we can run make in each of the paths in the sequence identified by the buildorder
for path in buildorder:
    cmd = 'make'
    arguments = sys.argv[1:]
    print()
    print('\033[95mCalling ' + cmd +  ' ' + str(arguments) +' in folder ' + path + '\033[0m')
    print()
    args = [cmd] + arguments
    print(args)
    subprocess.check_call(args, shell=False, cwd=path);

