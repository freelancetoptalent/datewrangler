"""
run "manage.py test".

TO DO: This is an eclectic collection of tests that should be moved to the other files at some point.
"""

from django.test import TestCase
from register.models import Person, RegRecord
from register.system_models import Event
from psd.management.commands.testdb import makeTestDB


class FactoryRecordMixin(object):

    def make_person(self, fname, gender, age, seekgen, seekagemin, seekagemax, textresponse = "" ):
        bob = Person(
            first_name=fname,
            gender=gender,
            age=age,
            seek_gender=seekgen,
            seek_age_min=seekagemin,
            seek_age_max=seekagemax,
            text_match=textresponse)
        bob.save()

        bob_reg = RegRecord(
            nickname=fname,
            psdid=fname,
            is_group=False,
            location='SF',
            event="testing1",
            seek_groups=True,
            groups_match_all=True
        )
        bob_reg.save()

        bob_reg.people.add(bob)
        bob_reg.save()

        return bob_reg


    def make_group(self, gname, match_all, WW=False, Pan=False):
        bob = Person(
            first_name=gname + "1",
            gender="M",
            age=42,
            seek_gender="W",
            seek_age_min=21,
            seek_age_max=100)
        if WW:
            bob.gender = "W"
        if Pan:
            bob.gender = "W,Q"
            bob.seek_gender = "W,M,TW,TM,Q"

        bob.save()
        bob2 = Person(
            first_name=gname + "2",
            gender="W",
            age=42,
            seek_gender="W",
            seek_age_min=21,
            seek_age_max=100)
        if Pan:
            bob2.gender = "M,TM"
            bob2.seek_gender = "W,M,TW,TM,Q"
        bob2.save()

        bob_reg = RegRecord(
            nickname=gname,
            psdid=gname,
            is_group=True,
            location='SF',
            groups_match_all=match_all,
            event="testing1",
            seek_groups=True,
        )
        bob_reg.save()

        bob_reg.people.add(bob)
        bob_reg.people.add(bob2)
        bob_reg.save()


class RegTestCase(TestCase, FactoryRecordMixin):

    def all_equal(self, *pairs):
        for p in pairs:
            self.assertEqual(*p)

    def setUp(self):
        #  print("\n\n\n\nSetup called\n\n\n\n")
        makeTestDB("testing1", True, False, verbose=False)
        self.event = Event.objects.get(event="testing1")

        self.make_person("SSM", "M", 42, "W", 18, 42)
        self.make_person("SSW", "W", 42, "M", 18, 42)
        self.make_person("SSW_old", "W", 82, "W", 18, 42)

        self.make_person("SPW", "W", 42, "W,M,TW,TM,Q", 18, 42)
        self.make_person("P_seek_W", "W,M,TW,TM,Q", 42, "W", 18, 42)
        self.make_person("TWQ_seek_P", "TW,Q", 42, "W,M,TW,TM,Q", 18, 42)

        self.make_group("GroupieAll", True)    # Man and women looking for women
        self.make_group("GroupieAny", False)   # Man and women looking for women (if either get a match, that's ok)  # NOQA
        self.make_group("GroupieWW", True, WW=True)  # Lesbian couple looking for women
        self.make_group("PanGroup", True, Pan=True)  # MF+ couple looking for anything (all)

    def test_event(self):
        evt = Event.objects.get(event="testing1")

        self.assertTrue(evt.event, "testing1")

        ceq = evt.cached_extra_questions
        self.assertEqual(len(ceq), 0)

    def test_add_note(self):
        bobrr = RegRecord.objects.get(event="testing1", psdid="SSM")
        bobrr.addNote("An added note.  Gets Drink!")
        self.assertTrue(bobrr.hasNotes)

        bobrr2 = RegRecord.objects.get(event="testing1", psdid="SSM")
        self.assertTrue(len(bobrr2.notes) > 0)
        self.assertTrue("DRINK" in bobrr2.registration_flag())

    def test_trans_cis_thing(self):
        genlist = [ "", "M", "TM", "CM", "TM,M", "CM,M", "TM,CM", "TM,CM,M", "M,W" ]

        lookers = [ self.make_person("look_man_"+x, "W", 42, x, 18, 42) for x in genlist ]
        amers = [ self.make_person("am_man_"+x, x, 42, "W", 18, 42) for x in genlist ]
        # Rows are what is being looked for, columns are what the target is.
        # So Row 3, column 2 corresponds to someone looking for TM and finding a M.
        #    This would _not_ be a match (due to ambiguity)
        #          ""      M       TM      CM      TM,M    CM,M    TM,CM   TM,CM,M M,W
        wills = [ [True,   False,  False,  False,  False,  False,  False,  False,  False],   # ""
                   [True,   True,   True,   True,   True,   True,   True,   True,   False],   # M
                   [True,   False,  True,   False,  True,   False,  False,  False,  False],   # TM
                   [True,   False,  False,  True,   False,  True,   False,  False,  False],   # CM
                   [True,   True,   True,   False,  True,   False,  False,  False,  False],   # TM,M
                   [True,   True,   False,  True,   False,  True,   False,  False,  False],   # CM,M
                   [True,   True,   True,   True,   True,   True,   True,   True,   False],   # TM,CM
                   [True,   True,   True,   True,   True,   True,   True,   True,   False],   # TM,CM,M
                   [True,   True,   True,   True,   True,   True,   True,   True,   True ]]   # M,W


        #print "Checking all cis/trans stuff"
        for lkid, lk in enumerate(lookers):
            for amid, am in enumerate(amers):
                wd = lk.will_date(am)
                if wd != wills[lkid][amid]:
                    print "Fail to match: %s looking for %s=%s  (got %s)" % (genlist[lkid], genlist[amid], wills[lkid][amid], wd)
                    print "\tlook: %s\n\t  am: %s" % (lk.minicode(), am.minicode())

         #self.assertEqual(wd, wills[lkid][ amid ])

    def test_description_strings(self):
        genlist=[ "", "M", "TM", "CM", "TM,M", "CM,M", "TM,CM", "TM,CM,M", "M,W" ]

        lookers=[ self.make_person("look_man_"+x, "W", 42, x, 18, 42) for x in genlist ]
        for (i,x) in enumerate(reversed(genlist)):
            lookers[i].indiv.gender=x

        snippits=[ "will prevent all matches", "men.", "old trans men",
                    "yr old cis men" ]
        #for l in lookers:
        #    print(l.indiv.gender + "->" + l.indiv.seek_gender + ": " + l.geekcode())



    def test_group_to_indiv(self):
        g1=RegRecord.objects.get(event="testing1", psdid="GroupieAll")
        gWW=RegRecord.objects.get(event="testing1", psdid="GroupieWW")

        bob=RegRecord.objects.get(event="testing1", psdid="SSM")

        self.assertEqual(bob.will_date(g1), False)
        self.assertEqual(g1.will_date(bob), False)
        self.assertEqual(bob.will_date(gWW), True)
        self.assertEqual(gWW.will_date(bob), False)

        bob=RegRecord.objects.get(event="testing1", psdid="SSW")
        self.assertEqual(bob.will_date(g1), False)
        self.assertEqual(g1.will_date(bob), False) # groups need mutual matches to consider

        self.assertEqual(bob.will_date(gWW), False)
        self.assertEqual(gWW.will_date(bob), False) # groups need mutual matches to consider

        # If willing to only date one of a pair?
        bob.groups_match_all=False
        bob.save()
        self.assertEqual(bob.will_date(g1), True)
        self.assertEqual(bob.will_date(gWW), False)


    def test_group_regrecord_methods(self):
        #self.make_group("GroupieAll", True)    # Man and women looking for women (and all must match)
        #self.make_group("GroupieAny", False)   # Man and women looking for women (if either get a match, that's ok)
        #self.make_group("GroupieWW", True, WW=True)  # Lesbian couple looking for women
        #self.make_group("PanGroup", True, Pan=True)  # MF+ couple looking for anything (all)

        g1=RegRecord.objects.get(event="testing1", psdid="GroupieAll")
        g2=RegRecord.objects.get(event="testing1", psdid="GroupieAny")
        gWW=RegRecord.objects.get(event="testing1", psdid="GroupieWW")
        #        import pdb; pdb.set_trace()

        self.assertTrue(g1.any_match_someone(g2) < 100)
        self.assertTrue(g1.all_match_someone(g2) > 1000)
        self.assertTrue(gWW.any_match_someone(g2) < 100)
        self.assertTrue(gWW.all_match_someone(g2) < 100)
        self.assertTrue(g2.all_match_someone(gWW) > 1000)
        self.assertTrue(g1.all_match_someone(gWW) > 1000)

        self.all_equal((g1.size, 2))

        mm=g2.members
        self.all_equal((mm[0].first_name, "GroupieAny1"),
                        (mm[1].first_name, "GroupieAny2"),
                        (g1.genders, set([ 'M','W' ])),
                        (gWW.genders, set('W')),
                        (gWW.seek_genders, set(['W'])),
                        (g1.seek_genders, set(['W']))       #set(['TW','CW','W']))
                       )


    def test_gay_group_to_straight_group(self):
        """
        Idea is one group is a man and women, both straight, looking for anyone to match either.
        How do they match compared to two gay women looking for women?
        """
        g1=RegRecord.objects.get(event="testing1", psdid="GroupieAny")
        g2=RegRecord.objects.get(event="testing1", psdid="GroupieAll")
        gWW=RegRecord.objects.get(event="testing1", psdid="GroupieWW")
        #import pdb; pdb.set_trace()

        self.assertEqual(g1.will_date(g2), True)
        self.assertEqual(g2.will_date(g1), False)

        self.assertEqual(g1.will_date(gWW), True)
        self.assertEqual(gWW.will_date(g1), True)

        self.assertEqual(g2.will_date(gWW), False)
        self.assertEqual(gWW.will_date(g2), True)



    def test_alt_genders(self):
        g1=RegRecord.objects.get(event="testing1", psdid="TWQ_seek_P")


    def test_many_regrecord_methods_once(self):
        bobrr=RegRecord.objects.get(event="testing1", psdid="SSM")

        #self.assertTrue(bobrr.hasNotes())

        self.assertTrue(bobrr.integrity_ok)

        ind=bobrr.indiv
        self.all_equal((ind.has_gender("M"), True),
                        (ind.age, 42))

        evnt=bobrr.ev

        self.all_equal((evnt.event, "testing1"),
                        (bobrr.size, 1),
                        (bobrr.is_indiv, True),
                        (bobrr.location_set, set(['SF'])),
                        (bobrr.has_gender('M'), True),
                        (bobrr.wants_gender('W'), True),
                        (bobrr.is_man_only, True),
                        (bobrr.is_woman_only, False),
                        (bobrr.only_alt_gendered,False),
                        (bobrr.wants_mf,False),
                        (bobrr.wants_m, False),
                        (bobrr.wants_f, True),
                        (bobrr.treat_as_man, True),
                        (bobrr.treat_as_woman, False),
                        (bobrr.straightish_male, True)
                      )
        self.assertFalse("rror" in bobrr.geekcode())
        #print bobrr.geekcode()
        self.assertTrue("->" in bobrr.minicode())
        self.assertFalse("rror" in bobrr.htmlcode())


    def test_many_person_methods_once(self):

        bobrr=RegRecord.objects.get(event="testing1", psdid="SSM")
        bob=bobrr.indiv
        self.all_equal(
            (bob.first_name, 'SSM'),
            (bob.gender_set, set('M')),
            (bob.seek_gender_set, set('W'))
       )

    def test_many_person_methods_once_2(self):

        bobrr=RegRecord.objects.get(event="testing1", psdid="SSW")
        bob=bobrr.indiv
        self.all_equal(
            (bob.first_name, 'SSW'),
            (bob.gender_set, set('W')),
            (bob.seek_gender_set, set('M'))
       )
        self.all_equal(
            (bobrr.treat_as_man, False),
            (bobrr.treat_as_woman, True)
       )

        bobrr=RegRecord.objects.get(event="testing1", psdid="SPW")
        bob=bobrr.indiv
        self.all_equal(
            (bob.first_name, 'SPW'),
            (bob.gender_set, set('W')),
            (bob.seek_gender_set, set(['M', 'W','TW','TM','Q']))
       )
        self.all_equal(
            (bobrr.treat_as_man, False),
            (bobrr.treat_as_woman, True)
       )

        bobrr=RegRecord.objects.get(event="testing1", psdid="P_seek_W")
        bob=bobrr.indiv
        self.all_equal(
            (bob.first_name, 'P_seek_W'),
            (bob.gender_set, set(['W','M','TW','TM','Q'])),
            (bob.seek_gender_set, set('W'))
       )
        self.all_equal(
            (bobrr.treat_as_man, True),
            (bobrr.treat_as_woman, False)
       )


    def test_no_crash(self):
        bobrr=RegRecord.objects.get(event="testing1", psdid="SSW")

        bobrr.all_past_dates()
        bobrr.all_additionals()
        self.assertTrue(bobrr.namestring != "")


    def test_modal_date(self):
        """
        Check all the stats of one person's interest in another
        Cut and paste this method to do new pairs of folks
        """
        bob=RegRecord.objects.get(event="testing1", psdid="SSM")
        lulu=RegRecord.objects.get(event="testing1", psdid="SSW")

        self.assertEqual(bob.mf_gender_match(lulu), False)
        self.assertEqual(bob.location_overlap(lulu), True)
        self.assertEqual(bob.ok_gay_match(lulu), True)
        self.assertEqual(bob.ok_str_match(lulu), True)
        self.assertEqual(bob.match_horror(lulu), 90)


    def test_person_interest(self):
        """
        Typical straight man looking for woman (who is looking for many things and thus
        likes the straight man
        """
        bob=RegRecord.objects.get(event="testing1", psdid="SSM")
        lulu=RegRecord.objects.get(event="testing1", psdid="SSW")
        event=Event.objects.get(event="testing1")

        self.assertTrue(bob.will_date(lulu))
        self.assertFalse(bob.will_date(bob))
        self.assertFalse(lulu.will_date(lulu))
        self.assertTrue(lulu.will_date(bob))

        #         self.assertEqual(bob.interest_score(lulu), 1)
        #         self.assertEqual(lulu.interest_score(bob), 3)
        #         self.assertEqual(lulu.interest_score(lulu), 5)

        # Check pansexual woman now
        lulu=RegRecord.objects.get(event="testing1", psdid="SPW")
        self.assertTrue(bob.will_date(lulu))
        self.assertTrue(lulu.will_date(lulu))
        self.assertTrue(lulu.will_date(bob))

        #self.assertEqual(bob.interest_score(lulu), 1)
        #self.assertEqual(lulu.interest_score(bob), 3)
        #self.assertEqual(lulu.interest_score(lulu), 5)


    def test_highlevel_links(self):

        response=self.client.get('/individual/testing1')
        self.assertTrue(response.status_code, 200)
        self.assertNotIn("Error", response.content)
        #print(response.content)

        # gets log-in screen
        response=self.client.get('/manage/testing1')
        self.assertTrue(response.status_code, 200)
        self.assertNotIn("Error", response.content)

#         from django.core.urlresolvers import reverse
#         response=client.get(reverse('polls:index'))
#
#         # get a response from '/'
#         response=client.get('/')
#         # we should expect a 404 from that address
#         response.status_code
#         404
#         # on the other hand we should expect to find something at '/polls/'
#         # we'll use 'reverse()' rather than a hardcoded URL
#         from django.core.urlresolvers import reverse
#         response=client.get(reverse('polls:index'))
#         response.status_code
#         200
#         response.content
#         '\n\n\n    <p>No polls are available.</p>\n\n'
#         # note - you might get unexpected results if your ``TIME_ZONE``
#         # in ``settings.py`` is not correct. If you need to change it,
#         # you will also need to restart your shell session
#         from polls.models import Question
#         from django.utils import timezone
#         # create a Question and save it
#         q=Question(question_text="Who is your favorite Beatle?", pub_date=timezone.now())
#         q.save()
#         # check the response once again
#         response=client.get('/polls/')
#         response.content
#         '\n\n\n    <ul>\n    \n        <li><a href="/polls/1/">Who is your favorite Beatle?</a></li>\n    \n    </ul>\n\n'
#         # If the following doesn't work, you probably omitted the call to
#         # setup_test_environment() described above
#         response.context['latest_question_list']
#         [<Question: Who is your favorite Beatle?>]



