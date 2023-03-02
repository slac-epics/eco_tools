#import re
import sys
#import shutil
#import tempfile
import os
#import subprocess

class Repo(object):
    def __init__( self, url, branch=None, package=None, tag=None ):
        self._retcode	= 0
        self._url	    = url
        if branch is None:
            self._branch    = self.GetWorkingBranch()
        else:
            self._branch    = branch
        self._package   = None
        if package is str:
            self._package = os.path.split( package )[1]
        self._tag    	= tag
        # self.grpowner	= None

    def __del__( self ):
        self.DoCleanup( 0 )

    # Override in child class
    def GetWorkingBranch( self ):
        return None

    def DoCleanup( self, errCode = 0 ):
        self._retcode = errCode
        if self._retcode != 0:
            traceback.print_tb(sys.exc_traceback)
            print "%s exited with return code %d." % (sys.argv[0], retcode)

    def __repr__( self ):
        strRep =  '%s("%s",branch=%s,pkg=%s,tag=%s' % ( self.__class__.__name__, self._url, \
                ( '"%s"' % self._branch  if self._branch  else 'None' ) \
                ( '"%s"' % self._package if self._package else 'None' ) \
                ( '"%s"' % self._tag     if self._tag     else 'None' ) )
        return strRep

    def __str__( self ):
        strRep =  "%s URL:    %s\n" % ( self.__class__.__name__, self._url )
        strRep += "%s branch: %s\n" % ( self.__class__.__name__, self._branch if self._branch else 'None' )
        strRep += "%s tag:    %s\n" % ( self.__class__.__name__, self._tag    if self._tag else 'None' )
        return strRep

    def ShowRepo( self, titleLine=None, prefix="" ):
        if titleLine:
            print titleLine
        if not self._url:
            print "%sURL:    Not Set!" % ( prefix )
        else:
            print "%sURL:    %s" % ( prefix, self._url )
        if self._branch:
            print "%sbranch: %s" % ( prefix, self._branch )
        if self._tag:
            print "%stag:    %s" % ( prefix, self._tag )

    def CheckoutRelease( self, buildDir ):
        print "\nPlease override Repo.CheckoutRelease() via a version control specific subclass."
        os.sys.exit()

    def GetDefaultPackage( self, package, verbose=False ):
        print "\nPlease override Repo.GetDefaultPackage() via a version control specific subclass."
        os.sys.exit()

    def GetTag( self ):
        return self._tag

    def GetUrl( self ):
        return self._url

    def RemoveTag( self, tag=None ):
        print "\nPlease override Repo.RemoveTag() via a version control specific subclass."
        os.sys.exit()

    def TagRelease( self, packagePath=None, release=None, branch=None, message="", verbose=True, dryRun=False ):
        print "\nPlease override Repo.TagRelease() via a version control specific subclass."
        os.sys.exit()
