
from django.test import TestCase
from register.models import MATCH_NO, Person
from .factories import RegRecordFactory, EventFactory, PersonFactory


class TestRegRecord(TestCase):


    def setUp(self):
        event = EventFactory(event='test1')





    def test_gay_straight_round_straights(self):
        p1 = PersonFactory( gender="M", seek_gender="W" )
        r1 = RegRecordFactory(event='test1', people=[p1])
        p2 = PersonFactory( gender="W", seek_gender="M" )
        r2 = RegRecordFactory(event='test1', people=[p2])

        self.assertEqual( r1.mf_gender_match( r2 ), False )
        self.assertEqual( r2.mf_gender_match( r1 ), False )

        self.assertEqual( r1.mf_gender_cross( r2 ), True )
        self.assertEqual( r2.mf_gender_cross( r1 ), True )

        self.assertEqual( r1.will_date( r2 ), True )
        self.assertEqual( r2.will_date( r1 ), True )

        self.assertEqual( r1.ok_gay_match( r2 ), True )
        self.assertEqual( r1.ok_str_match( r2 ), True )





    def test_gay_straight_round_gays(self):
        p1 = PersonFactory( gender="M", seek_gender="M,TM" )
        r1 = RegRecordFactory(event='test1', people=[p1])
        p2 = PersonFactory( gender="M", seek_gender="W" )
        r2 = RegRecordFactory(event='test1', people=[p2])

        self.assertEqual( r1.mf_gender_match( r2 ), True )
        self.assertEqual( r2.mf_gender_match( r1 ), True )

        self.assertEqual( r1.mf_gender_cross( r2 ), False )
        self.assertEqual( r2.mf_gender_cross( r1 ), False )

        self.assertEqual( r1.will_date( r2 ), True )
        self.assertEqual( r2.will_date( r1 ), False )

        self.assertEqual( r1.ok_gay_match( r2 ), True )
        self.assertEqual( r1.ok_str_match( r2 ), True )


    def test_gay_straight_round_bisex(self):
        # CW seeks TM,CW,TW
        p1 = PersonFactory( gender="CW", seek_gender="CM,CW,TW,Q" )
        r1 = RegRecordFactory(event='test1', people=[p1])

        # CM seeks CW
        p2 = PersonFactory( gender="CM,Q", seek_gender="CW" )
        r2 = RegRecordFactory(event='test1', people=[p2])

        self.assertEqual( r1.mf_gender_match( r2 ), False )
        self.assertEqual( r2.mf_gender_match( r1 ), False )

        self.assertEqual( r1.is_man, False )
        self.assertEqual( r1.is_woman, True )
        self.assertEqual( r2.is_man, True )
        self.assertEqual( r2.is_woman, False )
        
        self.assertEqual( r1.mf_gender_cross( r2 ), True )
        self.assertEqual( r2.mf_gender_cross( r1 ), True )

        self.assertEqual( r1.will_date( r2 ), True )
        self.assertEqual( r2.will_date( r1 ), True )

        self.assertEqual( r1.ok_gay_match( r2 ), False )
        self.assertEqual( r1.ok_str_match( r2 ), True )

        # CW-seek-TW  and TW-seeks-CW
        p3 = PersonFactory( gender="TW", seek_gender="CW" )
        r3 = RegRecordFactory(event='test1', people=[p3])
        self.assertEqual( r1.ok_gay_match( r3 ), True )
        self.assertEqual( r1.ok_str_match( r3 ), False )



    def test_gay_straight_round_bothgen(self):
        # MW
        p1 = PersonFactory( gender="CW,M,Q", seek_gender="TW" )
        r1 = RegRecordFactory(event='test1', people=[p1])

        self.assertEqual( r1.is_man, True )
        self.assertEqual( r1.is_woman, True )
        
        # M
        p2 = PersonFactory( gender="M,Q", seek_gender="W" )
        r2 = RegRecordFactory(event='test1', people=[p2])

        # W
        p3 = PersonFactory( gender="TW", seek_gender="W,CW,M,Q" )
        r3 = RegRecordFactory(event='test1', people=[p3])

        self.assertEqual( r1.mf_gender_match( r2 ), True )
        self.assertEqual( r2.mf_gender_match( r1 ), True )

        self.assertEqual( r1.mf_gender_cross( r2 ), True )
        self.assertEqual( r2.mf_gender_cross( r1 ), True )

        self.assertEqual( r1.will_date( r2 ), False )
        self.assertEqual( r2.will_date( r1 ), False )
        self.assertEqual( r1.will_date( r3 ), True )
        self.assertEqual( r3.will_date( r1 ), True )

        self.assertEqual( r1.ok_gay_match( r3 ), True )
        self.assertEqual( r1.ok_str_match( r3 ), True )

        # Make sure that there is alternation of dating for dual gender folks.
        self.assertEqual( r3.ok_gay_match( r1 ), not r3.ok_str_match( r1 ) )



    def test_gay_straight_round_altgen(self):
        p1 = PersonFactory( gender="Q", seek_gender="M,TM,W,CW,TW,Q" )
        r1 = RegRecordFactory(event='test1', people=[p1])
        p2 = PersonFactory( gender="M,Q", seek_gender="W,Q" )
        r2 = RegRecordFactory(event='test1', people=[p2])
        p3 = PersonFactory( gender="W,TW", seek_gender="W,Q" )
        r3 = RegRecordFactory(event='test1', people=[p3])

        self.assertEqual( r1.mf_gender_match( r2 ), False )
        self.assertEqual( r2.mf_gender_match( r1 ), False )

        self.assertEqual( r1.mf_gender_cross( r2 ), False )
        self.assertEqual( r2.mf_gender_cross( r1 ), False )
        print( r1 )
        print( r2 )
        
        self.assertEqual( r1.will_date( r2 ), True )
        self.assertEqual( r2.will_date( r1 ), True )

        self.assertEqual( r1.will_date( r3 ), True )
        self.assertEqual( r3.will_date( r1 ), True )

        self.assertEqual( r1.ok_gay_match( r2 ), False )
        self.assertEqual( r1.ok_str_match( r2 ), True )
        self.assertEqual( r1.ok_gay_match( r3 ), True )
        self.assertEqual( r1.ok_str_match( r3 ), False )

        self.assertEqual( r2.ok_gay_match( r1 ), True )
        self.assertEqual( r2.ok_str_match( r1 ), True )
        self.assertEqual( r3.ok_gay_match( r1 ), True )
        self.assertEqual( r3.ok_str_match( r1 ), True )







