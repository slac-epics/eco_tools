#!/bin/bash
# source this script from your bash or sh shell to add this eco_tools
# directory to your PATH.
# You'll need to do this from your shell to do development of these
# scripts, or to use the module conversion and migration tools it provides.
#
# NOTE: Don't run this in your shell startup if you prefer some other python installation.
#
if [ ! -z "`echo $0 | fgrep add-to-env.sh`" ]; then
	echo "Usage: source path/to/eco_tools/add-to-env.sh"
	exit 1
fi

# Make sure we have a canonical path to eco_tools
this_script=`readlink -f ${BASH_SOURCE[0]}`
eco_tools_dir=`readlink -f $(dirname $this_script)`

# Make sure we have PSPKG_ROOT and SETUP_SITE_TOP
if [ -z "$PSPKG_ROOT" -o -z "$SETUP_SITE_TOP" ]; then
	if [    -f /usr/local/controls/config/common_dirs.sh       ]; then
		source /usr/local/controls/config/common_dirs.sh
	elif [  -f /reg/g/pcds/pyps/config/common_dirs.sh       ]; then
		source /reg/g/pcds/pyps/config/common_dirs.sh
	elif [  -f /afs/slac/g/lcls/epics/config/common_dirs.sh ]; then
		source /afs/slac/g/lcls/epics/config/common_dirs.sh
	elif [  -f /afs/slac/g/pcds/config/common_dirs.sh       ]; then
		source /afs/slac/g/pcds/config/common_dirs.sh
	fi
fi

# Make sure we have a pathmunge function defined
if [ -z "`declare -f pathmunge`" ]; then
	if [    -f $SETUP_SITE_TOP/pathmunge.sh ]; then
		source $SETUP_SITE_TOP/pathmunge.sh
	elif [  -f /afs/slac/g/pcds/setup/pathmunge.sh ]; then
		source /afs/slac/g/pcds/setup/pathmunge.sh 
	elif [  -f /reg/g/pcds/setup/pathmunge.sh ]; then
		source /reg/g/pcds/setup/pathmunge.sh 
	fi
fi

# Add this eco_tools folder to the front of PATH
pathmunge $eco_tools_dir
