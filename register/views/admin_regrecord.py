"""
Code for manually breaking potential matches between two PSDIDs.
"""

import pdb, itertools
import sys
from functools import partial
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.template import RequestContext
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.core.urlresolvers import reverse
from django.forms.models import modelformset_factory
from django.forms.formsets import formset_factory
import re

from register.demographics import print_demographics_async
# from psd.RcodeHooks import schedule_async, install_packages_async, test_R_async, make_nametags_async
import register.demographics
import register.views.contact
from register.psdcheckbox import genCodeForSeekAndPrefs, genSeekAndPrefs
from register.models import Person, RegRecord, fetch_regrecord
from register.system_models import Event, TranslationRecord
from register.schedule_models import BreakRecord, DateRecord, CruiseRecord
from register.table_models import TableListRecord, TableRecord, RecessRecord
from matchmaker.models import MatchRecord
from matchmaker.matrix_maker import updateMatchRecords_async
from register.views.printouts import make_schedules
from register.forms import UpdateNotesForm, PersonSearchForm, MakeRecessForm, MakeTableTableForm, PrintSchedulesForm, ScheduleForm, NextSheetForm, PSDIDorEmailForm, BreakForm, MultiBreakForm, CruiseForm, TranslationForm
from register.models import fetch_matchrecord

from matchmaker import date_scheduler

import logging
logger = logging.getLogger('register.admin_regrecord')

import collections
import django.forms as forms



def break_a_match( psdid, other_psdid, reason ):
    """
    Enter a breakrecord after checking if it is not already present in database
    """
    psdid = psdid.upper()
    other_psdid = other_psdid.upper()

    break_listA = BreakRecord.objects.filter( psdid=psdid, other_psdid=other_psdid )
    break_listB = BreakRecord.objects.filter( psdid=other_psdid, other_psdid=psdid )
    if break_listA or break_listB:
        return 0
    else:
        mt = BreakRecord(psdid=psdid, other_psdid=other_psdid, notes=reason )
        mt.save()
        return 1


@staff_member_required
def break_matches(request, event_name, psdid ):
    """
    Break matches.  Remove from the current potential matches matrix and
    also add a BreakRecord so that there is never a match in the future,
    either.
    """
    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request, 'error.html', {'message' : "Sorry.  You are trying to do break list for an event '%s' that does not exist.  Please try again." % (event_name,)})

    try:
        rr = RegRecord.objects.get(psdid=psdid, event=event_name)
    except Event.DoesNotExist:
        return render(request, 'error.html', {'message' : "Sorry.  You are trying to do break list for a PSDID '%s' that does not exist.  Please try again." % (psdid,)})

    break_list = []
    if request.method == 'POST':
        break_list = request.POST.getlist('break')
        brecs = MatchRecord.objects.filter(event=event_name, psdid1=psdid, psdid2__in=break_list)
        for br in brecs:
            break_a_match(psdid, br.psdid2, "hand break via break_matches function")

        unbreak_list = request.POST.getlist('unbreak')
        BreakRecord.objects.filter( id__in= unbreak_list ).delete()


    break_list = set( itertools.chain( BreakRecord.objects.filter( psdid=psdid ), BreakRecord.objects.filter( other_psdid=psdid ) ) )
    broke_psdid_list = set( [br.psdid for br in break_list] )
    broke_psdid_list.update( [br.other_psdid for br in break_list] )

    liked = set( [r.psdid1 for r in MatchRecord.objects.filter( event=event_name, psdid2=psdid ) ])

    matches = MatchRecord.objects.filter( event=event_name, psdid1=psdid ).exclude( psdid2__in=broke_psdid_list ).order_by('psdid2')

    for m in matches:
        try:
            p2 = RegRecord.objects.get( psdid=m.psdid2, event=event_name )
            m.namestring = p2.namestring
            m.mutual = m.psdid2 in liked
        except:
            logger.error( "Failed to find the RegRecord for '%s-%s'" % ( event_name, m.psdid2 ) )
            m.namestring = "[Error: Failed to Find]"

    return render(request, 'matchlist.html', {'matches': matches, 'rr': rr, 'breaklist':break_list, 'event_name':event_name})

