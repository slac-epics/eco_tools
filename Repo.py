#import re
import sys
#import shutil
#import tempfile
import os
#import subprocess

class Repo(object):
    def __init__( self ):
        self._retcode	= 0
        # self.grpowner	= None

    def __del__( self ):
        self.DoCleanup( 0 )

    def DoCleanup( self, errCode = 0 ):
        self._retcode = errCode
        if self._retcode != 0:
            traceback.print_tb(sys.exc_traceback)
            print "%s exited with return code %d." % (sys.argv[0], retcode)

    def CheckoutRelease( self, buildBranch, buildDir ):
        print "\nPlease override Repo.CheckoutRelease() via a version control specific subclass."
        os.sys.exit()

    def RemoveTag( self ):
        print "\nPlease override Repo.RemoveTag() via a version control specific subclass."
        os.sys.exit()
    
    def TagRelease( self ):
        print "\nPlease override Repo.TagRelease() via a version control specific subclass."
        os.sys.exit()


