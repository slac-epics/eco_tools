#!/bin/bash
if [ -z "$PSPKG_ROOT" -o -z "$TOOLS_SITE_TOP" ]; then
    if [    -f /usr/local/controls/config/common_dirs.sh ]; then
        source /usr/local/controls/config/common_dirs.sh
    elif [  -f /reg/g/pcds/config/common_dirs.sh ]; then
        source /reg/g/pcds/config/common_dirs.sh
    else
        source /afs/slac/g/pcds/config/common_dirs.sh
    fi
fi

export PSPKG_RELEASE=git-utils-0.2.0
source $PSPKG_ROOT/etc/set_env.sh

eco_tools_dir=`dirname $0`
$eco_tools_dir/epics-release.py $*
