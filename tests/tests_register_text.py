"""
run "manage.py test".
"""

from django.test import TestCase
from register.models import Person, RegRecord
from register.system_models import Event, TranslationRecord
from psd.management.commands.testdb import makeTestDB
from tests.tests_register import FactoryRecordMixin
from register.models import getTextTranslationTable


class RegTestCaseText(TestCase, FactoryRecordMixin):

    def all_equal(self, *pairs):
        for p in pairs:
            self.assertEqual(*p)

    def setUp(self):
        Person.TEXT_TRANSLATION = None
        print "Check 1:"
        print Person.TEXT_TRANSLATION

        makeTestDB("testing1", True, False, verbose=False)
        
        self.event = Event.objects.get(event="testing1")
        self.event.free_text = True
        self.event.save()

        print "Check 2:"
        print Person.TEXT_TRANSLATION


        tr = TranslationRecord( base_word="dog", synonym="doggie" )
        tr.save()
        tr = TranslationRecord( base_word="apple", synonym="pear" )
        tr.save()

        print "Check 3:"
        print Person.TEXT_TRANSLATION

        self.make_person("SSM", "M", 42, "W", 18, 42, "dog; donkey; apple" )
        self.make_person("SSW", "W", 42, "M", 18, 42, "cat seeks dog" )

        print "Check 4:"
        print Person.TEXT_TRANSLATION

        # confusing hack thing?
        #Person.TEXT_TRANSLATION = None


    def test_match(self):
        bob=RegRecord.objects.get(event="testing1", psdid="SSM")
        lulu=RegRecord.objects.get(event="testing1", psdid="SSW")

        self.assertEqual(bob.match_horror(lulu), 90)
        self.assertEqual(lulu.match_horror(bob), 85)



    def testing_trans_main_call(self):
        tr = TranslationRecord( base_word="dog", synonym="doggie" )
        tr.save()
        tr = TranslationRecord( base_word="apple", synonym="pear" )
        tr.save()

        tbl = getTextTranslationTable()
        print tbl
        self.assertEqual( tbl, {'doggie':'dog', 'pear':'apple' } )


    def testing_translation_table_formation(self):

        bob = self.make_person( "SSM2", "M", 42, "W", 18, 42, "doggie; donkey; apple" )
        tbl = bob.indiv.textTranslationTable()
        print tbl
        self.assertEqual( tbl, {'doggie':'dog', 'pear':'apple' } )



    def testing_translation_table(self):

        bob = self.make_person( "SSM2", "M", 42, "W", 18, 42, "doggie; donkey; apple" )
        print bob.indiv.text_match
        print bob.indiv.my_text_answer
        wds = bob.indiv.my_text_answer.words()
        print wds
        self.assertEqual( wds, set( ['dog', 'donkey', 'apple' ] ) )



    def test_match_translate_table(self):

        bob = self.make_person( "SSM", "M", 42, "W", 18, 42, "doggie; donkey; apple" )
        bob2 = self.make_person( "SSM", "M", 42, "W", 18, 42, "dog; donkey; apple" )
        lulu = self.make_person("SSW", "W", 42, "M", 18, 42, "cat seeks dog" )
        evt = Event.objects.get(event="testing1")

        self.assertEqual(bob.match_horror(lulu, evt), 90)
        self.assertEqual(lulu.match_horror(bob2, evt), 85)
        self.assertEqual(lulu.match_horror(bob, evt), 85)




