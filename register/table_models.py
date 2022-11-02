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


import logging
logger = logging.getLogger('register.tablemodels')





class TableListRecord(models.Model):
    event = models.CharField(max_length=15, blank=True)

    def __unicode__(self):
        #numtabs = len( self.group_set.all() )
        #s = "List for %s (%s tables)" % (self.event, numtabs)
        s = "Table list for %s" % (self.event,)
        return s

    def describe(self):
        tablelist = TableRecord.objects.filter(group=self)
        statOK = [t.name for t in tablelist if t.statOK ]
        groupOK = [t.name for t in tablelist if t.groupOK ]
        lstS = ", ".join(statOK)
        lstG = ", ".join(groupOK)
        header = "%s tables with %s stationary-ok tables and %s group-OK tables" % (len(tablelist), len(statOK), len(groupOK) )
        header += "\n\nStationary: %s\n\nGroup: %s\n" % (lstS, lstG )
        return header


class TableRecord(models.Model):
    name = models.CharField(max_length=12, blank=True)
    statOK = models.BooleanField(default=False, verbose_name="Okay for stationary folks (Y/N)")
    groupOK =  models.BooleanField(default=False, verbose_name="Okay for groups (Y/N)")
    quality = models.PositiveIntegerField(verbose_name="Quality")
    description = models.CharField( max_length=12, blank=True) # Short description of table to help folks.
    group = models.ForeignKey(TableListRecord)

    def __unicode__(self):
        s = "%s/%s - %s" % ( self.group.event, self.name, self.quality )
        if self.statOK:
            s += "/stat"
        if self.groupOK:
            s += "/grp"
        if len( self.description ) > 0:
            s += " (%s)" % ( self.description, )
        return s




class RecessRecord(models.Model):
    """
    This means the given psdid has mandatory free time during the given
    rounds of the given event. Can also have the special psdid "template".
    The 'volatile' field should be set to False for hand-added recesses
    (e.g. a person has said they need to leave early).
    """
    psdid = models.CharField(max_length=12, blank=True)
    event = models.CharField(max_length=15)
    rounds = models.CharField(max_length=30)
    kind = models.CharField(max_length=20)
    volatile = models.BooleanField(default=False)

    def __unicode__(self):
        return "Recess for %s at %s: rounds %s '%s'" % (self.psdid, self.event, self.rounds, self.kind)

