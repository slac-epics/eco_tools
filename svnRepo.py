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
    def __init__( self, url, branch=None, package=None, tag=None ):
        super(svnRepo, self).__init__( url, branch, package, tag )
        self.grpowner	= DEF_PCDS_GROUP_OWNER
        self._version	= ""
        self._retcode	= 0
        self._tagUrl	= None
        self._svnStub1	= DEF_SVN_STUB1
        self._svnStub2	= DEF_SVN_STUB2
        self._svnRepo	= DEF_SVN_REPO

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
        defStub1	= "/".join( [ self._svnRepo, self._svnStub1 ] )
        defStub2	= "/".join( [ self._svnRepo, self._svnStub2 ] )
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
        targetUrl = self._url
        if self._tagUrl:
            targetUrl = self._tagUrl
        if verbose or dryRun:
            print "Checking out: %s\nto build dir: %s ..." % ( targetUrl, buildDir )
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
            cmdOutput = subprocess.check_output( cmdList ).splitlines()
            if len(cmdOutput) == 1:
                curUrl = cmdOutput[0]
                if curUrl == targetUrl:
                    # TODO: Move this to a function that fixes permissions
                    # for all files/directories owned by userid
                    # Use args to control whether files should be
                    # made writable or not
                    try:
                        self.execute( "chmod -R u+w %s" % ( buildDir ) )
                    except OSError:
                        # Just pass till this is more robust
                        pass
                        #raise BuildError, "Cannot make build dir writeable: %s" % ( buildDir )
                    except RuntimeError:
                        raise

                    cmdList = [ "svn", "update", "." ]
                    cmdOutput = subprocess.check_output( cmdList ).splitlines()
                    self.execute("/bin/rm -f %s" % ( self.built_cookie_path() ))
                    os.chdir( curDir )
                    return
                else:
                    # Not the right url, remove the bad checkout
                    os.chdir( curDir )
                    self.execute( "/bin/rm -rf %s" % buildDir )

        if not os.path.isdir( os.path.join( buildDir, '.svn' ) ):
            try:
                cmdList = [ "svn", "co", targetUrl, buildDir ]
                subprocess.check_call( cmdList, stdout=outputPipe, stderr=outputPipe )
            except RuntimeError:
                raise Releaser.BuildError, "CheckoutRelease: svn co failed for %s %s" % ( targetUrl, buildDir )

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

    def RemoveTag( self, package=None, tag=None ):
        if not package:
            package = self._package
        if not tag:
            tag = self._tag
        print "RemoveTag: Removing %s release tag %s ..." % ( package, tag )

        tagPath	= "/".join( [ DEF_SVN_TAGS, package, tag ]  )
        svnComment = "Removing unwanted tag %s for %s" % ( tag, package ) 
        try:
            cmdList = [ "svn", "ls", tagPath ]
            cmdOutput = subprocess.check_output( cmdList, stderr=subprocess.STDOUT )
        except:
            print "tagPath %s not found." % ( tagPath )
            return

        cmdList = [ "svn", "rm", tagPath, "-m", svnComment ]
        subprocess.check_call( cmdList )
        print "Successfully removed %s release tag %s." % ( package, tag )

    def TagRelease( self, packagePath=None, release=None, branch=None, message=None, verbose=True, dryRun=False ):
        if branch is None:
            branch = self._branch
        if message is None:
            message = self._message
        if release is None:
            release = self._tag
        self._tagUrl	= "/".join( [ DEF_SVN_TAGS, packagePath, release ]  )

        try: # See if tag already exists
            cmdList = [ "svn", "ls", self._tagUrl ]
            cmdOutput = subprocess.check_output( cmdList, stderr=subprocess.STDOUT )
            print "%s/%s already tagged." % ( packagePath, release )
            return
        except:
            pass

        if dryRun:
            print "--dryRun--",
        if verbose:
            print "Tagging %s ..." % ( self._tagUrl )
        if dryRun:
            return
        releaseComment	= "Release %s: " % release
        if message:
            releaseComment += message
        releaseComment	+= "\n%s %s %s" % ( "svn cp", self._url, self._tagUrl )
        cmdList = [ "svn", "cp", "--parents", self._url, self._tagUrl, "-m", releaseComment ]
        subprocess.check_call( cmdList )

