'''
Defaults for release paths, repo urls and repo paths'''
# repo_defaults.py
# Default string variables for cvs, svn, and git repo paths
DEF_SVN_REPO		= "file:///afs/slac/g/pcds/vol2/svn/pcds"
DEF_SVN_REPOS		= [ DEF_SVN_REPO ]
DEF_SVN_STUB1		= "epics/trunk"
DEF_SVN_STUB2		= "trunk/pcds/epics"
DEF_SVN_TAGS		= "/".join( [ DEF_SVN_REPO, "epics/tags" ])

DEF_EPICS_TOP_PCDS	= "/reg/g/pcds/package/epics/3.14"
DEF_EPICS_TOP_LCLS	= "/afs/slac/g/lcls/epics"
DEF_EPICS_TOP_AFS	= "/afs/slac/g/pcds/package/epics/3.14"
DEF_LCLS_GROUP_OWNER= "lcls"
DEF_LCLS_TOOLS		= '/afs/slac/g/lcls/tools'
DEF_PCDS_GROUP_OWNER= "ps-pcds"

DEF_GIT_REPOS		= "/afs/slac/g/cd/swe/git/repos"
#DEF_GIT_REPOS		= "git@code.stanford.edu:slac-epics"
DEF_GIT_EPICS		= DEF_GIT_REPOS + "/package/epics"
DEF_GIT_MODULES		= DEF_GIT_REPOS + "/package/epics/modules"
DEF_GIT_EXTENSIONS	= DEF_GIT_REPOS + "/package/epics/extensions"
DEF_GIT_EXT_TOP		= DEF_GIT_EXTENSIONS + "/extensions-top.git"
DEF_GIT_EXT_TOP_TAG	= "slac-master"

