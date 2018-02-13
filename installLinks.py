#!/usr/bin/env python
# installLinks.py
# Must have --buildTop arg as a src
# Optional: --installTop to specify destination TOP or defaults to current dir
#
# Directories are created to match each BUILD_TOP subdir,
# where subir is one of: bin include lib share

# Example:
# mkdir $INSTALL_TOP/bin       if $BUILD_TOP/bin      exists
# mkdir $INSTALL_TOP/bin/dir1  if $BUILD_TOP/bin/dir1 exists
# ...
# Soft links are created recursively for each file under BUILD_TOP
# $INSTALL_TOP/bin/file1 -> $BUILD_TOP/bin/file1
# $INSTALL_TOP/bin/file2 -> $BUILD_TOP/bin/file2
# ...
# $INSTALL_TOP/lib/file1 -> $BUILD_TOP/lib/file1
# ...

# For linux package to EPICS package, use --arch
# installLinks.py --buildTop $PROCSERV_TOP --installTop $EXTENSION_TOP --arch linux-x86
# $EXTENSION_TOP/bin/linux-x86/file1 -> $PROCSERV_TOP/bin/file1
# $EXTENSION_TOP/bin/linux-x86/file2 -> $PROCSERV_TOP/bin/file2
# ...
# $EXTENSION_TOP/lib/linux-x86/file2 -> $PROCSERV_TOP/lib/file2
# ...
# 
# For EPICS builds to EPICS installations, --arch is not used as all built architectures will be linked
# installLinks.py --buildTop $GATEWAY_TOP --installTop $EXTENSION_TOP
# $EXTENSION_TOP/bin/linux-x86/file1    -> $GATEWAY_TOP/bin/linux-x86/file1
# $EXTENSION_TOP/bin/linux-x86/file2    -> $GATEWAY_TOP/bin/linux-x86/file2
# ...
# $EXTENSION_TOP/bin/linux-x86_64/file1 -> $GATEWAY_TOP/bin/linux-x86_64/file1
# $EXTENSION_TOP/bin/linux-x86_64/file2 -> $GATEWAY_TOP/bin/linux-x86_64/file2
# ...
#

import sys
import argparse
import os
import filecmp
import traceback
import glob

def make_links( buildTop, installTop, subdir, arch=None, force=False, is_site_packages = False, is_pyinc = False, python='python2.7'):
    if not os.path.exists(buildTop):
        print "Error: buildTop %s does not exist!" % buildTop
        return
    if not os.path.exists(installTop):
        print "Error: installTop %s does not exist!" % installTop
        return
    if is_site_packages:
        subdir = 'lib/%s/site-packages' % python
    if is_pyinc:
        subdir = 'include/%s' % python
    for target in glob.glob('%s/%s/*' % ( buildTop, subdir ) ):
        if not os.path.exists(target):
            print '%s does not exist' % target
            continue
        (target_dir, target_base) = os.path.split( target )
        if subdir == 'lib' and target_base == python:
            continue
        if subdir == 'include' and target_base == python:
            continue

        # Create symlink filename
        if ( subdir == 'bin' or subdir == 'lib' ) and arch is not None:
            symlink = os.path.join( installTop, subdir, arch, target_base )
        else:
            symlink = os.path.join( installTop, subdir, target_base )

        # See if the target is a directory and if so, recurse
        if os.path.isdir( target ):
            if not os.path.isdir( symlink ):
                print "mkdir %s ..." % symlink
                os.makedirs( symlink, 0775 )
            [ symlink_path, symlink_subdir ] = os.path.split( symlink )
            [ target_path, target_subdir ] = os.path.split( target )
            make_links( target_path, symlink_path, symlink_subdir )
            continue

        if os.path.islink(symlink) and os.path.exists(symlink):
            existing_target = os.readlink(symlink)
            if existing_target == target:
                continue # same path
            st_target = os.stat(target)
            st_existing_target = os.stat(existing_target)
            if st_target.st_size == st_existing_target.st_size:
                if st_target == st_existing_target:
                    continue # same attributes (including inode, etc)
                if filecmp.cmp(target, existing_target):
                    continue # same contents
            msg = "Symbolic link %s has two possible targets:\n"
            msg += "    %s\n" % existing_target
            msg += "    %s" % target
            print msg
            # self.warnings.append(msg)
            print "Skipping link %s ..." % symlink
            continue
        
        if not force and not os.path.islink(symlink) and os.path.exists(symlink):
            print "Skipping pre-existing %s ..." % symlink
            continue

        # Remove pre-existing link or file
        if os.path.lexists(symlink):
            os.remove( symlink )

        print "Creating link %s ..." % symlink
        #print "%s -> %s" % ( symlink, target )
        os.symlink( target, symlink )
    return

def main():
    #
    # Parse the arguments.
    #
    parser = argparse.ArgumentParser()
    parser.add_argument( '-i', '--installTop', default='.', help='Install top.  Soft links created to make buildTop files accessible via paths w/ installTop.  Defaults to current dir.' )
    parser.add_argument( '-b', '--buildTop',   required=True, help='Build top.  Soft links created to bin executables, libs, etc under build top.' )
    parser.add_argument( '-a', '--arch', default=None, help='Target architecture.  If used, adds a target directory under bin, and lib subdirs.' )
    parser.add_argument( '--force', action='store_true', help='Use --force to remove conflicting files under installTop.' )
    options = parser.parse_args()

    make_links( options.buildTop, options.installTop, 'bin',     arch=options.arch, force=options.force )
    make_links( options.buildTop, options.installTop, 'lib',     arch=options.arch, force=options.force )
    make_links( options.buildTop, options.installTop, 'share',   arch=options.arch, force=options.force )
    make_links( options.buildTop, options.installTop, 'include', arch=options.arch, force=options.force )

if __name__ == '__main__':
    main()
