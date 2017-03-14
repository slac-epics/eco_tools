import re
import sys
import os
import subprocess

#import Releaser
import Repo
from repo_defaults import *
from cvs_utils import *

class cvsError( Exception ):
    pass

class cvsRepo( Repo.Repo ):
    def __init__( self, url, branch=None, tag=None ):
        super(cvsRepo, self).__init__( url, branch, tag )
        self._version	= ""
        self._retcode	= 0
        self._cvsStub1	= DEF_cvs_STUB1
        self._cvsStub2	= DEF_cvs_STUB2
        self._cvsRepo	= DEF_cvs_REPO
        self._cvsTags	= DEF_cvs_TAGS
        # Make sure we have a valid EPICS_SITE_TOP
        defaultEpicsSiteTop = DEF_EPICS_TOP_LCLS 
        if not os.path.isdir( defaultEpicsSiteTop ):
            defaultEpicsSiteTop = DEF_EPICS_TOP_AFS
        if not os.path.isdir( defaultEpicsSiteTop ):
            raise Releaser.ValidateError, ( "Can't find EPICS_SITE_TOP at %s" % defaultEpicsSiteTop )
        self._prefix	= defaultEpicsSiteTop

#	def __repr__( self ):
#		return "cvsRepo"

    def __str__( self ):
        strRep =  super(cvsRepo, self).__str__()
        strRep += "%s prefix: %s" % ( self.__class__.__name__, self._prefix if self._prefix else 'None' )
        return strRep

    def GetWorkingBranch( self ):
        return cvsGetWorkingBranch()

    def FindPackageRelease( packageSpec, tag, debug = False, verbose = False ):
        (repo_url, repo_tag) = (None, None)
        (packagePath, sep, packageName) = packageSpec.rpartition('/')

        print "FindPackageRelease STUBBED: Need to find packagePath=%s, packageName=%s\n" % (packagePath, packageName)
        return (repo_url, repo_tag)

    def GetDefaultPackage( self, package, verbose=False ):
        # TODO: Is this function necessary any more?
        # Can we just return package?

        # See if we're in a package directory
        defaultPackage	= None
        ( cvs_url, cvs_branch, cvs_tag ) = cvsGetWorkingBranch()
        if not cvs_url:
            print "Current directory is not an cvs working dir!"
            return None

        branchHead	= cvs_url
        ( branchHead, branchTail ) = os.path.split( branchHead )
        # Prepend the tail to the defaultPackage
        if	len(defaultPackage) == 0:
            defaultPackage = branchTail
        else:
            defaultPackage = os.path.join( branchTail, defaultPackage )
        if verbose:
            print "package:        ", package
            print "defaultPackage: ", defaultPackage
            print "self._branch:   ", self._branch
            print "self._url:      ", self._url
            print "cvs_url:        ", cvs_url
        return defaultPackage

    def CheckoutRelease( self, buildDir, verbose=False, dryRun=False ):
        if verbose or dryRun:
            print "Checking out: %s\nto build dir: %s ..." % ( self._url, buildDir )
        outputPipe = None
        if verbose:
            outputPipe = subprocess.PIPE
        if dryRun:
            print "CheckoutRelease: --dryRun--"
            return
        try:
            cmdList = [ "cvs", "co", self._url, buildDir ]
            subprocess.check_call( cmdList, stdout=outputPipe, stderr=outputPipe )
        except RuntimeError:
            raise Releaser.BuildError, "CheckoutRelease: cvs co failed for %s %s" % ( self._url, buildDir )

    def RemoveTag( self, dryRun=True ):
        print "RemoveTag: Removing %s release tag %s ..." % ( self._package[0], self._tag )
        if dryRun:
            print "RemoveTag: --dryRun--"
            return
        cmdList = [ "cvs", "tag", "-d", self._tag ]
        subprocess.check_call( cmdList )
        print "Successfully removed release tag %s." % ( self._tag )

    def TagRelease( self, verbose=True, message="TODO: Set message for TagRelease", dryRun=False ):
        if verbose:
            print "Tagging release %s %s ..." % ( self._branch, self._tag )
        if dryRun:
            print "TagRelease: --dryRun--"
            return

        cmdList = [ "cvs", "tag", self._tag, self._branch ]
        subprocess.check_call( cmdList )

