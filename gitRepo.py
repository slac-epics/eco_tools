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
        super(gitRepo, self).__init__( url, branch, tag )
        #self.grpowner	= DEF_PCDS_GROUP_OWNER
        #self._version	= ""
        #self._retcode	= 0
        #self._url       = url
        #self._branch    = branch
        #self._tag       = tag
        #self._gitRepo	= determineGitRoot()

#	def __repr__( self ):
#		return "gitRepo"

    def __str__( self ):
        strRep =  super(svnRepo, self).__str__()
        strRep += "%s prefix: %s" % ( self.__class__.__name__, self._prefix if self._prefix else 'None' )
        #print __repr__(), "_gitRepo: ", _gitRepo
        return strRep

    def GetWorkingBranch( self ):
        return gitGetWorkingBranch()

    def GetDefaultPackage( self, package ):
        return package

    def GetTag( self ):
        return self._tag

    def CheckoutRelease( self, buildDir, verbose=True, quiet=False, dryRun=False ):
        if verbose:
            print "Checking out: %s\nto build dir: %s ..." % ( self._url, buildDir )
        if dryRun:
            print "CheckoutRelease: --dryRun--"
            return

        outputPipe = None
        if quiet:
            outputPipe = subprocess.PIPE

        curDir = os.getcwd()
        if os.path.isdir( os.path.join( buildDir, '.git' ) ):
            os.chdir( buildDir )
        else:
            try:
                # Clone the repo
                cmdList = [ "git", "clone", self._url, buildDir ]
                subprocess.check_call( cmdList, stdout=outputPipe, stderr=outputPipe )
                os.chdir( buildDir )
            except RuntimeError, e:
                print e
                os.chdir(curDir)
                raise gitError, "BuildRelease RuntimeError: Failed to clone %s to %s" % ( self._url, buildDir )
            except subprocess.CalledProcessError, e:
                print e
                os.chdir(curDir)
                raise gitError, "BuildRelease CalledProcessError: Failed to clone %s in %s" % ( self._url, buildDir )

        # See if we've already created a branch for this tag
        branchSha = None
        try:
            cmdList = [ "git", "show-ref", '-s', 'refs/heads/%s' % self._tag ]
            gitOutput = subprocess.check_output( cmdList ).splitlines()
            if len(gitOutput) == 1:
                branchSha = gitOutput[0]
        except subprocess.CalledProcessError, e:
            pass

        try:
            # Fetch the tag
            cmdList = [ "git", "fetch", "origin", self._tag ]
            subprocess.check_call( cmdList, stdout=outputPipe, stderr=outputPipe )

            # Get the tagSha
            tagSha = None
            cmdList = [ "git", "show-ref", '-s', 'refs/tags/%s' % self._tag ]
            gitOutput = subprocess.check_output( cmdList ).splitlines()
            if len(gitOutput) == 1:
                tagSha = gitOutput[0]

            if branchSha and branchSha != tagSha:
                # Rename the branch to put it aside till we delete it later
                cmdList = [ "git", "branch", "-m", self._tag, 'obs-' + self._tag ]
                subprocess.check_call( cmdList, stdout=outputPipe, stderr=outputPipe )

            # Checkout the tag
            cmdList = [ "git", "checkout", 'refs/tags/%s' % self._tag ]
            subprocess.check_call( cmdList, stdout=outputPipe, stderr=outputPipe )

            if branchSha != tagSha:
                if branchSha:
                    # Delete the obsolete branch
                    cmdList = [ "git", "branch", "-D", 'obs-' + self._tag ]
                    subprocess.check_call( cmdList, stdout=outputPipe, stderr=outputPipe )

                # Create a branch from the tag for easier status checks if it doesn't already exist
                # or if the old one didn't match the tag
                cmdList = [ "git", "checkout", '-b', self._tag ]
                subprocess.check_call( cmdList, stdout=outputPipe, stderr=outputPipe )

        except RuntimeError, e:
            print e
            os.chdir(curDir)
            raise gitError, "BuildRelease RuntimeError: Failed to checkout %s in %s" % ( self._tag, buildDir )
        except subprocess.CalledProcessError, e:
            print e
            os.chdir(curDir)
            raise gitError, "BuildRelease CalledProcessError: Failed to checkout %s in %s" % ( self._tag, buildDir )
        os.chdir(curDir)

    def RemoveTag( self, package, release, verbose=True, dryRun=True ):
        if verbose:
            print "\nRemoving %s release tag %s ..." % ( package, release )
        if dryRun:
            print "RemoveTag: --dryRun--"
            return
        comment = "Removing unwanted tag %s for %s" % ( gitRmTagCmd, release, package )
        cmdList = [ "git", "tag", "-d", release ]
        subprocess.check_call( cmdList )
        print "Successfully removed %s release tag %s." % ( package, release )

    def TagRelease( self, package, release, branch=None, message="", verbose=True, dryRun=True ):
        if verbose:
            print "Tagging release %s %s ..." % ( self._branch, self._tag )
        if dryRun:
            print "TagRelease: --dryRun--"
            return
        comment = "Release %s/%s: %s" % ( package, release, message )
        cmdList = [ "git", "tag", release, "-m", comment ]
        subprocess.check_call( cmdList )

