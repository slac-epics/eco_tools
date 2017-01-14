import re
import sys
import shutil
import tempfile
import os
import grp
import pwd
import stat
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
        self.grpOwner	= None

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
            try:
                sys.stdout.flush()
                sys.stderr.flush()
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

        # Enable write access to build directory
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

    def fixPermissions( self, dir ):
        if self._verbose:
            print "Fixing permissions for %s ..." % dir
        sys.stdout.flush()
        userId  = os.geteuid()
        groupId = -1
        groups  = subprocess.check_output( [ "id" ] ).splitlines()
        if self.grpOwner is not None:
            if re.search( groups, self.grpOwner ):
                groupId = grp.getgrname(self.grpOwner).gr_gid 

        fileMode = stat.S_IWUSR | stat.S_IWGRP \
                 | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        dirMode  = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH | fileMode
        for dirPath, dirs, files in os.walk(dir):
            pathStatus = os.stat( dirPath )
            if userId == pathStatus.st_uid:
                os.chmod( dirPath, pathStatus.st_mode | dirMode )
                if groupId >= 0 and groupId != pathStatus.st_gid:
                    os.chown( dirPath, -1, groupId )
            for fileName in files:
                filePath   = os.path.join( dirPath, fileName )
                pathStatus = os.stat( filePath )
                if userId == pathStatus.st_uid:
                    os.chmod( filePath, pathStatus.st_mode | fileMode )
                    if groupId >= 0 and groupId != pathStatus.st_gid:
                        os.chown( filePath, -1, groupId )

    def BuildRelease( self, buildBranch, buildDir, outputPipe = subprocess.PIPE ):
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
            sys.stdout.flush()
            sys.stderr.flush()
            print "Building Release in %s ..." % ( buildDir )
            buildOutput = self.execute( "make -C %s" % buildDir, outputPipe )
            if self._debug:
                print "BuildRelease: SUCCESS"
        except RuntimeError, e:
            print e
            raise BuildError, "BuildRelease: FAILED"

        sys.stdout.flush()
        sys.stderr.flush()
        self.fixPermissions( self._installDir )

    def DoTestBuild( self ):
        try:
            self.BuildRelease( self._branch, self.tmpDir )
            self.DoCleanup()
        except BuildError:
            self.DoCleanup()
            raise

    def InstallPackage( self, installTop=None ):
        '''Use InstallPackage to automatically dertermine the buildDir from installTop and the repo specs.
        If you already know where to build you can just call BuildRelease() directly.'''
        if self._verbose:
            self._repo.ShowRepo( titleLine="InstallPackage: " + self._package, prefix="	" )
            #print self._repo
            #print "\nInstallPackage: installTop: %s" % installTop
            #print "InstallPackage: _branch:    %s" % self._branch
            #print "InstallPackage: _package:   %s" % self._package
            #print "InstallPackage: _version:   %s" % self._version

        if not self._installDir:
            if not installTop:
                print "InstallPackage Error: Need valid installTop to determine installDir!"
                return
            self._installDir = os.path.join( installTop, self._package )

        if self._installDir.startswith( DEF_EPICS_TOP_PCDS ):
            self.grpOwner = DEF_PCDS_GROUP_OWNER

        self.BuildRelease( self._ReleasePath, self._installDir )
        if self._verbose:
            print "InstallPackage: %s installed to:\n%s" % ( self._package, os.path.realpath(self._installDir) )

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
    if release is None:
        print "find_release Error: Unable to find package %s in svn or git repos" % package
    return release
