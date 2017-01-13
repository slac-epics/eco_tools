import re
import sys
import shutil
import tempfile
import os
import subprocess
import Repo
import gitRepo
import svnRepo
from git_utils import *
from svn_utils import *

class BuildError( Exception ):
    pass

class ValidateError( Exception ):
    pass

class InstallError( Exception ):
    pass

class Releaser(object):
    '''class Releaser( repo, package )
    repo must be a repo object that knows the URL, branch, tag, etc needed to checkout the required package version
    package is the name of the package and release, for example: base/R3.15.4-1.0, asyn/R4.29-0.1.3, edm/R1.12.96, etc
    Note: There are a number of additional arguments to __init__(), all w/ defaults
    These were grandfathered in as part of refactoring a prior version and may be
    more appropriately made into function parameters or in some cases may not be needed at all. 
    '''
    def __init__( self, repo, package, installDir=None, branch=None, noTag=True, debug=False, verbose=True, keepTmp=False, message=None, dryRun=False, quiet=False, batch=False ):
        self._installDir= installDir
        self._repo		= repo
        self._branch	= branch
        self._package	= package
        self._version	= ""
        self._dryRun	= dryRun
        self._batch		= batch
        self._debug		= debug
        self._quiet		= quiet
        self._verbose	= verbose
        self._message	= message
        self._keepTmp	= keepTmp
        self._noTag		= noTag
        self._ReleasePath= None
        self._retcode	= 0
        # Create a directory where files will be checked-out
        self.tmpDir		= tempfile.mktemp("-epics-release")
        self.grpowner	= None

    def __del__( self ):
        self.DoCleanup( 0 )

    def DoCleanup( self, errCode = 0 ):
        self._retcode = errCode
        if self._debug and self._retcode != 0:
            traceback.print_tb(sys.exc_traceback)
            print "%s exited with return code %d." % (sys.argv[0], retcode)

        if self._keepTmp:
            if os.path.exists(self.tmpDir):
                print "\n--keepTmp flag set. Remove the tmp build directory manually:"
                print "\t%s" % (self.tmpDir)
        else:
            if self._verbose:
                print "Cleaning up temporary files ..."
            sys.stdout.flush()
            try:
                sys.stdout.flush()
                if os.path.exists(self.tmpDir):
                    if self._verbose:
                        print "rm -rf", self.tmpDir
                    shutil.rmtree( self.tmpDir )
            except:
                print "failed:\n%s." % (sys.exc_value)
                print "\nCould not remove the following directories, remove them manually:"
                if os.path.exists(self.tmpDir):
                    print "\t%s" % (self.tmpDir)
    
    def RemoveTag( self ):
        return self._repo.RemoveTag( self._package, self._repo._tag )
    
    def TagRelease( self ):
        return self._repo.TagRelease( self._package, self._repo._tag, self._branch, self._message )

    def execute( self, cmd, outputPipe = subprocess.PIPE ):
        if self._verbose or self._dryRun:
            print "%s: %s" % ( ("--dryRun--" if self._dryRun else "EXEC"), cmd )
        if self._dryRun:
            return "--dryRun--"
        proc = subprocess.Popen( cmd, shell = True, executable = "/bin/bash",
                                stdout = outputPipe, stderr = outputPipe )
        (proc_stdout, proc_stderr) = proc.communicate( )
        if self._debug:
            print "process returned", proc.returncode
        if proc.returncode != 0:
            errMsg = "Command Failed: %s\n" % ( cmd )
            if proc_stdout:
                errMsg += proc_stdout
            if proc_stderr:
                errMsg += proc_stderr
            errMsg += "Return Code: %d\n" % ( proc.returncode )
            raise RuntimeError, errMsg
        return proc_stdout

    def RemoveBuild( self, buildDir ):
        print "\nRemoving build dir: %s ..." % ( buildDir )
        if rel._dryRun:
            return

        # Make sure we can write to the build directory
        try:
            self.execute("chmod -R u+w %s" % ( buildDir ))
        except OSError:
            raise BuildError, "Cannot make build dir writeable: %s" % ( buildDir )
        except RuntimeError:
            raise BuildError, "Build dir not found: %s" % ( buildDir )
        try:
            self.execute("/bin/rm -rf %s" % ( buildDir ))
        except OSError:
            raise BuildError, "Cannot remove build dir: %s" % ( buildDir )
        except RuntimeError:
            raise BuildError, "Build dir not found: %s" % ( buildDir )
        print "Successfully removed build dir: %s ..." % ( buildDir )

    def BuildRelease( self, buildBranch, buildDir, outputPipe = subprocess.PIPE ):
        # os.environ["EPICS_SITE_TOP"] = self._prefix
        if not buildDir:
            raise BuildError, "Build dir not defined!"
        if self._verbose:
            print "BuildRelease: Checking for buildDir %s" % buildDir
        if not os.path.exists( buildDir ):
            try:
                if self._dryRun:
                    print "os.makedirs %s drwxrwxr-x" % buildDir
                else:
                    os.makedirs( buildDir, 0775 )
            except OSError:
                raise BuildError, "Cannot create build dir: %s" % ( buildDir )

        # Make sure we can write to the build directory
        try:
            self.execute( "chmod -R u+w %s" % ( buildDir ) )
        except OSError:
            raise BuildError, "Cannot make build dir writeable: %s" % ( buildDir )

        try:
            # Checkout release to build dir
            self._repo.CheckoutRelease( buildDir, verbose=self._verbose, dryRun=self._dryRun )
        except RuntimeError, e:
            print e
            raise BuildError, "BuildRelease: FAILED"
        except RuntimeError, e:
            print e
            raise BuildError, "BuildRelease: FAILED"

        # Build release
        outputPipe = None
        if self._quiet:
            outputPipe = subprocess.PIPE
        try:
            print "Building Release in %s ..." % ( buildDir )
            buildOutput = self.execute( "make -C %s" % buildDir, outputPipe )
            if self._debug:
                print "BuildRelease: SUCCESS"
        except RuntimeError, e:
            print e
            raise BuildError, "BuildRelease: FAILED"

    def DoTestBuild( self ):
        try:
            self.BuildRelease( self._branch, self.tmpDir )
            self.DoCleanup()
        except BuildError:
            self.DoCleanup()
            raise

    def InstallPackage( self, installTop=None ):
        if self._verbose:
            #print self._repo
            print "\nInstallPackage: installTop: %s" % installTop
            self._repo.ShowRepo( titleLine="InstallPackage: Repo", prefix="	" )
            print "InstallPackage: _branch:    %s" % self._branch
            print "InstallPackage: _package:   %s" % self._package
            #print "InstallPackage: _version:   %s" % self._version

        if not self._installDir:
            if not installTop:
                print "InstallPackage Error: Unable to determine installDir!"
                return
            self._installDir = os.path.join( installTop, self._package )

        if self._installDir.startswith( DEF_EPICS_TOP_PCDS ):
            self.grpowner = DEF_PCDS_GROUP_OWNER

        if self._verbose:
            print "InstallPackage: Installing to %s" % self._installDir
        self.BuildRelease( self._ReleasePath, self._installDir )

        print "Fixing permissions ...",
        sys.stdout.flush()
        try:
            self.execute( 'find %s -type f -execdir chmod a-w  {} +' % ( self._installDir ) )
            self.execute( 'find %s -type d -execdir chmod ug+w {} +' % ( self._installDir ) )
            groups = self.execute("id")
            if self.grpowner:
                if re.search( groups, self.grpowner ):
                    self.execute("chgrp -R %s %s" % ( self.grpowner, self._installDir ))
            print "InstallPackage: Done fixing permissions."
        except:
            print "InstallPackage: Fixing permissions failed.\nERROR: %s." % ( sys.exc_value )
            pass

        print "Package %s installed to:\n%s" % ( self._package, self._installDir )

def find_release( package, verbose=False ):
    release = None
    ( package_name, package_release ) = os.path.split( package )
    (git_url, git_tag) = gitFindPackageRelease( package_name, package_release, debug=False, verbose=verbose )
    if git_url is not None:
        repo = gitRepo.gitRepo( git_url, None, git_tag )
        release = Releaser( repo, package, None, git_tag )
    if release is None:
        (svn_url, svn_branch, svn_tag) = svnFindPackageRelease( package_name, package_release, debug=False, verbose=verbose )
        if svn_url is not None:
            if verbose:
                print "find_release: Found svn_url=%s, svn_path=%s, svn_tag=%s" % ( svn_url, svn_branch, svn_tag )
            repo = svnRepo.svnRepo( svn_url, svn_branch, svn_tag )
            release = Releaser( repo, package )
    return release
