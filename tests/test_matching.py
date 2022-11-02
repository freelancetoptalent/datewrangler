
from django.test import TestCase
from register.models import MATCH_NO, Person
from .factories import RegRecordFactory, EventFactory, PersonFactory
import logging
from psd.management.commands.testdb import makeTestDB
from register.matchq_models import MatchQuestion

class TestRegMatch(TestCase):

    def setUp(self):
        event = EventFactory(event='test1')
        logging.disable(logging.CRITICAL)
        makeTestDB("testing1", False, False, verbose=False)



    def test_test_too_groupy(self):
        reg1 = RegRecordFactory(seek_groups=False)
        reg2 = RegRecordFactory(people = [PersonFactory(), PersonFactory()])
        assert reg2.is_group
        self.assertEqual(reg1.match_horror(reg2), MATCH_NO)


    def test_indiv_basic_matching(self):
        event = EventFactory(event='test1')
        person1 = PersonFactory(gender='M', seek_gender='W')
        reg1 = RegRecordFactory(event='test1', people=[person1])

        assert reg1.ev == event
        assert not reg1.is_group
        assert reg1.indiv == person1

        person2 = PersonFactory(gender='W', seek_gender='M')
        reg2 = RegRecordFactory(event='test1', people=[person2])
        self.assertEqual(reg1.match_horror(reg2), 100)



    def test_race_matching(self):
        print "Testing race question"
        q = MatchQuestion.objects.get( question_code = "race" )
        print q
        person1 = PersonFactory(gender='M', seek_gender='W')
        person1.set_response( q, q.yes_choice )
        reg1 = RegRecordFactory(event='test1', people=[person1])

        person2 = PersonFactory(gender='W', seek_gender='M')
        person2.set_response( q, q.yes_choice )
        reg2 = RegRecordFactory(event='test1', people=[person2])

        reg2.ev.extra_questions.add(MatchQuestion.objects.get(question_code="race"))
        reg2.ev.save()

        print reg2.ev
        print reg2.ev.extra_questions.all()
        print reg2.ev.longname

        print person1.single_question_horror( person2, q )
        self.assertEqual( person1.single_question_horror( person2, q )[0], -50 )

        self.assertEqual(reg1.match_horror(reg2), 50)



    def test_indiv_no_gender_matching(self):
        event = EventFactory(event='test1')
        person1 = PersonFactory(gender='M', seek_gender='W')
        reg1 = RegRecordFactory(event='test1', people=[person1])
        person2 = PersonFactory(gender='M', seek_gender='W')
        reg2 = RegRecordFactory(event='test1', people=[person2])
        self.assertEqual(reg1.match_horror(reg2), MATCH_NO)

    def test_indiv_age_bonus_matching(self):
        event = EventFactory(event='test1')
        person1 = PersonFactory(gender='M', seek_gender='W', seek_age_min=19, seek_age_max=31)
        reg1 = RegRecordFactory(event='test1', people=[person1])
        person2 = PersonFactory(gender='W', seek_gender='M', age=25)
        reg2 = RegRecordFactory(event='test1', people=[person2])
        self.assertEqual(reg1.match_horror(reg2), 95)
        
        

    def test_group_example(self):
        reg1 = RegRecordFactory(event='test1', people=[PersonFactory(), PersonFactory()])
        assert reg1.is_group
        assert Person.objects.count() == 2
        # add a 'group' matching test here...



    def test_test_too_groupy(self):
        reg1 = RegRecordFactory(seek_groups=False)
        reg2 = RegRecordFactory(people = [PersonFactory(), PersonFactory()])
        assert reg2.is_group
        self.assertEqual(reg1.match_horror(reg2), MATCH_NO)



    def test_genderqueer(self):
        event = EventFactory(event='test1')

        person1 = PersonFactory(gender='W', seek_gender='TM,Q', seek_age_min=19, seek_age_max=31)
        reg1 = RegRecordFactory(event='test1', people=[person1])
        person2 = PersonFactory(gender='M', seek_gender='W', age=25)
        reg2 = RegRecordFactory(event='test1', people=[person2])
        self.assertEqual( reg1.will_date( reg2 ), False )
        self.assertEqual( reg2.will_date( reg1 ), True )

        person2 = PersonFactory(gender='M,Q', seek_gender='W', age=25)
        reg2 = RegRecordFactory(event='test1', people=[person2])
        self.assertEqual( reg1.will_date( reg2 ), False )
        self.assertEqual( reg2.will_date( reg1 ), True )


    def test_staff_flag(self):
        event = EventFactory(event='test1')

        # staff person
        person1 = PersonFactory(gender='W', seek_gender='M', seek_age_min=19, seek_age_max=31)
        reg1 = RegRecordFactory(event='test1', people=[person1], is_staff=True)
        
        # other person
        person2 = PersonFactory(gender='M', seek_gender='W', age=25)
        reg2 = RegRecordFactory(event='test1', people=[person2])
        
        self.assertEqual( reg1.will_date( reg2 ), True )
        self.assertEqual( reg2.will_date( reg1 ), False )

        reg2 = RegRecordFactory(event='test1', people=[person2], volunteers_ok=True)
        self.assertEqual( reg1.will_date( reg2 ), True )
        self.assertEqual( reg2.will_date( reg1 ), True )

       
        
        
        