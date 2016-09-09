'''
Utilities for creating GIT bare repos, importing from CVS and such'''

import os
import subprocess
import fileinput

import gc

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

def determineGitRoot():
    '''Get the root folder for GIT repos at SLAC'''
    gitRoot = "/afs/slac/g/cd/swe/git/repos/"
    # The GIT_REPO_ROOT variable is mainly used when testing eco and is not something that we really expect from the environment.
    if "GIT_REPO_ROOT" in os.environ:
        gitRoot = os.environ["GIT_REPO_ROOT"]
    return gitRoot

def initBareRepo(parentFolder, packageName):
    gitMasterRepo = os.path.join(parentFolder, packageName+".git")
    print "Checking to see if git master repo exists at", gitMasterRepo
    if os.path.exists(gitMasterRepo):
        subprocess.check_call(["zenity", "--error", "--title", "Error", "--text", "Git master repo for package " + packageName + " already exists at " + gitMasterRepo])
        raise Exception("Git master repo already exists at " + gitMasterRepo)
    print "Initializing a bare repo in", parentFolder, "for package", packageName
    subprocess.check_call(["git", "init", "--bare", gitMasterRepo])
    if not os.path.exists(gitMasterRepo):
        raise Exception("Git master repo does not seem to exist at " + gitMasterRepo)
    return gitMasterRepo

def cloneMasterRepo(gitMasterRepo, tpath, packageName):
    '''Create a clone of the master repo given a destination folder'''
    print "Cloning the master repo at", gitMasterRepo, "into", tpath
    clonedFolder = os.path.join(tpath, packageName)
    subprocess.check_call(['git', 'clone', gitMasterRepo, clonedFolder])
    return clonedFolder

def createGitIgnore():
    gitIgnoreLines = ["bin/", "CVS/", "O.*/", "RELEASE_SITE", "db/", "dbd/", "iocBoot/*/envPaths", "*~"]
    with open(".gitignore", "w") as f:
        f.write("\n".join(gitIgnoreLines))
    subprocess.check_call(['git', 'add', '.gitignore'])

def commitAndPush():
    '''Call git commit and git push'''
    subprocess.check_call(['git', 'commit', '-m', 'Initial commit/import from eco. Added a default .gitignore and other defaults.'])
    subprocess.check_call(['git', 'push', 'origin', 'master'])

def addPackageToEcoModuleList(packageName, gitMasterRepo):
    '''Add the package with the given master repo to eco's modulelist'''
    curDir = os.getcwd()
    print "Adding package", packageName, "to eco_modulelist"
    gitModulesTxtFolder = os.path.join(os.environ['TOOLS'], 'eco_modulelist')
    os.chdir(gitModulesTxtFolder)
    subprocess.check_call(['git', 'pull', '--rebase'])
    with open('modulelist.txt', 'a') as f:
        f.write(packageName + "\t\t\t" + gitMasterRepo+"\n")
    subprocess.check_call(['git', 'add', 'modulelist.txt'])
    subprocess.check_call(['git', 'commit', '-m', 'eco added package ' + packageName + ' located at ' + gitMasterRepo])
    subprocess.check_call(['git', 'pull', '--rebase'])
    subprocess.check_call(['git', 'push', 'origin', 'master'])
    os.chdir(curDir)

def importHistoryFromCVS(tpath, gitRepo, CVSpackageLocation, modulesDir=None, module=None):
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
    #	blobfile		cvs2git-tmp/git-blob.dat
    #	dumpfile		cvs2git-tmp/git-dump.dat
    #	username		cvs2git
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

    # If a gitRepo wasn't provided, create a new bare repo
    if gitRepo is None:
        gitRepo = os.path.join( modulesDir, module+".git")
    if not os.path.exists(gitRepo):
        gitRepo = initBareRepo( modulesDir, module )
    os.chdir(gitRepo)

    # Use Python Pipes to import CVS dump into GIT
    p1 = subprocess.Popen(['cat', os.path.join(cvsgitdumppath, "cvs2git-tmp", "git-blob.dat"), os.path.join(cvsgitdumppath, "cvs2git-tmp", "git-dump.dat")], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['git', 'fast-import'], stdin=p1.stdout)
    p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
    p2.communicate()[0]
    print "Done importing CVS dump into git master repo"
    subprocess.call(['git', 'branch', '-D', 'TAG.FIXUP'])
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

def createBranchFromTag( tag, branchName ):
    '''Checkout the tag and create a branch using the tag as a starting point.'''
    subprocess.check_call(['git', 'checkout', tag])
    subprocess.check_call(['git', 'checkout', '-b', branchName])

