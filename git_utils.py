'''
Utilities for creating GIT bare repos, importing from CVS and such'''

import os
import fileinput
import subprocess
import sys

import gc

# TODO: Need to do a better job of handling differences in LCLS vs PCDS env
if 'TOOLS' not in os.environ:
    if os.path.exists( '/afs/slac/g/lcls/tools' ):
        os.environ['TOOLS'] = '/afs/slac/g/lcls/tools' 
sys.path.append( "%s/cvs2git/current" % os.environ['TOOLS'] )

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

DEF_GIT_REPOS		= "/afs/slac/g/cd/swe/git/repos"
#DEF_GIT_REPOS		= "git@code.stanford.edu:slac-epics"
DEF_GIT_MODULES		= DEF_GIT_REPOS + "/package/epics/modules"
LCLS_TOOLS			= '/afs/slac/g/lcls/tools'
TOOLS_SITE_TOP		= os.environ['TOOLS']
if  TOOLS_SITE_TOP is None:
    TOOLS_SITE_TOP	= LCLS_TOOLS

gitModulesTxtFile	= os.path.join( LCLS_TOOLS, 'eco_modulelist', 'modulelist.txt' )

def parseGitModulesTxt():
    '''Parse the GIT modules txt file and return a dict of packageName -> location'''
    package2Location = {}
    with open(gitModulesTxtFile, 'r') as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        parts = line.split()
        if(len(parts) < 2):
            print "Error parsing ", gitModulesTxtFile, "Cannot break", line, "into columns with enough fields using spaces/tabs"
            continue
        packageName = parts[0]
        packageLocation = parts[1]
        package2Location[packageName] = packageLocation
    return package2Location

git_package2Location = parseGitModulesTxt()

def determineGitRoot( ):
    '''Get the root folder for GIT repos at SLAC'''
    gitRoot = DEF_GIT_REPOS
    # The GIT_REPO_ROOT variable is mainly used when testing eco and is not something that we really expect from the environment.
    if "GIT_REPO_ROOT" in os.environ:
        gitRoot = os.environ["GIT_REPO_ROOT"]
    return gitRoot

def gitGetRemoteTag( url, tag, debug = False, verbose = False ):
    '''Fetchs tags from a git repo url and looks for a match w/ the desired tag.
    Returns a tuple of ( url, tag ), ( None, None ) on error.
    For a matching git remote, url must be a valid string and tag must be found.'''
    git_url     = None
    git_tag     = None
    if tag is None:
        tag			= 'HEAD'
        tag_spec	= tag
    else:
        tag_spec	= 'refs/tags/%s' % tag
    try:
        statusInfo = subprocess.check_output( [ 'git', 'ls-remote', url ], stderr=subprocess.STDOUT )
        for line in statusInfo.splitlines():
            if line is None:
                break
            tokens = line.split()
            if tokens[1] == tag_spec:
                git_url = url
                git_tag = tag
                break

    except OSError, e:
        if debug or verbose:
            print e
        pass
    except subprocess.CalledProcessError, e:
        if debug or verbose:
            print e
        pass
    if verbose:
        if git_url:
            print "gitGetRemoteTag: Found git_url=%s, git_tag=%s" % ( git_url, git_tag )
        else:
            print "gitGetRemoteTag: Unable to find url=%s, tag=%s" % ( url, tag )
    return ( git_url, git_tag )

def initBareRepo(parentFolder, packageName):
    gitMasterRepo = os.path.join(parentFolder, packageName+".git")
    print "Checking to see if git master repo exists at", gitMasterRepo
    if os.path.exists(gitMasterRepo):
        subprocess.check_call(["zenity", "--error", "--title", "Error", "--text", "Git master repo for package " + packageName + " already exists at " + gitMasterRepo])
        raise Exception("Git master repo already exists at " + gitMasterRepo)
    print "Creating a new bare repo in", parentFolder, "for package", packageName
    subprocess.check_call(["git", "init", "--bare", "--template=%s/templates" % DEF_GIT_MODULES, gitMasterRepo])
    if not os.path.exists(gitMasterRepo):
        raise Exception("Git master repo does not seem to exist at " + gitMasterRepo)
    return gitMasterRepo

def cloneMasterRepo(gitMasterRepo, tpath, packageName):
    '''Create a clone of the master repo given a destination folder'''
    print "Cloning the master repo at", gitMasterRepo, "into", tpath
    clonedFolder = os.path.join(tpath, packageName)
    subprocess.check_call(['git', 'clone', '--recursive', gitMasterRepo, clonedFolder])
    return clonedFolder

def createGitIgnore():
    gitIgnoreLines = ["bin/", "CVS/", "O.*/", "RELEASE_SITE", "db/", "dbd/", "iocBoot/*/envPaths", "*~"]
    with open(".gitignore", "w") as f:
        f.write("\n".join(gitIgnoreLines))
    subprocess.check_call(['git', 'add', '.gitignore'])

def gitCommitAndPush( message ):
    '''Call git commit and git push'''
    subprocess.check_call(['git', 'commit', '-m', message ])
    message = 'Initial commit/import from eco. Added a default .gitignore and other defaults.'
    subprocess.check_call(['git', 'push' ])

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
    subprocess.check_call(['git', 'push' ])
    os.chdir(curDir)

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

    # If a gitRepoPath wasn't provided, create a new bare repo
    if gitRepoPath is None:
        gitRepoPath = os.path.join( gitFolder, module+".git")
    if not os.path.exists(gitRepoPath):
        gitRepoPath = initBareRepo( gitFolder, module )
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

def createBranchFromTag( tag, branchName ):
    '''Checkout the tag and create a branch using the tag as a starting point.'''
    subprocess.check_call(['git', 'checkout', '-q', tag])
    subprocess.check_call(['git', 'checkout', '-b', branchName])

def gitGetWorkingBranch( debug = False, verbose = False ):
    '''See if the current directory is the top of an git working directory.
    Returns a 3-tuple of ( url, branch, tag ), ( None, None, None ) on error.
    For a valid git working dir, url must be a valid string, branch is the branch name or None if detached,
    tag is either None or a tag name if HEAD refers to a tag name.'''
    repo_url    = None
    repo_branch = None
    repo_tag    = None
    try:
        repoCmd = [ 'git', 'status' ]
        statusInfo = subprocess.check_output( repoCmd, stderr=subprocess.STDOUT )
        statusLines = statusInfo.splitlines()
        if len(statusLines) > 0 and statusLines[0].startswith( '# On branch ' ):
            repo_branch = statusLines[0].split()[3]

        repoCmd = [ 'git', 'remote', '-v' ]
        statusInfo = subprocess.check_output( repoCmd, stderr=subprocess.STDOUT )
        statusLines = statusInfo.splitlines()
        for line in statusLines:
            if line is None:
                break
            tokens = line.split()
            if tokens[0] == 'origin':
                repo_url = tokens[1]
                break

        # See if HEAD corresponds to any tags
        statusInfo = subprocess.check_output( [ 'git', 'name-rev', '--name-only', '--tags', 'HEAD' ], stderr=subprocess.STDOUT )
        statusLines = statusInfo.splitlines()
        if len(statusLines) > 0:
            # Just grab the first tag that matches
            repo_tag = statusLines[0].split('^')[0]

    except OSError, e:
        if debug:
            print e
        pass
    except subprocess.CalledProcessError, e:
        if debug:
            print e
        pass
    return ( repo_url, repo_branch, repo_tag )

def gitFindPackageRelease( packageSpec, tag, debug = False, verbose = False ):
    (repo_url, repo_tag) = (None, None)
    (packagePath, sep, packageName) = packageSpec.rpartition('/')
    # See if the package was listed in $TOOLS/eco_modulelist/modulelist.txt
    if packageName in git_package2Location:
        url_path = git_package2Location[packageName]
        (repo_url, repo_tag) = gitGetRemoteTag( url_path, tag, debug=debug )
    else:
        for url_root in [ DEF_GIT_MODULES, DEF_GIT_REPOS ]:
            if packagePath:
                url_path = '%s/%s/%s.git' % ( url_root, packagePath, packageName )
            else:
                url_path = '%s/%s.git' % ( url_root, packageName )
            (repo_url, repo_tag) = gitGetRemoteTag( url_path, tag, debug=debug )
            break
    if verbose:
        if repo_url:
            print "gitFindPackageRelease found %s/%s: url=%s, tag=%s" % ( packageSpec, tag, repo_url, repo_tag )
        else:
            print "gitFindPackageRelease Error: Cannot find %s/%s" % (packageSpec, tag)
    return (repo_url, repo_tag)

def parseGitModulesTxt():
    '''Parse the GIT modules txt file and return a dict of packageName -> location'''
    package2Location = {}
    gitModulesTxtFile = os.path.join(os.environ['TOOLS'], 'eco_modulelist', 'modulelist.txt')
    with open(gitModulesTxtFile, 'r') as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        parts = line.split()
        if(len(parts) < 2):
            print "Error parsing ", gitModulesTxtFile, "Cannot break", line, "into columns with enough fields using spaces/tabs"
            continue
        packageName = parts[0]
        packageLocation = parts[1]
        package2Location[packageName] = packageLocation
    return package2Location

