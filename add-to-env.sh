#!/bin/bash
# source this script from your bash or sh shell to add this eco_tools
# directory to your PATH.
if [ ! -z "`echo $0 | fgrep add-to-env.sh`" ]; then
	echo "Usage: source path/to/eco_tools/add-to-env.sh"
	exit 1
fi

# Make sure we have a canonical path to eco_tools
eco_tools_dir=`dirname $BASH_ARGV`
pushd $eco_tools_dir > /dev/null
eco_tools_dir=`pwd -P`
popd > /dev/null
#echo eco_tools_dir=$eco_tools_dir

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
