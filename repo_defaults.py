'''
Defaults for release paths, repo urls and repo paths'''
# repo_defaults.py
# Default string variables for cvs, svn, and git repo paths
DEF_CVS_ROOT		= '/afs/slac/g/lcls/cvs'
DEF_SVN_REPO		= "file:///afs/slac/g/pcds/vol2/svn/pcds"
DEF_SVN_REPOS		= [ DEF_SVN_REPO ]
DEF_SVN_STUB1		= "epics/trunk"
DEF_SVN_STUB2		= "trunk/pcds/epics"
DEF_SVN_TAGS		= "/".join( [ DEF_SVN_REPO, "epics/tags" ])

DEF_EPICS_TOP_AFS	= "/afs/slac/g/pcds/epics"
DEF_EPICS_TOP_LCLS  = "/afs/slac/g/lcls/epics"
DEF_EPICS_TOP_MCC   = "/usr/local/lcls/epics"
DEF_EPICS_TOP_PCDS	= "/reg/g/pcds/epics"
DEF_LCLS_GROUP_OWNER= "lcls"
DEF_LCLS_TOOLS		= '/afs/slac/g/lcls/tools'
DEF_PCDS_GROUP_OWNER= "ps-pcds"

# Use these for filesystem access
DEF_GIT_REPO_PATH		= "/afs/slac/g/cd/swe/git/repos"
DEF_GIT_EPICS_PATH		= DEF_GIT_REPO_PATH + "/package/epics"
DEF_GIT_BASE_PATH		= DEF_GIT_REPO_PATH + "/package/epics/base"
DEF_GIT_MODULES_PATH	= DEF_GIT_REPO_PATH + "/package/epics/modules"
DEF_GIT_EXTENSIONS_PATH	= DEF_GIT_REPO_PATH + "/package/epics/extensions"
DEF_GIT_EXT_TOP_PATH	= DEF_GIT_EXTENSIONS_PATH + "/extensions-top.git"

# Use these for remote repo access
DEF_GIT_REPOS_URL		= "file://" + DEF_GIT_REPO_PATH
#DEF_GIT_REPOS_URL		= "git@code.stanford.edu:slac-epics"
DEF_GIT_EPICS_URL		= "file://" + DEF_GIT_EPICS_PATH
DEF_GIT_MODULES_URL		= "file://" + DEF_GIT_MODULES_PATH
DEF_GIT_EXTENSIONS_URL	= "file://" + DEF_GIT_EXTENSIONS_PATH
DEF_GIT_EXT_TOP_URL		= "file://" + DEF_GIT_EXTENSIONS_PATH + "/extensions-top.git"
DEF_GIT_EXT_TOP_TAG		= "slac-master"
DEF_GIT_RELEASE_DEPTH = 10

