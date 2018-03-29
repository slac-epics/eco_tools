'''
Utilities for importing from CVS and such'''

import os
import fileinput
import subprocess
import sys
from repo_defaults import *

import gc

if 'TOOLS' in os.environ:
    TOOLS_SITE_TOP	= os.environ['TOOLS']
elif 'TOOLS_SITE_TOP' in os.environ:
    TOOLS_SITE_TOP	= os.environ['TOOLS_SITE_TOP']
else:
    TOOLS_SITE_TOP	= LCLS_TOOLS
    os.environ['TOOLS'] = TOOLS_SITE_TOP

cvs2git_dir = os.path.join( TOOLS_SITE_TOP, "cvs2git", "current" )
if not os.path.isdir(cvs2git_dir):
    cvs2git_dir = None

if cvs2git_dir:
    # TODO: Move cvs2svn elsewhere as we may not need it for long
    sys.path.append( cvs2git_dir )
    from cvs2svn_lib.git_run_options import GitRunOptions
    from cvs2svn_lib.context import Ctx
    from cvs2svn_lib.pass_manager import PassManager
    from cvs2svn_lib.passes import passes
    from cvs2svn_lib.main import main
    from cvs2svn_lib.symbol_strategy import ExcludeTrivialImportBranchRule
    from cvs2svn_lib.symbol_strategy import UnambiguousUsageRule
    from cvs2svn_lib.symbol_strategy import BranchIfCommitsRule
    from cvs2svn_lib.symbol_strategy import HeuristicStrategyRule
    from cvs2svn_lib.symbol_strategy import AllBranchRule
    from cvs2svn_lib.symbol_strategy import HeuristicPreferredParentRule


def importHistoryFromCVS(tpath, gitRepoPath, CVSpackageLocation, gitFolder=None, module=None):
    '''Import history into a git repo using cvs2git. tpath is a precreated temporary folder.''' 
    curDir = os.getcwd()
    os.chdir(tpath)
    os.mkdir("cvs2git-tmp")

    #cvs2git_path = os.path.join(os.environ['TOOLS'], "cvs2git", "current", "cvs2git")
    #if not os.path.exists( cvs2git_path ):
    #   raise Exception("Cannot find cvs2git in " + cvs2git_path)
    # Note: can't use --options option to read author info from a cvs2git options
    # file along w/ a cmd line CVSpackageLocation as cvs2git does not support that combo.
    #subprocess.check_call([ cvs2git_path,
    #                      "--blobfile=cvs2git-tmp/git-blob.dat", 
    #                      "--dumpfile=cvs2git-tmp/git-dump.dat", 
    #                      "--username=cvs2git",
    #   "--options=%s" % os.path.join(os.environ['TOOLS'], "cvs2git", "current", "cvs2git-slac.options"),
    #                      CVSpackageLocation])
    
    # Here's an alternative to using cmd line cvs2git by directly invoking
    # the cvs2git python classes that supports author info
    pass_manager = PassManager(passes)
 
    # Read SLAC cvs2git options file for author info
    # This maps cvs userid to git style user name and email
    # The options file also specifies:
    #   blobfile        cvs2git-tmp/git-blob.dat
    #   dumpfile        cvs2git-tmp/git-dump.dat
    #   username        cvs2git
    run_options = GitRunOptions( 'cvs2git', [
                        "--options=%s" % os.path.join( os.environ['TOOLS'],
                            "cvs2git", "current", "cvs2git-slac.options"), ], pass_manager )
 
    # Set project location and strategy
    run_options.set_project(
            CVSpackageLocation,
            symbol_transforms=run_options.options.symbol_transforms,
            symbol_strategy_rules=[
                ExcludeTrivialImportBranchRule(),
                UnambiguousUsageRule(),
                BranchIfCommitsRule(),
                HeuristicStrategyRule(),
                HeuristicPreferredParentRule() ] )

    # Run cvs2git conversion
    main( 'cvs2git', run_options, pass_manager )

    # Re-enable garbage collection
    gc.enable()

    cvsgitdumppath = os.path.abspath(tpath)

    # If a gitRepoPath wasn't provided, create a new bare repo
    if gitRepoPath is None:
        if not gitFolder:
            print "git repo path and import folder are not defined!"
            return
        if gitFolder.endswith(".git"):
            gitRepoPath = gitFolder
        else:
            gitRepoPath = os.path.join( gitFolder, module+".git")
    if os.path.exists(gitRepoPath):
        print "cvs import of repo already exists:", gitRepoPath
        return
    gitRepoPath = initBareRepo( gitRepoPath, module )
    os.chdir(gitRepoPath)

    # Use Python Pipes to import CVS dump into GIT
    p1 = subprocess.Popen(['cat', os.path.join(cvsgitdumppath, "cvs2git-tmp", "git-blob.dat"), os.path.join(cvsgitdumppath, "cvs2git-tmp", "git-dump.dat")], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['git', 'fast-import'], stdin=p1.stdout)
    p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
    p2.communicate()[0]
    print "Done importing CVS dump into git master repo"

    # If cvs2git created a TAG.FIXUP branch, delete it
    cmdOutput = subprocess.check_output( [ 'git', 'branch', '-l' ] ).splitlines()
    for line in cmdOutput:
        if 'TAG.FIXUP' in line:
            subprocess.call(['git', 'branch', '-D', 'TAG.FIXUP'])
            break

    subprocess.check_call(['git', 'gc', '--prune=now'])
    os.chdir(curDir)

def checkCVS2GitPresent():
    '''Make sure we have cvs2git present'''
    if not os.path.exists(os.path.join(os.environ['TOOLS'], "cvs2git", "current", "cvs2git")):
        raise Exception("Cannot find cvs2git in ${TOOLS} " + gitMasterRepo)
    
def removeModuleFromCVS(tpath, packageName, CVSpackageLocation):
    '''Remove the package from the CVS modules file by checking out CVSROOT in the temporary folder tpath'''
    print "Removing", packageName, "from CVS's module file."
    curDir = os.getcwd()
    os.chdir(tpath)
    subprocess.check_call(['cvs', 'checkout', 'CVSROOT'])
    os.chdir("CVSROOT")

    for line in fileinput.input("modules", inplace=True):
        line=line.strip()
        if line.startswith(packageName):
            print "# Commented out by eco %s" % (line)
        else:
            print line

    subprocess.check_call(['cvs', 'commit', '-m', 'eco commented out ' + packageName + ' as it was imported into git.'])
    
    os.chdir(curDir)

