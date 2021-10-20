#!/usr/bin/env python
'''This script imports a git repository branch from a git branch w/ a different origin.
Typically this will happen when combining version histories of the same
package from different version control systems and/or repositories.
Merge parents can be provided for specific commits to rewrite the branches
commit history to show the appropriate merge history vs the trunk branch.'''

import argparse
import os.path
import shutil
import sys
import tempfile


# Add git-utils-0.2.0 release w/ GitPython to path
import gitdb
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
 
    srcCommits	= list( repo.iter_commits(srcBranch) )
    lastCommit	= None
    if srcBranchEnd is not None:
        lastCommit = gitRepo.commit( srcBranchEnd )
    else:
        initial = srcCommits[-1].hexsha
        if not initial in mergePoints:
            print "Warning: The first commit on branch %s, %.7s, does not have a merge point!\n" % ( srcBranch, initial )

    # Grab the tags so we can remap them as well
    tags = gitRepo.tags

    newCommit = None
    while len(srcCommits) > 0:
        commit = srcCommits.pop()
        if commit is None:
            break
        if lastCommit is not None and commit != lastCommit:
            continue

        try:
            mergePoint = mergePoints[commit.hexsha]
        except KeyError:
            mergePoint = None
        parents	= commit.parents
        if newCommit is not None:
            parents = tuple( [ newCommit ] + list(parents)[1:] )
        if lastCommit is not None and commit == lastCommit:
            if verbose:
                print "Ending  branch at: %.7s" % commit.hexsha
            lastCommit	= None
            parents		= []
        if mergePoint is not None:
            parents	= tuple( list(parents) + [ mergePoint ] )
            if verbose:
                print "Found merge point: %.7s" % commit.hexsha
                print "Parents are : (",
                for p in parents:
                    print " %.7s" % p.hexsha,
                print ")"

        if commit.author_tz_offset < 0:
            author_date	= "%d -%04d" % ( commit.authored_date,  -commit.author_tz_offset/3600	  )
        else:
            author_date	= "%d +%04d" % ( commit.authored_date,	commit.author_tz_offset/3600	  )
        if commit.committer_tz_offset < 0:
            commit_date	= "%d -%04d" % ( commit.committed_date, -commit.committer_tz_offset/3600 )
        else:
            commit_date	= "%d +%04d" % ( commit.committed_date,	commit.committer_tz_offset/3600 )
        newCommit	= Commit.create_from_tree( repo, repo.tree(commit.tree), commit.message,
                        parent_commits=parents,
                        author=commit.author,		author_date=author_date,
                        committer=commit.committer,	commit_date=commit_date )
        if verbose or mergePoint is not None:
            print "Created new commit: %.7s from %.7s" % ( newCommit.hexsha, commit.hexsha )

        # Remap any tags from the old commit to the new one
        for tagRef in tags:
            #if ( tagRef.commit != commit and
            #   ( tagRef.commit.parents is None or
            #	 len(tagRef.commit.parents) == 0 or
            #	 tagRef.commit.parents[0].tree != commit.tree ) ):
            #	continue
            if tagRef.commit.tree != commit.tree:
                continue
            #print "tag %s: %s %.7s" % ( tagRef.name, tagRef.commit.message, tagRef.commit.hexsha )
            #print "commit %s %.7s" % ( commit.message, commit.hexsha )
            if tagRef.tag is not None:
                if tagRef.tag.tagger_tz_offset < 0:
                    committer_date	= "%d -%04d" % ( tagRef.tag.tagged_date, -tagRef.tag.tagger_tz_offset/3600 )
                else:
                    committer_date	= "%d +%04d" % ( tagRef.tag.tagged_date,  tagRef.tag.tagger_tz_offset/3600 )
                with gitRepo.git.custom_environment( GIT_COMMITTER_DATE  = "%s" % committer_date,
                                                     GIT_COMMITTER_EMAIL = "%s" % tagRef.tag.tagger.email,
                                                     GIT_COMMITTER_NAME  = "%s" % tagRef.tag.tagger.name ):
                    TagReference.create( gitRepo, tagRef.name, ref=newCommit, force=True, message=tagRef.tag.message )
            else:
                TagReference.create( gitRepo, tagRef.name, ref=newCommit, force=True )
            if verbose:
                print "Remapped tag %s to %.7s from %.7s" % ( tagRef.name, newCommit.hexsha, commit.hexsha )

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
    parser.add_argument( '-e', '--srcBranchEnd', action='store',  required=False, help='Last commit on src branch to recreate' )
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

        # Validate the merge commit
        try:
            mergeCommit	= gitRepo.commit( mergePoint[0] )
        except BadName:
            print "MergePoint %s is not a valid commit" % mergePoint[0]
            sys.exit(1)
        if not gitRepo.is_ancestor( mergeCommit.hexsha, args.srcBranch ):
            print 'Merge point %.7s is not on branch %s!' % ( mergeCommit.hexsha, args.srcBranch )
            sys.exit(1)

        # Validate the merge parent
        try:
            mergeParent	= gitRepo.commit( mergePoint[1] )
        except BadName:
            print "MergePoint parent %s is not a valid commit" % mergePoint[1]
            sys.exit(1)
        if not gitRepo.is_ancestor( mergeParent.hexsha, args.parentBranch ):
            if mergeParent.type == 'tag':
                if not gitRepo.is_ancestor( mergeParent.object.hexsha, args.parentBranch ):
                    print 'Warning, parent tag %.7s is not on parent branch %s!' % ( mergeParent.hexsha, args.parentBranch )
            elif mergeParent.type == 'commit' and mergeParent.parents is not None:
                if not gitRepo.is_ancestor( mergeParent.parents[0].hexsha, args.parentBranch ):
                    print 'Warning, parent commit %.7s is not on parent branch %s!' % ( mergeParent.hexsha, args.parentBranch )
            else:
                print 'Warning, commit %.7s is not on parent branch %s!' % ( mergeParent.hexsha, args.parentBranch )

        # Register the mergePoint
        mergePoints[ mergeCommit.hexsha ] = mergeParent

    # Import the branch
    importBranchTo( gitRepo, args.parentBranch, args.srcBranch, args.srcBranchEnd, dstBranch=args.dstBranch, mergePoints=mergePoints, verbose=args.verbose )

    print "Done."

