import re
import sys
#import shutil
#import optparse
#import traceback
#import tempfile
#import commands
#import stat
import os
import subprocess

import Releaser
from git_utils import *

DEF_SVN_REPO		= "file:///afs/slac/g/pcds/vol2/git/pcds"
DEF_SVN_MODULES		= DEF_SVN_REPO  + "/trunk/pcds/epics/modules"
DEF_SVN_STUB1		= "epics/trunk"
DEF_SVN_STUB2		= "trunk/pcds/epics"
DEF_SVN_REL_DIR		= "epics/tags"

# TODO: Move these to a common defaults file
DEF_EPICS_TOP_PCDS	= "/reg/g/pcds/package/epics/3.14"
DEF_EPICS_TOP_LCLS	= "/afs/slac/g/lcls/epics"
DEF_EPICS_TOP_AFS	= "/afs/slac/g/pcds/package/epics/3.14"
DEF_LCLS_GROUP_OWNER= "lcls"
DEF_PCDS_GROUP_OWNER= "ps-pcds"

class gitError( Exception ):
    pass

class gitReleaser( Releaser.Releaser ):
    def __init__( self, opt, args ):
        super(gitReleaser, self).__init__( opt, args )
        self.grpowner	= DEF_PCDS_GROUP_OWNER
        self._version	= ""
        self._retcode	= 0
        self._gitStub1	= DEF_SVN_STUB1
        self._gitStub2	= DEF_SVN_STUB2
        self._gitRepo	= DEF_SVN_REPO
        self._gitRelDir	= DEF_SVN_REL_DIR
        # Make sure we have a valid EPICS_SITE_TOP
        defaultEpicsSiteTop = DEF_EPICS_TOP_LCLS 
        if not os.path.isdir( defaultEpicsSiteTop ):
            defaultEpicsSiteTop = DEF_EPICS_TOP_AFS
        if not os.path.isdir( defaultEpicsSiteTop ):
            raise Releaser.ValidateError, ( "Can't find EPICS_SITE_TOP at %s" % defaultEpicsSiteTop )
        self._prefix	= defaultEpicsSiteTop

    def ValidateArgs( self ):
        # validate the module specification
        if self._package and "current" in self._package[0]:
            raise Releaser.ValidateError, "The module specification must not contain \"current\": %s" % (self._package[0])

        # See if we're in a package directory
        defaultPackage	= None
        ( git_url, git_branch, git_tag ) = gitGetWorkingBranch()
        if git_url:
            if self._opt.debug:
                print "git_url:", git_url
            branchHead	= git_url
            defStub1	= os.path.join( self._gitRepo, self._gitStub1 )
            defStub2	= os.path.join( self._gitRepo, self._gitStub2 )
            while branchHead != "":
                ( branchHead, branchTail ) = os.path.split( branchHead )
                if	defaultPackage is None:
                    # The first tail must be "current"
                    if branchTail != "current":
                        break
                    defaultPackage = ""
                    continue
                # Prepend the tail to the defaultPackage
                if	len(defaultPackage) == 0:
                    defaultPackage = branchTail
                else:
                    defaultPackage = os.path.join( branchTail, defaultPackage )

                # See if we're done
                if branchHead == defStub1:
                    break
                if branchHead == defStub2:
                    break
                if branchHead == "":
                    defaultPackage = ""
            if self._opt.debug:
                print "defaultPackage:", defaultPackage

        # If we have a defaultPackage from the working directory,
        # Check it against the other options
        if defaultPackage:
            if not self._package or not self._package[0]:
                self._package = [ defaultPackage ]

        # Determine the release package SVN URL
        if not self._opt.branch:
            if not self._package or not self._package[0]:
                raise Releaser.ValidateError, "No release package specified"
            if len( self._package ) > 1:
                raise Releaser.ValidateError, "Multiple  release packages specified: %s" % (self._package)
            if git_url:
                self._opt.branch = git_url
            else:
                self._opt.branch = os.path.join(	self._gitRepo, self._gitStub2,
                                                    self._package[0], "current"	)
                if not gitPathExists( self._opt.branch, self._opt.revision ):
                    self._opt.branch = os.path.join(self._gitRepo, self._gitStub1,
                                                    self._package[0], "current"	)

        # Make sure the release package exists
        if not gitPathExists( self._opt.branch, self._opt.revision ):
            raise Releaser.ValidateError, "Invalid git branch at rev %s\n\t%s" % (	self._opt.revision,
                                                                            self._opt.branch )

        # validate release tag
        if not self._opt.release:
            raise Releaser.ValidateError, "Release tag not specified (--release)"
        if not re.match( r"(R\d+(\.\d+)+-\d+\.\d+\.\d+)|(R\d+\.\d+\.\d+)", self._opt.release ):
            raise Releaser.ValidateError, "%s is an invalid release tag: Must be R[<orig_release>-]<major>.<minor>.<bugfix>" % self._opt.release
        if not self._ReleaseTag:
            if not self._package or not self._package[0]:
                raise Releaser.ValidateError, "No release package specified"
            self._ReleaseTag = os.path.join(	self._gitRepo, self._gitRelDir,
                                                self._package[0], self._opt.release	)

        if self._opt.noTag == False and gitPathExists( self._ReleaseTag ):
            raise Releaser.ValidateError, "SVN release tag already exists: %s" % ( self._ReleaseTag )
#		try:
#			if gitPathExists( self._ReleaseTag ):
#				raise Releaser.ValidateError, "SVN release tag already exists: %s" % ( self._ReleaseTag )
#		except:
#			pass
#		else:
#			raise Releaser.ValidateError, "SVN release tag already exists: %s" % ( self._ReleaseTag )

        # validate release directory
        if not os.path.exists(self._prefix):
            raise Releaser.ValidateError, "Invalid release directory %s" % ( self._prefix )
        if not self._opt.installDir:
            if not self._package or not self._package[0]:
                raise Releaser.ValidateError, "No release package specified"
            self._opt.installDir = os.path.join(self._prefix,
                                                self._package[0], self._opt.release	)

        # validate release message
        if not self._opt.message:
            if self._opt.noMsg:
                self._opt.message = ""
            else:
                print "Please enter a release comment (end w/ ctrl-d on blank line):"
                comment = ""
                try:
                    while True:
                        line = raw_input()
                        comment = "\n".join( [ comment, line ] ) 
                except EOFError:
                    self._opt.message = comment

        if self._opt.message is None:
                raise Releaser.ValidateError, "Release message not specified (-m)"

        if git_url:
            # Check release branch vs working dir branch
            if self._opt.branch != git_url:
                print "Release branch: %s\nWorking branch: %s" % ( self._opt.branch, git_url )
                if not self._opt.batch:
                    confirmResp = raw_input( 'Release branch does not match working dir.  Proceed (Y/n)?' )
                    if len(confirmResp) != 0 and confirmResp != "Y" and confirmResp != "y":
                        branchMsg = "Branch mismatch!\n"
                        raise Releaser.ValidateError, branchMsg

        # validate self._grpowner	= DEF_LCLS_GROUP_OWNER
        if self._opt.debug:
            print "ValidateArgs: Success"
            print "  gitrepo:    %s" % self._gitRepo
            print "  branch:     %s" % self._opt.branch
            print "  release:    %s" % self._opt.release
            print "  tag:        %s" % self._ReleaseTag
            print "  installDir: %s" % self._opt.installDir
            print "  message:    %s" % self._opt.message

    def CheckoutRelease( buildBranch, buildDir ):
        if self._opt.verbose:
            print "Checking out: %s\nto build dir: %s ..." % ( buildBranch, buildDir )
        outputPipe = None
        if self._opt.quiet:
            outputPipe = subprocess.PIPE
        try:
            self.execute( "git co %s %s" % ( buildBranch, buildDir ), outputPipe )
        except RuntimeError:
            raise Releaser.BuildError, "BuildRelease: git co failed for %s %s" % ( buildBranch, buildDir )

    def gitMakeDir( self, gitDir ):
        try:
            if self._gitRepo == gitDir:
                return
            if gitPathExists( gitDir ):
                return
            print "Creating SVN dir:", gitDir
            self.execute( "git mkdir --parents %s -m \"Creating release directory\"" % ( gitDir ) )
        except:
            raise gitError, "Error: gitMakeDir %s\n%s" % ( gitDir, sys.exc_value )

    def RemoveTag( self ):
        print "\nRemoving %s release tag %s ..." % ( self._package[0], self._opt.release )
        if rel._opt.dryRun:
            return
        self.gitMakeDir( os.path.split( self._ReleaseTag )[0] )
        gitRmTagCmd = "git rm %s" % ( self._ReleaseTag ) 
        self.execute( '%s -m "Removing unwanted tag %s for %s"' % ( gitRmTagCmd,
                            self._opt.release, self._package[0] ) ) 
        print "Successfully removed %s release tag %s." % ( self._package[0], self._opt.release )

    def TagRelease( self ):
        if self._opt.verbose:
            print "Tagging release ..."
        self.gitMakeDir( os.path.split( self._ReleaseTag )[0] )
        gitTagCmd = "git cp %s %s" % ( self._opt.branch, self._ReleaseTag ) 
        self.execute( '%s -m "Release %s/%s: %s\n%s"' % (	gitTagCmd,
                                                            self._package[0],	self._opt.release,
                                                            self._opt.message,	gitTagCmd ) ) 

