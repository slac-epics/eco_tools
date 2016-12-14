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
#	ioc/<ioc_name>		- IOC named ioc_name
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
	if git_url and opt.debug:
		print "git_url:    %s" % git_url
		print "git_branch: %s" % git_branch
		print "git_tag:    %s" % git_tag

	repo = None
	if git_url:
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
