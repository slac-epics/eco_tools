#!/bin/bash
#
# Simple shell script to clone a github repo and configure it for
# SLAC EPICS module development
#

URL=$1
GIT_DIR=$2
if [ -z "$GIT_DIR" ]; then
	if [ ! -z "$URL" ]; then
		GIT_DIR=`basename $URL`
	fi
fi
if [ -z "$URL" -o -z "$GIT_DIR" ]; then
	echo "Usage: ./git-clone-github.sh https://github.com/git-repo-path/git-repo-name.git"
    echo "Or: ./git-clone-github.sh git-repo-name.git"
	echo "Or: ./git-clone-github.sh https://github.com/git-repo-path/git-repo-name.git new_name.git"
    echo "Use the second form if you want to start with a empty bare repo."
    echo "Use the third form if you want to use a different name for the repo."
	exit 1
fi

# Make bash exit if any of the following cmds fail
set -e

# Make sure we're in the repo modules directory
if [ -z "$GIT_TOP" ]; then
	GIT_TOP=/afs/slac/g/cd/swe/git/repos
fi
PARENT_DIR=$GIT_TOP/package/epics/modules
cd $PARENT_DIR

# Create a bare it repo using our local templates directory
git init --bare --template=$PARENT_DIR/templates $GIT_DIR

if [ "$GIT_DIR" != "$URL" ]; then
    # Add the github URL as github-origin
    cd $GIT_DIR
    git remote add github-origin $URL

    # Fetch master as github-master and fetch the tags too
    git fetch github-origin master:github-master --tags
	git symbolic-ref HEAD refs/heads/github-master

    cd ..
    echo Successfully cloned $URL to $GIT_DIR
    echo
else
    echo Successfully created bare git repo $GIT_DIR
fi

