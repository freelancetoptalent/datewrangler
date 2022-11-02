"""
Code for some of the classes revolving around the number of tables and when breaks are in the scheduling.
"""

from django.db import models
import sys
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from register import describe
from register.decorators import memoized_property
from register.textquestion import TextResponse
from matchmaker.models import MatchRecord

import datetime

import logging
logger = logging.getLogger('register.systemmodels')



class Event(models.Model):
    event = models.CharField( max_length=20 )
    longname = models.CharField( max_length=40 )
    location = models.CharField( max_length= 100 )
    address = models.CharField( max_length=100 )
    locationURL = models.CharField( max_length=100 )
    accessdetails = models.TextField( max_length=200 )
    cost = models.PositiveIntegerField(verbose_name="Cost per person")
    doorcost = models.PositiveIntegerField(verbose_name="Cost per person at door")
    payment_systems = models.CharField( max_length=40, verbose_name="List of payment systems that are turned on" )
    paypal_email = models.EmailField(verbose_name="Email for paypal account")
    wepay_email = models.EmailField(verbose_name="Email for wepay account" )
    free_text = models.BooleanField( default=False, verbose_name="Have the free text question for matching?" )
    info_email = models.EmailField(verbose_name="Email for asking registration questions" )
    mailing_list_url = models.CharField( max_length=100, verbose_name="Link to the mailing list for this event" )
    homepage_url = models.CharField( max_length=100, verbose_name="Link to the home page for this event or event organizers" )
    has_childcare = models.BooleanField( default=False, verbose_name="Childcare will be provided at the event" )
    regclosed = models.BooleanField( default=False, verbose_name="Registration is closed---no additions allowed" )
    regfrozen = models.BooleanField( default=False, verbose_name="Registration is frozen--no updating of registration forms allowed" )
    no_ssm = models.BooleanField( default=False, verbose_name="Single straight men will be asked to bring a gender-balance companion" )
    no_emailing = models.BooleanField( default=False, verbose_name="Do not email update emails or admin log emails (check if there is no internet service)." )
    extra_questions = models.ManyToManyField('MatchQuestion', blank=True)
    date = models.DateField()
    starttime = models.TimeField()
    deadlinetime = models.TimeField()
    stoptime = models.TimeField()
    numrounds = models.IntegerField( default=0, verbose_name="Number of dating rounds (0 means unscheduled)" )

    # For tracking the event when it is running
    curround = models.IntegerField( default=0, verbose_name="Current round (0 means event not started)" )
    curroundend = models.TimeField( auto_now_add=True, blank = True )


    def __unicode__(self):
        return self.event + " on " + str(self.date)

    @memoized_property
    def cached_extra_questions(self):
        return self.extra_questions.all()

    def usepayment(self, system_code):
        """
        Different payment systems turned on or off for this event.
        :param system_code: List of payment systems hidden in forms.html (not the right place)
        :return: True or False
        """
        res = describe.csv_to_set(self.payment_systems)
        return system_code in res

    @memoized_property
    def use_stripe(self):
        return self.usepayment("ST")

    @memoized_property
    def use_paypal(self):
        return self.usepayment("PP")

    @memoized_property
    def running(self):
        return self.curround > 0 and self.numrounds > 0 and self.curround <= self.numrounds

    @memoized_property
    def completed(self):
        return self.numrounds > 0 and self.curround > self.numrounds



def getTextTranslationTable():
    """
    Build a dict of what words should be mapped to what words.  This will be used
    to translate people's text responses appropriately.
    """
    trs = TranslationRecord.objects.all()
    logger.debug( "Building translation table: got %d entries." % (len(trs), ) )
    tbl = {}
    for t in trs:
        tbl[ t.synonym ] = t.base_word
    return tbl




class TranslationRecord(models.Model):
    """
    To record text question word equivilencies (for the text matching)

    Any found synonym will be matched to the base word before calculating matching.
    """
    base_word = models.CharField(max_length=50, blank=True)
    synonym = models.CharField(max_length=50, blank=True)

    def __unicode__(self):
        return "%s maps to %s" % (self.synonym, self.base_word,)





class Organization(models.Model):
    site = models.ForeignKey(Site)
    info_email = models.EmailField(verbose_name="Email for asking registration questions" )
    mailing_list_url = models.CharField( max_length=100, verbose_name="Link to the mailing list for the organization" )
    homepage_url = models.CharField( max_length=100, verbose_name="Link to the home page for the organization" )

    def __unicode__(self):
        return "[Organization Object for %s]" % (self.site, )

