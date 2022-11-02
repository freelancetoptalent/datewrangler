"""
Models used to hold information about the scheduling, including what things to not schedule, the schedule itself,
auxillary things like cruising or notes to attach to a given RegRecord for communication.

"""


from django.db import models
import sys
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from register import describe
from register.decorators import memoized_property
from register.textquestion import TextResponse
from matchmaker.models import MatchRecord
from .psdcheckbox import getPSDCheckboxOptions, genSeekAndPrefs, ModelSetupError


import logging
logger = logging.getLogger('register.models')



class BreakRecord(models.Model):
    """
    This stores a hand-break (i.e., two people who should not be seated
    next to each other)

    There does not need to be symmetry in these (i.e. pairs of entries where
    if psdid, other_psdid is in the
    database, then the reverse should be as well.)
    """
    friend_ok = models.BooleanField(default=False, verbose_name="Friendship Date Still Okay (Y/N)")
    psdid = models.CharField(max_length=12, blank=True)
    other_psdid = models.CharField(max_length=12, blank=True)
    notes = models.TextField(blank=True)

    def __unicode__(self):
        return "%s X %s - %s" % ( self.psdid, self.other_psdid, self.notes )






class CruiseRecord(models.Model):
    """
    This stores a cruise (i.e. one person wants their info sent
    unilaterally to another person).
    """
    psdid = models.CharField(max_length=7, blank=True)
    other_psdid = models.CharField(max_length=7, blank=True)
    event = models.CharField( max_length=20 )

    def __unicode__(self):
        return "%s cruised %s at %s" % (self.psdid, self.other_psdid, self.event)





class LinkRecord(models.Model):
    """
    This registers that psdid should not date anyone that psdid_alias has dated
    """
    psdid = models.CharField(max_length=12, blank=True)
    psdid_alias = models.CharField(max_length=12, blank=True)

    def __unicode__(self):
        return "%s takes history from %s" % (self.psdid, self.psdid_alias,)


class DateSheetNote(models.Model):
    """
    Hack to keep OVERALL notes for date sheets (i.e., notes to go with date sheet email sent to psdid in question)
    """
    psdid = models.CharField(max_length=12, blank=True)
    event = models.CharField(max_length=20)

    notes = models.TextField(blank=True, null=True)


class DateRecord(models.Model):
    """
    This stores dating history.

    There _should be_ pairs of entries where if psdid, other_psdid is in the
    database, then the reverse should be as well.
    """
    friend_date = models.BooleanField(default=True, verbose_name="Date was a Friendship Date (Y/N)")
    psdid = models.CharField(max_length=12, blank=True)
    other_psdid = models.CharField(max_length=12, blank=True)
    table = models.CharField(max_length=12, blank=True)
    round = models.PositiveIntegerField(verbose_name="Dating Round")
    #    event = models.ForeignKey(Event, null=True)
    event = models.CharField(max_length=20)
    said_yes = models.NullBooleanField(default=True, verbose_name="psdid said YES to other_psdid (Y/N)", null=True)
    they_said_yes = models.NullBooleanField(default=True, verbose_name="other_psdid said YES to psdid (Y/N)", null=True)

    # To be implemented eventually!!
    # user_comments = models.TextField(blank=True,null=True)
    # notes = models.TextField(blank=True,null=True)  # For admin notes

    def is_mutual(self):
        if self.said_yes == None or self.they_said_yes == None:
            return None
        elif self.said_yes and self.they_said_yes:
            return True
        else:
            return False

    @property
    def we_filled(self):
        return self.said_yes != None

    @property
    def they_filled(self):
        return self.they_said_yes != None

    @property
    def filled(self):
        return self.said_yes != None and self.they_said_yes != None

    def __unicode__(self):
        if self.said_yes == None:
            if self.they_said_yes == None:
                ss = " ?/?"
            elif self.they_said_yes:
                ss = " ?/yes"
            else:
                ss = " ?/no"

            if self.friend_date:
                ss = ss + " (F)"
            return "%s dating %s - %s" % (self.psdid, self.other_psdid, ss,)
        else:
            ss = ""
            if self.said_yes:
                if self.they_said_yes == None:
                    ss = "yes/?"
                elif self.they_said_yes:
                    ss = "mutual"
                else:
                    ss = "yes/no"
            else:
                if self.they_said_yes == None:
                    ss = "no/?"
                elif self.they_said_yes:
                    ss = "no/yes"
                else:
                    ss = "no/no"

            if self.friend_date:
                ss = ss + " (F)"
            return "%s dating %s - %s" % (self.psdid, self.other_psdid, ss)



