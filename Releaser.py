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
    package is the name of the package, w/o the release, for example: base/R3.15.4-1.0, asyn/R4.29-0.1.3, edm/R1.12.96, etc
    Note: There are a number of additional arguments to __init__(), all w/ defaults
    These were grandfathered in as part of refactoring a prior version and may be
    more appropriately made into function parameters or in some cases may not be needed at all. 
    '''
    def __init__( self, repo, packagePath, installDir=None, branch=None, noTag=True, debug=False, verbose=False, keepTmp=False, message=None, dryRun=False, quiet=False, batch=False ):
        self._installDir= installDir
        self._repo		= repo
        self._branch	= branch
        self._packagePath= packagePath
        if self._packagePath:
            self._packageName = os.path.split( self._packagePath )[1]
        self._version	= ""
        self._dryRun	= dryRun
        self._batch		= batch
        self._debug		= debug
        self._quiet		= quiet
        self._verbose	= verbose
        self._message	= message
        self._keepTmp	= keepTmp
        self._noTag		= noTag
        self._installDir= None
        self._ReleasePath= None
        self._CookieJarPath= None
        # TODO: Derive _EpicsHostArch from the module's RELEASE_SITE file instead of env
        self._EpicsHostArch = determine_epics_host_arch()
        if  self._EpicsHostArch is None:
            self._EpicsHostArch = 'unknown-host-arch'
        self._retcode	= 0
        # Create a directory where files will be checked-out
        self._tmpDir	= tempfile.mktemp("-epics-release")
        self._grpOwner	= None

    def __str__( self ):
        strRep =  "Releaser:\n"
        # TODO: Cleanup this classroom!  Throw out class variables we don't need
        strRep += "%s Repo:         \n%s" % ( self.__class__.__name__, self._repo )
        strRep += "%s branch:       %s\n" % ( self.__class__.__name__, self._branch 	if self._branch else 'None' )
        strRep += "%s packageName:  %s\n" % ( self.__class__.__name__, self._packageName if self._packageName else 'None' )
        strRep += "%s packagePath:  %s\n" % ( self.__class__.__name__, self._packagePath if self._packagePath else 'None' )
        strRep += "%s version:      %s\n" % ( self.__class__.__name__, self._version    if self._version else 'None' )
        strRep += "%s dryRun:       %s\n" % ( self.__class__.__name__, self._dryRun    	if self._dryRun else 'None' )
        strRep += "%s batch:        %s\n" % ( self.__class__.__name__, self._batch    	if self._batch else 'None' )
        strRep += "%s debug:        %s\n" % ( self.__class__.__name__, self._debug    	if self._debug else 'None' )
        strRep += "%s quiet:        %s\n" % ( self.__class__.__name__, self._quiet    	if self._quiet else 'None' )
        strRep += "%s ReleasePath:  %s\n" % ( self.__class__.__name__, self._ReleasePath   if self._ReleasePath else 'None' )
        strRep += "%s installDir:   %s\n" % ( self.__class__.__name__, self._installDir    if self._installDir else 'None' )
        strRep += "%s EpicsHostArch:%s\n" % ( self.__class__.__name__, self._EpicsHostArch if self._EpicsHostArch else 'None' )
        strRep += "%s tmpDir:       %s\n" % ( self.__class__.__name__, self._tmpDir    	if self._tmpDir else 'None' )
        strRep += "%s grpOwner:     %s\n" % ( self.__class__.__name__, self._grpOwner   if self._grpOwner else 'None' )
        return strRep

    def __del__( self ):
        self.DoCleanup( 0 )

    def DoCleanup( self, errCode = 0 ):
        self._retcode = errCode
        if self._debug and self._retcode != 0:
            traceback.print_tb(sys.exc_traceback)
            print "%s exited with return code %d." % (sys.argv[0], retcode)

        if self._keepTmp:
            if os.path.exists(self._tmpDir):
                print "\n--keepTmp flag set. Remove the tmp build directory manually:"
                print "\t%s" % (self._tmpDir)
        else:
            try:
                sys.stdout.flush()
                sys.stderr.flush()
                if os.path.exists(self._tmpDir):
                    if self._verbose:
                        print "Removing temporary dir %s ..." % self._tmpDir
                    shutil.rmtree( self._tmpDir )
            except:
                print "failed:\n%s." % (sys.exc_value)
                print "\nCould not remove the following directories, remove them manually:"
                if os.path.exists(self._tmpDir):
                    print "\t%s" % (self._tmpDir)
    
    def RemoveTag( self, tag=None ):
        if tag is not None:
            tag = self._repo._tag
        return self._repo.RemoveTag( package=self._packagePath, tag=tag )

    def TagRelease( self, message=None ):
        return self._repo.TagRelease( packagePath=self._packagePath, branch=self._branch, message=message )

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

        # TODO: Move this to a function that fixes permissions
        # Enable write access to build directory
        try:
            self.execute("chmod -R u+w %s" % ( buildDir ))
        except OSError:
            # Just pass till this is more robust
            pass
            #raise BuildError, "Cannot make build dir writeable: %s" % ( buildDir )
        except RuntimeError:
            # Just pass till this is more robust
            pass
            #raise BuildError, "Build dir not found: %s" % ( buildDir )

        try:
            self.execute("/bin/rm -rf %s" % ( buildDir ))
        except OSError:
            raise BuildError, "Cannot remove build dir: %s" % ( buildDir )
        except RuntimeError:
            raise BuildError, "Build dir not found: %s" % ( buildDir )
        print "Successfully removed build dir: %s ..." % ( buildDir )

    # TODO: Move this to a standalone function usable
    # by any class
    # def fixPermissions( self, dir, makeFilesWritable=False ):
    def fixPermissions( self, dir ):
        if self._verbose:
            print "Fixing permissions for %s ..." % dir
        sys.stdout.flush()
        userId  = os.geteuid()
        groupId = -1
        groups  = subprocess.check_output( [ "id" ] )
        if self._grpOwner is not None:
            if re.search( groups, self._grpOwner ):
                groupId = grp.getgrname(self._grpOwner).gr_gid 

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
            dirName = os.path.split( dirPath )[-1]
            if dirName == '.git' or dirName == '.svn' or dirName == 'CVS':
                continue
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

    def getCookieJarPath( self ):
        if self._CookieJarPath:
            return self._CookieJarPath 
        # TODO: Derive _EpicsHostArch from the module's RELEASE_SITE file instead of env
        if os.path.isdir( os.path.join( self._ReleasePath, "build" ) ):
            return os.path.join( self._ReleasePath, "build", "O." + self._EpicsHostArch )
        else:
            return os.path.join( self._ReleasePath, "configure", "O." + self._EpicsHostArch )

    def update_built_cookie( self ):
        cookieJarPath = self.getCookieJarPath()
        if not os.path.isdir( cookieJarPath ):
            os.makedirs( cookieJarPath )
        self.execute( "touch %s" % self.built_cookie_path() )
        self._CookieJarPath = cookieJarPath

    def built_cookie_path( self ):
        cookieJarPath = self.getCookieJarPath()
        return os.path.join( cookieJarPath, ".is_built" )

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

    def BuildRelease( self, buildBranch, buildDir, force=False, outputPipe = subprocess.PIPE ):
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

        # TODO: Move this to a function that fixes permissions
        # If user owns the build directory, make it writable.
        # Shouldn't have to do this now that we leave directories writable
        try:
            self.execute( "chmod -R u+w %s" % ( buildDir ) )
        except OSError:
            # Just pass till this is more robust
            pass
            #raise BuildError, "Cannot make build dir writeable: %s" % ( buildDir )
        except RuntimeError:
            # Just pass till this is more robust
            pass
            #raise BuildError, "Cannot make build dir writeable: %s" % ( buildDir )

        if	self._ReleasePath != buildDir:
            self._ReleasePath =  buildDir

        if self._verbose:
            print "BuildRelease: Checking built cookie %s" % ( self.built_cookie_path() )
        if os.path.isfile( self.built_cookie_path() ):
            if force:
                self.execute("/bin/rm -f %s" % ( self.built_cookie_path() ))
            else:
                #if self._verbose:
                print "BuildRelease %s: Already built!" % ( buildDir )
                return

        try:
            self.execute("/bin/rm -f %s" % ( self.built_cookie_path() ))
            if self._repo._url.find( 'extensions' ) > 0:
                # For extensions, we first checkout extensions-top
                topRepo = gitRepo.gitRepo( DEF_GIT_EXT_TOP_URL, None, "extensions-top", DEF_GIT_EXT_TOP_TAG )
                topRepo.CheckoutRelease( buildDir, verbose=self._verbose, dryRun=self._dryRun )

                # Then checkout the package to src/packageName
                extSrcDir = os.path.join( buildDir, 'src', self._packageName )
                self._repo.CheckoutRelease( extSrcDir, verbose=self._verbose, dryRun=self._dryRun )
            else:
                # Checkout release to build dir
                self._repo.CheckoutRelease( buildDir, verbose=self._verbose, dryRun=self._dryRun )
        except RuntimeError, e:
            print e
            raise BuildError, "BuildRelease %s: FAILED" % buildDir
        except gitRepo.gitError, e:
            print e
            raise BuildError, "BuildRelease %s: FAILED" % buildDir

        # See if it's built for any architecture
        hasBuilt = self.hasBuilt()

        # Build release
        outputPipe = None
        if self._quiet:
            outputPipe = subprocess.PIPE
        try:
            print "\nBuilding Release in %s ..." % ( buildDir )
            sys.stdout.flush()
            sys.stderr.flush()
            buildOutput = self.execute( "make -C %s" % buildDir, outputPipe )
            self.update_built_cookie()
            if self._verbose:
                print "BuildRelease %s: SUCCESS" % ( buildDir )
        except RuntimeError, e:
            print e
            if hasBuilt == False:
                cmdList = [ "rm", "-rf",    buildDir + "-FAILED" ]
                subprocess.call( cmdList )
                cmdList = [ "mv", buildDir, buildDir + "-FAILED" ]
                subprocess.call( cmdList )
                buildDir += "-FAILED"
            raise BuildError, "BuildRelease FAILED in %s" % ( buildDir )

        sys.stdout.flush()
        sys.stderr.flush()
        self.fixPermissions( buildDir )

        try:
            if os.path.isdir( buildDir + "-FAILED" ):
                # rm any stale -FAILED on success
                cmdList = [ "rm", "-rf",    buildDir + "-FAILED" ]
                subprocess.call( cmdList )
        except RuntimeError, e:
            print e
            pass

    def DoTestBuild( self ):
        try:
            self.BuildRelease( self._ReleasePath, self._tmpDir )
            self.DoCleanup()
        except BuildError:
            print "DoTestBuild: %s Build error from BuildRelease in %s" % ( self._packageName, self._tmpDir )
            self.DoCleanup()
            raise
        except subprocess.CalledProcessError, e:
            print "DoTestBuild: %s CalledProcessError from BuildRelease in %s" % ( self._packageName, self._tmpDir )
            print e
            pass

    def InstallPackage( self, installTop=None, force=False ):
        '''Use InstallPackage to automatically determine the buildDir from installTop and the repo specs.
        If you already know where to build you can just call BuildRelease() directly.'''
        if self._verbose:
            self._repo.ShowRepo( titleLine="InstallPackage: " + self._packageName, prefix="	" )
            print self

        if not self._installDir:
            epics_site_top	= determine_epics_site_top()
            if not installTop and not epics_site_top:
                print "InstallPackage Error: Need valid installTop to determine installDir!"
                return
            if not installTop:
                if		os.path.split( self._packagePath )[0] == 'modules' \
                     or	self._repo.GetUrl().find('modules') >= 0:
                    epics_modules_top = determine_epics_modules_top()
                    if not epics_modules_top:
                        print "InstallPackage Error: Unable to determine EPICS modules installTop!"
                        return
                    installTop = epics_modules_top

            if not installTop:
                if		self._packagePath.find('extensions') >= 0 \
                     or	self._repo.GetUrl().find('extensions') >= 0:
                    installTop = os.path.join( epics_site_top, 'extensions' ) 
 
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

            self._installDir = os.path.join( installTop, self._packageName, self._repo.GetTag() )

        if self._installDir.startswith( DEF_EPICS_TOP_PCDS ):
            self._grpOwner = DEF_PCDS_GROUP_OWNER

        try:
            self.BuildRelease( self._ReleasePath, self._installDir, force=force )
            if self._verbose:
                print "InstallPackage: %s installed to:\n%s" % ( self._packageName, os.path.realpath(self._installDir) )
        except BuildError, e:
            print "InstallPackage: %s Build error from BuildRelease in %s" % ( self._packageName, os.path.realpath(self._installDir) )
            print e
            pass
        except subprocess.CalledProcessError, e:
            print "InstallPackage: %s CalledProcessError from BuildRelease in %s" % ( self._packageName, os.path.realpath(self._installDir) )
            print e
            pass

def find_release( packageSpec, verbose=False ):
    '''packageSpec should be packageName/Version.  Ex: ADCore/R2.6-0.1.0
       packageSpec can include one or two parent directories to help specify the package,
       of which the last component is the packageName.
       Ex. ioc/amo/gigECam, extensions/caqtdm'''
    release = None
    repo = None
    ( packagePath, packageVersion ) = os.path.split( packageSpec )
    packageName = os.path.split(packagePath)[1]
    (git_url, git_tag) = gitFindPackageRelease( packagePath, packageVersion, debug=False, verbose=verbose )
    if git_url is not None:
        repo = gitRepo.gitRepo( git_url, None, packageName, git_tag )
        release = Releaser( repo, packagePath, None, git_tag, verbose=verbose )
    if release is None:
        (svn_url, svn_branch, svn_tag) = svnFindPackageRelease( packagePath, packageVersion, debug=False, verbose=verbose )
        if svn_url is not None:
            if verbose:
                print "find_release: Found svn_url=%s, svn_path=%s, svn_tag=%s" % ( svn_url, svn_branch, svn_tag )
            repo = svnRepo.svnRepo( svn_url, svn_branch, packageName, svn_tag )
            release = Releaser( repo, packagePath, verbose=verbose )
    if verbose:
        if repo is not None:
            repo.ShowRepo( titleLine="find_release found: " + packageSpec, prefix=" " )
        else:
            print "find_release: Could not find packageSpec: %s" % packageSpec
    return release
