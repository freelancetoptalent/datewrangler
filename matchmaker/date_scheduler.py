"""
Schedule dates, given a match-matrix

Guts of the work in the polymatch module.

See schedule() method.
"""

import traceback
from matchmaker import loader, polymatch
import logging, time
logger = logging.getLogger('psd.date_scheduler')
from register.models import *
from matchmaker.models import *
import itertools

from matchmaker import table_matcher

# def find_sad_people( schedules, target, event_name ):
#     sad = []
#     tps = { 'alt':0, 'main':0, 'bad':0, 'friend':0 }
#     total = 0
#     num_sad = 0
#     num_underserved = 0
#     logger.info( "Finding Sad People---Those with few dates, not counting 'bad' dates." )
#     print "PSDID\tgot\tex bad\t%\t#m\t#one\tminicode"
#     for psdid,sch in schedules.items():
#         dts = sch.count_dates()
#
#         for t in tps.iterkeys():
#             tps[t] += dts.get(t,0)
#         exbad = dts.get('bad',0)
#
#
#         tdat = dts.get('alt',0) + dts.get('main',0)
#         rr = RegRecord.objects.get(psdid=psdid,event=event_name)
#         if rr.matches > 0:
#             pergot = 100 * tdat / min(rr.matches,target)
#         else:
#             pergot = 0
#         if tdat < 5 or pergot <= 50 or (tdat < target/2 and pergot <= 75):
#             print "%s\t%s\t%s\t%s\t%s\t%s\t%s" % (psdid, tdat, exbad, pergot, rr.matches, rr.oneway, rr.minicode() )
#             num_sad = num_sad + 1
#             if pergot <= 75:
#                 num_underserved = num_underserved + 1
#         total += tdat
#
#     print "Counts of dates scheduled"
#     print tps
#
#     print "Number of sad people = %s" % (num_sad, )
#     print "Number of underserved people = %s \t(people who got lot fewer than their potential)" % (num_sad, )
#     print "Mean real dates = %s" % (1.0*total/len(schedules) )
#     print "Total Dates = %s" % ( sum( [x for x in tps.itervalues()] ), )


def printtable( lst ):
    """
    Print a table to the screen
    A table is a list of regrecords along with some summary statistics as to the match successes
    """
    print "\tCounts of date types"
    print "PSDID\tgood\tbad\tfriend\ttotal\t%\tposs\tshorted\tminicode"
    for l in lst:
        print l
    print "\tTotal: %s" % (len(lst), )


def get_counts( daters ):
    baseline = daters["baseline"]

    counts = dict( (d.name, len(d)) for d in baseline )
    return counts



def find_really_sad_people( schedules, target, event_name, daters ):
    sad = []
    tps = { 'alt':0, 'main':0, 'bad':0, 'friend':0 }
    total = 0

    counts = get_counts( daters )

    print "Target number of dates = %s" % (target, )
    baseline = daters["baseline"]

    sadtable = {}
    sadtable['sad'] = []
    sadtable['very sad'] = []
    sadtable['underserved'] = []

    logger.info( "Finding Sad People---Those with few dates" )
    neg_impacted = 0

    print "Total number of items: %s" % (len( schedules.items() ), )

    for psdid,sch in schedules.items():
        dts = sch.count_dates()

        for t in dts.iterkeys():
            tps[t] = tps.get(t,0) + dts.get(t,0)

        good = dts.get('main',0) + dts.get('alt',0)

        tdat = dts.get('alt',0) + dts.get('main',0) + dts.get('bad',0)

        if ( RegRecord.objects.filter(psdid=psdid,event=event_name).count() > 1 ):
            print( "Got multiple reg records for %s and %s" % ( psdid, event_name ) )
            
        rr = RegRecord.objects.get(psdid=psdid,event=event_name)
        if counts[ psdid ] > 0:
            pergot = 100 * tdat / min(counts[ psdid ], target)
        else:
            pergot = 0
        shorted =  min(counts[ psdid ], target) - tdat
        underserved = shorted >= 3
        if tdat < 5 or good < 4 or underserved: # pergot <= 75: #0 or (tdat < target/2 and pergot <= 75):
            neg_impacted += 1
            tabstr = "".join(itertools.repeat( "%s\t", 9 ) )
            hitstr = tabstr % (psdid, good, dts.get('bad',0), dts.get( 'friend', 0),
                                       tdat, pergot,
                                       counts[ psdid ], shorted, rr.minicode() )
            if tdat < 5:
                sadtable['very sad'].append( hitstr )
            if good < 4:
                sadtable['sad'].append( hitstr )
            if underserved:
                sadtable['underserved'].append( hitstr )

        total += tdat

    print( "\n\nVery Sad People (Fewer than 5 dates, period.)" )
    printtable( sadtable['very sad'] )
    print( "\n\nSad People (Fewer than 4 good dates.)" )
    printtable( sadtable['sad'] )
    print( "\n\nUnderserved people (Not a good percentage of what was possible)." )
    printtable( sadtable['underserved'] )
    print( "\n\tNote: regrecords can be multiply listed on above" )
    print "\nTotal number of negatively served people = %s" % (neg_impacted, )

    print "\n\nCounts of total number of dates scheduled"
    for t in tps:
        print "%s\t%s" % (t, tps[t])

    print "\n\nMean real dates = %s" % (1.0*total/len(schedules) )
    print "Total Dates = %s" % ( sum( [x for x in tps.itervalues()] ), )



def print_and_log( str ):
    logger.info( str )
    print( str )




def schedule(event_name, rounds, trials, who_include="In"):
    target = rounds - 3
    print_and_log("""
        Scheduling for event %s
        folks included: %s
        rounds: %s
        trials: %s
        target dates: %s""" % (event_name, who_include, rounds, trials, target))
    try:
        daters = loader.get_all_daters(event_name, who_include)
        print_and_log( "Number of daters to schedule: %s" % (len(daters['all']), ) )

        print_and_log( "making schedules now" )
        schedules = polymatch.make_schedules_random(event_name, daters, rounds, trials, scramble_rounds=True)

        if len(schedules) == 0:
            print_and_log( "No one scheduled.  Bailing" )
            return
        else:
            print_and_log( "Daters have been scheduled" )

        find_really_sad_people( schedules, target, event_name, daters )


        ## That returned a dict mapping psdids to lists of (psdid, datetype) 2-tuples.
        print_and_log( "Saving the generated table of dates..." )
        loader.save_date_table(schedules, event_name, erase_old=True)

        print_and_log( "Scheduling dates to tables..." )
        table_matcher.run_event(event_name)
    except Exception as inst:
        print_and_log( "Scheduler failed with %s" % (inst,) )
        dbstr = traceback.format_exc(inst)
        print_and_log( "Details are:\n%s\n" % ( dbstr, ) )

    print_and_log( "Finished scheduling" )





