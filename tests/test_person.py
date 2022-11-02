
## Test the basic methods for Person,
## mainly gender questions such as want_f, etc.

from django.test import TestCase
from register.models import MATCH_NO, Person
from .factories import RegRecordFactory, EventFactory, PersonFactory


class TestPerson(TestCase):




    def test_group_example(self):
        reg1 = RegRecordFactory(event='test1', people=[PersonFactory(), PersonFactory()])
        assert reg1.is_group
        assert Person.objects.count() == 2


    def test_SSM_man(self):
        strs = [ "CM", "TM", "M", "CM,M", "TM,M", "CM,TM,M" ]

        for gnd in strs:
            p1 = PersonFactory( gender=gnd, seek_gender="W" )
            self.assertEqual( p1.gender_set, set( gnd.split("," ) ) )
            self.assertEqual( p1.seek_gender_set, set( ["W"] ) )
            self.assertEqual( p1.pref_gender_set, set( [] ) )

            self.assertTrue( p1.has_gender( gnd.split("," )[0] ) )
            self.assertTrue( p1.wants_gender( "W" ) )

            self.assertTrue( p1.is_man_only )
            self.assertFalse( p1.is_woman_only )
            self.assertFalse( p1.only_alt_gendered )
            self.assertFalse( p1.wants_mf )
            self.assertFalse( p1.wants_m )
            self.assertTrue( p1.wants_f )




    def test_bi_woman(self):
        strs = [ "CW", "TW", "W", "CW,W", "TW,W", "CW,TW,W" ]

        for gnd in strs:

            p1 = PersonFactory( gender=gnd, seek_gender="M,CM,W,TW-2" )
            self.assertEqual( p1.gender_set, set( gnd.split("," ) ) )
            self.assertEqual( p1.seek_gender_set, set( ["M","CM","W","TW"] ) )
            self.assertEqual( p1.pref_gender_set, set( ["TW"] ) )

            self.assertTrue( p1.has_gender( gnd.split("," )[0] ) )
            self.assertTrue( p1.wants_gender( "W" ) )

            self.assertFalse( p1.is_man_only )
            self.assertTrue( p1.is_woman_only )
            self.assertFalse( p1.only_alt_gendered )
            self.assertTrue( p1.wants_mf )
            self.assertTrue( p1.wants_m )
            self.assertTrue( p1.wants_f )





    def test_alt_person(self):
        strs = [ "Q", "NA", "NA,Q" ]

        for gnd in strs:

            p1 = PersonFactory( gender=gnd, seek_gender="M,CM,W,TW-2" )
            self.assertEqual( p1.gender_set, set( gnd.split("," ) ) )
            self.assertEqual( p1.seek_gender_set, set( ["M","CM","W","TW"] ) )
            self.assertEqual( p1.pref_gender_set, set( ["TW"] ) )

            self.assertTrue( p1.has_gender( gnd.split("," )[0] ) )
            self.assertTrue( p1.wants_gender( "W" ) )

            self.assertFalse( p1.is_man_only )
            self.assertFalse( p1.is_woman_only )
            self.assertTrue( p1.only_alt_gendered )
            self.assertTrue( p1.wants_mf )
            self.assertTrue( p1.wants_m )
            self.assertTrue( p1.wants_f )





