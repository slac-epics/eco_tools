import re
import sys
import os
import subprocess

import Repo
from git_utils import *


# TODO: Move these to a common defaults file
DEF_EPICS_TOP_PCDS	= "/reg/g/pcds/package/epics/3.14"
DEF_EPICS_TOP_LCLS	= "/afs/slac/g/lcls/epics"
DEF_EPICS_TOP_AFS	= "/afs/slac/g/pcds/package/epics/3.14"
DEF_LCLS_GROUP_OWNER= "lcls"
DEF_PCDS_GROUP_OWNER= "ps-pcds"

class gitError( Exception ):
    pass

class gitRepo( Repo.Repo ):
    def __init__( self, url, branch=None, tag=None ):
        super(gitRepo, self).__init__( )
        #self.grpowner	= DEF_PCDS_GROUP_OWNER
        #self._version	= ""
        #self._retcode	= 0
        self._url       = url
        self._branch    = branch
        self._tag       = tag
        self._gitRepo	= determineGitRoot()

    def GetWorkingBranch( self ):
        return gitGetWorkingBranch()

    def GetDefaultPackage( self, package ):
        return package

    def GetTag( self ):
        return self._tag

    def CheckoutRelease( self, buildBranch, buildDir, verbose=False, quiet=False ):
        if verbose:
            print "Checking out: %s\nto build dir: %s ..." % ( buildBranch, buildDir )
        outputPipe = None
        if quiet:
            outputPipe = subprocess.PIPE
        try:
            self.execute( "git co %s %s" % ( buildBranch, buildDir ), outputPipe )
        except RuntimeError:
            raise Releaser.BuildError, "BuildRelease: git co failed for %s %s" % ( buildBranch, buildDir )

    def RemoveTag( self, package, release, verbose=True, dryRun=False ):
        if verbose:
            print "\nRemoving %s release tag %s ..." % ( package, release )
        if dryRun:
            return
        gitRmTagCmd = "git rm %s" % ( release ) 
        self.execute( '%s -m "Removing unwanted tag %s for %s"' % ( gitRmTagCmd,
                            release, package ) ) 
        print "Successfully removed %s release tag %s." % ( package, release )

    def TagRelease( self, package, release, branch=None, message="", verbose=False ):
        if verbose:
            print "Tagging release ..."
        gitTagCmd = "git tag %s" % ( release ) 
        self.execute( '%s -m "Release %s/%s: %s"' % (	gitTagCmd, package,	release, message ) ) 

