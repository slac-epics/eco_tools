import re
import sys
import shutil
#import optparse
#import traceback
import tempfile
#import commands
#import stat
import os
import subprocess

class BuildError( Exception ):
    pass

class ValidateError( Exception ):
    pass

class InstallError( Exception ):
    pass

class Releaser(object):
    def __init__( self, opt, args ):
        self._opt		= opt
        self._package	= args
        self._package	= ""
        self._version	= ""
        self._ReleaseTag= None
        self._retcode	= 0
        # Create a directory where files will be checked-out
        self.tmpDir		= tempfile.mktemp("-epics-release")
        self.grpowner	= None

    def __del__( self ):
        self.DoCleanup( 0 )

    def DoCleanup( self, errCode = 0 ):
        self._retcode = errCode
        if self._opt.debug and self._retcode != 0:
            traceback.print_tb(sys.exc_traceback)
            print "%s exited with return code %d." % (sys.argv[0], retcode)

        if self._opt.keeptmp:
            if os.path.exists(self.tmpDir):
                print "\n--keeptmp flag set. Remove the tmp build directory manually:"
                print "\t%s" % (self.tmpDir)
        else:
            if self._opt.verbose:
                print "Cleaning up temporary files ..."
            sys.stdout.flush()
            try:
                sys.stdout.flush()
                if os.path.exists(self.tmpDir):
                    if self._opt.verbose:
                        print "rm -rf", self.tmpDir
                    shutil.rmtree( self.tmpDir )
            except:
                print "failed:\n%s." % (sys.exc_value)
                print "\nCould not remove the following directories, remove them manually:"
                if os.path.exists(self.tmpDir):
                    print "\t%s" % (self.tmpDir)
    
    def CheckoutRelease( self, buildBranch, buildDir ):
        print "\nPlease override Releaser.CheckoutRelease() via a version control specific subclass."
        os.sys.exit()

    def RemoveTag( self ):
        print "\nPlease override Releaser.RemoveTag() via a version control specific subclass."
        os.sys.exit()
    
    def TagRelease( self ):
        print "\nPlease override Releaser.TagRelease() via a version control specific subclass."
        os.sys.exit()

    def ValidateArgs( self ):
        print "\nPlease override Releaser.ValidateArgs() via a version control specific subclass."
        os.sys.exit()

    def execute( self, cmd, outputPipe = subprocess.PIPE ):
        if self._opt.verbose:
            print "EXEC: %s" % ( cmd )
        proc = subprocess.Popen( cmd, shell = True, executable = "/bin/bash",
                                stdout = outputPipe, stderr = outputPipe )
        (proc_stdout, proc_stderr) = proc.communicate( )
        if self._opt.debug:
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
        if rel._opt.dryRun:
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
        os.environ["EPICS_SITE_TOP"] = self._prefix
        if not os.path.exists( buildDir ):
            try:
                if self._opt.debug:
                    print "mkdir -p",	buildDir
                os.makedirs( buildDir, 0775 )
            except OSError:
                raise BuildError, "Cannot create build dir: %s" % ( buildDir )

        # Make sure we can write to the build directory
        try:
            self.execute("chmod -R u+w %s" % ( buildDir ))
        except OSError:
            raise BuildError, "Cannot make build dir writeable: %s" % ( buildDir )

        # Checkout release to build dir
        self.CheckoutRelease( buildBranch, buildDir )

        # Build release
        outputPipe = None
        if self._opt.quiet:
            outputPipe = subprocess.PIPE
        try:
            print "Building Release in %s ..." % ( buildDir )
            buildOutput = self.execute( "make -C %s" % buildDir, outputPipe )
            if self._opt.debug:
                print "BuildRelease: SUCCESS"
        except RuntimeError, e:
            print e
            raise BuildError, "BuildRelease: FAILED"

    def DoTestBuild( self ):
        try:
            self.BuildRelease( self._opt.branch, self.tmpDir )
            self.DoCleanup()
        except BuildError:
            self.DoCleanup()
            raise

    def InstallPackage( self ):
        self.BuildRelease( self._ReleaseTag, self._opt.installDir )

        print "Fixing permissions ...",
        sys.stdout.flush()
        try:
            groups = self.execute("id")
            if re.search( groups, self.grpowner ):
                self.execute("chgrp -R %s %s" % ( self.grpowner, self._opt.installDir ))
            self.execute("chmod -R ugo-w %s" % ( self._opt.installDir ))
            print "done"
        except:
            print "failed.\nERROR: %s." % ( sys.exc_value )

        print "Package %s version %s released." % ( self._package[0], self._opt.release )
