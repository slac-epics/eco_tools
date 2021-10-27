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
#  Requested features to be added:
#   - Add setting of directory permissions per new acl list changes; 
#     i.e. set a flag to lock them
#   - Only put IOC_SITE_TOP in RELEASE_SITE if actually needed, not just
#     generically
#   - Break it into two scripts: one just to create the RELEASE_SITE file 
#     so that it could be used when checkout has already been done
#   - Make it go and change the $IOC/*/startup.cmd files to new release 
#       for all/subset of iocs in checked out app?s iocBoot
#
#--------------------------------------------------------------
#  For file history, please use the git log
#==============================================================
import sys
import os
import socket
import subprocess
import optparse
import readline
import shutil
import tempfile
import re

from cram_utils import *
from cvs_utils import *
from git_utils import *
from svn_utils import *
from site_utils import *
from version_utils import *
import cvs2git_utils


from eco_version import eco_tools_version

git_package2Location = parseGitModulesTxt()
cvs_modules2Location = parseCVSModulesTxt()

# TODO: 1. Breakout packageName completer code into it's own function
# TODO: 2. Combine assemble_env_inputs_from_term and assemble_env_inputs_from_file into one function w/ a from_file boolean
# Determine the package and tag to checkout
def assemble_env_inputs_from_term(options):

    packageName = None
    packageSpec = None
    if options.module:
        packageSpec = options.module
        packageName = os.path.split(packageSpec)[1]

    packageNames = set().union(git_package2Location.keys(), cvs_modules2Location.keys())

    def packageNameCompleter(text, state):
        options = [x for x in packageNames if x.startswith(text)]
        try:
            return options[state]
        except IndexError:
            return None

    readline.set_completer(packageNameCompleter)
    readline.parse_and_bind("tab: complete")

    while not packageName:
        packageSpec = raw_input('Enter name of module/package to checkout: ').strip()
        packageName = os.path.split(packageSpec)[1]

    # Remove completer after we are done...
    readline.set_completer()
    readline.set_completer_delims(" \t\n")
    readline.parse_and_bind('tab: self-insert')

    dirName     = ""
    tagName     = ""
    repoPath	= None
    if hasattr(options, 'tag') and options.tag:
        tagName = options.tag
    else:
        tags = []
        if packageName in cvs_modules2Location and os.path.isdir( DEF_CVS_ROOT ):            
            # cvs REPO
            if not dirName:
                dirName = 'MAIN_TRUNK'
            tags = cvsGetRemoteTags( packageName )
            repoPath = cvs_modules2Location[packageName]
        elif packageSpec in git_package2Location:
            repoPath = git_package2Location[packageSpec]
        elif packageName in git_package2Location:
            repoPath = git_package2Location[packageName]
        else:
            pathToGitRepo = determinePathToGitRepo( packageSpec, verbose=options.verbose )
            if pathToGitRepo:
                if "svn" in pathToGitRepo:
                    # svn REPO
                    if not dirName:
                        dirName = "current"
                    tags = svnGetRemoteTags( pathToGitRepo, verbose=options.verbose )
                else:
                    # git REPO
                    if not dirName:
                        dirName = packageName + "-git"
                    tags = gitGetRemoteTags( pathToGitRepo, verbose=options.verbose )

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

        readline.set_completer()
        readline.parse_and_bind('tab: self-insert')

    if not dirName:
        dirName = packageName + "-git"

    if tagName == "":
        if  dirName == 'MAIN_TRUNK':
            tagName = dirName
    else:
        dirName = tagName
    if options.destination:
        destinationPath = options.destination
    else:
        ( parent_dir, cur_basename ) = os.path.split( os.getcwd() )
        destinationPath = dirName
        if os.path.isdir(packageName):
            # Already a folder for different checkouts of this packageName.  Use it.
            destinationPath = os.path.join( packageName, dirName )

        # Don't create packageName/packageName/dirName
        if cur_basename != packageName:
            # svn and CVS default to creating parent packageName folder
            # git only creates the parent directory if options.createParent is set
            if options.createParent or dirName != (packageName + "-git"):
                destinationPath = os.path.join( packageName, dirName )

    checkOutModule( packageSpec, repoPath, tagName, destinationPath, options )

# Determine the package and tag to checkout
def assemble_env_inputs_from_file(packageSpec, tagName, options):
    repoPath	= None
    packageName = os.path.split(packageSpec)[1]
    if packageSpec in cvs_modules2Location and os.path.isdir( DEF_CVS_ROOT ):            
        # cvs REPO
        repoPath = cvs_modules2Location[packageSpec]
    elif packageSpec in git_package2Location:
        repoPath = git_package2Location[packageSpec]
    elif packageName in git_package2Location:
        repoPath = git_package2Location[packageName]
    else:
        repoPath = determinePathToGitRepo( packageSpec )

    if tagName == "" or tagName == 'HEAD':
        if repoPath:
            if "svn" in repoPath:
                # svn REPO
                dirName = "current"
            else:
                # git REPO
                dirName = packageName + '-git'
        else:
            # cvs REPO
            dirName = 'MAIN_TRUNK'
            tagName = 'MAIN_TRUNK'
    else:
        dirName = tagName

    ( parent_dir, cur_basename ) = os.path.split( os.getcwd() )
    destinationPath = dirName
    if os.path.isdir(packageName):
        # Already a folder for different checkouts of this packageName.  Use it.
        destinationPath = os.path.join( packageName, dirName )

    # Don't create packageName/packageName/dirName
    if cur_basename != packageName:
        # svn and CVS default to creating parent packageName folder
        # git only creates the parent directory if user selects --createParent
        if options.createParent or dirName != (packageName + "-git"):
            destinationPath = os.path.join( packageName, dirName )

    checkOutModule( packageSpec, repoPath, tagName, destinationPath, options, from_file=True )
 
def checkOutModule(packageSpec, repoPath, tag, destinationPath, options, from_file=False ):
    '''Checkout the module from GIT/CVS. 
    We first check to see if GIT has the module; if so, we clone the repo from git and do a headless checkout for the selected tag.
    Otherwise, we issue a command to CVS.
    '''

    packageName = os.path.split(packageSpec)[1]
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
        sys.exit(1)

    parent_dir = os.path.dirname( destinationPath )
    if len(parent_dir) > 0 and parent_dir != '.' and not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir, 0775)
        except OSError, e:
            sys.stderr.write( 'Unable to create directory: %s\n' % parent_dir )
            sys.exit(1)

    # Remember current dir
    curDir = os.getcwd()

    #
    # TODO: Move this git vs svn vs cvs stuff to the Repo class and it's subclasses
    # Share common logic w/ epics-build and epics-release
    #

    if not repoPath:
        # See if we can find it in with the git repos
        repoPath = determinePathToGitRepo(packageSpec)
    if not repoPath:
        print "Unable to determine repo path for %s" % packageSpec
        return

    if "git" not in repoPath and "svn" not in repoPath and cvs_modules2Location is not None:
        # Do CVS checkout
        if (tag == 'MAIN_TRUNK'):
            cmd='cvs checkout -P -d ' + destinationPath + ' ' + packageSpec    
            print cmd
        else:
            cmd='cvs checkout -P -r '+ tag +' -d '+ destinationPath +' ' + packageSpec    
            print cmd
        os.system(cmd)
        if not os.path.isdir(destinationPath):
            sys.stderr.write( "Error: unable to do cvs checkout of %s\n" % packageSpec )
            sys.exit(1)
        os.chdir(destinationPath)
    else:
        pathToSvnRepo = None
        if  repoPath.startswith("file:///"):
            pathToSvnRepo = repoPath
        if  repoPath.startswith("svn:///"):
            pathToSvnRepo = repoPath.replace("svn:///", "file:///")
        if  pathToSvnRepo:
            if ( not tag or tag == 'current' ):
                pathToSvnRepo = pathToSvnRepo.replace("tags","trunk")
            else:
                pathToSvnRepo = pathToSvnRepo.replace( "trunk/pcds/epics/extensions","epics/tags/extensions" )
                pathToSvnRepo = pathToSvnRepo.replace( "trunk/pcds/epics/modules","epics/tags/modules" )
                pathToSvnRepo = pathToSvnRepo.replace( "trunk","tags" )
                pathToSvnRepo = pathToSvnRepo.replace( "current",tag )
            cmd=[ 'svn', 'checkout', pathToSvnRepo, destinationPath ]
            print cmd
            subprocess.check_call(cmd)
            if not os.path.isdir(destinationPath):
                sys.stderr.write( "Error: unable to do svn checkout of %s\n" % packageName )
                sys.exit(1)
            os.chdir(destinationPath)
        else:
            print packageName, "is a git package.\nCloning the repository at", repoPath
            if os.path.exists(destinationPath):
                print "The folder", os.path.abspath(destinationPath), "already exists. If you intended to update the checkout, please do a git pull to pull in the latest changes."
                print "Aborting....."
                sys.exit(1)
            # TODO: Verify the tag exists before we clone the repo for better user error msg and to avoid broken release dirs
            branch = None
            depth  = None
            if (tag != ''):
                branch = tag
                # Don't do shallow clone for eco as users may want to fix bugs, retag, and push from there.
                # depth  = DEF_GIT_RELEASE_DEPTH
            cloneUpstreamRepo( repoPath, destinationPath, '', branch=branch, depth=depth, verbose=options.verbose )
            os.chdir(destinationPath)
            if (tag != ''):
                # Do a headless checkout to the specified tag
                cmd=['git', 'checkout', tag]
                print cmd
                subprocess.check_call(cmd)
            #else: TODO Checkout a default branch if one isn't already selected.
            # 1. current release branch
            # 2. trunk
            # 3. slac-trunk
            # 4. lcls-trunk
            # 5. pcds-trunk

    # See if we need to create or update a RELEASE_SITE file
    # Not needed if this is an EPICS base package
    # If the package has a configure/RELEASE file, make sure we either have
    # a valid RELEASE_SITE in TOP/../..
    # or provide and/or update TOP/RELEASE_SITE as needed

    # Check if any configuration file has included ../../RELEASE_SITE and if
    # ../../RELEASE_SITE exists.
    hasDotDotRelease = (hasIncludeDotDotReleaseSite() and
                       os.path.isfile( os.path.join( curDir, destinationPath, 
                                                  '..', '..', 'RELEASE_SITE' )))

    if  (       not isBaseTop(      os.path.join( curDir, destinationPath ) )
            and     isEpicsPackage( os.path.join( curDir, destinationPath ) )
            and not hasDotDotRelease
            # Step on a RELEASE_SITE pulled from the repo? No for PCDS, Yes for LCLS
            # TODO: Add a user prompt here w/ appropriate default
            and (   not isPCDSPath( curDir )
                or  not os.path.isfile( os.path.join(curDir, destinationPath, 'RELEASE_SITE') ) ) ):
        if from_file:
            inputs = assemble_release_site_inputs( batch=True )
        else:
            inputs = assemble_release_site_inputs( batch=options.batch )
        export_release_site_file( inputs, debug=options.debug )

    # Restore current working dir
    os.chdir(curDir)

def initGitBareRepo( options ):
    '''Initialize a bare repo in the user specified folder'''
    showStatusZenity = False
    zenityVersion = None
    try:
        zenityVersion = subprocess.check_output(["zenity", "--version"]).strip()
    except:
        print( "zenity not found!" )
        return
    gitRoot = determineGitRoot()
    if 'CVSROOT' not in os.environ:
        os.environ['CVSROOT'] = DEF_CVS_ROOT
 
    if options.module:
        packageSpec = options.module
    else: # TODO: Handle zenityVersion None
        # Ask the user for the name of the package
        packageSpec = subprocess.check_output(["zenity", "--entry", "--title", "Package Name", "--text", "Please enter the name of the package"]).strip()
        showStatusZenity = True
    packageName = os.path.split(packageSpec)[1]

    packageLocation = None
    if packageSpec in git_package2Location:
        packageLocation = git_package2Location[packageSpec]
    elif packageName in git_package2Location:
        packageLocation = git_package2Location[packageName]
    elif packageSpec in cvs_modules2Location:
        packageLocation = os.path.join(os.environ['CVSROOT'], cvs_modules2Location[packageSpec])
    elif packageName in cvs_modules2Location:
        packageLocation = os.path.join(os.environ['CVSROOT'], cvs_modules2Location[packageName])
    if packageLocation:
        print "Error: The package " + packageSpec + " is already registered and exists in:\n" + packageLocation
        if showStatusZenity:
            subprocess.check_call(["zenity", "--error", "--title", "Error", "--text", "The package " + packageName + " is already registered and exists in " + packageLocation])
        return
 
    if options.destination:
        bareRepoParentFolder = options.destination
    else:
        # Ask the use where the upstream bare repo is to be created
        showStatusZenity = True
        bareRepoParentFolder = subprocess.check_output(["zenity", "--file-selection", "--title", "Please choose the parent folder where you want to create the bare repo", "--directory", "--filename="+gitRoot]).strip()


    gitRepoPath = os.path.join( bareRepoParentFolder, packageName+".git" )
    try:
        # Create the upstream repo as a bare repo
        initBareRepo( gitRepoPath )
    except Exception as e:
        print "initGitBareRepo Error: initBareRepo call failed!\ngitRepoPath = " + gitRepoPath 
        print str(e)
        return

    tpath = tempfile.mkdtemp()
    curDir = os.getcwd()

    clonedFolder = cloneUpstreamRepo(gitRepoPath, tpath, packageName)
    os.chdir(clonedFolder)

    createGitIgnore()
    if options.apptype:
        apptype = options.apptype
    else:
        apptype = determineCramAppType()
    if apptype.lower() != 'none':
        createCramPackageInfo(packageName, apptype)

    gitCommitAndPush( 'Initial commit/import from eco. Added a default .gitignore and other defaults.' )

    os.chdir(curDir)
    shutil.rmtree(tpath)
    
    addPackageToEcoModuleList(packageSpec, gitRepoPath)
    
    print "Done creating bare repo for package ", packageSpec, ". Use eco to clone this repo into your working directory."
    if showStatusZenity:
        subprocess.check_call(	["zenity", "--info", "--title", "Repo created for " + packageSpec,
                                "--text", "Done creating bare repo for package " + packageSpec +
                                ". Use eco to clone this repo into your working directory."] )

def importFromCVS( options ):
    '''Import package from CVS and place into new git repo. Uses ${TOOLS}/cvs2git/current/cvs2git to do the actual importing'''
    gitRoot = determineGitRoot()
    cvs2git_utils.checkCVS2GitPresent()
    showStatusZenity = False
 
    if options.module:
        packageName = options.module
    else:
        # Ask the user for the name of the package
        showStatusZenity = True
        packageName = subprocess.check_output( ["zenity", "--entry", "--title", "Package Name", "--text",
                                                "Please enter the name of the package"] ).strip()

    if packageName in git_package2Location:
        print "eco cvs2git error: %s is already registered and exists here:\n%s" % ( packageName, git_package2Location[packageName] )
        return
    if packageName not in cvs_modules2Location:
        print "eco cvs2git error: %s does not seem to be a CVS module." % packageName
        print "Make sure it exists in %s/CVSROOT/modules" % os.environ['CVSROOT']
        return

    if 'CVSROOT' not in os.environ:
        os.environ['CVSROOT'] = DEF_CVS_ROOT
    CVSpackageLocation = os.path.join(os.environ['CVSROOT'], cvs_modules2Location[packageName])
    print "Importing CVS package from ", CVSpackageLocation

    if options.destination:
        bareRepoParentFolder = options.destination
    else:
        # Ask the use where the upstream repo is to be created
        showStatusZenity = True
        bareRepoParentFolder = subprocess.check_output(	["zenity", "--file-selection", "--title",
                                                        "Please choose the parent folder where you want to create the upstream bare git repo",
                                                        "--directory", "--filename="+gitRoot] ).strip()

    curDir = os.getcwd()
    tpath = tempfile.mkdtemp()

    gitRepoPath = bareRepoParentFolder
    if not gitRepoPath.endswith( packageName+".git" ):
        gitRepoPath = os.path.join( gitRepoPath, packageName+".git")

    try:
        cvs2git_utils.importHistoryFromCVS(tpath, gitRepoPath, CVSpackageLocation)
    except Exception as e:
        print str(e)
        return

    print "CVS history for ", packageName, " imported to ", gitRepoPath

    # Add .gitignore
    clonedFolder = cloneUpstreamRepo(gitRepoPath, tpath, packageName)
    os.chdir(clonedFolder)
    createGitIgnore()
    # We expect .cram/packageinfo to be there already
    
    gitCommitAndPush( 'Initial commit/import from eco. Added a default .gitignore and other defaults.' )

    os.chdir(curDir)

    addPackageToEcoModuleList(packageName, gitRepoPath)
    cvs2git_utils.removeModuleFromCVS(tpath, packageName, CVSpackageLocation)

    os.chdir(curDir)
    shutil.rmtree(tpath)

    print "Done creating bare repo for package ", packageName, ". Use eco to clone this repo into your working directory."
    if showStatusZenity:
        subprocess.check_call(	["zenity", "--info", "--title", "Repo created for " + packageName,
                                "--text", "Done creating bare repo for package " + packageName +
                                ". Use eco to clone this repo into your working directory."] )


def module_callback(option, opt_str, value, parser):
    print 'Processing MODULE option; Setting', option.dest, 'to', value
    setattr(parser.values, option.dest, value)
    if len(parser.rargs) > 0 and not parser.rargs[0].startswith("-"):
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
    parser = optparse.OptionParser(usage=usage, version=eco_tools_version)

    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', help='print verbose output')
    parser.add_option('-a', '--apptype', action='store', help='Cram app type. Used by initrepo to add .cram/packageinfo')
    parser.add_option('-b', '--batch',   action='store_true', dest='batch', help='Run without confirmation prompts')
    parser.add_option('-c', '--createParent',   action='store_true', dest='createParent', default=True, help='Automatically create parent dir using module name.')
    parser.add_option('-n', '--noCreateParent', action='store_false', dest='createParent', default=True, help='Do not create parent dir using module name unless a tag is specified.')
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
    "initrepo": initGitBareRepo,
    "cvs2git":  importFromCVS
}

def main(argv=None):
    options = process_options(argv)

    if (options.input_file_path):
        if options.input_file_path in commands:
            commands[options.input_file_path]( options )
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

            assemble_env_inputs_from_file(key,value,options)
           
            print 'done with ' + line
            # repeat above for all lines in file

        in_file.close()

    else:
        assemble_env_inputs_from_term(options)

    return 0
    

if __name__ == '__main__':
    status = main()
    sys.exit(status)
