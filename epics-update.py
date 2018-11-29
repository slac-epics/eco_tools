#!/usr/bin/env python
#  Name: epics-update.py
#  Abs:  A tool to update EPICS packages
#
#  Example:
#    epics-update ?
#
#  Requested features to be added:
#
#==============================================================
import sys
import os
import socket
import subprocess
import argparse
import readline
import shutil
import tempfile
import textwrap
import json
import Repo
import gitRepo
import svnRepo
import Releaser 
from git_utils import *
from svn_utils import *
from site_utils import *
from version_utils import *
from eco_version import eco_tools_version

from repo_defaults import *

def process_options(argv):
    if argv is None:
        argv = sys.argv[1:]
    description =	'epics-update supports various ways of updating EPICS packages.\n'
    epilog_fmt  =	'\nExamples:\n' \
                    'epics-update --RELEASE_SITE\n' \
                    'epics-update -p asyn/R4.31-1.0.0 -p busy/R1.6.1-0.2.5\n'
    epilog = textwrap.dedent( epilog_fmt )
    parser = argparse.ArgumentParser( description=description, formatter_class=argparse.RawDescriptionHelpFormatter, epilog=epilog )
    parser.add_argument( '-p', '--package',   dest='packages', action='append', \
                        help='EPICS module-name/release-version. Ex: asyn/R4.30-1.0.1', default=[] )
    parser.add_argument( '-f', '--input_file_path', action='store', help='Read list of module releases from this file' )
    parser.add_argument( '-r', '--RELEASE_SITE', action='store_true',  help='Update RELEASE_SITE' )
    parser.add_argument( '-t', '--top',      action='store',  default='.', help='Top of release area.' )
    parser.add_argument( '-v', '--verbose',  action="store_true", help='show more verbose output.' )
    parser.add_argument( '--version',  		 action="version", version=eco_tools_version )

    options = parser.parse_args( )

    return options 

def main(argv=None):
    options = process_options(argv)

    if (options.input_file_path):
        try:
            in_file = open(options.input_file_path, 'r')
        except IOError, e:
            sys.stderr.write('Could not open "%s": %s\n' % (options.input_file_path, e.strerror))
            return None

        # Read in pairs (package release) one per line
        for line in in_file:
            # Remove comments
            line = line.partition('#')[0]

            # Add anything that looks like a module release specification
            modulePath = line.strip()
            (module, release) = os.path.split( modulePath )
            if module and release:
                options.packages += [ modulePath ]
                if options.verbose:
                    print 'Adding: %s' % modulePath

            # repeat above for all lines in file

        in_file.close()

    count = 0
    if options.RELEASE_SITE:
        curDir = os.getcwd()
        os.chdir( options.top )
        if options.verbose:
            print "Updating %s/RELEASE_SITE ..." % options.top
        inputs = assemble_release_site_inputs( batch=True )
        export_release_site_file( inputs, debug=options.verbose )
        os.chdir( curDir )
        count += 1

    if len( options.packages ) > 0:
        count += update_pkg_dependency( options.top, options.packages, verbose=options.verbose )

    print "Done: Updated %d RELEASE file%s." % ( count, "" if count == 1 else "s" )
    return 0

if __name__ == '__main__':
    status = main()
    sys.exit(status)
