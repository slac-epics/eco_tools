#!/bin/bash

this_script=`readlink -f ${BASH_SOURCE[0]}`
eco_tools_dir=`readlink -f $(dirname $this_script)`
source $eco_tools_dir/setup_eco_env.sh

$eco_tools_dir/epics-build.py $* 2>&1 | tee build.log
exit ${PIPESTATUS[0]}
