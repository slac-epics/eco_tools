#!/bin/bash

this_script=`readlink -f ${BASH_SOURCE[0]}`
eco_tools_dir=`readlink -f $(dirname $this_script)`
#source $eco_tools_dir/setup_eco_env.sh
source $eco_tools_dir/add-to-env.sh

$eco_tools_dir/svnModuleToGit.py  "$@"
