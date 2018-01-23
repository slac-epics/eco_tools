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

# NOTE: The epics-release.sh script is normally not used, as
# the eco_tools soft link epics-release points directly to
# epics-release.py to avoid losing quotes around -m "Message Contents"
# which breaks comment args when this epics-release.sh script is invoked.
export PSPKG_RELEASE=git-utils-0.2.0
source $PSPKG_ROOT/etc/set_env.sh

eco_tools_dir=`dirname $0`
$eco_tools_dir/epics-release.py $*
