"""
Code to build database of who is willing to date whom
"""

from django.db import transaction

from register.schedule_models import LinkRecord, BreakRecord, DateRecord
from register.models import RegRecord, Person
from matchmaker.models import MatchRecord
from collections import defaultdict

import logging
logger = logging.getLogger(__name__)

from register.models import match_category
from register.models import MATCH_NO
from register.models import MATCH_GOOD
from register.models import MATCH_THRESHOLD

from django.db.models.query import QuerySet


def print_matrix(m, no_group=False):
    for a in m.keys():
        if not no_group or (not a[1].is_group and not a[0].is_group):
           print("%d\t %s(%s) X %s(%s)\n" % ( m[a], a[0].nickname, a[0].minicode(), a[1].nickname, a[1].minicode(),))


# def make_matrix(matrix_type):
#     assert matrix_type in ('gay','str','all')
#     lefts = RegRecord.objects.all()
#     rights = RegRecord.objects.all()
#     return dict(((l,r), l.matrix_score(r, matrix_type)) \
#                 for l in lefts for r in rights)


# def mutualize_matrix(scores):
#     for (l,r) in scores:
#         scores[l,r] = max(scores[l,r], scores[r,l])


# def make_sym_matrix(matrix_type):
#     m = make_matrix(matrix_type)
#     mutualize_matrix(m)
#     return m


def write_csv(event,fh):
    fh.write("event,PSDID1,PSDID2,match,gay_ok,str_ok\n") # header
    regs = RegRecord.objects.filter(event=event)
    for l in regs:
        for r in regs:
            match = max(l.match_horror(r), r.match_horror(l))
            gay_ok = l.ok_gay_match(r) and r.ok_gay_match(l)
            str_ok = l.ok_str_match(r) and r.ok_str_match(l)
            cells = (l.event,l.psdid,r.psdid,match,int(gay_ok),int(str_ok))
            row = ','.join(str(c) for c in cells)
            fh.write(row)
            fh.write('\n')



def sum_mean_median(nums):
    if len(nums) == 0:
        return (0,0,0)

    total = sum(nums)
    mean = float(total) / len(nums)
    ## Now, the median.
    snums = sorted(nums)
    index = len(nums) / 2
    if len(nums) % 2 == 1:
        ## Even length array: average the two middle entries.
        median = (snums[index] + snums[index - 1]) / 2.
    else:
        ## Odd length array: len/2 will be the middle.
        median = snums[index]
    return (total, mean, median)


def all_alias_history( rr ):
    """
    Get all psdids that dated anyone listed as an alias for the
    given rr
    """
    aliases = LinkRecord.objects.filter( psdid=rr.psdid )
    drids = set(c.psdid_alias for c in aliases)

    to_ban = set()
    for alias in drids:
        drs = BreakRecord.objects.filter( psdid=alias )
        to_ban ^= set(c.other_psdid for c in drs)

        odrs = BreakRecord.objects.filter(other_psdid=alias)
        to_ban ^= set(c.psdid for c in odrs)

        drs = DateRecord.objects.filter(psdid=alias).exclude( event=rr.event )
        to_ban ^= set(c.other_psdid for c in drs)

    return to_ban


def expand_psdid_set( psdid_set ):
    """
    Return all aliases of all psdids in this set
    """
    aliases = LinkRecord.objects.filter( psdid__in=psdid_set )
    return set( a.psdid_alias for a in aliases )


@transaction.atomic
def updateSingleMatch(l, r, event, update_database=True, matches=None, likes=None, likeds=None):
        """
        Update match preference for 'l' to 'r' for event 'event'
        Used for tweaking an individual dater and seeing the results.
        """
        return updateMatches( l, (r,), event, update_database=True, matches=None, likes=None, likeds=None)



@transaction.atomic
def updateMatches(l, regs, event, update_database=True, matches=None, likes=None, likeds=None, verbose=False):
        """
                Update match preference for RegRecord 'l' to all RegRecords in regs for event object event

        :param l:
        :param regs: List of RegRecord objects
        :param event:
        :param update_database:
        :param matches:
        :param likes:
        :param likeds:
        :param verbose:
        :return: String describing the update
        """
        alladd = l.all_additionals()
        allpast = l.all_past_dates(exclude_event=event.event)
        numadd = len(alladd)

        alladd ^= allpast
        ltot = len(alladd)
        alladd ^= all_alias_history(l)
        nalias = len(alladd) - ltot
        alladd ^= expand_psdid_set(alladd)
        nexp = len(alladd) - nalias - ltot
        outputStr = "%7s [brks: %2d past: %2d alias: %2d expnd: %2d]: " % (l.psdid, numadd, len(allpast), nalias, nexp)

        tick = 0

        for r in regs:
            tick = tick + 1
            if l.psdid == r.psdid:
                continue

            lint, expl1 = l.match_horror_full(r, event)
            rint, expl2 = r.match_horror_full(l, event)

            # Already have dated/broken link
            if r.psdid in alladd and max(lint, rint) <= MATCH_THRESHOLD:
                outputStr += "b"

            if not r.psdid in alladd and lint <= MATCH_THRESHOLD:
                if matches != None:
                    likes[l.psdid] += 1
                    likeds[r.psdid] += 1
                match = max(lint, rint)
                if match <= MATCH_THRESHOLD:
                    if match <= MATCH_GOOD:
                        if matches != None:
                            matches[l.psdid] += 1
                        outputStr += "*"
                    else:
                        if matches != None:
                            matches[l.psdid] += 0 #0.5
                        outputStr += "+"
                else:
                    outputStr += "."
                if update_database:
                        gay_ok = l.ok_gay_match(r)
                        str_ok = l.ok_str_match(r)
                        mt = MatchRecord(event=event.event, psdid1=l.psdid, psdid2=r.psdid, match=lint,
                                         gay_ok=gay_ok, str_ok=str_ok)
                        mt.save()

        if update_database and matches != None:
            l.matches = matches[l.psdid]
            l.oneway = likes[l.psdid]
            l.save()

        return outputStr


@transaction.atomic
def updateMatches(l, regs, event, update_database=True, matches=None, likes=None, likeds=None, verbose=False):
    """
            Update match preference for RegRecord 'l' to all RegRecords in regs for event object event

    :param l:
    :param regs: List of RegRecord objects
    :param event:
    :param update_database:
    :param matches:
    :param likes:
    :param likeds:
    :param verbose:
    :return: String describing the update
    """
    alladd = l.all_additionals()
    allpast = l.all_past_dates(exclude_event=event.event)
    numadd = len(alladd)

    alladd ^= allpast
    ltot = len(alladd)
    alladd ^= all_alias_history(l)
    nalias = len(alladd) - ltot
    alladd ^= expand_psdid_set(alladd)
    nexp = len(alladd) - nalias - ltot
    outputStr = "%9s [brks: %2d past: %2d alias: %2d expnd: %2d]: " % (l.psdid, numadd, len(allpast), nalias, nexp)

    tick = 0

    for r in regs:
        tick = tick + 1
        if l.psdid == r.psdid:
            continue

        lint, expl1 = l.match_horror_full(r, event)
        rint, expl2 = r.match_horror_full(l, event)

        if False:
            outputStr += '\n'
            outputStr += '\n'.join(expl1)
            outputStr += '\n'.join(expl2)
            outputStr += '\n\n'

        # Already have dated/broken link
        if r.psdid in alladd and max(lint, rint) <= MATCH_THRESHOLD:
            outputStr += "b"

        if not r.psdid in alladd and lint <= MATCH_THRESHOLD:
            if matches != None:
                likes[l.psdid] += 1
                likeds[r.psdid] += 1
            match = max(lint, rint)
            if match <= MATCH_THRESHOLD:
                if match <= MATCH_GOOD:
                    if matches != None:
                        matches[l.psdid] += 1
                    outputStr += "*"
                else:
                    if matches != None:
                        matches[l.psdid] += 0  # 0.5
                    outputStr += "+"
            else:
                outputStr += "."
            if update_database:
                gay_ok = l.ok_gay_match(r)
                str_ok = l.ok_str_match(r)
                mt = MatchRecord(event=event.event, psdid1=l.psdid, psdid2=r.psdid, match=lint,
                                 gay_ok=gay_ok, str_ok=str_ok)
                mt.save()

    if update_database and matches != None:
        l.matches = matches[l.psdid]
        l.oneway = likes[l.psdid]
        l.save()

    return outputStr


@transaction.atomic
def updateMatchPairsFor( rr, update_database=True, verbose=False):
    """
    Update match preference for RegRecord 'l' to all RegRecords in regs for event object event

    :param rr: RegRecord to update matches for
    :param regs: List of RegRecord objects
    :param event:
    :param update_database:
    :param verbose:
    :return: String describing the update
    """

    regs = RegRecord.objects.filter( event=rr.event, cancelled=False )
    assert isinstance(regs, QuerySet )

    alladd = rr.all_additionals()
    numadd = len(alladd)

    allpast = rr.all_past_dates(exclude_event=rr.event)

    alladd ^= allpast
    ltot = len(alladd)

    alladd ^= all_alias_history(rr)
    nalias = len(alladd) - ltot
    alladd ^= expand_psdid_set(alladd)
    nexp = len(alladd) - nalias - ltot

    outputStr = "Matching for %s\n    # Breaks: %2d (from breakrecords)\n# Past Dates: %2d\n     # alias: %2d (dates, etc., from linked psd IDs)\n  # expanded: %2d (alt PSD IDs from original set)\n\n" % (rr.psdid, numadd, len(allpast), nalias, nexp)

    tick = 0

    likes = 0
    matches = 0
    likeds = 0
    brokens = 0

    if update_database:
        MatchRecord.objects.filter(event=rr.event, psdid1 = rr.psdid).delete()
        MatchRecord.objects.filter(event=rr.event, psdid2 = rr.psdid).delete()


    for r in regs:

        tick = tick + 1
        if rr.psdid == r.psdid:
            continue

        lint, expl1 = rr.match_horror_full(r, rr.event)
        rint, expl2 = r.match_horror_full(rr, rr.event)


        outputStr += "\n%3d %9s: " % ( tick, r.psdid )

        # Already have dated/broken link
        if r.psdid in alladd:
            if max(lint, rint) <= MATCH_THRESHOLD:
                outputStr += "match, but already dated/link broken"
            else:
                outputStr += "link broken (prior date or hand break)"
            brokens += 1
            continue

        if rint <= MATCH_THRESHOLD:
            likeds += 1

        if not r.psdid in alladd and lint <= MATCH_THRESHOLD:
            likes += 1
            match = max(lint, rint)
            if match <= MATCH_THRESHOLD:
                if match <= MATCH_GOOD:
                    if matches != None:
                        matches += 1
                    outputStr += "match"
                else:
                    if matches != None:
                        matches += 0  # 0.5
                    outputStr += "poor match"
            else:
                outputStr += "no match (but liked)"
        else:
            outputStr += "no match (mutual)"

        if verbose:
            outputStr += "\n\t%s->%s: %s = %d\n\t%s->%s: %s = %d" % ( rr.psdid, r.psdid, expl1, lint, r.psdid, rr.psdid, expl2, rint )

        if update_database:
            if lint <= MATCH_THRESHOLD:
                gay_ok = rr.ok_gay_match(r)
                str_ok = rr.ok_str_match(r)
                mt = MatchRecord(event=rr.event, psdid1=rr.psdid, psdid2=r.psdid, match=lint,
                                 gay_ok=gay_ok, str_ok=str_ok)
                mt.save()
            if rint <= MATCH_THRESHOLD:
                gay_ok = r.ok_gay_match(r)
                str_ok = r.ok_str_match(r)
                mt = MatchRecord(event=rr.event, psdid1=r.psdid, psdid2=rr.psdid, match=rint,
                                 gay_ok=gay_ok, str_ok=str_ok)
                mt.save()


    if update_database:
        rr.matches = matches
        rr.oneway = likes
        rr.save()
    outputStr += "\n\nRecords examined: %d\nMatches: %d\nLikes: %d\nLiked by: %d\nBroken %d" % ( tick, matches, likes, likeds, brokens, )

    return outputStr




def updateMatchPairsFor_oldversion( rr, event ):
    """
    Update single person
    Also regenerate all matches _to_ single person.

    :param rr:  RegRecord
    :param event:  Event object
    :return: Result (as string) of the matching checks
    """

    regs = RegRecord.objects.filter(event=event.event, cancelled=False)

    assert isinstance(regs, QuerySet )

    outputStr = updateMatches( rr, regs, event, True )

    outputStr += "\n\nReverse matching updates:\n"

    for r in regs:
        outputStr += "%s\n" % ( updateSingleMatch( r, rr, event, True ), )

    return outputStr





def updateMatchRecords_async(event, update_database=True, last_triple=False, verbose=False):
    """
    Figure out pairs of potential dates.   Also store number of matches
    for each regrecord.

    Will not match folks who have previous dating history or who are 'banned' by
    a special entry in the 'additionals' table.

    Regarding the gay_ok and str_ok flags: this code makes an _asymmetric matrix_ where entries are nonzero
        if psdid1 is okay with it being a gay dating round or straight dating round.

    Returns: triple of (number matches, number regrecords, number of possible pairings)
    """

    yield "Generating match records (who can date whom) for event %s (name %s)\n" % (event, event.event )

    MatchRecord.objects.filter( event=event.event ).delete()

    yield """
Counts:
breaks - number of hand-coded breaks in database for this PSDID
  past - number of past recorded dates in database, excluding this event, for this PSDID
 alias - number of dates connected to any alias of given PSDID
expand - number of aliases connected to people given PSDID has dated.

Codes:
       . = one-way match from person to another (so no mutual match)
       + = tolerable match
       * = good match
       b = broken match due to prior history or break record.
"""
    regs = RegRecord.objects.filter(event=event.event, cancelled=False)

    ticker=0
    matches = defaultdict(int)
    likes = defaultdict(int)
    likeds = defaultdict(int)

    # force the entire regs list to load by calling len()
    yield "\nNumber of regrecords fetched: %s\n" % (len(regs), )
    logger.info( "Fetched %s records" % ( len(regs) ) )
    
    for l in regs:
        ticker = ticker + 1
 
        outputStr = updateMatches( l, regs, event, update_database, matches, likes, likeds, verbose )
        next_line = "%03d] %s\n" % (ticker, outputStr, )
        logger.info( next_line )
        yield next_line

    yield("%s total matches: mean = %s,  median = %s\n" % sum_mean_median(matches.values())  )
    yield("%s total interest: mean = %s,  median likes = %s\n" % sum_mean_median(likes.values()) )
    yield("Is liked by = %s\n" % ( sum_mean_median(likeds.values())[2], ) )

    if last_triple:
        recticker=(len(regs)-1)*len(regs)
        logger.info( "Finishing update_async" )
        yield (sum(matches.values()), len(regs), recticker )





def updateMatchRecords(event, verbose=False, update_database=True):
    """
    Returns: triple of (number matches, number regrecords, number of possible pairings)
    """

    recIter = updateMatchRecords_async( event, update_database, last_triple=True, verbose=verbose )
    for ln in recIter:
        if verbose:
            print ln

    return ln


