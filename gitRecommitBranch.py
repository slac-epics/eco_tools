#!/usr/bin/env python
'''This script imports a git repository branch from a git branch w/ a different origin.
Typically this will happen when combining version histories of the same
package from different version control systems and/or repositories.
Merge parents can be provided for specific commits to rewrite the branches
commit history to show the appropriate merge history vs the master branch.'''

import argparse
import os.path
import shutil
import sys
import tempfile

# Import GitPython classes
# GitPython can be obtained from https://github.com/gitpython-developers/GitPython
from git import *

def importBranchTo( repo, parentBranch, srcBranch, srcBranchEnd=None, mergePoints=None, dstBranch='new-branch', verbose=False ):
    '''Takes a GitPython repo, the name of the destination branch, the source branch to import,
       an optional source branch end commit, and a mergePoints dictionary which
       should have at least one merge point whose sha1 is on the source branch
       and whose value is on the parent branch.
       The mergePoints keys are sha1 hash strings, and the values are commit objects'''

    if dstBranch is None:
        dstBranch = 'new-branch'
    print "Importing branch %s w merge points on %s to branch %s" % ( srcBranch, parentBranch, dstBranch )

    if mergePoints is None or len(mergePoints.keys()) == 0:
        raise Exception( 'Must provide at least one merge point!' )
 
    for key in mergePoints.keys():
        if not repo.is_ancestor( key, srcBranch ):
            raise Exception( 'Merge point %.7s is not on branch %s!' % ( key, srcBranch ) )
        if not repo.is_ancestor( mergePoints[key].hexsha, parentBranch ):
            raise Exception( 'Parent commit %.7s is not on branch %s!' % ( mergePoints[key].hexsha, parentBranch ) )

    srcCommits = list( repo.iter_commits(srcBranch) )
    initial = srcCommits[-1].hexsha
    if not initial in mergePoints:
        print "Warning: The first commit on branch %s, %.7s, does not have a merge point!\n" % ( srcBranch, initial )

    newCommit = None
    while len(srcCommits) > 0:
        c = srcCommits.pop()
        if c is None:
            break
        try:
            mergePoint = mergePoints[c.hexsha]
        except KeyError:
            mergePoint = None
        parents	= c.parents
        if newCommit is not None:
            parents = tuple( [ newCommit ] + list(parents)[1:] )
        if verbose and mergePoint is not None:
            print "Found merge point: %.7s" % c.hexsha
            print "Parent is : %.7s" % mergePoint
            parents	= tuple( list(parents) + [ mergePoint ] )

        if c.author_tz_offset < 0:
            author_date	= "%d -%04d" % ( c.authored_date,  -c.author_tz_offset	  )
        else:
            author_date	= "%d +%04d" % ( c.authored_date,	c.author_tz_offset	  )
        if c.committer_tz_offset < 0:
            commit_date	= "%d -%04d" % ( c.committed_date, -c.committer_tz_offset )
        else:
            commit_date	= "%d +%04d" % ( c.committed_date,	c.committer_tz_offset )
        newCommit	= Commit.create_from_tree( repo, repo.tree(c.tree), c.message,
                        parent_commits=parents,
                        author=c.author,		author_date=author_date,
                        committer=c.committer,	commit_date=commit_date )
        if verbose and mergePoint is not None:
            print "Created new commit: %s" % newCommit

    new_branch = repo.create_head( dstBranch )
    new_branch.set_commit( newCommit.hexsha )
    if verbose:
        print "Done importing branch %s.\n" % ( srcBranch )

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='''This script recreates the git commit history for a branch w/
                                                     merge points added as specified in the arguments.
                                                     A merge point consists of two colon separated git object
                                                     references, which can be hex sha1 id's, or symbolic references
                                                     such as tags.
                                                     Example: -m 7f3456a7:R2-0 -m 388adcaa:R2-1''')
    parser.add_argument( '-m', '--mergePoint',   action='append', required=True,  help='mergePoint, ex: 7f3456a7:R2-0' )
    parser.add_argument( '-p', '--parentBranch', action='store',  required=True,  help='Name of parent branch' )
    parser.add_argument( '-d', '--dstBranch',    action='store',  required=True,  help='Name of dest branch' )
    parser.add_argument( '-s', '--srcBranch',    action='store',  required=True,  help='Name of src branch' )
    parser.add_argument( '-v', '--verbose',      action='store_true',  help='Print more status msgs' )

    args = parser.parse_args( )

    # Use current directory for git repo
    gitRepo = Repo()
    mergePoints = { }

    # Validate the branch specifiers
    try:
        branchCommit = gitRepo.commit( args.srcBranch )
    except BadName:
        print "srcBranch %s is not a valid commit" % args.srcBranch
        sys.exit(1)
    try:
        branchCommit = gitRepo.commit( args.parentBranch )
    except BadName:
        print "parentBranch %s is not a valid commit" % args.parentBranch
        sys.exit(1)
    try:
        branchCommit = gitRepo.commit( args.dstBranch )
        print "dstBranch %s already exists!" % args.dstBranch
        sys.exit(1)
    except BadName:
        pass

    # Validate the mergePoints
    for m in args.mergePoint:
        mergePoint = m.split(':')
        if len(mergePoint) != 2:
            print "Invalid mergePoint: %s\nShould be 2 colon separated commit identifiers." % m
            sys.exit(1)
        try:
            mergeCommit	= gitRepo.commit( mergePoint[0] )
        except BadName:
            print "MergePoint %s is not a valid commit" % mergePoint[0]
            sys.exit(1)
        try:
            mergeParent	= gitRepo.commit( mergePoint[1] )
        except BadName:
            print "MergePoint parent %s is not a valid commit" % mergePoint[1]
            sys.exit(1)
        if not gitRepo.is_ancestor( mergeCommit.hexsha, args.srcBranch ):
            print 'Merge point %.7s is not on branch %s!' % ( mergeCommit.hexsha, args.srcBranch )
            sys.exit(1)
        if not gitRepo.is_ancestor( mergeParent.hexsha, args.parentBranch ):
            print 'Parent commit %.7s is not on parent branch %s!' % ( mergeParent.hexsha, args.parentBranch )
            sys.exit(1)
        mergePoints[ mergeCommit.hexsha ] = mergeParent

    # Hack for testing
    #mergeCommit	= gitRepo.commit( 'ccbc86e52' )
    #mergeParent	= gitRepo.commit( 'R2-0' )
    #mergePoints[ mergeCommit.hexsha ] = mergeParent
    #mergeCommit	= gitRepo.commit( '94964409' )
    #mergeParent	= gitRepo.commit( 'R2-1' )
    #mergePoints[ mergeCommit.hexsha ] = mergeParent

    # Import the branch
    importBranchTo( gitRepo, args.parentBranch, args.srcBranch, dstBranch=args.dstBranch, mergePoints=mergePoints, verbose=args.verbose )

    print "Done."

