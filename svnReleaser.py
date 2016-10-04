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
from svn_utils import *

DEF_SVN_REPO		= "file:///afs/slac/g/pcds/vol2/svn/pcds"
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

class svnError( Exception ):
    pass

class svnReleaser( Releaser.Releaser ):
    def __init__( self, opt, args ):
        super(svnReleaser, self).__init__( opt, args )
        self.grpowner	= DEF_PCDS_GROUP_OWNER
        self._version	= ""
        self._retcode	= 0
        self._svnStub1	= DEF_SVN_STUB1
        self._svnStub2	= DEF_SVN_STUB2
        self._svnRepo	= DEF_SVN_REPO
        self._svnRelDir	= DEF_SVN_REL_DIR
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
        ( svn_url, svn_branch, svn_tag ) = svnGetWorkingBranch()
        if svn_url:
            if self._opt.debug:
                print "svn_url:", svn_url
            branchHead	= svn_url
            defStub1	= os.path.join( self._svnRepo, self._svnStub1 )
            defStub2	= os.path.join( self._svnRepo, self._svnStub2 )
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
            if svn_url:
                self._opt.branch = svn_url
            else:
                self._opt.branch = os.path.join(	self._svnRepo, self._svnStub2,
                                                    self._package[0], "current"	)
                if not svnPathExists( self._opt.branch, self._opt.revision ):
                    self._opt.branch = os.path.join(self._svnRepo, self._svnStub1,
                                                    self._package[0], "current"	)

        # Make sure the release package exists
        if not svnPathExists( self._opt.branch, self._opt.revision ):
            raise Releaser.ValidateError, "Invalid svn branch at rev %s\n\t%s" % (	self._opt.revision,
                                                                            self._opt.branch )

        # validate release tag
        if not self._opt.release:
            raise Releaser.ValidateError, "Release tag not specified (--release)"
        if not re.match( r"(R\d+(\.\d+)+-\d+\.\d+\.\d+)|(R\d+\.\d+\.\d+)", self._opt.release ):
            raise Releaser.ValidateError, "%s is an invalid release tag: Must be R[<orig_release>-]<major>.<minor>.<bugfix>" % self._opt.release
        if not self._ReleaseTag:
            if not self._package or not self._package[0]:
                raise Releaser.ValidateError, "No release package specified"
            self._ReleaseTag = os.path.join(	self._svnRepo, self._svnRelDir,
                                                self._package[0], self._opt.release	)

        if self._opt.noTag == False and svnPathExists( self._ReleaseTag ):
            raise Releaser.ValidateError, "SVN release tag already exists: %s" % ( self._ReleaseTag )
#		try:
#			if svnPathExists( self._ReleaseTag ):
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

        if svn_url:
            # Check release branch vs working dir branch
            if self._opt.branch != svn_url:
                print "Release branch: %s\nWorking branch: %s" % ( self._opt.branch, svn_url )
                if not self._opt.batch:
                    confirmResp = raw_input( 'Release branch does not match working dir.  Proceed (Y/n)?' )
                    if len(confirmResp) != 0 and confirmResp != "Y" and confirmResp != "y":
                        branchMsg = "Branch mismatch!\n"
                        raise Releaser.ValidateError, branchMsg

        # validate self._grpowner	= DEF_LCLS_GROUP_OWNER
        if self._opt.debug:
            print "ValidateArgs: Success"
            print "  svnrepo:    %s" % self._svnRepo
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
            self.execute( "svn co %s %s" % ( buildBranch, buildDir ), outputPipe )
        except RuntimeError:
            raise Releaser.BuildError, "BuildRelease: svn co failed for %s %s" % ( buildBranch, buildDir )

    def svnMakeDir( self, svnDir ):
        try:
            if self._svnRepo == svnDir:
                return
            if svnPathExists( svnDir ):
                return
            print "Creating SVN dir:", svnDir
            self.execute( "svn mkdir --parents %s -m \"Creating release directory\"" % ( svnDir ) )
        except:
            raise svnError, "Error: svnMakeDir %s\n%s" % ( svnDir, sys.exc_value )

    def RemoveTag( self ):
        print "\nRemoving %s release tag %s ..." % ( self._package[0], self._opt.release )
        if rel._opt.dryRun:
            return
        self.svnMakeDir( os.path.split( self._ReleaseTag )[0] )
        svnRmTagCmd = "svn rm %s" % ( self._ReleaseTag ) 
        self.execute( '%s -m "Removing unwanted tag %s for %s"' % ( svnRmTagCmd,
                            self._opt.release, self._package[0] ) ) 
        print "Successfully removed %s release tag %s." % ( self._package[0], self._opt.release )

    def TagRelease( self ):
        if self._opt.verbose:
            print "Tagging release ..."
        self.svnMakeDir( os.path.split( self._ReleaseTag )[0] )
        svnTagCmd = "svn cp %s %s" % ( self._opt.branch, self._ReleaseTag ) 
        self.execute( '%s -m "Release %s/%s: %s\n%s"' % (	svnTagCmd,
                                                            self._package[0],	self._opt.release,
                                                            self._opt.message,	svnTagCmd ) ) 

