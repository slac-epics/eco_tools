#!/usr/bin/env python
#==============================================================
#
#  Abs:  A tool to checkout an EPICS package
#  Creates a configure/RELEASE.local file if not found to support local builds
#
#  configure/RELEASE.local needs to be included from configure/RELEASE if not already
#  there as it is in many of the new modules versions from the EPICS collaboration.
#
#  Also creates a RELEASE_SITE file if needed based on an eco_tools template.
#  RELEASE_SITE is read by configure/RELEASE.local to define EPICS_BASE and EPICS_MODULES
#  with the aim that no changes to configure/RELEASE are needed.
#  Two possible locations for RELEASE_SITE are supported:
#   Module's will use $TOP/../../RELEASE_SITE if found.  This is the pattern for
#       our module releases, where $TOP/../.. is the same as the $EPICS_MODULES directory.
#       Thus all module releases under $EPICS_SITE_TOP/R3.15.0-0.1.0/modules would
#       share the same RELEASE_SITE defining BASE_MODULE_VERSION as R3.15.0-0.1.0
#
#   IOC's will typically add a RELEASE_SITE in $TOP so they can select which version
#       of base to use.  These IOC RELEASE_SITE files should be added to the repo
#       so they will get tagged w/ the release tag.
#
#   Module developers can also use a $TOP/RELEASE_SITE for standalone module development
#   but should not add it to the repo so the module can be built against different
#   versions of BASE.
#
#  Name: epics-checkout.py
#
#  Facility:  SLAC/LCLS/PCDS
#
#  Auth: 29-Nov-2010, Dayle Kotturi       (dayle)
#  Auth: 04-Nov-2011, Murali Shankar      (mshankar)
#  Auth: 10-Oct-2016, Bruce Hill          (bhill)
#  Rev:  dd-mmm-yyyy, Reviewer's Name     (USERNAME)
#
#  Requested features to be added:
#   - Add setting of directory permissions per new acl list changes; 
#     i.e. set a flag to lock them
#   - Only put IOC_SITE_TOP in RELEASE_SITE if actually needed, not just
#     generically
#   - Make use of "cvs rlog" command to show user all the possible tags
#   - Make it runnable with command line args or a file instead of terminal 
#     input; this includes making it checkout multiple packages at a time
#   - Break it into two scripts: one just to create the RELEASE_SITE file 
#     so that it could be used when checkout has already been done
#   - Make it work for subversion
#   - Make it go and change the $IOC/*/startup.cmd files to new release 
#       for all/subset of iocs in checked out app?s iocBoot
#
#--------------------------------------------------------------
#  For file history, please use the git log
#  Mod:
#  09-Dec-2010, Dayle Kotturi
#    Bring in defaults for each setting from the environmens
#  14-Dec-2010, Dayle Kotturi
#    Add EPICS_BASE_VER to entries in RELEASE_SITE; 
#    Use env var by same name as default 
#    If the HEAD is checked out, name the directory MAIN_TRUNK
#  15-Dec-2010, Dayle Kotturi
#    Add this header of comments
#    Add WWW_DIR to entries in RELEASE_SITE;
#    Use /afs/slac/www/grp/lcls as the default for WWW_DIR 
#    Change default for WWW_DIR to env var LCLS_WWW
#    Add capability to accept a file of 'package tag' pairs, 
#    one per line to do checkout with default env vars
#  04-Nov-2011 Murali Shankar
#    Removed all references to LCLS_WWW or WWW per Ernest
#  06-Dec-2011 Murali Shankar
#    Restored this version from CVS. Ernest wants me to update instead.
#  23-Feb-2012 Murali Shankar
#    Removed leading and trailing whitespace from inputs per Suzie and Ernest's request
#  04-June-2012 Murali Shankar
#    Updated the help per Ernest
#  04-June-2012 Murali Shankar
#    Added support for the -m modulename argument per Ernest
#  25-Sept-2012 Murali Shankar
#    Added a -P argument to cvs checkout per Ernest
#  13-Aug-2013 Murali Shankar
#    Support for PACKAGE_SITE_TOP; default value for this comes from PACKAGE_TOP per Ernest/Sonya
#  10-Oct-2013 Murali Shankar
#    Added support for BUILD_TARGETS using CROSS_COMPILER_TARGET_ARCHS in ${EPICS_BASE_RELEASE}/config/CONFIG_SITE and ${EPICS_BASE_RELEASE}/bin
#  12-Dec-2013 Murali Shankar
#    Pulled support for BUILD_TARGETS per Ernest as this generates fake conflicts with base's checkRelease
#  08-Jan-2014 Murali Shankar
#    Added support for specifying destination folder when using eco in interactive mode.
#  11-Feb-2014 Murali Shankar
#    Bug fix for specifying destination folder when using eco - the final cd was not using the correct variable - hence exception.
#  26-Aug-2014 Murali Shankar
#    Added support for TOOLS_SITE_TOP and ALARM_CONFIGS_TOP for Kristi
#  28-Jul-2015 Murali Shankar
#    Added a validation method to make sure folks have their enviroment variables set correctly.
#==============================================================
import sys
import os
import socket
import subprocess
import optparse
import readline
import shutil
import tempfile
import json

from cram_utils import *
from git_utils import *
from version_utils import *


GIT_REPO_MODULES = '/afs/slac/g/cd/swe/git/repos/package/epics/modules'

__all__ = ['export_release_site_file', 'assemble_release_site_inputs','assemble_cvs_inputs_from_file', 'assemble_cvs_inputs_from_term']

def parseGitModulesTxt():
    '''Parse the GIT modules txt file and return a dict of packageName -> location'''
    package2Location = {}
    gitModulesTxtFile = os.path.join(os.environ['TOOLS'], 'eco_modulelist', 'modulelist.txt')
    with open(gitModulesTxtFile, 'r') as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        parts = line.split()
        if(len(parts) < 2):
            print "Error parsing ", gitModulesTxtFile, "Cannot break", line, "into columns with enough fields using spaces/tabs"
            continue
        packageName = parts[0]
        packageLocation = parts[1]
        package2Location[packageName] = packageLocation
    return package2Location
        
def parseCVSModulesTxt():
    '''Parse the CVS modules file and return a dict of packageName -> location'''
    package2Location = {}
    cvsModulesTxtFile = os.path.join(os.environ['CVSROOT'], 'CVSROOT', 'modules')
    if not os.path.exists(cvsModulesTxtFile):
        print "Cannot determine CVS modules from modules file."
        return package2Location
    
    with open(cvsModulesTxtFile, 'r') as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        parts = line.split()
        if(len(parts) < 2):
            print "Error parsing ", cvsModulesTxtFile, "Cannot break", line, "into columns with enough fields using spaces/tabs"
            continue
        packageName = parts[0]
        packageLocation = parts[1]
        package2Location[packageName] = packageLocation
    return package2Location
        



git_package2Location = parseGitModulesTxt()
cvs_modules2Location = parseCVSModulesTxt()

def export_release_site_file( inputs, debug=False):
    """
    Use the contents of a dictionary of top level dirs to create a 
    RELEASE_SITE dir in a specified dir
    """

    #out_file = sys.stdout for testing 

    output_file_and_path = './RELEASE_SITE'
    try:
        out_file = open(output_file_and_path, 'w')
    except IOError, e:
        sys.stderr.write('Could not open "%s": %s\n' % (output_file_and_path, e.strerror))
        return None

    print >> out_file, '#=============================================================================='
    print >> out_file, '# RELEASE_SITE Location of EPICS_SITE_TOP, EPICS_MODULES, and BASE_MODULE_VERSION'
    print >> out_file, '# Run "gnumake clean uninstall install" in the application'
    print >> out_file, '# top directory each time this file is changed.'
    print >> out_file, '#=============================================================================='
    print >> out_file, 'BASE_MODULE_VERSION=%s'%inputs['EPICS_BASE_VER']
    print >> out_file, 'EPICS_SITE_TOP=%s'    % inputs['EPICS_SITE_TOP'] 
    if 'BASE_SITE_TOP' in inputs:
        print >> out_file, 'BASE_SITE_TOP=%s'     % inputs['BASE_SITE_TOP']
    if VersionToRelNumber(inputs['EPICS_BASE_VER'], debug=debug) < 3.141205:
        print >> out_file, 'MODULES_SITE_TOP=%s'  % inputs['EPICS_MODULES']
    print >> out_file, 'EPICS_MODULES=%s'     % inputs['EPICS_MODULES']
    if 'IOC_SITE_TOP' in inputs:
        print >> out_file, 'IOC_SITE_TOP=%s'      % inputs['IOC_SITE_TOP']
    if VersionToRelNumber(inputs['EPICS_BASE_VER'], debug=debug) < 3.141205:
        print >> out_file, 'EPICS_BASE_VER=%s' %inputs['EPICS_BASE_VER']
    print >> out_file, 'PACKAGE_SITE_TOP=%s'  % inputs['PACKAGE_SITE_TOP']
    if 'PSPKG_ROOT' in inputs:
        print >> out_file, 'PSPKG_ROOT=%s'        % inputs['PSPKG_ROOT']
    if 'TOOLS_SITE_TOP' in inputs:
        print >> out_file, 'TOOLS_SITE_TOP=%s'    % inputs['TOOLS_SITE_TOP']
    if 'ALARM_CONFIGS_TOP' in inputs:
        print >> out_file, 'ALARM_CONFIGS_TOP=%s' % inputs['ALARM_CONFIGS_TOP']
    print >> out_file, '#=============================================================================='
    if out_file != sys.stdout:
        out_file.close()

    # change back to level where repo is
    os.chdir('../..')

def assemble_release_site_inputs( batch=False ):

    input_dict = {}

    epics_base_ver = determine_epics_base_ver()
    epics_site_top = determine_epics_site_top()

    if not epics_base_ver:
        # base_versions = get_base_versions( epics_site_top )
        print 'TODO: Provide list of available epics_base_ver options to choose from'
        epics_base_ver = 'unknown-base-ver'
    input_dict['EPICS_BASE_VER'] = epics_base_ver
    if not batch:
        prompt5 = 'Enter EPICS_BASE_VER or [RETURN] to use "' + epics_base_ver + '">'
        user_input = raw_input(prompt5).strip()
        if user_input:
            input_dict['EPICS_BASE_VER'] = user_input
    print 'Using EPICS_BASE_VER: ' + input_dict['EPICS_BASE_VER']

    # TODO: Substitute input_dict['EPICS_BASE_VER'] for any substrings below that match
    # the default epics_base_ver we got from the environment before prompting the user.
    # That way users can easily change the base version in one place

    input_dict['EPICS_SITE_TOP'] = epics_site_top
    if not batch:
        prompt1 = 'Enter full path for EPICS_SITE_TOP or [RETURN] to use "' + epics_site_top + '">'
        user_input = raw_input(prompt1).strip()
        if user_input:
            input_dict['EPICS_SITE_TOP'] = user_input
    print 'Using EPICS_SITE_TOP: ' + input_dict['EPICS_SITE_TOP']

    input_dict['BASE_SITE_TOP'] = os.path.join( input_dict['EPICS_SITE_TOP'], 'base' )
    print 'Using BASE_SITE_TOP: ' + input_dict['BASE_SITE_TOP']

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
        user_input = raw_input(prompt5).strip()
        if user_input:
            input_dict['EPICS_MODULES'] = user_input
    print 'Using EPICS_MODULES: ' + input_dict['EPICS_MODULES']

    ioc_site_top = os.path.join( input_dict['EPICS_SITE_TOP'], 'iocTop' )
    if os.path.isdir( ioc_site_top ):
        input_dict['IOC_SITE_TOP'] = ioc_site_top
        print 'Using IOC_SITE_TOP: ' + input_dict['IOC_SITE_TOP']

    package_site_top = getEnv('PACKAGE_TOP')
    if not os.path.isdir( package_site_top ):
        package_site_top = getEnv('PACKAGE_SITE_TOP')
    if not os.path.isdir( package_site_top ):
        package_site_top = '/reg/g/pcds/package'
    if not os.path.isdir( package_site_top ):
        package_site_top = '/afs/slac/g/lcls/package'
    if not os.path.isdir( package_site_top ):
        package_site_top = '/afs/slac/g/pcds/package'
    input_dict['PACKAGE_SITE_TOP'] = package_site_top
    if not batch:
        prompt6 = 'Enter full path for PACKAGE_SITE_TOP or [RETURN] to use "' + package_site_top + '">'
        user_input = raw_input(prompt6).strip()
        if user_input:
            input_dict['PACKAGE_SITE_TOP'] = user_input
    print 'Using PACKAGE_SITE_TOP: ' + input_dict['PACKAGE_SITE_TOP']

    if VersionToRelNumber(input_dict['EPICS_BASE_VER']) >= 3.141205:
        pspkg_root = getEnv('PSPKG_ROOT')
        if not os.path.isdir( pspkg_root ):
            pspkg_root = '/reg/g/pcds/pkg_mgr'
        if not os.path.isdir( pspkg_root ):
            pspkg_root = '/afs/slac/g/lcls/pkg_mgr'
        if not os.path.isdir( pspkg_root ):
            pspkg_root = '/afs/slac/g/pcds/pkg_mgr'
        print 'Using PSPKG_ROOT:', pspkg_root
        input_dict['PSPKG_ROOT'] = pspkg_root

    input_dict['TOOLS_SITE_TOP'] = ''
    input_dict['ALARM_CONFIGS_TOP'] = ''
    tools_site_top = getEnv('TOOLS')
    if os.path.isdir(tools_site_top):
        input_dict['TOOLS_SITE_TOP'] = tools_site_top
        if not batch:
            prompt6 = 'Enter full path for TOOLS_SITE_TOP or [RETURN] to use "' + tools_site_top + '">'
            user_input = raw_input(prompt6).strip()
            if user_input:
                input_dict['TOOLS_SITE_TOP'] = user_input
        if os.path.isdir( input_dict['TOOLS_SITE_TOP'] ):
            print 'Using TOOLS_SITE_TOP: ' + input_dict['TOOLS_SITE_TOP']

            alarm_configs_top = os.path.join( input_dict['TOOLS_SITE_TOP'], 'AlarmConfigsTop' )
            input_dict['ALARM_CONFIGS_TOP'] = alarm_configs_top
            if not batch:
                prompt6 = 'Enter full path for ALARM_CONFIGS_TOP or [RETURN] to use "' + alarm_configs_top + '">'
                user_input = raw_input(prompt6).strip()
                if user_input:
                    input_dict['ALARM_CONFIGS_TOP'] = user_input
            if os.path.isdir( input_dict['ALARM_CONFIGS_TOP'] ):
                print 'Using ALARM_CONFIGS_TOP: ' + input_dict['ALARM_CONFIGS_TOP']

    return input_dict


# TODO: 1. Breakout packageName completer code into it's own function
# TODO: 2. Combine assemble_cvs_inputs_from_term and assemble_cvs_inputs_from_file into one function w/ a from_file boolean
# Determine the package and tag to checkout
def assemble_cvs_inputs_from_term(options):
    cvs_dict = {}

    cvs_dict['REPOSITORY'] = None

    if options.module:
        cvs_dict['REPOSITORY'] = options.module

    packageNames = set().union(git_package2Location.keys(), cvs_modules2Location.keys())
    def packageNameCompleter(text, state):
        options = [x for x in packageNames if x.startswith(text)]
        try:
            return options[state]
        except IndexError:
            return None

    readline.set_completer(packageNameCompleter)
    readline.parse_and_bind("tab: complete")

    while not cvs_dict['REPOSITORY']:
       cvs_dict['REPOSITORY'] = raw_input('Enter name of module/package to checkout: ').strip()
    packageName = cvs_dict['REPOSITORY']

    # Remove completer after we are done...
    readline.set_completer()
    readline.set_completer_delims(" \t\n")
    readline.parse_and_bind('tab: self-insert')

    dirName     = ""
    tagName     = ""
    if hasattr(options, 'tag') and options.tag:
        tagName = options.tag
    else:
        tags = []
        pathToGitRepo = determinePathToGitRepo( packageName )
        autoGitPath = False
        if autoGitPath and not pathToGitRepo:
            pathToGitRepo = os.path.join( GIT_REPO_MODULES, packageName + '.git' )
            if not os.path.exists( pathToGitRepo ):
                pathToGitRepo = None
        if pathToGitRepo:
            dirName = '%s-git' % packageName
            if os.path.exists(os.path.join(pathToGitRepo, "refs", "tags")):
                # Determine the list of tags..
                tags = os.listdir(os.path.join(pathToGitRepo, "refs", "tags"))
            else:
                print "Git repo at", pathToGitRepo, "does not seem to have any tags"
    
        else:
            dirName = 'MAIN_TRUNK'
            p1 = subprocess.Popen(['cvs', '-Q', 'rlog', '-h', cvs_dict['REPOSITORY']], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['awk', '-F"[.:]"', '/^\t/&&$(NF-1)!=0{print $1}'], stdin=p1.stdout, stdout=subprocess.PIPE)
            p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
            output = p2.communicate()[0]

            plaintags = set()
            for line in output.split('\n'):
                line = line.strip()
                parts = line.split()
                if len(parts) < 1:
                    continue
                plaintags.add(parts[0].split(":")[0])
            tags = sorted(plaintags)

        if len(tags) > 0:            
            def tagCompleter(text, state):
                options = [x for x in tags if x.startswith(text)]
                try:
                    return options[state]
                except IndexError:
                    return None
            readline.set_completer(tagCompleter)
            readline.set_completer_delims(" \t\n")
            readline.parse_and_bind("tab: complete")

        if not options.batch:
            prompt1 = 'Enter name of tag or [RETURN] to create a sandbox named %s>' % dirName
            tagName = raw_input(prompt1).strip()
        if  tagName == "" and dirName == 'MAIN_TRUNK':
            tagName = 'MAIN_TRUNK'

        readline.set_completer()
        readline.parse_and_bind('tab: self-insert')

    if tagName != "":
        dirName = tagName
    cvs_dict['RELEASE'] = dirName

    if options.destination:
        destinationPath = options.destination
    else:
        ( parent_dir, folder_name ) = os.path.split( os.getcwd() )
        if folder_name == packageName:
            destinationPath = dirName
        else:
            destinationPath = os.path.join( packageName, dirName )

    curDir = os.getcwd()
    checkOutModule( packageName, tagName, destinationPath, options )
    # TODO: checkOutModule changes cwd to curDir/destinationPath.  Do we want functions to change current dir and not restore?
    # os.chdir(curDir)

# Determine the package and tag to checkout
def assemble_cvs_inputs_from_file(repo, rel, options):
    cvs_dict = {}

    cvs_dict['REPOSITORY'] = repo
    cvs_dict['RELEASE'] = rel

    if cvs_dict['RELEASE'] == "" or cvs_dict['RELEASE'] == 'HEAD':
        cvs_dict['RELEASE'] = 'MAIN_TRUNK'

    packageName = cvs_dict['REPOSITORY']
    tagName     = cvs_dict['RELEASE']

    ( parent_dir, folder_name ) = os.path.split( os.getcwd() )
    if folder_name == packageName:
        destinationPath = tagName
    else:
        destinationPath = os.path.join( packageName, tagName )

    curDir = os.getcwd()
    checkOutModule( packageName, tagName, destinationPath, options, from_file=True )
    # TODO: checkOutModule changes cwd to curDir/destinationPath.  Do we want functions to change current dir and not restore?
    # os.chdir(curDir)
 
def checkOutModule(packageName, tag, destinationPath, options, from_file=False ):
    '''Checkout the module from GIT/CVS. 
    We first check to see if GIT has the module; if so, we clone the repo from git and do a headless checkout for the selected tag.
    Otherwise, we issue a command to CVS.
    '''

    if tag == '':
        print "Checkout %s to sandbox directory %s" % ( packageName, destinationPath )
    else:
        print "Checkout %s, tag %s, to directory %s" % ( packageName, tag, destinationPath )
    if not options.batch:
        confirmResp = raw_input( 'Proceed (Y/n)?' )
        if len(confirmResp) != 0 and confirmResp != "Y" and confirmResp != "y":
            print "Aborting....."
            sys.exit(0)

    # TODO: Can we update existing dir using repo?
    if os.path.exists(destinationPath):
        print 'Directory already exists!  Aborting.....'
        sys.exit(0)

    parent_dir = os.path.dirname( destinationPath )
    if len(parent_dir) > 0 and parent_dir != '.' and not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    # Remember current dir
    curDir = os.getcwd()

    #
    # TODO: Move this git vs svn vs cvs stuff to the Repo class and it's subclasses
    # Share common logic w/ epics-build and epics-release
    #

    # See if we can find it in with the git repos
    pathToGitRepo = determinePathToGitRepo(packageName)

    if pathToGitRepo:
        if pathToGitRepo.startswith("svn:///"):
            pathToSVNRepo =  pathToGitRepo.replace("svn:///", "file:///")
            if ( tag == 'MAIN_TRUNK' or tag == 'current' ):
                cmd=[ 'svn', 'checkout', pathToSVNRepo, destinationPath ]
            else:
                cmd=[ 'svn', 'checkout', '--revision', tag, pathToSVNRepo, destinationPath ]
            print cmd
            subprocess.check_call(cmd)
            os.chdir(destinationPath)
        else:
            print packageName, "is a git package.\nCloning the repository at", pathToGitRepo
            if os.path.exists(destinationPath):
                print "The folder", os.path.abspath(destinationPath), "already exists. If you intended to update the checkout, please do a git pull to pull in the latest changes."
                print "Aborting....."
                sys.exit(1)
            # TODO: Verify the tag exists before we clone the repo for better user error msg and to avoid broken release dirs
            cmd=['git', 'clone', '--recursive', pathToGitRepo, destinationPath]
            print cmd
            subprocess.check_call(cmd)
            os.chdir(destinationPath)
            if (tag != ''):
                # Do a headless checkout to the specified tag
                cmd=['git', 'checkout', tag]
                print cmd
                subprocess.check_call(cmd)
            #else: TODO Checkout a default branch if one isn't already selected.
            # 1. current release branch
            # 2. master
            # 3. github-master
            # 4. lcls-trunk
            # 5. pcds-trunk
    else:
        if (tag == 'MAIN_TRUNK'):
            cmd='cvs checkout -P -d ' + destinationPath + ' ' + packageName    
            print cmd
        else:
            cmd='cvs checkout -P -r '+ tag +' -d '+ destinationPath +' ' + packageName    
            print cmd
        os.system(cmd)
        os.chdir(destinationPath)

    # See if we need to create or update a RELEASE_SITE file
    # Not needed if this is an EPICS base package
    # If the package has a configure/RELEASE file, make sure we either have
    # a valid RELEASE_SITE in TOP/../..
    # or provide and/or update TOP/RELEASE_SITE as needed
    if	(		not isBaseTop(		os.path.join( curDir, destinationPath ) )
            and		isEpicsPackage( os.path.join( curDir, destinationPath ) )
            and not os.path.isfile( os.path.join( curDir, destinationPath, '..', '..', 'RELEASE_SITE' ) )
            # Step on a RELEASE_SITE pulled from the repo? No for PCDS, Yes for LCLS
            # TODO: Add a user prompt here w/ appropriate default
            and	(	not isPCDSPath( curDir )
                or	not os.path.isfile( os.path.join(curDir, destinationPath, 'RELEASE_SITE') )	) ):
        if from_file:
            inputs = assemble_release_site_inputs( batch=True )
        else:
            inputs = assemble_release_site_inputs( batch=options.batch )
        export_release_site_file( inputs, debug=options.debug )

    # TODO: checkOutModule changes cwd to curDir/destinationPath.  Do we want functions to change current dir and not restore?
    # os.chdir(curDir)

def determinePathToGitRepo(packageName):
    '''If the specified package is stored in GIT, then return the URL to the GIT repo. Otherwise, return None'''
    # See if the package was listed in $TOOLS/eco_modulelist/modulelist.txt
    if packageName in git_package2Location:
        return git_package2Location[packageName]
    # Check under the root of the git repo area for a bare repo w/ the right name
    gitRoot = determineGitRoot()
    gitPackageDir = packageName + ".git"
    for dirPath, dirs, files in os.walk( gitRoot, topdown=True ):
        if len( dirs ) == 0:
            continue
        for dir in dirs[:]:
            if dir == gitPackageDir:
                return os.path.join( gitRoot, dirPath, dir )
            if dir.endswith( ".git" ):
                # Remove from list so we don't search recursively
                dirs.remove( dir )
    return None


def initGitBareRepo():
    '''Initialize a bare repo in the user specified folder'''
    gitRoot = determineGitRoot()
    
    # Ask the user for the name of the package
    packageName = subprocess.check_output(["zenity", "--entry", "--title", "Package Name", "--text", "Please enter the name of the package"]).strip()
    if packageName in git_package2Location or packageName in cvs_modules2Location:
        if packageName in git_package2Location:
            packageLocation = git_package2Location[packageName]
        elif packageName in cvs_modules2Location:
            packageLocation = os.path.join(os.environ['CVSROOT'], cvs_modules2Location[packageName])
        subprocess.check_call(["zenity", "--error", "--title", "Error", "--text", "The package " + packageName + " already is already registered and exists in " + packageLocation])
        return
    
    # Ask the use where the master repo is to be created
    bareRepoParentFolder = subprocess.check_output(["zenity", "--file-selection", "--title", "Please choose the parent folder where you want to create the bare repo", "--directory", "--filename="+gitRoot]).strip()
    
    apptype = determineCramAppType()

    # Create the master repo as a bare repo
    gitMasterRepo = initBareRepo(bareRepoParentFolder, packageName)
                                        
    tpath = tempfile.mkdtemp()
    curDir = os.getcwd()
    
    clonedFolder = cloneMasterRepo(gitMasterRepo, tpath, packageName)
    os.chdir(clonedFolder)
    
    createGitIgnore()
    createCramPackageInfo(packageName, apptype)
        
    commitAndPush()

    os.chdir(curDir)
    shutil.rmtree(tpath)
    
    addPackageToEcoModuleList(packageName, gitMasterRepo)
    
    print "Done creating bare repo for package ", packageName, ". Use eco to clone this repo into your working directory."
    subprocess.check_call(["zenity", "--info", "--title", "Repo created for " + packageName, "--text", "Done creating bare repo for package " + packageName + ". Use eco to clone this repo into your working directory."])

def importFromCVS():
    '''Import package from CVS and place into new git repo. Uses ${TOOLS}/cvs2git/current/cvs2git to do the actual importing'''
    gitRoot = determineGitRoot()
    checkCVS2GitPresent()
 
    # Ask the user for the name of the package
    packageName = subprocess.check_output(["zenity", "--entry", "--title", "Package Name", "--text", "Please enter the name of the package"]).strip()
    if packageName in git_package2Location:
        subprocess.check_call(["zenity", "--error", "--title", "Error", "--text", "The package " + packageName + " is already registered and exists here - " + packageLocation])
        return
    if packageName not in cvs_modules2Location:
        subprocess.check_call(["zenity", "--error", "--title", "Error", "--text", "The package " + packageName + " does not seem to be a CVS package."])
        return
    
    CVSpackageLocation = os.path.join(os.environ['CVSROOT'], cvs_modules2Location[packageName])
    print "Importing CVS package from ", CVSpackageLocation
    
    # Ask the use where the master repo is to be created
    bareRepoParentFolder = subprocess.check_output(["zenity", "--file-selection", "--title", "Please choose the parent folder where you want to create the master git repo", "--directory", "--filename="+gitRoot]).strip()
    
    # Create a bare master repo to load the CVS history into
    gitMasterRepo = initBareRepo(bareRepoParentFolder, packageName)     

    curDir = os.getcwd()
    tpath = tempfile.mkdtemp()

    importHistoryFromCVS(tpath, gitMasterRepo, CVSpackageLocation)
    print "CVS history for ", packageName, " imported to ", gitMasterRepo

    # Add .gitignore
    clonedFolder = cloneMasterRepo(gitMasterRepo, tpath, packageName)
    os.chdir(clonedFolder)
    createGitIgnore()
    # We expect .cram/packageinfo to be there already
    
    commitAndPush()

    os.chdir(curDir)

    addPackageToEcoModuleList(packageName, gitMasterRepo)
    removeModuleFromCVS(tpath, packageName, CVSpackageLocation)

    os.chdir(curDir)
    shutil.rmtree(tpath)
    
    print "Done creating bare master repo for package ", packageName, ". Use eco to clone this repo into your working directory."
    subprocess.check_call(["zenity", "--info", "--title", "Repo created for " + packageName, "--text", "Done creating bare repo for package " + packageName + ". Use eco to clone this repo into your working directory."])


def module_callback(option, opt_str, value, parser):
    print 'Processing MODULE option; Setting ', option.dest, ' to ', value
    setattr(parser.values, option.dest, value)
    if len(parser.rargs) > 0:
        print 'Setting tag to ' + parser.rargs[0]
        setattr(parser.values, 'tag', parser.rargs[0])
        parser.rargs.pop(0)

def process_options(argv):
    if argv is None:
        argv = sys.argv[1:]

    usage = 'Usage: %prog <Command or File_listing_packages_and_tags (one pair per line)>\n'\
            + '\n'\
            + 'epics-checkout (eco) is a script that wraps git clone/cvs checkout and does some additional things that make compilation of modules within the EPICS LCLS/PCDS environment easier.\n'\
            + 'The main intent of epics-checkout is to get hardcoded paths out of configure/RELEASE.\n'\
            + 'It generates a file called RELEASE_SITE that contains these hardcoded paths; the configure/RELEASE.local now instead includes RELEASE_SITE\n'\
            + '\n'\
            + 'epics-checkout has interactive and batch modes.\n'\
            + 'To start epics-checkout in interactive mode, simply type epics-checkout or eco\n'\
            + 'For the batch mode, you can pass in a file containing a list of the modules you want to checkout; for example, eco modulelist.txt.\n'\
            + 'Each line in this file contains the module name and the branch/tag label. \n'\
            + 'For example, a line for the sequencer would have "seq  seq-R2-0-11-lcls4"\n'\
            + '\n'\
            + 'epics-checkout also supports a command called initrepo "eco initrepo" that creates a bare git repository for your package.\n'\
            + '"epics-checkout initrepo" prompts you for a package name and type and repo location.\n'\
            + 'It then creates a bare git repo in the location specified; it also creates a default .gitignore and cram configuration for your package.\n'\
            + '\n'\
            + 'epics-checkout also supports a command called cvs2git "eco cvs2git" that imports a module from CVS into a git bare repo.\n'\
            + '"eco cvs2git" prompts you for a module name and type and repo location.\n'\
            + 'It then creates a bare git repo in the location specified; imports the history from CVS and adds a default .gitignore.\n'\
            + 'It comments out the module location in the CVSROOT/modules file; however, it does NOT do a cvs remove of the software from CVS.\n'\
            + '\n'
    version = '%prog 0.1'
    parser = optparse.OptionParser(usage=usage, version=version)

    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', help='print verbose output')
    parser.add_option('-b', '--batch',   action='store_true', dest='batch', help='Run without confirmation prompts')
    parser.add_option('-m', '--module',  action='callback', dest='module', help='Module to checkout, optionally add the tag to use', type='string', callback=module_callback)
    parser.add_option('-d', '--destination',  action='store', dest='destination', help='Checkout the package to this folder. Uses cvs -d. For example, eco -d CATER_12345 on MAIN_TRUNK checks out MAIN_TRUNK into a folder called CATER_12345. This option is ignored in batch mode.', type='string')
    # parser.add_option('-t', '--tag',  action='store', dest='tag', help='CVS tag to checkout - defaults to MAIN_TRUNK', type='string', default='MAIN_TRUNK')
    parser.add_option( '--debug', action='store_true', dest='debug', help='print debugging output')

    parser.set_defaults(verbose=False,
        db_file=None)

    (options, args) = parser.parse_args(argv)

    if len(args) == 1:
        options.input_file_path = os.path.normcase(args[0])
    else:
        options.input_file_path = None

    return options 

commands = {
    "initrepo" : initGitBareRepo,
    "cvs2git" : importFromCVS
}

def main(argv=None):
    options = process_options(argv)

    if (options.input_file_path):
        if options.input_file_path in commands:
            commands[options.input_file_path]()
            return
        try:
            in_file = open(options.input_file_path, 'r')
        except IOError, e:
            sys.stderr.write('Could not open module specification file "%s": %s\n' % (options.input_file_path, e.strerror))
            return None

        # Read in pairs (package release) one per line
        for line in in_file:
            # Remove comments
            line = line.partition('#')[0]

            # Turn 'a = b' into a key/value pair and remove leading and trailing whitespace
            (key, sep, value) = line.partition(' ')
            key = key.strip()
            value = value.strip()

            print 'key is: ' + key
            print 'value is: ' + value

            assemble_cvs_inputs_from_file(key,value,options)
           
            print 'done with ' + line
            # repeat above for all lines in file

        in_file.close()

    else:
        assemble_cvs_inputs_from_term(options)

    return 0
    

if __name__ == '__main__':
    status = main()
    sys.exit(status)
