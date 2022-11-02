"""

This file tests group matching with more complex gender patterns. 

"""


from django.test import TestCase
from register.models import MATCH_NO, Person
from .factories import RegRecordFactory, EventFactory, PersonFactory
from psd.management.commands.testdb import makeTestDB

import logging

class TestRegMatch(TestCase):

    def setUp(self):
        event = EventFactory(event='test1')
        logging.disable(logging.CRITICAL)
        makeTestDB("testing1", True, False, trigender=True, verbose=False)

    def test_some_groups_matches(self):
        bob = RegRecordFactory(event="test1", seek_groups=False)
        mack_and_sue = RegRecordFactory(event="test1", people = [PersonFactory(gender="M", seek_gender="W"),
                                          PersonFactory(gender="W,CW", seek_gender="W,M")])
        assert mack_and_sue.is_group
        self.assertEqual(bob.match_horror(mack_and_sue), MATCH_NO)

        p1 = PersonFactory( seek_gender="CM,TM,CW,TW,M,W,Q", age=100 )
        bob = RegRecordFactory( event="test1", people=[p1], seek_groups=True )

        self.assertTrue( bob.will_date( mack_and_sue ) )
        self.assertFalse( mack_and_sue.will_date( bob ) )




    def test_no_interest_groups_matches(self):
        """
        All of group likes Ann, but Ann doesn't like anyone in group
        """
        p1 = PersonFactory( gender="W", seek_gender="M", seek_age_min=20, seek_age_max=40 )
        ann = RegRecordFactory(event="test1", seek_groups=True, groups_match_all=True, people=[p1] )

        mack_and_sue = RegRecordFactory(event="test1", groups_match_all=False,
                                people = [PersonFactory(gender="M", age=50, seek_gender="W"),
                                          PersonFactory(gender="W,CW", age=50, seek_gender="W,M")])
        assert mack_and_sue.is_group
        self.assertEqual(ann.match_horror(mack_and_sue), MATCH_NO)

        print ann.geekcode()
        print mack_and_sue.geekcode()
        evt = ann.ev

        for p in mack_and_sue.members:
            print "%s: grp->indiv = %s\t\tindiv->grp = %s" % ( p.minicode(), p.match_horror( ann.indiv, evt ), ann.indiv.match_horror( p, evt ) )
        self.assertEqual( mack_and_sue.members[0].match_horror( ann.indiv, evt ), 100 )
        self.assertEqual( mack_and_sue.members[1].match_horror( ann.indiv, evt ), 100 )
        self.assertEqual( ann.indiv.match_horror( mack_and_sue.members[0], evt ), 10000 )
        self.assertEqual( ann.indiv.match_horror( mack_and_sue.members[1], evt ), 10000 )


        self.assertEqual( ann.groups_match_all, True )
        self.assertEqual( mack_and_sue.groups_match_all, False )
        self.assertEqual( ann.will_date( mack_and_sue ), False )
        self.assertEqual( mack_and_sue.will_date( ann ), False )  # mutual needed

        ann.groups_match_all = False
        self.assertEqual( ann.groups_match_all, False )
        self.assertEqual( mack_and_sue.groups_match_all, False )
        self.assertEqual( ann.will_date( mack_and_sue ), False )
        self.assertEqual( mack_and_sue.will_date( ann ), False )

        mack_and_sue.groups_match_all = True
        self.assertEqual( ann.groups_match_all, False )
        self.assertEqual( mack_and_sue.groups_match_all, True )
        self.assertEqual( ann.will_date( mack_and_sue ), False )
        self.assertEqual( mack_and_sue.will_date( ann ), False )

        ann.groups_match_all = True
        mack_and_sue.groups_match_all = True
        self.assertEqual( ann.will_date( mack_and_sue ), False )
        self.assertEqual( mack_and_sue.will_date( ann ), False )



    def test_single_member_interest_groups_matches(self):
        """
        Ann wants one person in group.  Both people in group want Ann.
        """
        p1 = PersonFactory( gender="W", seek_gender="M", seek_age_min=20, seek_age_max=40 )
        ann = RegRecordFactory(event="test1", seek_groups=True, groups_match_all=True, people=[p1] )

        mack_and_sue = RegRecordFactory(event="test1", groups_match_all=False,
                                people = [PersonFactory(gender="M", age=30, seek_gender="W"),
                                          PersonFactory(gender="W,CW", age=50, seek_gender="W,M")])

        print ann.geekcode()
        print mack_and_sue.geekcode()
        evt = ann.ev

        for p in mack_and_sue.members:
            print "%s: grp->indiv = %s\t\tindiv->grp = %s" % ( p.minicode(), p.match_horror( ann.indiv, evt ), ann.indiv.match_horror( p, evt ) )
        self.assertEqual( mack_and_sue.members[0].match_horror( ann.indiv, evt ), 100 )
        self.assertEqual( mack_and_sue.members[1].match_horror( ann.indiv, evt ), 100 )
        self.assertEqual( ann.indiv.match_horror( mack_and_sue.members[0], evt ), 100 )
        self.assertEqual( ann.indiv.match_horror( mack_and_sue.members[1], evt ), 10000 )

        ann.groups_match_all = True
        mack_and_sue.groups_match_all = False
        self.assertEqual( ann.will_date( mack_and_sue ), False )
        self.assertEqual( mack_and_sue.will_date( ann ), False )

        ann.groups_match_all = False
        mack_and_sue.groups_match_all = True
        self.assertEqual( ann.will_date( mack_and_sue ), True )
        self.assertEqual( mack_and_sue.will_date( ann ), False )

        mack_and_sue.groups_match_all = False
        ann.groups_match_all = False
        self.assertEqual( ann.will_date( mack_and_sue ), True )
        self.assertEqual( mack_and_sue.will_date( ann ), True )

        mack_and_sue.groups_match_all = True
        ann.groups_match_all = True
        self.assertEqual( ann.will_date( mack_and_sue ), False )
        self.assertEqual( mack_and_sue.will_date( ann ), False )



    def test_single_member_interest_groups_matches(self):
        """
        Ann wants one person in group.  That person in group wants Ann, but not the other person
        """
        p1 = PersonFactory( gender="W", seek_gender="M", seek_age_min=20, seek_age_max=40 )
        ann = RegRecordFactory(event="test1", seek_groups=True, groups_match_all=True, people=[p1] )

        mack_and_sue = RegRecordFactory(event="test1", groups_match_all=False,
                                people = [PersonFactory(gender="M", age=30, seek_gender="W"),
                                          PersonFactory(gender="W,CW", age=50, seek_gender="TW,M")])

        print ann.geekcode()
        print mack_and_sue.geekcode()
        evt = ann.ev

        for p in mack_and_sue.members:
            print "%s: grp->indiv = %s\t\tindiv->grp = %s" % ( p.minicode(), p.match_horror( ann.indiv, evt ), ann.indiv.match_horror( p, evt ) )
        self.assertEqual( mack_and_sue.members[0].match_horror( ann.indiv, evt ), 100 )
        self.assertEqual( mack_and_sue.members[1].match_horror( ann.indiv, evt ), 10000 )
        self.assertEqual( ann.indiv.match_horror( mack_and_sue.members[0], evt ), 95 )
        self.assertEqual( ann.indiv.match_horror( mack_and_sue.members[1], evt ), 10000 )

        ann.groups_match_all = False
        mack_and_sue.groups_match_all = False
        self.assertEqual( ann.will_date( mack_and_sue ), True )
        self.assertEqual( mack_and_sue.will_date( ann ), True )

        ann.groups_match_all = False
        mack_and_sue.groups_match_all = True
        self.assertEqual( ann.will_date( mack_and_sue ), True )
        self.assertEqual( mack_and_sue.will_date( ann ), False )

        ann.groups_match_all = True
        mack_and_sue.groups_match_all = False
        self.assertEqual( ann.will_date( mack_and_sue ), False )
        self.assertEqual( mack_and_sue.will_date( ann ), True )

        ann.groups_match_all = True
        mack_and_sue.groups_match_all = True
        self.assertEqual( ann.will_date( mack_and_sue ), False )
        self.assertEqual( mack_and_sue.will_date( ann ), False )



    def test_cross_groups_matches(self):
        """
        Ann wants one person in group.  The other person in group wants Ann, but not the person Ann wants
        """
        p1 = PersonFactory( gender="W", seek_gender="M", seek_age_min=20, seek_age_max=40 )
        ann = RegRecordFactory(event="test1", seek_groups=True, groups_match_all=True, people=[p1] )

        mack_and_sue = RegRecordFactory(event="test1", groups_match_all=False,
                                people = [PersonFactory(gender="M", age=30, seek_gender="TW,Q"),
                                          PersonFactory(gender="W,CW", age=50, seek_gender="W,M")])
        evt = ann.ev

        for p in mack_and_sue.members:
            print "%s: grp->indiv = %s\t\tindiv->grp = %s" % ( p.minicode(), p.match_horror( ann.indiv, evt ), ann.indiv.match_horror( p, evt ) )
        self.assertEqual( mack_and_sue.members[0].match_horror( ann.indiv, evt ), 10000 )
        self.assertEqual( mack_and_sue.members[1].match_horror( ann.indiv, evt ), 100 )
        self.assertEqual( ann.indiv.match_horror( mack_and_sue.members[0], evt ), 95 )
        self.assertEqual( ann.indiv.match_horror( mack_and_sue.members[1], evt ), 10000 )


        ann.groups_match_all = False
        mack_and_sue.groups_match_all = False
        self.assertEqual( ann.will_date( mack_and_sue ), True )
        self.assertEqual( mack_and_sue.will_date( ann ), False )

        ann.groups_match_all = False
        mack_and_sue.groups_match_all = True
        self.assertEqual( ann.will_date( mack_and_sue ), True )
        self.assertEqual( mack_and_sue.will_date( ann ), False )

        ann.groups_match_all = True
        mack_and_sue.groups_match_all = False
        self.assertEqual( ann.will_date( mack_and_sue ), False)
        self.assertEqual( mack_and_sue.will_date( ann ), False )

        ann.groups_match_all = True
        mack_and_sue.groups_match_all = True
        self.assertEqual( ann.will_date( mack_and_sue ), False )
        self.assertEqual( mack_and_sue.will_date( ann ), False )




