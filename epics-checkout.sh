#!/bin/bash
if [ -z "$PSPKG_ROOT" -o -z "$TOOLS_SITE_TOP" ]; then
    if [ -d /reg/g/pcds/config/common_dirs.sh ]; then
        source /reg/g/pcds/config/common_dirs.sh
    else
        source /afs/slac/g/pcds/config/common_dirs.sh
    fi
fi

export PSPKG_RELEASE=git-utils-0.2.0
source $PSPKG_ROOT/etc/set_env.sh

eco_tools_dir=`readlink -f $(dirname $0)`
$eco_tools_dir/epics-checkout.py $*
