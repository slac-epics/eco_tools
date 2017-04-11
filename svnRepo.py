import re
import sys
import os
import subprocess

#import Releaser
import Repo
from repo_defaults import *
from svn_utils import *

class svnError( Exception ):
    pass

class svnRepo( Repo.Repo ):
    def __init__( self, url, branch=None, tag=None ):
        super(svnRepo, self).__init__( url, branch, tag )
        self.grpowner	= DEF_PCDS_GROUP_OWNER
        self._version	= ""
        self._retcode	= 0
        self._svnStub1	= DEF_SVN_STUB1
        self._svnStub2	= DEF_SVN_STUB2
        self._svnRepo	= DEF_SVN_REPO
        self._svnTags	= DEF_SVN_TAGS
        # Make sure we have a valid EPICS_SITE_TOP
        #defaultEpicsSiteTop = DEF_EPICS_TOP_LCLS 
        #if not os.path.isdir( defaultEpicsSiteTop ):
        #	defaultEpicsSiteTop = DEF_EPICS_TOP_AFS
        #if not os.path.isdir( defaultEpicsSiteTop ):
        #	raise Releaser.ValidateError, ( "Can't find EPICS_SITE_TOP at %s" % defaultEpicsSiteTop )
        #self._prefix	= determine_epics_site_top()

#	def __repr__( self ):
#		return "svnRepo"

    def __str__( self ):
        strRep =  super(svnRepo, self).__str__()
        #strRep += "%s prefix: %s" % ( self.__class__.__name__, self._prefix if self._prefix else 'None' )
        return strRep

    def GetWorkingBranch( self ):
        return svnGetWorkingBranch()

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
        ( svn_url, svn_branch, svn_tag ) = svnGetWorkingBranch()
        if not svn_url:
            print "Current directory is not an svn working dir!"
            return None

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
        if verbose:
            print "package:        ", package
            print "defaultPackage: ", defaultPackage
            print "self._branch:   ", self._branch
            print "self._url:      ", self._url
            print "svn_url:        ", svn_url
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

        curDir = os.getcwd()
        if os.path.isdir( os.path.join( buildDir, '.svn' ) ):
            os.chdir( buildDir )

            # See if the tag is already checked out
            curTag = None
            cmdList = [ "svn", "info", "." ]
            gitOutput = subprocess.check_output( cmdList ).splitlines()
            if len(gitOutput) == 1:
                curUrl = gitOutput[0]
                if curUrl == self._url:
                    os.chdir( curDir )
                    return
        else:
            try:
                cmdList = [ "svn", "co", self._url, buildDir ]
                subprocess.check_call( cmdList, stdout=outputPipe, stderr=outputPipe )
            except RuntimeError:
                raise Releaser.BuildError, "CheckoutRelease: svn co failed for %s %s" % ( self._url, buildDir )

    def svnMakeDir( self, svnDir, dryRun=True ):
        try:
            if self._svnRepo == svnDir:
                return
            if svnPathExists( svnDir ):
                return
            print "Creating SVN dir:", svnDir
            if dryRun:
                print "svnMakeDir: --dryRun--"
                return
            svnComment = "Creating release directory"
            cmdList = [ "svn", "mkdir", "--parents", svnDir, "-m", svnComment ]
            subprocess.check_call( cmdList )
        except:
            raise svnError, "Error: svnMakeDir %s\n%s" % ( svnDir, sys.exc_value )

    def RemoveTag( self, dryRun=True ):
        print "RemoveTag: Removing %s release tag %s ..." % ( self._package[0], self._tag )
        if dryRun:
            print "RemoveTag: --dryRun--"
            return
        self.svnMakeDir( os.path.split( self._ReleaseTag )[0] )
        svnRmTagCmd = "svn rm %s" % ( self._ReleaseTag ) 
        svnComment = "Removing unwanted tag %s for %s" % ( svnRmTagCmd, self._tag, self._branch ) 
        cmdList = [ "svn", "rm", self._ReleaseTag, "-m", svnComment ]
        subprocess.check_call( cmdList )
        print "Successfully removed %s release tag %s." % ( self._branch, self._tag )

    def TagRelease( self, verbose=True, message="TODO: Set message for TagRelease", dryRun=False ):
        if verbose:
            print "Tagging release %s %s ..." % ( self._branch, self._tag )
        if dryRun:
            print "TagRelease: --dryRun--"
            return
        #self.svnMakeDir( os.path.split( self._ReleaseTag )[0] )
        releaseComment = "Release %s/%s: %s\n%s" % (	self._branch,	self._tag,
                                                        message,		"svn cp" )
        cmdList = [ "svn", "cp", self._branch, self._tag, self._branch, "-m", releaseComment ]
        subprocess.check_call( cmdList )

