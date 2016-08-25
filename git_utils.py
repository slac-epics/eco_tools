'''
Utilities for creating GIT bare repos, importing from CVS and such'''

import os
import subprocess
import fileinput

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

def importHistoryFromCVS(tpath, gitMasterRepo, CVSpackageLocation):
    '''Import history into a bare repo using cvs2git. tpath is a precreated temporary folder.''' 
    curDir = os.getcwd()
    os.chdir(tpath)
    os.mkdir("cvs2git-tmp")
    if not os.path.exists(os.path.join(os.environ['TOOLS'], "cvs2git", "current", "cvs2git")):
        raise Exception("Cannot find cvs2git in ${TOOLS} " + gitMasterRepo)
    subprocess.check_call([os.path.join(os.environ['TOOLS'], "cvs2git", "current", "cvs2git"),
                           "--blobfile=cvs2git-tmp/git-blob.dat", 
                           "--dumpfile=cvs2git-tmp/git-dump.dat", 
                           "--username=cvs2git",
                           CVSpackageLocation])
    cvsgitdumppath = os.path.abspath(tpath)
    os.chdir(gitMasterRepo)
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

