#!/bin/bash
if [ -z "$PSPKG_ROOT" -o -z "$TOOLS_SITE_TOP" ]; then
    if [    -f /usr/local/controls/config/common_dirs.sh ]; then
        source /usr/local/controls/config/common_dirs.sh
    elif [  -f /reg/g/pcds/config/common_dirs.sh ]; then
        source /reg/g/pcds/config/common_dirs.sh
    elif [  -f /afs/slac/g/lcls/config/common_dirs.sh ]; then
        source /afs/slac/g/lcls/config/common_dirs.sh
    else
        source /afs/slac/g/pcds/config/common_dirs.sh
    fi
fi

export PSPKG_RELEASE=git-utils-0.2.0
source $PSPKG_ROOT/etc/set_env.sh

this_script=`readlink -f $0`
eco_tools_dir=`readlink -f $(dirname $this_script)`
$eco_tools_dir/epics-versions.py $*
