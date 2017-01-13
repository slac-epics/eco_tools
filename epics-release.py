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

DEF_EPICS_TOP_PCDS	= "/reg/g/pcds/package/epics/3.14"
DEF_EPICS_TOP_LCLS	= "/afs/slac/g/lcls/epics"
DEF_EPICS_TOP_AFS	= "/afs/slac/g/pcds/package/epics/3.14"
DEF_LCLS_GROUP_OWNER= "lcls"
DEF_PCDS_GROUP_OWNER= "ps-pcds"
debugScript			= False


# TODO: Cleanup this function
def ValidateArgs( repo, package, verbose=False ):
    # validate the repo
    if not repo:
        raise ValidateError, "Repo not found for package %s" % (package)
    defaultPackage	= None
    ( repo_url, repo_branch, repo_tag ) = repo.GetWorkingBranch()
    if repo_url:
        if verbose:
            print "Releaser.ValidateArgs: repo_url    =", repo_url
            print "Releaser.ValidateArgs: repo_branch =", repo_branch
            print "Releaser.ValidateArgs: repo_tag    =", repo_tag
            print "Releaser.ValidateArgs: package     =", package
        defaultPackage = repo.GetDefaultPackage( package )

    if verbose:
        print "defaultPackage:", defaultPackage

    # If we have a defaultPackage from the working directory,
    # Check it against the other options
    if defaultPackage:
        if not package or not package[0]:
            package = [ defaultPackage ]

    # Determine the release package SVN URL
    if not self._branch:
        if not package or not package[0]:
            raise ValidateError, "No release package specified"
        if len( package ) > 1:
            raise ValidateError, "Multiple  release packages specified: %s" % (package)
        if repo_url:
            self._branch = repo_url
        else:
            self._branch = os.path.join(	self._repo, self._gitStub2,
                                                package[0], "current"	)
            if not gitPathExists( self._branch, self._opt.revision ):
                self._branch = os.path.join(self._repo, self._gitStub1,
                                                package[0], "current"	)

    # Make sure the release package exists
    if not gitPathExists( self._branch, self._opt.revision ):
        raise ValidateError, "Invalid git branch at rev %s\n\t%s" % (	self._opt.revision,
                                                                        self._branch )

    # validate release tag
    if not self._tag:
        raise ValidateError, "Release tag not specified (--release)"
    if not re.match( r"(R\d+(\.\d+)+-\d+\.\d+\.\d+)|(R\d+\.\d+\.\d+)", self._tag ):
        raise ValidateError, "%s is an invalid release tag: Must be R[<orig_release>-]<major>.<minor>.<bugfix>" % self._tag
    if not self._ReleasePath:
        if not package or not package[0]:
            raise ValidateError, "No release package specified"
        self._ReleasePath = os.path.join(	self._repo, self._gitRelDir,
                                            package[0], self._tag	)

    if self._noTag == False and gitPathExists( self._ReleasePath ):
        raise ValidateError, "SVN release tag already exists: %s" % ( self._ReleasePath )
#		try:
#			if gitPathExists( self._ReleasePath ):
#				raise ValidateError, "SVN release tag already exists: %s" % ( self._ReleasePath )
#		except:
#			pass
#		else:
#			raise ValidateError, "SVN release tag already exists: %s" % ( self._ReleasePath )

    # validate release directory
    if not os.path.exists(self._prefix):
        raise ValidateError, "Invalid release directory %s" % ( self._prefix )
    if not self._installDir:
        if not package or not package[0]:
            raise ValidateError, "No release package specified"
        self._installDir = os.path.join(self._prefix,
                                            package[0], self._tag	)

    # validate release message
    if not self._message:
        print "Please enter a release comment (end w/ ctrl-d on blank line):"
        comment = ""
        try:
            while True:
                line = raw_input()
                comment = "\n".join( [ comment, line ] ) 
        except EOFError:
            self._message = comment

    if self._message is None:
            raise ValidateError, "Release message not specified (-m)"

    if repo_url:
        # Check release branch vs working dir branch
        if self._branch != repo_url:
            print "Release branch: %s\nWorking branch: %s" % ( self._branch, repo_url )
            if not self._batch:
                confirmResp = raw_input( 'Release branch does not match working dir.  Proceed (Y/n)?' )
                if len(confirmResp) != 0 and confirmResp != "Y" and confirmResp != "y":
                    branchMsg = "Branch mismatch!\n"
                    raise ValidateError, branchMsg

    # validate self._grpowner	= DEF_LCLS_GROUP_OWNER
    if verbose:
        print "ValidateArgs: Success"
        print "  repo_url:    %s" % repo_url
        print "  branch:      %s" % self._branch
        print "  tag:         %s" % self._tag
        print "  releasePath: %s" % self._ReleasePath
        print "  installDir:  %s" % self._installDir
        print "  message:     %s" % self._message

# Entry point of the script. This is main()
try:
    # Make sure we have a valid EPICS_SITE_TOP
    defaultEpicsSiteTop = DEF_EPICS_TOP_LCLS 
    if not os.path.isdir( defaultEpicsSiteTop ):
        defaultEpicsSiteTop = DEF_EPICS_TOP_AFS
    if not os.path.isdir( defaultEpicsSiteTop ):
        raise ValidateError, ( "Can't find EPICS_SITE_TOP at %s" % defaultEpicsSiteTop )

    parser = optparse.OptionParser( usage="usage: %prog [options] [ <module> ] -r <release> -m \"My release comments\"\n\tEx: %prog ioc/xpp/vacuum -r R0.1.0 -m \"Adding baratron gauge\"\n\tFor help: %prog --help" )
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
    parser.add_option(	"", "--notag", dest="noTag", action="store_true",
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
    parser.add_option(	"", "--noTestBuild", dest="noTestBuild", action="store_true",
                        help="Skip test build" )
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

    # See if this is a git working dir
    ( git_url, git_branch, git_tag ) = gitGetWorkingBranch()

    repo = None
    if git_url:
        if opt.debug:
            print "git_url:    %s" % git_url
            print "git_branch: %s" % git_branch
            print "git_tag:    %s" % git_tag
        # Create a git release handler
        repo = gitRepo( git_url, git_branch, git_tag )

    else:
        # See if this is an svn working dir
        ( svn_url, svn_branch, svn_tag ) = svnGetWorkingBranch()

        if svn_url:
            if opt.debug:
                print "svn_url:    %s" % svn_url
                print "svn_branch: %s" % svn_branch
                print "svn_tag:    %s" % svn_tag
            # Create an svn release handler
            repo = svnRepo( svn_url, svn_branch, svn_tag )

    # Have to have a repo to do a release
    if repo is None:
        raise ValidateError, ( "Can't establish a repo branch" )

    rel = Releaser( repo, opt, args )

    # If removing old release, don't build or tag
    if	rel._opt.nukeRelease:
        rel._opt.rmBuild		= True
        rel._opt.rmTag			= True

    # Are we removing something?
    if	rel._opt.rmBuild or rel._opt.rmTag:
        # Removing stuff, no need to TestBuild or Tag
        rel._opt.noTestbuild	= True
        rel._opt.noTag			= True

    # Will we tag?
    if	rel._opt.noTag:
        # Not tagging, no need for msg or TestBuild
        rel._opt.noMsg			= True
        rel._opt.noTestBuild	= True

    # Check for valid arguments
    rel.ValidateArgs( )

    # Confirm buildDir, installDir, and tag
    if not rel._opt.batch and not rel._opt.dryRun:
        print "branch:       %s"	% rel._opt.branch
        if rel._opt.rmBuild:
            print "rm buildDir: %s"	% rel._opt.installDir
        else:
            print "installDir:  %s"	% rel._opt.installDir
        if rel._opt.rmTag:
            print "rm tag:  %s" % ( rel._ReleaseTag )
        confirmResp = raw_input( 'Proceed (Y/n)?' )
        if len(confirmResp) != 0 and confirmResp != "Y" and confirmResp != "y":
            sys.exit(0)

    # dryRun, just show release info
    if rel._opt.dryRun:
        print "DryRun:"
        print "  branch:     %s" % rel._opt.branch
        print "  installDir: %s" % rel._opt.installDir
        print "  message:  \n%s" % rel._opt.message

    if rel._opt.rmBuild or rel._opt.rmTag:
        if rel._opt.rmBuild:
            try:
                rel.RemoveBuild( rel._opt.installDir )
            except BuildError, e:
                print e
                pass
        if rel._opt.rmTag:
            rel.RemoveTag()

        # Remove options do not try to do
        # a release, so exit now
        sys.exit(0)

    if rel._opt.dryRun:
        sys.exit(0)

    #
    # Proceed with the release
    #

    # Do a test build first
    if not rel._opt.noTestBuild:
        rel.DoTestBuild()

    # release tag
    if not rel._opt.noTag:
        rel.TagRelease( )

    # Install package
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
