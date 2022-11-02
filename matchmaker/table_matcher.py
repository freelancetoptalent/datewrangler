import sys
import random

from psd.shared import counter
from register.models import *


def shuffled(items):
    val = list(items)
    random.shuffle(val)
    return val

class OutOfTables(Exception):
    def __init__(self, tm, date, round):
        self.tm = tm
        self.date = date
        self.round = round
    def __str__(self):
        return "Out of Tables for date %s in round %s.  Need Stationary OK: %s   Need Group OK: %s" % (self.date, self.round, self.tm.needs_stat_table(self.date), self.tm.needs_group_table(self.date) )


class TableMatcher(object):
## Call with list of DateRecords, TableRecords, RegRecords.
    def __init__(self, daters, dates, tables):
        rounds = max(x.round for x in dates)
        self.rounds = rounds
        self.table_ranking = sorted(shuffled(tables), key=lambda x: x.quality, reverse=True)
        self.table_lookup = dict((x.name, x) for x in tables)
        self.table_chart = dict((x.name, [None] * rounds) for x in tables)
        self.daters = daters
        self.dater_lookup = dict((x.psdid, x) for x in daters)
        self.date_chart = dict((x.psdid, [None] * rounds) for x in daters)

        for date in dates:
            self.date_chart[date.psdid][date.round-1] = date

        self.priority = {}
        for dater in daters:
            if dater.stationary:
                self.priority[dater.psdid] = 2
            elif dater.is_group:
                self.priority[dater.psdid] = 1
            else:
                self.priority[dater.psdid] = 0

    def is_taken(self, table_name, round):
        return bool(self.table_chart[table_name][round])

    def can_seat(self, table_name, date):
        table = self.table_lookup[table_name]
        if not table.statOK and self.needs_stat_table(date):
            return False
        elif not table.groupOK and self.needs_group_table(date):
            return False
        else:
            return True

    def needs_stat_table(self, date):
        p1 = self.dater_lookup[date.psdid]
        p2 = self.dater_lookup[date.other_psdid]
        return p1.stationary or p2.stationary

    def needs_group_table(self, date):
        p1 = self.dater_lookup[date.psdid]
        p2 = self.dater_lookup[date.other_psdid]
        return p1.is_group or p2.is_group

    def assign_table(self, date, table_name):
        other_date = self.date_chart[date.other_psdid][date.round-1]
        date.table = table_name
        other_date.table = table_name
        ## Technically, both of those DateRecords take place at that table
        ## during that round, but we're just putting this here to mark
        ## that it's taken. So, doesn't matter which DateRecord gets it.
        self.table_chart[table_name][date.round-1] = date

    def best_available_tables(self, round):
        '''Returns an ITERATOR that gives all tables free
           during the given round, best tables first.'''
        for table in self.table_ranking:
            if not self.table_chart[table.name][round]:
                yield table

    def seat_one_dater(self, dater, round, force=False):
        """Takes a dater and a round number. Returns True
        if that dater is now satisfactorily seated for that
        round (whether we did anything or not). If force=False,
        give up unless they are at a table and can be assigned
        to stay there."""
        my_schedule = self.date_chart[dater.psdid]
        date = my_schedule[round]
        ## 1. Need seating? If not, great.
        if not date:
            return True

        ## 2. Already seated for this round? Great.
        if date.table:
            return True

        ## 3. Can stay where you are? Great.
        table_name = self._starts_at(dater, round)
        if table_name:
            if not self.is_taken(table_name, round):
                if self.can_seat(table_name, date):
                    self.assign_table(date, table_name)
                    return True
        if not force:
            return False

        ## 4. If force=True, can risk displacing someone else.
        for table in self.best_available_tables(round):
            if self.can_seat(table.name, date):
                self.assign_table(date, table.name)
                return True
        raise OutOfTables( self, date, round ) #, "Could not seat %s in round %s" % (date, round)

    def _tier(self, dater):
        return self.priority[dater.psdid]

    def _starts_at(self, dater, round):
        ## Nobody begins round 0 sitting down.
        if not round:
            return False
        ## Most of the "round - 1" in this module is translating
        ## from human round numbers (first round is "1") to Python
        ## list indexes (first round is "0"). Not this one! This
        ## actually means "previous round".
        prev_date = self.date_chart[dater.psdid][round-1]
        if not prev_date:
            return False
        return prev_date.table

    def assign_one_round(self, i):
        print "Assigning round %s" % (i, )
        ## Because tables for them are limited, people with mobility issues
        ## and groups of people get to claim seats first with no funny
        ## business. In both cases, people already sitting down go first.
        dibs_getters = []
        dibs_getters.extend(d for d in self.daters if d.stationary and self._starts_at(d, i))
        dibs_getters.extend(d for d in self.daters if d.stationary and not self._starts_at(d, i))
        dibs_getters.extend(d for d in self.daters if d.is_group and self._starts_at(d, i))
        dibs_getters.extend(d for d in self.daters if d.is_group and not self._starts_at(d, i))
        for dater in dibs_getters:
            self.seat_one_dater(dater, i, force=True)

        ## Now the rest. This is the tricky part.
        seated = [d for d in self.daters if not (d.stationary or d.is_group) and self._starts_at(d, i)]
        unseated = [d for d in self.daters if not (d.stationary or d.is_group) and not self._starts_at(d, i)]

        random.shuffle(seated)
        for dater in seated:
            result = self.seat_one_dater(dater, i, force=False)
            if not result:
                ## Their table is taken-- they go stand up and wait for
                ## everybody who MIGHT get to keep their current location
                ## has had a change.
                unseated.append(dater)

        random.shuffle(unseated)
        for dater in unseated:
            self.seat_one_dater(dater, i, force=True)

        self.evaluate_table_fill(i)

    def evaluate_table_fill(self, i):
        d = {}
        for table in self.table_ranking:
            if table.quality not in d:
                d[table.quality] = [0,0]
            sched = self.table_chart[table.name]
            d[table.quality][1] += 1
            if bool(sched[i]):
                d[table.quality][0] += 1
        print(', '.join("%s: %s/%s" % (q, d[q][0], d[q][1]) for q in sorted(d, reverse=True)))

    def assign_all_dates(self, save=True):
        for i in range(self.rounds):
            self.assign_one_round(i)

        print "Saving date schedule to database..."
        for psdid in sorted(self.date_chart):
            schedule = self.date_chart[psdid]
            for date in schedule:
                if not date:
                    continue
                if save:
                    date.save()
                else:
                    args = (date.psdid, date.other_psdid, date.table, date.round)
                    print("%s meets %s at table %s in round %s" % args)

def test_integrity(date_chart):
    tablemap = {}
    print "Testing integrity of date sheets (looking for symmetry, etc)"
    for psdid in sorted(date_chart):
        schedule = date_chart[psdid]
        for i, date in enumerate(schedule):
            if not date:
                continue
            if date.round != i+1:
                raise Exception, "Broken date chart - %s's date in position %s is for round %s" % (psdid, i, date.round)
            other_date = date_chart[date.other_psdid][date.round-1]
            if other_date.psdid != date.other_psdid:
                raise Exception, "In round %s, %s -> %s but %s -> %s" % (date.round,
                            date.psdid, date.other_psdid, other_date.psdid, other_date.other_psdid)
            if date.round != other_date.round:
                raise Exception, "This should REALLY be impossible."
            if date.table != other_date.table:
                raise Exception, "%s and %s in round %s disagree on tables: %s/%s" % (
                            date.psdid, date.other_psdid, date.round, date.table, other_date.table)
            ## Now check no table is overcommitted.
            k = (date.table, date.round)
            if k not in tablemap:
                ## Fine.
                tablemap[k] = (date.psdid, date.other_psdid)
            ## Else, had better look like other half of this date.
            elif tablemap[k] != (date.other_psdid, date.psdid):
                raise Exception, "Table %s, round %s, %s expected to meet %s but found %s" % (
                        date.table, date.round, date.psdid, date.other_psdid, tablemap[k])
        #print("Integrity checked for %s" % psdid)
    return True

def person_seating_quality(itinerary):
    location = None
    stay = move = get_up = sit_down = 0
    for date in itinerary:
        if date is None:
            if location is None:
                pass
            else:
                get_up += 1
                location = None
        elif location is None:
            location = date.table
            sit_down +=1
        elif location == date.table:
            stay += 1
        else:
            location = date.table
            move += 1
    ## If you date in the final round, get up to leave.
    if itinerary[-1]:
        get_up += 1
    assert sit_down == get_up
    return stay - move

def seating_quality(date_chart):
    ## Skip people with zero dates.
    scores = [person_seating_quality(sched) for sched in date_chart.values() if any(sched)]
    return counter(scores)

def fetch_tables(event_name):
    tablelist = TableListRecord.objects.get( event=event_name )
    return TableRecord.objects.filter(group=tablelist)

def test_event(event_name):
    from register.models import DateRecord, TableRecord, RegRecord
    dates = DateRecord.objects.filter(event=event_name)
    tables = fetch_tables(event_name)
    daters = RegRecord.objects.filter(event=event_name)
    matcher = TableMatcher(daters, dates, tables)
    matcher.assign_all_dates(save=False)
    test_integrity(matcher.date_chart)
    return matcher

def run_event(event_name):
    from register.models import DateRecord, TableRecord, RegRecord
    dates = DateRecord.objects.filter(event=event_name)
    tables = fetch_tables(event_name)
    daters = RegRecord.objects.filter(event=event_name)

    matcher = TableMatcher(daters, dates, tables)

    print "Assigning all dates to tables"
    matcher.assign_all_dates(save=True)
    print "Testing integrity of assignment"
    test_integrity(matcher.date_chart)
    return matcher

if __name__ == '__main__':
    test_event(sys.argv[1])
