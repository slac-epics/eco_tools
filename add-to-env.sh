#!/bin/bash
if [    -f $SETUP_SITE_TOP/pathmunge.sh ]; then
	source $SETUP_SITE_TOP/pathmunge.sh
elif [  -f /afs/slac/g/pcds/setup/pathmunge.sh ]; then
	source /afs/slac/g/pcds/setup/pathmunge.sh 
elif [  -f /reg/g/pcds/setup/pathmunge.sh ]; then
	source /reg/g/pcds/setup/pathmunge.sh 
fi
eco_tools_dir=`dirname $0`
pathmunge $eco_tools_dir
