"""
This module schedules dates

Key method is 'make_schedules_random'

It takes as input (via the database) the match matrices which tell us who likes who.

IMPORTANT:
This is called by the date_scheduler module.  Look there first.
"""

import math
import random
import logging

from collections import defaultdict

from register.table_models import RecessRecord

MAGIC_TABLE_NUMBER = 60

from psd.shared import strip_matches

logger = logging.getLogger(__name__)

def weighted_choice(d):
    total = sum(d.itervalues())
    rnd = random.random() * total
    for k in d:
        rnd -= d[k]
        if rnd < 0:
            return k

class Dater(defaultdict):
    '''This class represents one person's preferences. It maps
       psdids to quality-of-match scores, e.g. {'AB123': 10, 'FG354': 1}. Each
       Dater has a .name attribute.

       It is a subclass of defaultdict, meaning that if you
       iterate over this object, you get a list of all psdids
       that this person has an interest in dating. (The
       "default" part is that if you look up a missing key,
       you get 0 instead of a thrown exception.'''

    def __init__(self, name, d=None):
        d = d or ()
        self.name = name
        super(Dater, self).__init__(int, d)

    def copy(self, exclude=None):
        new_dater = Dater(self.name, super(Dater, self).copy())
        if exclude:
            for psdid in exclude:
                if psdid in new_dater:
                    del new_dater[psdid]
        return new_dater

    def __str__(self):
        return "<Dater - %s - %s>" % (self.name, dict(self))




class Slate(dict):
    '''This class represents what will happen during one round.
       It maps psdids to (partner, datetype) tuples, e.g.
       {'AB123': ('JJ001', 'main'), 'FG354': ('', 'none')}.

       It is a subclass of dict with custom methods for adding
       dates to it. If you iterate over it, you get a list of
       all psdids that have an assigned state for this round
       (potentially including people who have recess or who
       have nothing at all going on).'''

    def __init__(self):
        self.count = 0

    def add(self, date, style):
        assert type(date) is Date
        if date.name1 in self:
            raise ValueError, "%s is dating %s, can't date" % (date.name1, self[date.name1], date.name2)
        if date.name2 in self:
            raise ValueError, "%s is dating %s, can't date" % (date.name2, self[date.name2], date.name1)
        self[date.name1] = (date.name2, style)
        self[date.name2] = (date.name1, style)
        self.count += 1

    def extend(self, dates, style='unknown'):
        """
        Add list of dates to slate
        """
        for date in dates:
            self.add(date, style)



class Date(object):
    '''This class represents a date. Maybe we should just use DateRecord for it.'''
    def __init__(self, a, b):
        self.name1 = a
        self.name2 = b
        #self.datetype = datetype


class Itinerary(dict):
    '''This class represents one person's date sheet. It's a
       dict whose keys are POSITIVE integers (round numbers)
       and whose values are (partner, datetype) tuples, e.g.
       {'1': ('JJ001', 'main'), '3': ('FG354': 'friend')}

       Each itinerary has a .name attribute and protection
       against setting keys that don't look like round numbers.
       Iterating over it gives a sequence of 2-tuples, with
       the iterator filling in ('', 'none') for unassigned
       rounds. len() will return the number of assigned
       rounds.'''

    def __init__(self, name, n_rounds):
        self.name = name
        self.n_rounds = n_rounds

    def __setitem__(self, k, v):
        if not isinstance(k, int) or k < 1:
            raise ValueError, "Round number must be positive integer, not %s" % k
        super(Itinerary, self).__setitem__(k, v)

    def __iter__(self):
        for i in range(1, self.n_rounds +1):
            yield self.get(i) or ('', 'none')

    def count_dates(self):
        cnts = {}
        for date in self.itervalues():
            cnts[date[1]] = cnts.get(date[1],0) + 1
        return cnts



## Schedule a single round
## Select pairs that will date until there is nothing left to match up
## 'people' is a list of Dater objects.
def pair_off(people):
    ## List of people from MOST matchable to LEAST.
    ## (Note: that's the reverse of old code.)
    ##
    ## Copy people -- we'll be deleting fields from them.
    logger.info("Pairing off %s people" % len(people))
    people = [x.copy() for x in people]
    done = set()
    matches = []
    while len(people) > 1:
        person = people[-1]
        if person.name not in done and any(person.values()):
            name = people[-1].name
            pick = weighted_choice(people[-1])
            matches.append(Date(name, pick))
            logger.debug("%s picked %s with score %s" % (name, pick, people[-1][pick]))
            for person in people:
                if name in person: del person[name]
                if pick in person: del person[pick]
            done.add(name)
            done.add(pick)
        people.pop()
    return matches




def pair_off_random(people, trials, skips=None):
    trials = max(trials, 1)
    possible = [x for x in people if len(x)]
    desired = len(possible) / 2
    best = []
    for i in range(trials):
        logger.debug("pair_off_random pairing attempt #%s/%s - %s people" % (i+1, trials, len(people)))
        t2 = order_by_chances(people, skips)

        pairs = pair_off(t2)
        ln = len(pairs)
        logger.debug("    Got %s pairs" % ln)

        if i > 0:
            if ln > len(best):
                best = pairs
                logger.debug("    ... best so far.")
            else:
                logger.debug("    ... rejecting.")
        else:
            best = pairs

        if ln == desired:
            logger.debug("    Max possible - no more trials.")
            break
        elif ln == 0:
            logger.debug("    No matches - more trials won't help.")
            break
    logger.info("%s paired of %s eligible (%s total) people" % (len(best) * 2, len(possible), len(people)))
    return best


def order_by_chances(people, rounds_missed=None, randomness=1.5):
    ## Sort people from *most* matchable to *least* matchable.
    logger.debug("Ordering %s people. Skips: %s" % (len(people), rounds_missed))
    boosts = dict((x.name, random.random() * randomness) for x in people)
    if rounds_missed is None:
        def score(x):
            return min(10, len(x)) + boosts[x.name]
    else:
        def score(x):
            ## Not positive I understand this, but it's definitely the
            ## algorithm from before. Mostly definitely?
            ## Idea: if have more than 10 matches, you only get dinged 0.25 per match
            ## above 10 (so someone with 30 possible dates is not totally always last to pick)
            #pieces = sorted((10, len(x)))
            #return (-rounds_missed.get(x.name, 0), pieces[0] + pieces[1]/4 + boosts[x.name])
            return ( min(10, len(x)) + boosts[x.name] - 10*rounds_missed.get(x.name, 0) )
    people.sort(key=score, reverse=True)
    return people


def random_equal_partition(things, n_pieces):
    ## Copy input list.
    things = things[:]
    random.shuffle(things)
    piecelen = len(things) / n_pieces
    if len(things) % n_pieces:
        piecelen += 1
    pieces = []
    while things:
        pieces.append(things[:piecelen])
        things[:piecelen] = []
    return pieces

def assign_recesses(psdids, event_name):
    recesses = []
    templates = RecessRecord.objects.filter(event=event_name, psdid='template')
    givens = RecessRecord.objects.filter(event=event_name, volatile=False).exclude(psdid='template')
    #RecessRecord.objects.filter(event=event_name).exclude(volatile=False).exclude(psdid='template').delete()
    kinds = set(x.kind for x in templates)
    for kind in kinds:
        my_givens = [x for x in givens if x.kind == kind]
        already_done = set(x.psdid for x in my_givens)
        my_psdids = [x for x in psdids if x not in already_done]
        options = [x for x in templates if x.kind == kind]
        assignments = zip(options, random_equal_partition(my_psdids, len(options)))
        for template, assigned in assignments:
            for psdid in assigned:
                r = RecessRecord(event=event_name, psdid=psdid, rounds=template.rounds, kind=template.kind, volatile=True)
                recesses.append(r)
    recesses.extend(givens)
    return recesses

def seed_schedules_with_recesses(recesses):
    schedules = {}
    for r in recesses:
        rounds = [int(x) for x in r.rounds.split(',')]
        for round in rounds:
            if round not in schedules:
                schedules[round] = Slate()
            assert r.psdid not in schedules[round]
            schedules[round][r.psdid] = (r.kind, 'recess')
    return schedules


def add_more_dates( slate, people, skips, date_type, trials ):
    logger.info( "** Adding more dates of type %s" % (date_type, ) )
    remaining = [x.copy(exclude=slate) for x in people if x.name not in slate]

    if len(remaining) > 1:
        alt_lookup = dict((x.name, x) for x in people)
        for person in remaining:
            for other in remaining:
                if other.name == person.name:
                    continue
                alt_value = alt_lookup[person.name][other.name]
                person[other.name] = max(alt_value, person[other.name])

        ## style="alt" means this round still counts as a skip
        ## for them-- in other words, bi women who end up dating a man
        ## during a gay round still go to the front of the line for
        ## women in the next gay round.
        altdates = pair_off_random(remaining, trials / 2, skips)
        logger.info("# '%s' matches = %s" % (date_type, len(altdates)) )

        if date_type == "friend":
            logger.info( "Dropping half the friend dates" )
            random.shuffle(altdates)
            altdates = altdates[:(len(altdates)/2)]
            logger.info("# Revised '%s' matches = %s" % (date_type, len(altdates)) )

        slate.extend(altdates, date_type)
        logger.info("after '%s' matches - %s people assigned out of %s" % (date_type, len(slate), len(people)))
        return slate



def make_date_schedules( daters, rounds=12, trials=20, scramble_rounds=True, initial_schedules=None):
    orig_daters = daters
    daters = {}
    for d in orig_daters:
        cpy = [x.copy() for x in orig_daters[d] ]
        if d == "gay":
            people_a = cpy
        elif d == "str":
            people_b = cpy
        elif d == "friend":
            people_f = cpy
        else:
            daters[ d ] = cpy

    if people_f == None:
        people_f = []

    schedules = initial_schedules or {}

    skips_a = defaultdict(int)
    skips_b = defaultdict(int)

    round_ids = range(1, 1 + rounds)
    if scramble_rounds:
        random.shuffle(round_ids)

    for i, round_id in enumerate(round_ids, 1):
        round_type = 'A' if round_id % 2 else 'B'
        if round_type == 'A':
            people, alt_people = people_a, people_b
            skips, alt_skips = skips_a, skips_b
            logger.info("\n\n\n*** Step %s: Processing round %s. Type = A" % (i, round_id))
        else:
            people, alt_people = people_b, people_a
            skips, alt_skips = skips_b, skips_a
            logger.info("\n\n\n*** Step %s: Processing round %s. Type = B" % (i, round_id))

        slate = schedules.get(round_id) or Slate()
        ## TODO: assert that nothing is pre-assigned except recess?
        logger.info("%s people pre-assigned" % len(slate))

        add_more_dates( slate, people, skips, "main", trials )
        add_more_dates( slate, alt_people, skips, "alt", trials )
        for d in daters:
            add_more_dates( slate, daters[d], skips, d, trials )
        add_more_dates( slate, people_f, None, "friend", trials )

        # remove pairs that have been scheduled
        strip_matches(people_a, slate)
        strip_matches(people_b, slate)
        for d in daters:
            strip_matches(daters[d], slate)
        strip_matches(people_f, slate)

        schedules[round_id] = slate

        main_matched = set(x for x in slate if slate[x][1] == 'main')
        skipcreds = ""
        for person in people:
            if person.name not in main_matched:
                skipcreds += person.name + ", "
                skips[person.name] += 1
        if len(skipcreds) > 0:
            logger.debug("    Skip credits to %s" % ( skipcreds[0:-2]))

    return schedules




def slates_to_itineraries(slates, daters):
    n_rounds = len(slates)
    assert set(slates.keys()) == set(range(1, n_rounds + 1))
    #all_names = set(name for slate in slates.values() for name in slate)
    all_names = set(d.name for d in daters['all'])
    d = dict((x, Itinerary(x, n_rounds)) for x in all_names)
    for i in sorted(slates):
        slate = slates[i]
        for name in slate:
            d[name][i] = slate[name]
        #for name in d:
        #    if i not in d[name]:
        #        d[name][i] = ('', 'none')
        #assert set(len(x) for x in d.values()) == set((i,))
    return d

def badness_score(people, dates ):
    '''Given a date schedule for the whole event, give it a
       badness score.'''
    def person_badness(name):
        if name not in dates: return 50
        real_dates = len([x for x in dates[name] if x[1] == 'main'])
        if real_dates < 4: return 20
        if real_dates < 6: return 10
        if real_dates < 8: return 2
        return 0

    return sum(person_badness(x.name) for x in people)

    rounds = len(dates.values()[0])
    miss_percent = {}
    for person in people:
        if person.name not in dates:
            logger.critical("No datelist found for %s" % person.name)
            continue
        if not len(person):
            logger.critical("No potentials for %s ?!?!" % person.name)
            continue
        ## Can we just use len(person), or might there be zeroes?
        ## And do we need to skip people with zero possible dates?
        #theoretical_max = min(len(person), rounds)
        theoretical_max = rounds - 3
        real_dates = len([x for x in dates[person.name] if x[1] == 'main'])
        miss_percent[person.name] = 100.0 * real_dates / theoretical_max
    vals = miss_percent.values()
    return max(vals) + int(root_mean_square(vals))



def root_mean_square(vals):
    squares = [x ** 2 for x in vals]
    mean = sum(squares) / len(squares)
    return math.sqrt(mean)

## Now expects 'daters', dict mapping four keys to lists of Daters.
def make_schedules_random(event_name, daters, rounds, trials=20, scramble_rounds=True):
    if not scramble_rounds:
        logger.warning("Not scrambling rounds -- will alternate gay/str!  Later rounds will suck!")
    best = None
    best_score = 1000000
    for i in range(trials):
        print( "Beginning Trial %s" % (i,) )
        recesses = assign_recesses([x.name for x in daters['all']], event_name)
        startslates = seed_schedules_with_recesses(recesses)
        slates = make_date_schedules( daters, rounds,
            trials, scramble_rounds, initial_schedules=startslates)
        # Send in the list of daters so that people with 0 dates
        # don't just vanish.
        dates = slates_to_itineraries(slates, daters)
        score = badness_score(daters['all'], dates)
        if score < best_score:
            print( "Found superior match-up.  Score = %s" % (score, ) )
            best_score = score
            best = dates
    return best



def print_summary(dates, daters):
    types = ['main', 'alt', 'bad', 'friend', 'none']
    ## TODO: Make sure this is properly symmetrized at this point.
    ## Unrequited interest does not count as a possible date.
    dater_lookup = dict((x.psdid, x) for x in daters)
    format = "%8s: %6s %6s %6s %6s %6s | %8s"
    print(format % ('ID', 'main', 'alt', 'bad', 'friend', 'none', 'badness'))
    print("-" * 28)
    screwed = []
    for psdid in sorted(dates):
        me = dater_lookup[psdid]
        my_schedule = dates[psdid]
        counts = dict((x, 0) for x in types)
        for date in my_schedule:
            counts[date[1]] += 1
        solid_dates = counts['main'] + counts['alt']
        max_possible = min(len(my_schedule), len([x for x in me if x]))
        badness = 1 - (solid_dates / float(max_possible))
        if badness > 0.6 or solid_dates < 5:
            screwed.append((psdid, my_schedule))
        print(format % (psdid, counts['main'], counts['alt'], counts['bad'], counts['friend'],
                                counts['none'], badness))
    print()
    print("Screwed people:")
    for line in screwed:
        print("%s: %s" % line)




