
from django.test import TestCase
from register.models import MATCH_NO, Person
from .factories import RegRecordFactory, EventFactory, PersonFactory


class TestRegRecord(TestCase):


    def setUp(self):
        event = EventFactory(event='test1')









    def test_SSM_man(self):
        strs = [ "CM", "TM", "M", "CM,M", "TM,M", "CM,TM,M" ]

        for gnd in strs:
            p1 = PersonFactory( gender=gnd, seek_gender="W" )
            r1 = RegRecordFactory(event='test1', people=[p1])

            self.assertTrue( r1.is_indiv )
            self.assertTrue( len( r1.members ) == 1 )
            self.assertTrue( r1.size == 1 )
            self.assertTrue( r1.integrity_ok() )
            self.assertEqual( r1.indiv, p1 )

            r1.has_gender( gnd.split("," )[0] )

            self.assertEqual( r1.genders, set( gnd.split("," ) ) )
            self.assertEqual( r1.seek_genders, set( ["W"] ) )

            self.assertTrue( r1.has_gender( gnd.split("," )[0] ) )
            self.assertTrue( r1.wants_gender( "W" ) )

            self.assertTrue( r1.is_man )
            self.assertFalse( r1.is_woman )
            self.assertTrue( r1.is_man_only )
            self.assertFalse( r1.is_woman_only )
            self.assertFalse( r1.only_alt_gendered )
            self.assertFalse( r1.wants_mf )
            self.assertFalse( r1.wants_m )
            self.assertTrue( r1.wants_f )

            self.assertTrue( r1.treat_as_man )
            self.assertFalse( r1.treat_as_woman )
            self.assertTrue( r1.straightish_male )







