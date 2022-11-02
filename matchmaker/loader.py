import logging
from collections import defaultdict

from register.models import RegRecord
from register.schedule_models import DateRecord, BreakRecord
from matchmaker.models import MatchRecord

from psd.shared import strip_pairs
from .polymatch import Dater
import math

logger = logging.getLogger("loader")


from register.models import match_category
from register.models import MATCH_NO
from register.models import MATCH_GOOD
from register.models import MATCH_THRESHOLD

class LoaderException(Exception):
    """
    Used when loading goes bad.
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


def load_regs(event, who):
    if who == 'NotNo':
        regs = RegRecord.objects.filter(cancelled=False)
    elif who == 'Paid':
        regs = RegRecord.objects.filter(paid=False)
    elif who == 'Pending':
        ## Check this is right-- basically, want all non-cancelled regs
        ## that are pending OR paid.
        regs = RegRecord.objects.filter(cancelled=False).exclude(pending=False, paid=False)
    elif who == 'In':
        regs = RegRecord.objects.filter(here=True)
    elif who == 'Test':
        regs = RegRecord.objects.all()[:20]
    elif who == 'All':
        logger.warning("Including all people -- NOT JUST 'PAID' AND 'HERE' LISTS")
        regs = RegRecord.objects.all()
    ## Is that all? Is some of the reformatting loadPeople does still needed with Django?
    return regs.filter(event=event)


def convert_match( match_score ):
    """
    Invert scores

    Ideally get the good scores in the MATCH_GOOD/2 to MATCH_GOOD range,
    bad scores below that.
    """
    if match_score > MATCH_THRESHOLD:
        return 0
    elif match_score > MATCH_GOOD:
        return 1 + (int)( (MATCH_GOOD/2) - (MATCH_GOOD/2)*(match_score - MATCH_GOOD) / (MATCH_THRESHOLD - MATCH_GOOD) )
    else:
        return MATCH_GOOD - match_score / 2


def load_nametags(regs):
    ## ??
    return [(r.nickname, r.psdid, p.first_name) for r in regs for p in r.people]



def load_daters(regs):
    """
    Return several lists in a dict.

    Each list is a list of Dater objects.  A dater object is a dict of likes and a psdid for a name.
    """
    events = list(set(x.event for x in regs))
    assert len(events) == 1, "Have %s different events %s" % (len(events), ",".join( [str(x) for x in events] ) )

    reg_lookup = dict((x.psdid, x) for x in regs)
    all_matches = MatchRecord.objects.filter(event=events[0], psdid1__in=reg_lookup, psdid2__in=reg_lookup)
    all_merged = dict((x.psdid, Dater(x.psdid)) for x in regs)
    all_as_gay = dict((x.psdid, Dater(x.psdid)) for x in regs)
    all_as_str = dict((x.psdid, Dater(x.psdid)) for x in regs)
    all_bad_date = dict((x.psdid, Dater(x.psdid)) for x in regs)
    all_friends = dict((x.psdid, Dater(x.psdid)) for x in regs)
    baseline = dict((x.psdid, Dater(x.psdid)) for x in regs)

    for m in all_matches:
        mscore = convert_match( m.match )
        if m.match <= MATCH_GOOD:
            logger.info( "Converting (good match) %s to %s" % (m.match, mscore ) )
            all_merged[m.psdid1][m.psdid2] = mscore
            if m.gay_ok:
                all_as_gay[m.psdid1][m.psdid2] = mscore
            ## Not an elif! For monosexuals these are both true.
            if m.str_ok:
                all_as_str[m.psdid1][m.psdid2] = mscore
        if m.match < MATCH_THRESHOLD:
            if m.match > MATCH_GOOD:
                logger.info( "Converting (bad match) %s to %s" % (m.match, mscore ) )
            all_bad_date[m.psdid1][m.psdid2] = mscore
            baseline[m.psdid1][m.psdid2] = mscore


    for r1 in regs:
        if not r1.friend_dates:
            continue
        for r2 in regs:
            if r1.psdid != r2.psdid and r2.psdid not in all_merged[r1.psdid]:
                all_friends[r1.psdid][r2.psdid] = 1

    return {'all': all_merged.values(),
            'gay': all_as_gay.values(),
            'str': all_as_str.values(),
            'bad': all_bad_date.values(),
            'friend': all_friends.values(),
            'baseline':baseline.values() }


def load_break_pairs(psdids, which_mat="both"):
    ## Used to be loadBreakMatrix, and return a matrix.
    ## Now just list of pairs.
    bad_pairs = set()
    if which_mat != 'datehistory':
        breaks = BreakRecord.objects.filter(psdid__in=psdids, other_psdid__in=psdids)
        for pair in breaks:
            bad_pairs.add(tuple(sorted([pair.psdid, pair.other_psdid])))

    if which_mat == 'additionals':
        dates = DateRecord.objects.filter(psdid__in=psdids, other_psdid__in=psdids)
        for date in dates:
            bad_pairs.add(tuple(sorted([date.psdid, date.other_psdid])))

    return bad_pairs



## I think all this needs is to be table-aware... the tables
## are getting assigned at some point.
def save_date_table(schedules, event_name, erase_old=False):
    if erase_old:
        DateRecord.objects.filter(event=event_name).delete()
    for psdid in schedules:
        for round, date_tuple in enumerate(schedules[psdid], 1):
            other_psdid, datetype = date_tuple
            if datetype == 'none' or datetype=='recess':
                continue
            date = DateRecord(psdid=psdid, other_psdid=other_psdid, round=round, said_yes=None, they_said_yes=None,
                              event=event_name, friend_date=(datetype == 'friend'))
            date.save()



#############################################################################
## Match setup code
#############################################################################

def bidirectional_clean(daters, style='min'):
    if style == 'min':
        def func(x, y):
            return min(x, y)
    elif style == 'mean':
        def func(x, y):
            if x and y: return (x+y) / 2
            else:       return 0
    elif style == 'geo':
        def func(x, y):
            if x and y: return math.sqrt( x * y )
            else:       return 0
    ## Is this superfluous? We build a friend matrix directly.
    elif style == 'friend':
        def func(x, y):
            ## Note OR, not AND
            if x or y:  return 0
            else:       return 1

    for first in daters:
        for second in daters:
            ## Cheap way of making sure we only do each pair once:
            if second.name <= first.name:
                continue

            score_a = first[second.name]
            score_b = second[first.name]
            score = func(score_a, score_b)
            if score:
                first[second.name] = second[first.name] = score
            else:
                del first[second.name]
                del second[first.name]
    return daters

# def blend_matrix(daters_a, daters_b, fix_level=4):
#     daters_a = [x.copy() for x in daters_a]
#     b_lookup = dict((x.name, x) for x in daters_b)
#     for dater in daters_a:
#         if len(dater) < fix_level:
#             ## TODO: is this right, putting in the bonus hundreds?
#             for x in dater:
#                 dater[x] *= 100
#             alt_dater = b_lookup[dater.name]
#             for x in alt_dater:
#                 dater[x] += alt_dater[x]
#     return daters_a


def get_all_daters(event, who):
    ##
    ## Step 1: load data
    ##
    logger.info("Inclusion mode = %s" % who)
    regs = load_regs(event, who)
    psdids = [x.psdid for x in regs]
    logger.info("Selected %s records" % len(regs))

    if len(regs) == 0:
        raise LoaderException( "No records selected for event %s, include %s" % (event, who, ) )

    ## Returns a dict with keys 'dates', 'friends', 'straight_rounds', 'gay_rounds'
    daters = load_daters(regs)
    breaks = load_break_pairs(psdids)

    ##
    ## Step 2: remove people who can't date
    ##
    ## TODO: Make sure strip_pairs doesn't need to return a value,
    ## and can take a list of pairs like this.
    for folks in daters.values():
        strip_pairs(folks, breaks)
    ## TODO: Put in some data integrity tests here.

    ##
    ## Step 3: make new versions of people-lists, with second-choice genders included
    ##
    ## TODO: We really blend them both into each other here? Isn't there
    ## some other place we do the fallback stuff?
    ## TODO: Commented out since this seems a bad choice. Esp now that we have omnibus bad
    ## date matrix.
    ## gay_daters = blend_matrix(daters['gay'], daters['str'])
    ## str_daters = blend_matrix(daters['str'], daters['gay'])

    ##
    ## Step 4: symmetrize preferences (so nobody likes anyone who doesn't like them back)
    ##
    #import pdb; pdb.set_trace()

    bidirectional_clean(daters['gay'], style='geo')
    bidirectional_clean(daters['str'], style='geo')
    bidirectional_clean(daters['all'], style='geo')
    bidirectional_clean(daters['bad'], style='geo')
    bidirectional_clean(daters['baseline'], style='geo')
    bidirectional_clean(daters['friend'], style='min')

    return daters

