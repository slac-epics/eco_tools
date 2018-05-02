#!/bin/bash
# This file is intended to be sourced by eco_tools launchers to
# setupt the minimum env for common eco_tools.
# 
# For gitRecommitBranch.py and other migration tools, use add-to-env.sh
# instead of this script.
#
if [ ! -z "`echo $0 | fgrep get_eco_common_env.sh`" ]; then
	echo "Usage: source path/to/eco_tools/get_eco_common_env.sh"
	exit 1
fi

# Make sure we have a canonical path to eco_tools
this_script=`readlink -f $BASH_ARGV`
eco_tools_dir=`readlink -f $(dirname $this_script)`

# Make sure we have PSPKG_ROOT and SETUP_SITE_TOP
if [ -z "$PSPKG_ROOT" -o -z "$TOOLS_SITE_TOP" ]; then
	if [ ! -z "$CONFIG_SITE_TOP" -a -f $CONFIG_SITE_TOP/common_dirs.sh ]; then
		source $CONFIG_SITE_TOP/common_dirs.sh
	elif [  -f /usr/local/controls/config/common_dirs.sh ]; then
		source /usr/local/controls/config/common_dirs.sh
	elif [  -f /reg/g/pcds/pyps/config/common_dirs.sh ]; then
		source /reg/g/pcds/pyps/config/common_dirs.sh
	elif [  -f /afs/slac/g/pcds/config/common_dirs.sh ]; then
		source /afs/slac/g/pcds/config/common_dirs.sh
	elif [  -f /afs/slac/g/lcls/epics/config/common_dirs.sh ]; then
		source /afs/slac/g/lcls/epics/config/common_dirs.sh
	fi
fi

# Add the git-utils-0.2.0 pkg_mgr release for python/2.7.5
export PSPKG_RELEASE=git-utils-0.2.0
if [  -d  "$PSPKG_ROOT/release/$PSPKG_RELEASE" ]; then
	source $PSPKG_ROOT/etc/set_env.sh
fi

