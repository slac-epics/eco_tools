#!/bin/bash
#
# Simple shell script to create a bare github repo and configure it for
# SLAC EPICS module development
#

if [ "$1" == "--version" ]; then
	grep eco_tools_version `dirname $0`/eco_version.py
	exit 1
fi
if [ -z "$1" -o "$1" == "-h" -o "$1" == "--help" ]; then
	echo "Usage: ./git-bare-repo.sh /path/to/your_repo/repo_name.git"
	echo "For new EPICS modules, you can just use relative pathname module_name.git"
	echo "For all other repos, please specify an absolute repo pathname."
	exit 1
fi
GIT_DIR=$1
if [ -d $GIT_DIR ]; then
	echo "Error: $GIT_DIR already exists!"
	exit 1
fi

# Make bash exit if any of the following cmds fail
set -e

# Find the git repo templates
if [ -z "$GIT_TOP" ]; then
	GIT_TOP=/afs/slac/g/cd/swe/git/repos
fi
PARENT_DIR=$GIT_TOP/package/epics/modules
TEMPLATES=$GIT_TOP/package/epics/epics-git-templates-git/templates
cd $PARENT_DIR

# Create a bare it repo using our local templates directory
git init --bare --template=$TEMPLATES $GIT_DIR

echo Successfully created bare repo $GIT_DIR
