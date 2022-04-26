#!/bin/bash

API=https://api.github.com
SLAC_EPICS=https://github.com/slac-epics
test -z $1 && echo "Usage: push2slac-epics.sh githubUserName:githubPassword" 1>&2 && exit 1
GH_USER=$1

# Get list of repos under slac-epics
REPOS=/tmp/slac-epics-repos-$$
echo "Fetching $SLAC_EPICS module list ..."
curl ${API}/orgs/slac-epics/repos > $REPOS
pushd $GIT_TOP/package/epics/modules
for m in *.git
	do
		MODNAME=${m/.git/}
		fgrep full_name $REPOS | fgrep "slac-epics/$MODNAME" 
		if (($?)); then
			echo "Creating $SLAC_EPICS/$m ..."
			curl -u $GH_USER ${API}/orgs/slac-epics/repos -d "{\"name\":\"$MODNAME\"}" 2>&1 > /dev/null
		fi
		echo "Updating $SLAC_EPICS/$m ..."
		git --git-dir=$m push --all $SLAC_EPICS/$m
		git --git-dir=$m push --tags $SLAC_EPICS/$m
	done
popd

# Push base as well
git --git-dir=$GIT_TOP/package/epics/base/base.git push --all $SLAC_EPICS/epics-base.git
git --git-dir=$GIT_TOP/package/epics/base/base.git push --tags $SLAC_EPICS/epics-base.git
