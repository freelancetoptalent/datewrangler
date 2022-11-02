"""
Utility function to get the schedule of dates for a given psdid at given event.

This method used by both the contact and dashboard packages.
"""

from functools import partial
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.template import RequestContext
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse

from register.models import fetch_regrecord
from register.schedule_models import DateRecord
from register.system_models import Event
from register.models import fetch_matchrecord

import logging
logger = logging.getLogger(__name__)



class DateRecordStub:
    round = 0
    other_person = ""
    other_code = None

    def __init__(self, round, other_person, other_code ):
        self.round= round
        self.other_person = other_person
        self.other_code = other_code



def get_date_schedule( psdid, event_name ):
    """
    Get sequence of dates for 'psdid' at 'event_name'
    Used for printing to django templates
    """

    # Get event, throw error if not found
    event = Event.objects.get(event=event_name)
    numround = event.numrounds

    print "Getting date schedule for %s at %s" % (psdid, event_name )
    dates = DateRecord.objects.filter( event=event_name, psdid=psdid ).order_by('round')
    
    full_date = []
    for d in dates:
            d.other_person = fetch_regrecord( event_name, d.other_psdid )
            if not d.other_person == None:
                d.other_code = d.other_person.minicode()
                d.other_nick = d.other_person.nickname
            else:
                d.other_code = "missing person"

            d.match = fetch_matchrecord( d.psdid, d.other_psdid, event_name )
            full_date.append( d )
            

    gots = [x.round for x in dates]
    miss = set(range(1, numround + 1)).difference(gots)

    for rnd in miss:
        full_date.append( DateRecordStub( rnd, "no date", "" ) )

    full_date = sorted( full_date, key=lambda dr: dr.round )

    #for d in full_date:
    #    print "%s - %s" % ( d.round, d.other_person )
    return full_date

