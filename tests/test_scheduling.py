##
## Very basic scheduling testing
##
## WARNING: Stocastically this can get jammed up sometimes.  So if the test fails, re-run once to see if that
## fixes it.
## (We should fix the algorithm, however.)

from django.test import TestCase
from register.models import MATCH_NO, Person, RegRecord, fetch_regrecord
from register.system_models import Event
from register.schedule_models import DateRecord, BreakRecord
from .factories import RegRecordFactory, EventFactory, PersonFactory
from matchmaker.matrix_maker import updateMatchRecords
from register.views.dashboard import make_table_table, make_recess_rounds
from matchmaker.date_scheduler import schedule
import logging
from matchmaker.models import MatchRecord

class TestScheduling(TestCase):


    def setUp(self):
        event = EventFactory(event='test1')
        logging.disable(logging.CRITICAL)

        make_recess_rounds( "test1", "break", "4,5\n5,6")
        make_table_table( "test1", 21, set( [1,2,3,4] ), set( [3,4,5,6,7,8] ) )


    def print_schedule(self, event_name):
        print "Here we go!"

        try:
            event = Event.objects.get(event=event_name)
        except Event.DoesNotExist:
            return render_to_response( 'error.html', {'message' : "Sorry.  You are trying to generate the date matrix for an event '%s' that does not exist.  Please try again." % (event_name,)},
                                       context_instance=RequestContext(request)  )

        rr = RegRecord.objects.filter(event=event_name, cancelled=False)
        rr = sorted(rr, key=lambda reg: reg.psdid )

        mxrnd = 0
        for r in rr:
            dates = get_date_schedule( r.psdid, event_name )
            r.dates = dates
            if len(dates) > 0:
                mxrnd = max( dates[-1].round, mxrnd )
            print dates



    def test_schedule_break_record(self):

        for i in range(0, 10):
            if i % 2 == 0:
                p1 = PersonFactory( gender="M", seek_gender="W" )
            else:
                p1 = PersonFactory( gender="W", seek_gender="M" )
            r1 = RegRecordFactory( event="test1", people=[p1] )

        rrs = RegRecord.objects.all()

        br = BreakRecord( psdid=rrs[0].psdid, other_psdid=rrs[1].psdid, notes="break!" )
        br.save()
        br = BreakRecord( psdid=rrs[0].psdid, other_psdid=rrs[3].psdid, notes="break!" )
        br.save()
        br = BreakRecord( psdid=rrs[0].psdid, other_psdid=rrs[5].psdid, notes="break!" )
        br.save()
        br = BreakRecord( psdid=rrs[0].psdid, other_psdid=rrs[7].psdid, notes="break!" )
        br.save()

        evt = Event.objects.get( event="test1" )
        updateMatchRecords(evt, verbose=True, update_database=True)


        print "Listing all matches"
        rM = rrs[0]
        matches = rM.get_matches()
        for m in matches:
            print m
        print "Total Matches = %s" % ( len( matches) )

        schedule( "test1", 12, 3, who_include="NotNo" )


        # our person has 1 date
        ds = rM.get_date_sheet()
        print ds
        print len(ds)
        dts = 0
        for d in ds:
            if type( d ) is DateRecord:
                dts += 1
                self.assertTrue( not d.table is None )
                print d.table
                self.assertTrue( not d.match is None )
                print d.match
                self.assertTrue( d.match.match == 100 )
        self.assertEqual( dts, 1 )




    def test_schedule_somehere(self):

        for i in range(0, 10):
            if i % 2 == 0:
                p1 = PersonFactory( gender="M", seek_gender="W" )
            else:
                p1 = PersonFactory( gender="W", seek_gender="M" )
            hr = i in [0,1,3,5,7]
            r1 = RegRecordFactory( event="test1", people=[p1], here=hr )


        evt = Event.objects.get( event="test1" )
        updateMatchRecords(evt, verbose=True, update_database=True)

        rrs = RegRecord.objects.all()

        print "Listing all matches"
        rM = rrs[0]
        matches = rM.get_matches()
        for m in matches:
            print m
        print "Total Matches = %s" % ( len( matches) )


#         for x in [0, 1,3,5,7]:
#             print "Marking %s / %s as here" % (x, rrs[x] )
#             rrs[x].here = True
#             rrs[x].save()

        rrs = RegRecord.objects.all()
        for r in rrs:
            print "RR %s is here? %s" % ( r, r.here )


        schedule( "test1", 12, 3, who_include="In" )


        # our person has 4 dates
        ds = rM.get_date_sheet()
        print ds
        print len(ds)
        dts = 0
        for d in ds:
            if type( d ) is DateRecord:
                dts += 1
                self.assertTrue( not d.table is None )
                print d.table
                self.assertTrue( not d.match is None )
                print d.match
                self.assertTrue( d.match.match == 100 )
        self.assertEqual( dts, 4 )

        # one of matches has 1 date
        ds = rrs[1].get_date_sheet()
        print ds
        print len(ds)
        dts = 0
        for d in ds:
            if type( d ) is DateRecord:
                dts += 1
                self.assertTrue( not d.table is None )
                print d.table
                self.assertTrue( not d.match is None )
                print d.match
                self.assertTrue( d.match.match == 100 )
        self.assertEqual( dts, 1 )






    def test_schedule_small(self):

        for i in range(0, 10):
            if i % 2 == 0:
                p1 = PersonFactory( gender="M", seek_gender="W" )
            else:
                p1 = PersonFactory( gender="W", seek_gender="M" )
            r1 = RegRecordFactory( event="test1", people=[p1] )
        p1 = PersonFactory( gender="Q", seek_gender="M" )
        r1 = RegRecordFactory( event="test1", people=[p1] )
        print "Sad person: %s" % (r1, )
        p2 = PersonFactory( gender="M", seek_gender="Q" )
        r2 = RegRecordFactory( event="test1", people=[p2] )
        p3 = PersonFactory( gender="M", seek_gender="Q", age=100 )
        r3 = RegRecordFactory( event="test1", people=[p3] )

        evt = Event.objects.get( event="test1" )
        updateMatchRecords(evt, verbose=True, update_database=True)

        rrs = RegRecord.objects.all()
        rM = rrs[0]

        print "Listing all matches"
        matches = rM.get_matches()
        for m in matches:
            print m
        print "Total Matches = %s" % ( len( matches) )


        schedule( "test1", 12, 3, who_include="NotNo" )

        # Check: unmatched person has no dates
        ds = r3.get_date_sheet()
        print ds
        self.assertEqual( ds, [] )

        # Check: single-date person has one date
        ds = r2.get_date_sheet()
        print ds
        dts = 0
        for d in ds:
            dts += type( d ) is DateRecord
        self.assertEqual( dts, 1 )

        # generic person has 5 dates
        ds = rM.get_date_sheet()
        print ds
        print len(ds)
        dts = 0
        for d in ds:
            if type( d ) is DateRecord:
                dts += 1
                self.assertTrue( not d.table is None )
                print d.table
                self.assertTrue( not d.match is None )
                print d.match
                self.assertTrue( d.match.match == 100 )
        self.assertEqual( dts, 5 )



    def test_schedule_straights(self):

        for i in range(0, 40):
            if i % 2 == 0:
                p1 = PersonFactory( gender="M", seek_gender="W" )
            else:
                p1 = PersonFactory( gender="W", seek_gender="M" )
            r1 = RegRecordFactory( event="test1", people=[p1] )
        p1 = PersonFactory( gender="Q", seek_gender="M" )
        r1 = RegRecordFactory( event="test1", people=[p1] )
        print "Sad person: %s" % (r1, )
        p2 = PersonFactory( gender="M", seek_gender="Q" )
        r2 = RegRecordFactory( event="test1", people=[p2] )
        p3 = PersonFactory( gender="M", seek_gender="Q", age=100 )
        r3 = RegRecordFactory( event="test1", people=[p3] )

        evt = Event.objects.get( event="test1" )
        updateMatchRecords(evt, verbose=True, update_database=True)

        rrs = RegRecord.objects.all()
        rM = rrs[0]

        print "Listing all matches"
        matches = rM.get_matches()
        for m in matches:
            print m
        print "Total Matches = %s" % ( len( matches) )


        schedule( "test1", 10, 3, who_include="NotNo" )

        #self.print_schedule( "test1" )


        # Check: unmatched person has no dates
        ds = r3.get_date_sheet()
        print ds
        self.assertEqual( ds, [] )

        # Check: single-date person has one date
        ds = r2.get_date_sheet()
        print ds
        dts = 0
        for d in ds:
            dts += type( d ) is DateRecord
        self.assertEqual( dts, 1 )

        # generic person has 10 dates
        ds = rM.get_date_sheet()
        print ds
        print len(ds)
        self.assertEqual( len(ds), 10 )
        dts = 0
        for d in ds:
            if type( d ) is DateRecord:
                dts += 1
                self.assertTrue( not d.table is None )
                print d.table
                self.assertTrue( not d.match is None )
                print d.match
                self.assertTrue( d.match.match == 100 )
        self.assertEqual( dts, 8 )




    def test_schedule_bisexuals(self):
        """
        Ensure alternating rounds works
        """

        for i in range(0, 40):
            if i % 2 == 0:
                p1 = PersonFactory( gender="M", seek_gender="W" )
            else:
                p1 = PersonFactory( gender="W", seek_gender="M,W" )
            r1 = RegRecordFactory( event="test1", people=[p1] )
        p1 = PersonFactory( gender="Q", seek_gender="M" )
        r1 = RegRecordFactory( event="test1", people=[p1] )
        print "Sad person: %s" % (r1, )
        p2 = PersonFactory( gender="M", seek_gender="Q" )
        r2 = RegRecordFactory( event="test1", people=[p2] )
        p3 = PersonFactory( gender="M", seek_gender="Q", age=100 )
        r3 = RegRecordFactory( event="test1", people=[p3] )

        evt = Event.objects.get( event="test1" )
        updateMatchRecords(evt, verbose=True, update_database=True)

        rrs = RegRecord.objects.all()
        rM = rrs[0]
        rW = rrs[1]

        print "Listing all matches"
        matches = rM.get_matches()
        for m in matches:
            print m
        print "Total Matches = %s" % ( len( matches) )


        RNDS = 10
        schedule( "test1", RNDS, 3, who_include="NotNo" )

        #self.print_schedule( "test1" )

        # Check: unmatched person has no dates
        ds = r3.get_date_sheet()
        print ds
        self.assertEqual( ds, [] )

        # Check: single-date person has one date
        ds = r2.get_date_sheet()
        print ds
        dts = 0
        for d in ds:
            dts += type( d ) is DateRecord
        self.assertEqual( dts, 1 )

        ds = rM.get_date_sheet()
        print ds
        print len(ds)
        dts = 0
        for d in ds:
            if type( d ) is DateRecord:
                dts += 1
                self.assertTrue( not d.table is None )
                print d.table
                self.assertTrue( not d.match is None )
                print d.match
                self.assertTrue( d.match.match == 100 )
        self.assertEqual( dts, 4 )


        # generic bi person has 10 dates
        ds = rW.get_date_sheet()
        print ds
        print len(ds)
        self.assertEqual( len(ds), RNDS )
        dts = 0
        for d in ds:
            if type( d ) is DateRecord:
                dts += 1
                self.assertTrue( not d.table is None )
                print d.table
                self.assertTrue( not d.match is None )
                print d.match
                self.assertTrue( d.match.match == 100 )
        self.assertEqual( dts, 8 )
