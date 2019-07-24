#!/usr/bin/env python
import re
import sys

# Check the python version
if sys.version_info[0] < 2 or ( sys.version_info[0] == 2 and sys.version_info[1] < 7 ):
    print >> sys.stderr, "Python version %d.%d not supported." % (sys.version_info[0], sys.version_info[1])
    print >> sys.stderr, "Please use python 2.7 or newer for epics-release."
    sys.exit(1)

import shutil
import optparse
import traceback
import tempfile
import commands
import stat
import os
import subprocess
from cram_utils import *
from git_utils import *
from svn_utils import *
from site_utils import *
from version_utils import *
from eco_version import eco_tools_version
from gitRepo  import *
from svnRepo  import *
from Releaser import *
from repo_defaults import *

# This script releases an EPICS package into the release area.
# It is written to support the following version control repositories:
#	PCDS SVN repository
#	LCLS CVS repository
#   SLAC git repositories under /afs/slac/g/cd/swe/git/repos
#
# Packages include the following:
#	base				- EPICS base
#	extensions			- EPICS extensions
#	modules/<mod_name>	- Module named mod_name
#	<ioc_name>			- LCLS IOC named ioc_name
#	ioc/common/<ioc_name>	- Common IOC named ioc_name
# For each package released
# it will:
#	Check for invalid versions in configure/RELEASE files
#	Checkout and test build the package in a temp directory
#		If the build fails, the release is canceled and the
#		build output sent to stderr
#	Determine the appropriate release version string
#		This can be specified via the cmd line
#		Enhancements to this script will be able to determine
#		the appropriate version for major, minor, or bug-fix releases
#	Checkout the release version to the release area
#	Build the release version in the release area
#
# Copyright 2010,2011,2012,2014,2015,2016,2017,2018 Stanford University
# Author: Bruce Hill <bhill@slac.stanford.edu>
#
# Released under the GPLv2 licence <http://www.gnu.org/licenses/gpl-2.0.html>
#
debugScript			= False


# TODO: Cleanup this function
# We need to push most of these tests to the sub-classes of repo
def ValidateArgs( repo, packageSpec, opt ):
    # release=None, message=None, verbose=False, batch=False )
    # validate the repo
    if not repo:
        raise ValidateError, "Repo not found for packageSpec %s" % (packageSpec)
    defaultPackage	= None
    ( repo_url, repo_branch, repo_tag ) = repo.GetWorkingBranch()
    if repo_url:
        defaultPackage = repo.GetDefaultPackage( packageSpec )

    # If we have a defaultPackage from the working directory,
    # Check it against the other options
    if defaultPackage:
        if not packageSpec:
            packageSpec = [ defaultPackage ]

    if opt.verbose:
        print "epics-release ValidateArgs: repo_url       =", repo_url
        print "epics-release ValidateArgs: repo_branch    =", repo_branch
        print "epics-release ValidateArgs: repo_tag       =", repo_tag
        print "epics-release ValidateArgs: packageSpec    =", packageSpec
        print "epics-release ValidateArgs: defaultPackage =", defaultPackage
        print "epics-release ValidateArgs: release        =", opt.release

    # Determine the release package URL
    if not repo_branch:
        if not packageSpec:
            raise ValidateError, "No release package specified"
        if packageSpec is list and len( packageSpec ) > 1:
            raise ValidateError, "Multiple release packages specified: %s" % (packageSpec)
        if repo_url:
            repo_branch = repo_url

    # Make sure the release package exists
    #if not gitPathExists( repo_branch, repo_tag ):
    #	raise ValidateError, "Invalid git branch %s tag %s" % ( repo_branch,  repo_tag )

    # TODO: Auto generate release tag

    # validate release tag
    if opt.release is None:
        if repo_tag is not None:
            opt.release = repo_tag
    if opt.release is None:
        raise ValidateError, "Release tag not specified (--release)"

    if not re.match( r"(\S*R\d+([\-\.]\d+)-\d+\.\d+\.\d+?)|(\S*R\d+[\.\-]\d+([\-\.]\d+)?)", opt.release ):
        raise ValidateError, "%s is an invalid release tag: Must be R[<orig_release>-]<major>.<minor>.<bugfix>" % opt.release

    if not opt.noTag and repo_tag != opt.release:
        # validate release message
        if not opt.message:
            print "Please enter a release comment (end w/ ctrl-d on blank line):"
            comment = ""
            try:
                while True:
                    line = raw_input()
                    comment = "\n".join( [ comment, line ] ) 
            except EOFError:
                opt.message = comment

        if opt.message is None:
            raise ValidateError, "Release message not specified (-m)"

    # if repo_url: This is an svn only test
    if False:
        # Check release branch vs working dir branch
        if repo_branch != repo_url:
            print "Release branch: %s\nWorking branch: %s" % ( repo_branch, repo_url )
            if not opt.batch:
                confirmResp = raw_input( 'Release branch does not match working dir.  Proceed (Y/n)?' )
                if len(confirmResp) != 0 and confirmResp != "Y" and confirmResp != "y":
                    branchMsg = "Branch mismatch!\n"
                    raise ValidateError, branchMsg

    versionFileName = git_get_versionFileName()
    if versionFileName and os.path.isfile( versionFileName ):
        # TODO: has it changed, show the change, prompt to edit
        print "Did you remember to update the version file? %s" % versionFileName

    if os.path.isfile( "RELEASE_NOTES" ):
        # TODO: has it changed, is tag found, show the change
        # TODO: prompt to edit, pre-populate release entry
        print "Did you remember to update the RELEASE_NOTES file?"

    # validate repo_grpowner	= DEF_LCLS_GROUP_OWNER
    if opt.verbose:
        print "ValidateArgs: Success"
        print "  repo_url:    %s" % repo_url
        print "  branch:      %s" % repo_branch
        print "  tag:         %s" % opt.release
        #print "  releasePath: %s" % repo_ReleasePath
        if opt.message:
            print "  message: %s" % opt.message

# Entry point of the script. This is main()
try:
    # Make sure we have a valid EPICS_SITE_TOP
    defaultEpicsSiteTop = determine_epics_site_top()
    if not defaultEpicsSiteTop or not os.path.isdir( defaultEpicsSiteTop ):
        raise ValidateError, ( "Can't find EPICS_SITE_TOP at %s" % defaultEpicsSiteTop )

    parser = optparse.OptionParser(
        usage =	"usage: %prog [options] -r <release> [ <packageSpec> ] [ -m \"My release comments\" ]\n"
                "\tEx: %prog -r R0.1.0 ioc/xpp/vacuum -m \"Adding baratron gauge\"\n"
                "\tFor help: %prog --help",
        version = eco_tools_version )
    parser.set_defaults(	verbose		= False,
                            revision	= "HEAD",
                            batch		= False,
                            noTag		= False,
                            noMsg		= False,
                            debug		= debugScript,
                            keeptmp		= False	)
    parser.add_option(	"-r", "-R", "--release", dest="release",
                        help="release version string, ex. -r R1.2.3-0.1.0" )
    parser.add_option(	"-m", "--message", dest="message",
                        help="release message in quotes"	)
    parser.add_option(	"-v", "--verbose", dest="verbose", action="store_true",
                        help="show commands as they are executed" )
    parser.add_option(	"-q", "--quiet", dest="quiet", action="store_true",
                        help="do not show build or checkout output" )
    parser.add_option(	"", "--revision", dest="revision",
                        help="specify revision or branch, defaults to %default"	)
    parser.add_option(	"", "--noMsg", dest="noMsg", action="store_true",
                        help="do not include a release message"	)
    parser.add_option(	"-n", "--noTag", dest="noTag", action="store_true",
                        help="do not tag, just rebuild an existing release"	)
    parser.add_option(	"-i", "--install", dest="installDir",
                        help="install directory, "
                            "ex. /afs/slac/g/lcls/epics/iocTop/BLD/R1.2.3" )
    parser.add_option(	"-d", "--debug", dest="debug", action="store_true",
                        help="display more info for debugging script" )
    parser.add_option(	"", "--dryRun", dest="dryRun", action="store_true",
                        help="Do test build but no tag or install" )
    parser.add_option(	"", "--noTestBuild", dest="noTestBuild", action="store_true", default=True,
                        help="Skip test build" )
    parser.add_option(	"", "--testBuild", dest="noTestBuild", action="store_false",
                        help="Do a test build" )
    parser.add_option(	"", "--rmBuild", dest="rmBuild", action="store_true",
                        help="Remove release build.  "
                            "Does not do a new release." )
    parser.add_option(	"", "--rmTag", dest="rmTag", action="store_true",
                        help="Remove release tag.  "
                            "Does not do a new release." )
    parser.add_option(	"-x", "--nukeRelease", dest="nukeRelease", action="store_true",
                        help="Remove tag and build of release.  "
                            "Does not do a new release." )
    parser.add_option(	"",	  "--keeptmp", dest="keeptmp", action="store_true",
                        help="do not erase the temp build directory" )
    parser.add_option(	"",	  "--batch", dest="batch", action="store_true",
                        help="do not prompt for confirmation" )
    # Future options
    #add_option( "--repo", "repository address."
    #add_option( "--prefix", "path to the root of the release area"

    # Parse the command line arguments
    ( opt, args ) = parser.parse_args()

    if not opt.release:
        raise ValidateError, ( "Release tag not specified!" )

    if opt.verbose:
        print "epics-release main: opt.message=%s, args=%s" % ( opt.message, args )

    repo         = None
    packageMatch = None
    packageName  = None
    packagePath  = None

    # See if this is a git working dir
    ( git_url, git_branch, git_tag ) = gitGetWorkingBranch()
    repo_tag = git_tag

    if git_url:
        if opt.verbose:
            print "git_url:    %s" % git_url
            print "git_branch: %s" % git_branch
        # Create a git release handler
        ( urlPath, packageGitDir ) = os.path.split( git_url )
        if packageGitDir is None:
            ( urlPath, packageGitDir ) = os.path.split( urlPath )

        # Find the packageName
        if packageGitDir == '.git':
            ( urlPath, packageName ) = os.path.split( urlPath )
        else:
            packageMatch = re.match( r"(\S+).git", packageGitDir )
            if packageMatch:
                packageName = packageMatch.group(1)

        # Find the packagePath
        ( packageHead, packageTail ) = os.path.split( urlPath )
        packagePath = os.path.join( packageTail, packageName )
        while packageHead:
            if packageHead.endswith( "epics" ):
                break
            if packageHead.endswith( "repos" ):
                break
            if packageHead.endswith( ".com" ):
                break
            if packageHead.endswith( ".edu" ):
                break
            ( packageHead, packageTail ) = os.path.split( packageHead )
            packagePath = os.path.join( packageTail, packagePath )

        # Create a gitRepo object for this url
        repo = gitRepo.gitRepo( git_url, git_branch, packageName, opt.release )
        if git_tag == opt.release:
            opt.noTag = True
            opt.noTestBuild	= True
    else:
        # See if this is an svn working dir
        ( svn_url, svn_branch, svn_tag ) = svnGetWorkingBranch()

        if svn_url:
            packageMatch = re.match( r"\S+(epics/trunk/|trunk/pcds/epics/)(\S+)/current", svn_url )
            if packageMatch:
                packagePath = packageMatch.group(2)
                packageName = os.path.split( packagePath )[1]
            if opt.noTag:
                svn_url	= "/".join( [ DEF_SVN_TAGS, packagePath, opt.release ] )
            if opt.verbose:
                print "svn_url:    %s" % svn_url
                print "svn_branch: %s" % svn_branch
            # Create an svn release handler
            repo = svnRepo.svnRepo( svn_url, svn_branch, packagePath, opt.release )

    if len(args) > 0:
        packageSpec = args[0]
        packagePath = packageSpec
        if opt.release:
            if os.path.split(packageSpec)[1] != opt.release:
                packageSpec = os.path.join( packageSpec, opt.release )
        if opt.verbose:
            print "epics-release main: packageSpec=%s, args=%s" % ( packageSpec, args )
        release = find_release( packageSpec, repo_url=repo.GetUrl(), verbose=opt.verbose )
        if release:
            if not release._packageName:
                raise ValidateError, ( "Invalid package specified: %s" % packageSpec )
            repo = release._repo
            packageName = release._packageName

    if not packageName:
        raise ValidateError, ( "No package specified and unable to determine it from current dir" )
    elif opt.verbose:
        print "package:    %s" % packageName

    # Have to have a repo to do a release
    if repo is None:
        raise ValidateError, ( "Can't establish a repo branch" )

    pkgReleaser = Releaser( repo, packagePath, verbose=opt.verbose )

    # If removing old release, don't build or tag
    if	opt.nukeRelease:
        opt.rmBuild		= True
        opt.rmTag		= True

    # Are we removing something?
    if	opt.rmBuild or opt.rmTag:
        # Removing stuff, no need to TestBuild or Tag
        opt.noTestbuild	= True
        opt.noTag		= True

    # Will we tag?
    if	opt.noTag:
        # Not tagging, no need for msg or TestBuild
        opt.noMsg		= True
        opt.noTestBuild	= True

    # Check for valid arguments
    ValidateArgs( repo, packagePath, opt )

    if not opt.installDir:
        # See if we can get the releaseDir from cram
        releaseDir = getCramReleaseDir( )
        if releaseDir:
            opt.installDir = os.path.join(	releaseDir, opt.release	)

    if not opt.installDir:
        # See if we can derive the releaseDir from the packagePath
        epics_base_ver = None
        topDirDependents = getEpicsPkgDependents( os.getcwd(), debug=debugScript )
        if 'base' in topDirDependents:
            epics_base_ver = topDirDependents['base']
            if strContainsMacros( epics_base_ver ):
                raise ValidateError, "Unable to determine EPICS base version from RELEASE files"
        if not packageName:
            raise ValidateError, "No release package specified"
        if os.path.split( packagePath )[0] == 'modules':
            if not epics_base_ver:
                epics_base_ver = determine_epics_base_ver()
            if not epics_base_ver:
                raise ValidateError, "Unable to determine EPICS base version"
            opt.installDir = os.path.join(	defaultEpicsSiteTop, epics_base_ver,
                                            packagePath, opt.release	)
        else:
            opt.installDir = os.path.join(	defaultEpicsSiteTop, packagePath, opt.release )
    pkgReleaser._installDir = opt.installDir
    print     "repo_url:    %s" % repo.GetUrl()
    if opt.rmTag:
        print "rm tag:      %s" % opt.release
    else:
        print "tag:         %s" % opt.release 
    if opt.rmBuild:
        print "rm buildDir: %s"	% opt.installDir
    else:
        print "installDir:  %s"	% opt.installDir
    if opt.dryRun:
        print "DryRun:      True"
    if	opt.noTag:
        opt.noTestBuild	= True

    if opt.verbose and git_url:
        if git_tag != opt.release:
            print "Need to tag %s\n" % opt.release
        # Make sure the tag has been pushed
        (remote_tag_sha, remote_tag ) = gitGetRemoteTag( git_url, opt.release )
        local_tag_sha = gitGetTagSha( opt.release )
        if remote_tag != opt.release or remote_tag_sha != local_tag_sha:
            print "Need to push tag %s\n" % opt.release

    # Confirm buildDir, installDir, and tag
    if not opt.batch and not opt.dryRun:
        confirmResp = raw_input( 'Proceed (Y/n)?' )
        if len(confirmResp) != 0 and confirmResp != "Y" and confirmResp != "y":
            sys.exit(0)

    # dryRun, just show release info
    if opt.dryRun:
        print "--dryRun--"
        if opt.rmTag:
            print "rm tag:      %s" % opt.release
        if opt.rmBuild:
            print "rm buildDir: %s"	% opt.installDir
        if not opt.rmTag and not opt.rmBuild:
            print "MakeRelease: %s" % opt.release
            print "branch:      %s" % repo._branch
            print "installDir:  %s" % opt.installDir
            print "message:     %s" % opt.message
        sys.exit(0)

    if opt.rmBuild or opt.rmTag:
        if opt.rmBuild:
            try:
                pkgReleaser.RemoveBuild( opt.installDir )
            except BuildError, e:
                print e
                pass
        if opt.rmTag:
            pkgReleaser.RemoveTag( tag=opt.release )

        # Remove options do not try to do
        # a release, so exit now
        sys.exit(0)

    #
    # Proceed with the release
    #

    # Do a test build first
    if not opt.noTestBuild:
        pkgReleaser.DoTestBuild()

    if not opt.noTag:
        # release tag
        if repo_tag != opt.release:
            pkgReleaser.TagRelease( message=opt.message )

        if git_url:
            # Make sure the tag has been pushed
            if gitGetRemoteTag( git_url, opt.release )[1] is None:
                repo.PushTag( opt.release )

    # Install package
    # pkgReleaser.InstallPackage( repo_installDir	)
    result = pkgReleaser.InstallPackage( )
    if result != 0:
        sys.exit( 1 )

    # All done!
    sys.exit(0)

except ValidateError:
    print "Error: %s\n" % sys.exc_value 
    parser.print_usage()
    sys.exit(6)

except BuildError:
    print "\nError: BUILD FAILURE"
    print "%s\n" % sys.exc_value 
    print "Fix build problems and commit any necessary changes"
    sys.exit(5)

except svnError:
    print "\nsvn FAILURE"
    print "%s\n" % sys.exc_value 
    print "Please copy script output and notify someone appropriate"
    sys.exit(4)

except InstallError:
    print "\nERROR: INSTALL FAILURE"
    print "%s\n" % sys.exc_value 
    sys.exit(3)

except KeyboardInterrupt:
    print "\nERROR: interrupted by user."
    sys.exit(2)

except SystemExit:
    raise

except:
    if debugScript:
        traceback.print_tb(sys.exc_traceback)
    print "%s exited with ERROR:\n%s\n" % ( sys.argv[0], sys.exc_value )
    sys.exit( 1 )
