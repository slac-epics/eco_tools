#!/usr/bin/env python
import re
import sys
import shutil
import optparse
import traceback
import tempfile
import commands
import stat
import os
import subprocess
from git_utils import *
from svn_utils import *
from version_utils import *
from eco_version import eco_tools_version
from gitRepo  import *
from svnRepo  import *
from Releaser import *

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
#   Create a branch named branch/<package> if it does not exist
#   Copy the current version of the package to branch/<package>/<version>
#	Checkout the release version to the release area
#	Build the release version in the release area
#
# Copyright 2010,2011,2012,2014,2015,2016 Stanford University
# Author: Bruce Hill <bhill@slac.stanford.edu>
#
# TODO: Branch releases working, but could use more testing w/ different variations
# TODO: Fix ability to release revisions other than HEAD
#
# Released under the GPLv2 licence <http://www.gnu.org/licenses/gpl-2.0.html>
#
DEF_CVS_REPO		= "/afs/slac/g/lcls/cvs"

DEF_CVS_MODULES		= DEF_CVS_REPO  + "/epics/site/src"

DEF_EPICS_TOP_PCDS	= "/reg/g/pcds/epics"
DEF_EPICS_TOP_LCLS	= "/afs/slac/g/lcls/epics"
DEF_EPICS_TOP_AFS	= "/afs/slac/g/pcds/epics"
DEF_LCLS_GROUP_OWNER= "lcls"
DEF_PCDS_GROUP_OWNER= "ps-pcds"
debugScript			= False


# TODO: Cleanup this function
# We need to push most of these tests to the sub-classes of repo
def ValidateArgs( repo, package, opt ):
    # release=None, message=None, verbose=False, batch=False )
    # validate the repo
    if not repo:
        raise ValidateError, "Repo not found for package %s" % (package)
    defaultPackage	= None
    ( repo_url, repo_branch, repo_tag ) = repo.GetWorkingBranch()
    if repo_url:
        defaultPackage = repo.GetDefaultPackage( package )

    # If we have a defaultPackage from the working directory,
    # Check it against the other options
    if defaultPackage:
        if not package or not package[0]:
            package = [ defaultPackage ]

    if opt.verbose:
        print "epics-release ValidateArgs: repo_url       =", repo_url
        print "epics-release ValidateArgs: repo_branch    =", repo_branch
        print "epics-release ValidateArgs: repo_tag       =", repo_tag
        print "epics-release ValidateArgs: package        =", package
        print "epics-release ValidateArgs: defaultPackage =", defaultPackage
        print "epics-release ValidateArgs: release        =", opt.release

    # Determine the release package URL
    if not repo_branch:
        if not package or not package[0]:
            raise ValidateError, "No release package specified"
        if len( package ) > 1:
            raise ValidateError, "Multiple  release packages specified: %s" % (package)
        if repo_url:
            repo_branch = repo_url
        else:
            # FIXME: Is this needed or just leftover from svn variant?
            repo_branch = os.path.join(	repo._url, repo_gitStub2,
                                                package[0], "current"	)
            #if not gitPathExists( repo_branch, repo_tag ):
            #	repo_branch = os.path.join(repo._repo, repo_gitStub1,
            #									package[0], "current"	)

    # Make sure the release package exists
    #if not gitPathExists( repo_branch, repo_tag ):
    #	raise ValidateError, "Invalid git branch %s tag %s" % ( repo_branch,  repo_tag )

    # validate release tag
    if opt.release is None:
        if repo_tag is not None:
            opt.release = repo_tag
    if opt.release is None:
        raise ValidateError, "Release tag not specified (--release)"

    if not re.match( r"(R\d+(\.\d+)+-\d+\.\d+\.\d+)|(R\d+\.\d+\.\d+)", opt.release ):
        raise ValidateError, "%s is an invalid release tag: Must be R[<orig_release>-]<major>.<minor>.<bugfix>" % opt.release
    #if not repo_ReleasePath:
    #	if not package or not package[0]:
    #		raise ValidateError, "No release package specified"
    #	repo_ReleasePath = os.path.join(	repo_repo, repo_gitRelDir,
    #										package[0], opt.release	)

    #if repo_noTag == False and gitPathExists( repo_ReleasePath ):
    #	raise ValidateError, "GIT release tag already exists: %s" % ( repo_ReleasePath )
#		try:
#			if gitPathExists( repo_ReleasePath ):
#				raise ValidateError, "SVN release tag already exists: %s" % ( repo_ReleasePath )
#		except:
#			pass
#		else:
#			raise ValidateError, "SVN release tag already exists: %s" % ( repo_ReleasePath )

    if not opt.noTag:
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
        usage =	"usage: %prog [options] [ <module> ] -r <release> -m \"My release comments\"\n"
                "\tEx: %prog ioc/xpp/vacuum -r R0.1.0 -m \"Adding baratron gauge\"\n"
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
    parser.add_option(	"-b", "--branch", dest="branch",
                        help="branch to release, "
                            "ex. $REPO/epics/branch/bugFix/ioc/cam/R0.2.1" )
    parser.add_option(	"-i", "--install", dest="installDir",
                        help="install directory, "
                            "ex. /reg/g/pcds/package/epics/3.14/base/R0.0.1" )
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

    repo         = None
    packageMatch = None
    packageName  = None

    # See if this is a git working dir
    ( git_url, git_branch, git_tag ) = gitGetWorkingBranch()

    if git_url:
        if opt.verbose:
            print "git_url:    %s" % git_url
            print "git_branch: %s" % git_branch
        # Create a git release handler
        repo = gitRepo.gitRepo( git_url, git_branch, opt.release )
        if git_tag == opt.release:
            opt.noTag = True
            opt.noTestBuild	= True
        packageMatch = re.match( r"\S+(epics/)(\S+).git", git_url )
        if packageMatch:
            packageName = packageMatch.group(2)
    else:
        # See if this is an svn working dir
        ( svn_url, svn_branch, svn_tag ) = svnGetWorkingBranch()

        if svn_url:
            if opt.verbose:
                print "svn_url:    %s" % svn_url
                print "svn_branch: %s" % svn_branch
            # Create an svn release handler
            repo = svnRepo.svnRepo( svn_url, svn_branch, opt.release )
        packageMatch = re.match( r"\S+(epics/|epics/trunk)(\S+)/current", svn_url )
        if packageMatch:
            packageName = packageMatch.group(2)

    if len(args) > 0:
        if not packageName:
            packageName = args[0]
        elif packageName != args[0]:
            packageName = args[0]
            raise ValidateError, ( "TODO: Need to find repo for manually specified package!" )

    if not packageName:
        raise ValidateError, ( "No package specified and unable to determine it from current dir" )
    elif opt.verbose:
        print "package:    %s" % packageName

    # Have to have a repo to do a release
    if repo is None:
        raise ValidateError, ( "Can't establish a repo branch" )

    rel = Releaser( repo, packageName, verbose=opt.verbose )

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
    ValidateArgs( repo, packageName, opt )

    if not opt.installDir:
        if not packageName:
            raise ValidateError, "No release package specified"
        if os.path.split( packageName )[0] == 'modules':
            epics_base_ver = determine_epics_base_ver()
            if not epics_base_ver:
                raise ValidateError, "Unable to determine EPICS base version"
            opt.installDir = os.path.join(	defaultEpicsSiteTop, epics_base_ver,
                                            packageName, opt.release	)
        else:
            opt.installDir = os.path.join(	defaultEpicsSiteTop, packageName, opt.release )

    print "repo_url:    %s" % repo.GetUrl()
    print "tag:         %s" % opt.release
    if opt.rmBuild:
        print "rm buildDir: %s"	% opt.installDir
    else:
        print "installDir:  %s"	% opt.installDir
    if opt.rmTag:
        print "rm tag:  %s" % ( rel._ReleaseTag )
    if	opt.noTag:
        opt.noTestBuild	= True

    # Confirm buildDir, installDir, and tag
    if not opt.batch and not opt.dryRun:
        confirmResp = raw_input( 'Proceed (Y/n)?' )
        if len(confirmResp) != 0 and confirmResp != "Y" and confirmResp != "y":
            sys.exit(0)

    # dryRun, just show release info
    if opt.dryRun:
        print "DryRun:"
        print "  branch:     %s" % opt.branch
        print "  installDir: %s" % opt.installDir
        print "  message:  \n%s" % opt.message

    if opt.rmBuild or opt.rmTag:
        if opt.rmBuild:
            try:
                rel.RemoveBuild( opt.installDir )
            except BuildError, e:
                print e
                pass
        if opt.rmTag:
            rel.RemoveTag()

        # Remove options do not try to do
        # a release, so exit now
        sys.exit(0)

    if opt.dryRun:
        sys.exit(0)

    #
    # Proceed with the release
    #

    # Do a test build first
    if not opt.noTestBuild:
        rel.DoTestBuild()

    # release tag
    if not opt.noTag:
        rel.TagRelease( )

    # Install package
    # rel.InstallPackage( repo_installDir	)
    rel.InstallPackage( )

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
