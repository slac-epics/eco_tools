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
from cram_utils import *
from git_utils import *
from svn_utils import *
from site_utils import *
from version_utils import *

def makeDirsWritable( dirPathTop ):
    userId  = os.geteuid()
    for dirPath, dirs, files in os.walk(dirPathTop):
        dirName = os.path.split( dirPath )[-1]
        pathStatus = os.stat( dirPath )
        if pathStatus.st_mode & stat.S_IWGRP:
            continue
        # See if user owns the directory
        if userId != pathStatus.st_uid:
            print "Error: %s does not own %s and cannot make it writable!"
            return 1
        
        # Make it writable.
        try:
            os.chmod( dirPath, pathStatus.st_mode | (stat.S_IWUSR | stat.S_IWGRP) )
        except OSError, e:
            print "Error: Unable to make %s writable!" % buildDir
            print e.strerror
            raise
    return 0

class BuildError( Exception ):
    pass

class ValidateError( Exception ):
    pass

class InstallError( Exception ):
    pass

def find_release( packageSpec, repo_url=None, verbose=False ):
    '''packageSpec should be packageName/Version.  Ex: ADCore/R2.6-0.1.0
       packageSpec can include one or two parent directories to help specify the package,
       of which the last component is the packageName.
       Ex. ioc/amo/gigECam/R3.1.1, extensions/caqtdm/R0.5'''
    release = None
    repo = None
    if verbose:
        print "find_release packageSpec=%s" % ( packageSpec )
    ( packagePath, packageVersion ) = os.path.split( packageSpec )
    packageName = os.path.split(packagePath)[1]
    if repo_url is not None:
        if repo_url.endswith( '.git' ):
            repo = gitRepo.gitRepo( repo_url, None, packageName, packageVersion )
            release = Releaser( repo, packagePath, None, packageVersion, verbose=verbose )
        elif repo_url.find( 'svn' ) >= 0:
            repo = svnRepo.svnRepo( repo_url, repo_url, packageName, packageVersion )
            release = Releaser( repo, packagePath, None, packageVersion, verbose=verbose )
    else:
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

class Releaser(object):
    '''class Releaser( repo, package )
    repo must be a repo object that knows the URL, branch, tag, etc needed to checkout
    the required package version package is the name of the package, w/o the release.
    For example: base/R3.15.4-1.0, asyn/R4.29-0.1.3, edm/R1.12.96, etc
    Note: There are a number of additional arguments to __init__(), all w/ defaults
    These were grandfathered in as part of refactoring a prior version and may be
    more appropriately made into function parameters or in some cases may not be needed at all.
    '''
    def __init__( self, repo, packagePath, installDir=None, branch=None, noTag=False, debug=False, verbose=False, keepTmp=False, message=None, dryRun=False, quiet=False, batch=False ):
        self._installDir= installDir
        self._repo		= repo
        self._branch	= branch
        self._packagePath= packagePath
        if self._packagePath:
            self._packageName = os.path.split( self._packagePath )[1]
        else:
            self._packageName = None
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
        # Create a directory where files will be checked-out (mktemp() is deprecated)
        self._tmpDir	= tempfile.mkdtemp( suffix="-epics-release" )
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
        strRep += "%s tmpDir:       %s\n" % ( self.__class__.__name__, self._tmpDir		if self._tmpDir else 'None' )
        strRep += "%s grpOwner:     %s\n" % ( self.__class__.__name__, self._grpOwner   if self._grpOwner else 'None' )
        return strRep

    def __del__( self ):
        self.DoCleanup( 0 )

    def DoCleanup( self, errCode=0 ):
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
        buildRemoved = False
        try:
            shutil.rmtree( buildDir )
            buildRemoved = True
        except:
            pass

        if not buildRemoved:
            if makeDirsWritable( buildDir ) == 0:
                shutil.rmtree( buildDir )
                buildRemoved = True
        if buildRemoved:
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
        modeUserGroupWrite = stat.S_IWUSR | stat.S_IWGRP
        for dirPath, dirs, files in os.walk(dir):
            pathStatus = os.stat( dirPath )
            dirName = os.path.split( dirPath )[-1]
            if userId == pathStatus.st_uid:
                isRepoPath = '.git' in dirPath or '.svn' in dirPath or 'CVS' in dirPath
                if dirName == 'edl' or dirName.endswith( 'Screens' ):
                    # Leave edl directories read-only to avoid edm replacing release screens
                    os.chmod( dirPath, pathStatus.st_mode & ~modeUserGroupWrite )
                else:
                    os.chmod( dirPath, pathStatus.st_mode | dirModeAllow )
                if groupId >= 0 and groupId != pathStatus.st_gid:
                    os.chown( dirPath, -1, groupId )
                for fileName in files:
                    filePath   = os.path.join( dirPath, fileName )
                    pathStatus = os.lstat( filePath )
                    if os.path.islink(filePath) and hasattr(os, 'lchmod' ):
                        os.lchmod( filePath, pathStatus.st_mode & ~modeUserGroupWrite )
                    elif isRepoPath:
                        os.chmod( filePath, pathStatus.st_mode | modeUserGroupWrite )
                    else:
                        os.chmod( filePath, pathStatus.st_mode & ~modeUserGroupWrite )
                    if groupId >= 0 and groupId != pathStatus.st_gid:
                        os.lchown( filePath, -1, groupId )

    def getCookieJarPath( self ):
        if self._CookieJarPath:
            return self._CookieJarPath 
        # TODO: Derive _EpicsHostArch from the module's RELEASE_SITE file instead of env
        if os.path.isdir( os.path.join( self._ReleasePath, "build" ) ):
            return os.path.join( self._ReleasePath, "build", "configure", "O." + self._EpicsHostArch )
        else:
            return os.path.join( self._ReleasePath, "configure", "O." + self._EpicsHostArch )

    def update_built_cookie( self ):
        cookieJarPath = self.getCookieJarPath()
        if not os.path.isdir( cookieJarPath ):
            os.makedirs( cookieJarPath, 0775 )
        self.execute( "touch %s" % self.built_cookie_path() )
        self._CookieJarPath = cookieJarPath

    def remove_built_cookie( self ):
        if not os.path.isfile( self.built_cookie_path() ):
            return
        cookieJarPath = self.getCookieJarPath()
        pathStatus = os.stat( cookieJarPath )
        if not (pathStatus.st_mode & stat.S_IWGRP):
            os.chmod( cookieJarPath, pathStatus.st_mode | (stat.S_IWUSR | stat.S_IWGRP) )
        self.execute("/bin/rm -f %s" % ( self.built_cookie_path() ))

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

    def BuildRelease( self, buildDir, force=False, rmFailed=False, verbose=False, outputPipe = subprocess.PIPE ):
        status = 0
        if not buildDir:
            raise BuildError, "Build dir not defined!"
        if self._verbose:
            print "BuildRelease: Checking for buildDir %s" % buildDir
        if os.path.exists( buildDir ):
            buildDirExists = True
        else:
            buildDirExists = False
            try:
                if self._dryRun:
                    print "os.makedirs %s drwxrwxr-x" % buildDir
                else:
                    os.makedirs( buildDir, 0775 )
            except OSError:
                raise BuildError, "Cannot create build dir: %s" % ( buildDir )

        if	self._ReleasePath != buildDir:
            self._ReleasePath =  buildDir

        if self._verbose:
            print "BuildRelease: Checking built cookie %s" % ( self.built_cookie_path() )
        if os.path.isfile( self.built_cookie_path() ):
            if force:
                self.remove_built_cookie()
            else:
                #if self._verbose:
                print "BuildRelease %s: Already built!" % ( buildDir )
                return status

        print "\nBuildRelease: %s ..." % ( buildDir )
        sys.stdout.flush()
        sys.stderr.flush()
        try:
            # Checkout release to build dir
            self._repo.CheckoutRelease( buildDir, verbose=self._verbose, dryRun=self._dryRun )
        except RuntimeError, e:
            print e
            raise BuildError, "BuildRelease %s: Checkout FAILED" % buildDir
        except gitRepo.gitError, e:
            print e
            raise BuildError, "BuildRelease %s: Checkout FAILED" % buildDir

        # See if it's built for any architecture
        hasBuilt = self.hasBuilt()

        # Build release
        outputPipe = None
        if self._quiet:
            outputPipe = subprocess.PIPE
        try:
            # Check Dependendents
            print "\nChecking dependents for %s ..." % ( buildDir )
            buildDep = getEpicsPkgDependents( buildDir )
            if 'base' in buildDep:
                # Find the EPICS base version for this release
                epics_base_ver = buildDep['base']

                # Find EPICS_MODULE_TOP for this release
                # Note: Do not use determine_epics_modules_top() here as it gets base from env
                epics_site_top = determine_epics_site_top()
                if VersionToRelNumber(epics_base_ver) > 3.1412:
                    epics_modules_top = os.path.join( epics_site_top, epics_base_ver, 'modules'	)
                else:
                    epics_modules_top = os.path.join( epics_site_top, 'modules', 'R3-14-12' )
                if not os.path.isdir( epics_modules_top ):
                    epics_modules_top = os.path.join( epics_site_top, 'modules' )

                # Check each dependent module release and build if needed
                for dep in buildDep:
                    if dep == 'base':
                        continue	# Just check module dependents
                    package = "%s/%s" % ( dep, buildDep[dep] )
                    if verbose:
                        print "BuildRelease: Checking dep: package=%s" % ( package )
                    release = find_release( package, verbose=self._verbose )
                    if release is not None:
                        result = release.InstallPackage( epics_modules_top )
                        if result != 0:
                            status = result

            print "\nBuilding Release in %s ..." % ( buildDir )
            sys.stdout.flush()
            sys.stderr.flush()
            if		os.path.isfile( os.path.join( buildDir, 'makefile' )) \
                or	os.path.isfile( os.path.join( buildDir, 'Makefile' )) \
                or	'modules' in buildDir:
                buildOutput = self.execute( "make -C %s" % buildDir, outputPipe )

            # Build succeeded!   Update the built_cookie
            self.update_built_cookie()
            if self._verbose:
                print "BuildRelease %s: SUCCESS" % ( buildDir )
        except RuntimeError, e:
            print e
            if hasBuilt == False and not buildDirExists:
                cmdList = [ "rm", "-rf",    buildDir + "-FAILED" ]
                subprocess.call( cmdList )
                if rmFailed:
                    cmdList = [ "rm", "-rf",    buildDir ]
                else:
                    cmdList = [ "mv", buildDir, buildDir + "-FAILED" ]
                    buildDir += "-FAILED"
                subprocess.call( cmdList )
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
        return status

    def DoTestBuild( self ):
        try:
            status = self.BuildRelease( self._tmpDir, rmFailed=True )
            self.DoCleanup()
        except BuildError:
            print "DoTestBuild: %s Build error from BuildRelease in %s" % ( self._packageName, self._tmpDir )
            self.DoCleanup()
            status = -1
            raise
        except subprocess.CalledProcessError, e:
            print "DoTestBuild: %s CalledProcessError from BuildRelease in %s" % ( self._packageName, self._tmpDir )
            print e
            status = -1
            pass
        return status

    def InstallPackage( self, installTop=None, force=False, rmFailed=False ):
        '''Use InstallPackage to automatically determine the buildDir from installTop and the repo specs.
        If you already know where to build you can just call BuildRelease() directly.'''
        if self._verbose:
            self._repo.ShowRepo( titleLine="InstallPackage: " + self._packageName, prefix="	" )
            print self

        status = 0
        if not self._installDir:
            # See if we can get the releaseDir from cram
            releaseDir = getCramReleaseDir( self._repo.GetUrl(), self._repo.GetTag() )
            if releaseDir:
                self._installDir = os.path.join( releaseDir, self._repo.GetTag() )

        if not self._installDir:
            epics_site_top	= determine_epics_site_top()
            if not installTop and not epics_site_top:
                print "InstallPackage Error: Need valid installTop to determine installDir!"
                return status

            # Is Package a module?
            if	os.path.split( self._packagePath )[0] == 'modules' \
            or  self._repo.GetUrl().find('modules') >= 0:
                # Package is a module
                if installTop is not None:
                    if not installTop.endswith( '/' + self._packageName ):
                        if not installTop.endswith( '/modules' ):
                            installTop += '/modules'
                    if not os.path.isdir( installTop ):
                        print "Invalid top %s" % installTop
                        installTop = None
                if installTop is None:
                    epics_modules_top = determine_epics_modules_top()
                    if not epics_modules_top:
                        print "InstallPackage Error: Unable to determine EPICS modules installTop!"
                        return status
                    installTop = epics_modules_top

            # Is Package an extension?
            if not installTop:
                if		self._packagePath.find('extensions') >= 0 \
                     or	self._repo.GetUrl().find('extensions') >= 0:
                    installTop = os.path.join( epics_site_top, 'extensions' ) 

            # Is Package an IOC?
            if		installTop is None \
                and	(	os.path.split( self._packagePath )[0].startswith('ioc') \
                    or  self._repo.GetUrl().find('ioc') >= 0 ):
                # Package is an IOC
                topVariants = [ epics_site_top ]
                for topVariant in defEpicsTopVariants:
                    topVariants.append( os.path.join( epics_site_top, topVariant ) )
                for topVariant in topVariants:
                    epics_ioc_top = os.path.join( topVariant, os.path.split(self._packagePath)[0] )
                    if os.path.isdir( epics_ioc_top ):
                        installTop = os.path.join( topVariant, self._packagePath )
                        if not os.path.isdir( installTop ):
                            os.makedirs( installTop, 0775 )
 
            if not installTop:
                print "InstallPackage Error: Unable to determine installTop!"
                return -1
            if not os.path.isdir( installTop ):
                print "InstallPackage Error: Invalid installTop:", installTop
                return -1
            # Canonicalize installTop
            cmdList = [ "readlink", "-e", installTop ]
            cmdOutput = subprocess.check_output( cmdList ).splitlines()
            if len(cmdOutput) == 1:
                installTop = cmdOutput[0]

            if installTop.endswith( '/' + self._packageName ):
                self._installDir = os.path.join( installTop, self._repo.GetTag() )
            else:
                self._installDir = os.path.join( installTop, self._packageName, self._repo.GetTag() )

        if self._installDir.startswith( DEF_EPICS_TOP_PCDS ):
            self._grpOwner = DEF_PCDS_GROUP_OWNER

        try:
            result = self.BuildRelease( self._installDir, force=force, rmFailed=rmFailed, verbose=self._verbose )
            if result != 0:
                status = result
            if self._verbose:
                print "InstallPackage: %s installed to:\n%s" % ( self._packageName, os.path.realpath(self._installDir) )
        except BuildError, e:
            print "InstallPackage: %s Build error from BuildRelease in %s" % ( self._packageName, os.path.realpath(self._installDir) )
            print e
            status = -1
            pass
        except subprocess.CalledProcessError, e:
            print "InstallPackage: %s CalledProcessError from BuildRelease in %s" % ( self._packageName, os.path.realpath(self._installDir) )
            print e
            status = -1
            pass
        return status
