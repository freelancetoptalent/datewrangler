# views.py

import itertools
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
from register.models import Person, RegRecord, RecessRecord, BreakRecord, DateRecord, CruiseRecord, Event, TableListRecord, TableRecord, TranslationRecord, fetch_regrecord
from matchmaker.models import MatchRecord
from matchmaker.matrix_maker import updateMatchRecords_async
from register.views.printouts import make_schedules
from register.forms import UpdateNotesForm, PersonSearchForm, MakeRecessForm, MakeTableTableForm, PrintSchedulesForm, ScheduleForm, HandMatchesForm, NextSheetForm, PSDIDorEmailForm, BreakForm, MultiBreakForm, CruiseForm, TranslationForm
from register.models import fetch_matchrecord
from register.views.admin_regrecord import break_a_match
from matchmaker import date_scheduler

from register.views.util import HttpStreamTextResponse, async_print_text_response
import register.views.textwrangler as textwrangler

import logging
logger = logging.getLogger('register.commander')

import collections
import django.forms as forms


class MyAction:
      action = "default"
      action_description = "default action"
      argument_description = "bleh"

      def __init__(self, arg1, arg2, arg3):
          self.action=arg1
          self.action_description=arg2
          self.argument_description=arg3

ACTIONS = ( MyAction('', 'Clean Display', ''),
        MyAction('maketestdb', 'Make testing database', ''),
        MyAction('fix', 'Admin: Fix Group Flags - set the "group" flag based on number of people listed on regrecord', ''),
        MyAction('clean', 'Admin: Clean Database (remove Person Records and User accounts without RegRecords)', '' ),
        MyAction('dropmissingsheets', "Remove match records for event that are not fully filled in", "" ),
        MyAction('installRpackages', 'Admin: Install SQL package into R program from CRAN repository.', '' ),
        MyAction('testR', 'Admin: Test R Calling.', '' ),
        )




def clean_database():
    """
    Delete person records with no regrecords.
    Delete users with no regrecords that are not staff level
    List regrecords that have no user account.
    """

    results = unicode("")
    users = User.objects.all()
    rrs = RegRecord.objects.all()

    all_rr_ids= set()
    allfolk = set()
    results += "\nID List: "
    for rr in rrs:
        folk = [p.psdid for p in rr.people.all() ]
        allfolk.update(folk)
        #results += "\n" + rr.psdid + "/" + str(rr)
        all_rr_ids.add( rr.psdid )
        try:
            usr = User.objects.get( username=rr.psdid )
        except User.DoesNotExist:
            results += "\nNo user for %s\n" % (rr,)
        except User.MultipleObjectsReturned:
            results += "\nMultiple users for %s\n" % (rr, )

    people_deleted = 0
    for p in Person.objects.all():
        if not p.psdid in allfolk:
            res = "Deleting %s" % p
            logger.debug( res )
            results += "\n" + res
            p.delete()
            people_deleted += 1

    users_deleted = 0
    for usr in users:
        if not usr.is_staff:
            if not usr.username in all_rr_ids:
                res = "Deleting User %s" % usr
                logger.debug( res )
                results += "\n" + res
                usr.delete()
                users_deleted += 1
        else:
            results += "\nSkipping staff " + str(usr)

    return """<pre>database cleaned
    # People deleted = %s
    # users deleted = %s
    Details: %s
    </pre><br>
    All rrs: %s""" % (people_deleted, users_deleted, results, all_rr_ids )


def fix_group_codes():
    res = ""
    for rr in RegRecord.objects.all():
        if (rr.is_group and len( rr.people.all() ) == 1) or (not rr.is_group and len(rr.people.all()) != 1):
            st = "%s  %s  %s  %s" % ( rr.psdid, rr.event, rr.is_group, len(rr.people.all()))
            logger.debug( "Fix Group Code: " + st )
            res += "\n<br>" + st
            if rr.is_group:
                 rr.is_group = False
            else:
                 rr.is_group = True
            rr.save()
    if res == "":
        res = "no broken group flags found"

    res2 = ""
    for pp in Person.objects.all():
        seeks = pp.seek_gender_set
        prefs = pp.pref_gender_set
        if seeks == prefs:
            pp.seek_gender = genCodeForSeekAndPrefs( seeks, set() )
            pp.save()
            res2 += "\n<br>Updated seek-pref set for %s to %s" % (pp, pp.seek_gender)
    if res2 == "":
        res2 = "no bad seek-pref sets found"

    return res + "\n<br>" + res2




@staff_member_required
def commander( request, action=None, extraArg=None ):
    """
    This method redirects a bunch of calls to a bunch of different functions.
    It also prints out a list of commands you can do with these calls.
    """
    if action=="" or action=="main":
        results="""Click on action desired."""
    elif action=="allevents":
        rev = reverse("admin:register_event_changelist")
        return HttpResponseRedirect( rev )
    elif action=="clean":
        results=clean_database()
    elif action=="fix":
        results=fix_group_codes()

    elif action=="installRpackages":
        return HttpStreamTextResponse( install_packages_async(), head_string="<p>Attempting to download and install R packages</p>" )
    elif action=="testR":
        return HttpStreamTextResponse( test_R_async(), head_string="<p>Testing R Code</p>" )

    else:
       results="Action '%s' not understood." % (action,)

    if not results == """Click on action desired.""":
        results = "<b>RESULT:</b><p>" + results

    return render(request,  'dashboard/commander.html', {'event_name':'commander',
                                   'actions':ACTIONS,
                                   'results':results } )



