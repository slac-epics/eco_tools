import re
import sys
import os
import shutil
import subprocess

import Repo
from git_utils import *
from site_utils import *
from version_utils import *
from repo_defaults import *

class gitError( Exception ):
    pass

class gitRepo( Repo.Repo ):
    def __init__( self, url, branch=None, package=None, tag=None ):
        super(gitRepo, self).__init__( url, branch, package, tag )

#	def __repr__( self ):
#		return "gitRepo"

    def __str__( self ):
        strRep =  super(gitRepo, self).__str__()
        #print __repr__(), "_gitRepo: ", _gitRepo
        return strRep

    def GetWorkingBranch( self ):
        return gitGetWorkingBranch()

    def GetDefaultPackage( self, package, verbose=False ):
        return package

    def GetTag( self ):
        return self._tag

    def CheckoutRelease( self, buildDir, verbose=True, quiet=False, dryRun=False, depth=None ):
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
            try:
                # See if the tag is already checked out
                # Get the current HEAD SHA
                os.chdir( buildDir )
                curSha = None
                cmdList = [ "git", "rev-parse", "HEAD" ]
                gitOutput = subprocess.check_output( cmdList ).splitlines()
                if len(gitOutput) == 1:
                    curSha = gitOutput[0]

                # Get the tag SHA
                tagSha = None
                cmdList = [ "git", "rev-parse", self._tag ]
                gitOutput = subprocess.check_output( cmdList ).splitlines()
                if len(gitOutput) == 1:
                    tagSha = gitOutput[0]

                # If they match, it's already checked out!
                if curSha == tagSha:
                    os.chdir( curDir )
                    return

            except RuntimeError, e:
                print e
                pass

            except subprocess.CalledProcessError, e:
                print e
                pass

        if not os.path.isdir( os.path.join( buildDir, '.git' ) ):
            try:
                if depth == -1:
                    # Default to shallow depth for tagged releases
                    if self._tag:
                        depth = DEF_GIT_RELEASE_DEPTH
                    else:
                        depth = None
                # Clone the repo
                cloneMasterRepo( self._url, buildDir, '', branch=self._tag, depth=depth )
                os.chdir( buildDir )
            except RuntimeError, e:
                print e
                os.chdir(curDir)
                raise gitError, "CheckoutRelease RuntimeError: Failed to clone %s to %s" % ( self._url, buildDir )
            except subprocess.CalledProcessError, e:
                print e
                os.chdir(curDir)
                raise gitError, "CheckoutRelease CalledProcessError: Failed to clone %s in %s" % ( self._url, buildDir )

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
            # Refresh the tags
            # TODO: May fail if git repo is read-only
            if verbose:
                print "CheckoutRelease running: git fetch origin refs/tags/%s" % self._tag
            cmdList = [ "git", "fetch", "origin", "refs/tags/" + self._tag ]
            subprocess.check_call( cmdList, stdout=outputPipe, stderr=outputPipe )

            tagSha = gitGetTagSha( self._tag )

            if branchSha and branchSha != tagSha:
                # Rename the branch to put it aside till we delete it later
                cmdList = [ "git", "branch", "-m", self._tag, 'obs-' + self._tag ]
                subprocess.check_call( cmdList, stdout=outputPipe, stderr=outputPipe )

            # Checkout the tag
            #cmdList = [ "git", "checkout", '-q', 'refs/tags/%s' % self._tag ]
            cmdList = [ "git", "checkout", '-q', self._tag ]
            subprocess.check_call( cmdList, stdout=outputPipe, stderr=outputPipe )

            if branchSha != tagSha:
                if branchSha:
                    # Delete the obsolete branch
                    cmdList = [ "git", "branch", "-D", 'obs-' + self._tag ]
                    subprocess.check_call( cmdList, stdout=outputPipe, stderr=outputPipe )

                # Create a branch from the tag for easier status checks if it doesn't already exist
                # or if the old one didn't match the tag
                #cmdList = [ "git", "checkout", '-b', self._tag ]
                #subprocess.check_call( cmdList, stdout=outputPipe, stderr=outputPipe )

            # See if a RELEASE_SITE file needs to be provided
            if not os.path.isfile( 'RELEASE_SITE'):
                useDotDotRelease = (	hasIncludeDotDotReleaseSite()
                                    and	os.path.isfile( os.path.join( '..', '..', 'RELEASE_SITE' ) ) )
                if	(		not isBaseTop(		'.' )
                        and		isEpicsPackage( '.' )
                        and not useDotDotRelease ):
                    inputs = assemble_release_site_inputs( batch=True )
                    export_release_site_file( inputs )

        except RuntimeError, e:
            print e
            os.chdir(curDir)
            raise gitError, "CheckoutRelease RuntimeError: Failed to checkout %s in %s" % ( self._tag, buildDir )
        except subprocess.CalledProcessError, e:
            print e
            os.chdir(curDir)
            raise gitError, "CheckoutRelease CalledProcessError: Failed to checkout %s in %s" % ( self._tag, buildDir )
        os.chdir(curDir)

    def RemoveTag( self, package=None, tag=None, verbose=True, dryRun=False ):
        if not package:
            package = self._package
            tag = self._tag
        if verbose:
            print "\nRemoving %s release tag %s ..." % ( package, tag )
        cmdList = [ "git", "tag", "-d", tag ]
        subprocess.check_call( cmdList )
        print "Successfully removed %s release tag %s." % ( package, tag )

    def PushTag( self, release, verbose=True, dryRun=False ):
        if dryRun:
            print "--dryRun-- Push tag %s" % ( release )
            return

        if verbose:
            print "Pushing tag %s ..." % ( release )
        subprocess.check_call( [ 'git', 'push', 'origin', release ] )

    def TagRelease( self, packagePath=None, release=None, branch=None, message="", verbose=True, dryRun=False ):
        if release is None:
            release = self._tag
        if dryRun:
            print "--dryRun-- Tag %s release %s" % ( packagePath, release )
            return

        if verbose:
            print "Tagging %s release %s ..." % ( packagePath, release )
        comment = "Release %s/%s: %s" % ( packagePath, release, message )
        cmdList = [ "git", "tag", release, 'HEAD', "-m", comment ]
        subprocess.check_call( cmdList )
        subprocess.check_call( [ 'git', 'push', '-u', 'origin' ] )
        subprocess.check_call( [ 'git', 'push', 'origin', release ] )

