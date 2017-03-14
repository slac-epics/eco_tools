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
from version_utils import *

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
        self._EpicsHostArch = determine_epics_host_arch()
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
            try:
                sys.stdout.flush()
                sys.stderr.flush()
                if os.path.exists(self.tmpDir):
                    if self._verbose:
                        print "Removing temporary dir %s ..." % self.tmpDir
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
        groups  = subprocess.check_output( [ "id" ] )
        if self.grpOwner is not None:
            if re.search( groups, self.grpOwner ):
                groupId = grp.getgrname(self.grpOwner).gr_gid 

        # Make sure directories are able to be read and traversed
        # and leave them writable so we can build on a new host
        # without having to fix permissions for directories that
        # might be owned by someone else who created the initial release.
        dirModeAllow = stat.S_IWUSR | stat.S_IWGRP | \
                       stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH	| \
                       stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        # Deny write access to files
        fileModeDeny = stat.S_IWUSR | stat.S_IWGRP
        for dirPath, dirs, files in os.walk(dir):
            pathStatus = os.stat( dirPath )
            if userId == pathStatus.st_uid:
                os.chmod( dirPath, pathStatus.st_mode | dirModeAllow )
                if groupId >= 0 and groupId != pathStatus.st_gid:
                    os.chown( dirPath, -1, groupId )
            for fileName in files:
                filePath   = os.path.join( dirPath, fileName )
                pathStatus = os.stat( filePath )
                if userId == pathStatus.st_uid:
                    os.chmod( filePath, pathStatus.st_mode & ~fileModeDeny )
                    if groupId >= 0 and groupId != pathStatus.st_gid:
                        os.chown( filePath, -1, groupId )

    def built_cookie_path( self ):
        return os.path.join( self._ReleasePath, "configure", "O." + self._EpicsHostArch, ".is_built" )

    def hasBuilt( self ):
        '''Returns True if module has built for any architecture.'''
        hasBuilt = False
        try:
            findOutput = subprocess.check_output( [ "find", self._ReleasePath, "-name", ".is_built" ] ).splitlines()
            if len(findOutput) > 0:
                hasBuilt = True
        except:
            pass
        return hasBuilt

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
        # Shouldn't have to do this now that we leave directories writable
        # Won't work unless userid matches so need to check before trying
        #try:
        #	self.execute( "chmod -R u+w %s" % ( buildDir ) )
        #except OSError:
        #	raise BuildError, "Cannot make build dir writeable: %s" % ( buildDir )

        if	self._ReleasePath != buildDir:
            self._ReleasePath =  buildDir

        try:
            # Checkout release to build dir
            self._repo.CheckoutRelease( buildDir, verbose=self._verbose, dryRun=self._dryRun )
        except RuntimeError, e:
            print e
            raise BuildError, "BuildRelease: FAILED"
        except gitRepo.gitError, e:
            print e
            raise BuildError, "BuildRelease: FAILED"

        if self._verbose:
            print "BuildRelease: Checking built cookie %s" % ( self.built_cookie_path() )
        if os.path.isfile( self.built_cookie_path() ):
            if self._verbose:
                print "BuildRelease %s: Already built!" % ( buildDir )
            return

        # See if it's built for any architecture
        hasBuilt = self.hasBuilt()

        # Build release
        outputPipe = None
        if self._quiet:
            outputPipe = subprocess.PIPE
        try:
            sys.stdout.flush()
            sys.stderr.flush()
            print "Building Release in %s ..." % ( buildDir )
            buildOutput = self.execute( "make -C %s" % buildDir, outputPipe )
            self.execute( "touch %s" % self.built_cookie_path() )
            if self._verbose:
                print "BuildRelease %s: SUCCESS" % ( buildDir )
        except RuntimeError, e:
            print e
            if hasBuilt == False:
                self.execute( "mv %s %s-FAILED" % ( buildDir, buildDir ) )
                buildDir += "-FAILED"
            raise BuildError, "BuildRelease FAILED in %s" % ( buildDir )

        sys.stdout.flush()
        sys.stderr.flush()
        self.fixPermissions( buildDir )

    def DoTestBuild( self ):
        try:
            self.BuildRelease( self._ReleasePath, self.tmpDir )
            self.DoCleanup()
        except BuildError:
            print "DoTestBuild: %s Build error from BuildRelease in %s" % ( self._package, self.tmpDir )
            self.DoCleanup()
            raise
        except subprocess.CalledProcessError, e:
            print "DoTestBuild: %s CalledProcessError from BuildRelease in %s" % ( self._package, self.tmpDir )
            print e
            pass

    def InstallPackage( self, installTop=None ):
        '''Use InstallPackage to automatically determine the buildDir from installTop and the repo specs.
        If you already know where to build you can just call BuildRelease() directly.'''
        if self._verbose:
            self._repo.ShowRepo( titleLine="InstallPackage: " + self._package, prefix="	" )

        if not self._installDir:
            epics_site_top	= determine_epics_site_top()
            if not installTop and not epics_site_top:
                print "InstallPackage Error: Need valid installTop to determine installDir!"
                return
            if not installTop:
                if		os.path.split( self._package )[0] == 'modules' \
                     or	self._repo.GetUrl().find('modules') >= 0:
                    # TODO: Get BASE_MODULE_VERSION or EPICS_BASE_VER from env
                    epics_base_ver = determine_epics_base_ver()
                    installTop = os.path.join( epics_site_top, epics_base_ver, 'modules' )

            if not installTop:
                print "InstallPackage Error: Unable to determine installTop!"
                return
            cmdList = [ "readlink", "-e", installTop ]
            cmdOutput = subprocess.check_output( cmdList ).splitlines()
            if len(cmdOutput) == 1:
                installTop = cmdOutput[0]
            if not os.path.isdir( installTop ):
                print "InstallPackage Error: Invalid installTop:", installTop
                return

            moduleName = os.path.split( self._package )[-1]
            self._installDir = os.path.join( installTop, moduleName, self._repo.GetTag() )

        if self._installDir.startswith( DEF_EPICS_TOP_PCDS ):
            self.grpOwner = DEF_PCDS_GROUP_OWNER

        try:
            self.BuildRelease( self._ReleasePath, self._installDir )
            if self._verbose:
                print "InstallPackage: %s installed to:\n%s" % ( self._package, os.path.realpath(self._installDir) )
        except BuildError, e:
            print "InstallPackage: %s Build error from BuildRelease in %s" % ( self._package, os.path.realpath(self._installDir) )
            print e
            pass
        except subprocess.CalledProcessError, e:
            print "InstallPackage: %s CalledProcessError from BuildRelease in %s" % ( self._package, os.path.realpath(self._installDir) )
            print e
            pass

def find_release( package, verbose=False ):
    release = None
    ( package_name, package_release ) = os.path.split( package )
    (git_url, git_tag) = gitFindPackageRelease( package_name, package_release, debug=False, verbose=verbose )
    if git_url is not None:
        repo = gitRepo.gitRepo( git_url, None, git_tag )
        release = Releaser( repo, package_name, None, git_tag )
    if release is None:
        (svn_url, svn_branch, svn_tag) = svnFindPackageRelease( package_name, package_release, debug=False, verbose=verbose )
        if svn_url is not None:
            if verbose:
                print "find_release: Found svn_url=%s, svn_path=%s, svn_tag=%s" % ( svn_url, svn_branch, svn_tag )
            repo = svnRepo.svnRepo( svn_url, svn_branch, svn_tag )
            release = Releaser( repo, package )
    if release is None:
        print "find_release Error: Unable to find package %s in svn or git repos" % package
    elif verbose:
        repo.ShowRepo( titleLine="find_release: " + package, prefix=" " )
    return release
