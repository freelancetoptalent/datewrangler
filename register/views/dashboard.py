# views.py

"""
This has much of the administrative function for managing a given event. It has a list of actions, ACTION, which gets
rendered into a webpage with a link for each action. These links then get dynamically mapped two different function
calls to implement those actions. Most of these functions are themselves forms that then get filled out and submitted.

There are two ways that this dynamic list can appear. It can appear as a webpage and also as plain text tacked on
to the end of a streaming text response, for example after running the scheduler.

The core dispatching function is called event_manager, near the bottom of this script.
"""

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
import datetime
import re

from register.demographics import print_demographics_async
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
from register.forms import UpdateNotesForm, PersonSearchForm, MakeRecessForm, MakeTableTableForm, ManualDateForm, PrintSchedulesForm, ScheduleForm, HandMatchesForm, NextSheetForm, PSDIDorEmailForm, BreakForm, MultiBreakForm, CruiseForm, TranslationForm, RunEventForm
from register.forms import PaymentPasterForm
from register.models import fetch_matchrecord
from register.views.admin_regrecord import break_a_match
from matchmaker import date_scheduler

from register.views.util import HttpStreamTextResponse, async_print_text_response
import register.views.textwrangler as textwrangler
from register.views.date_schedule import get_date_schedule

import logging
logger = logging.getLogger(__name__)

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
        MyAction('allevents', 'View All Events', ''),
        MyAction('editevent', 'Edit the Event Record', ''),
        MyAction('regrecords', 'Edit Reg Records', '' ),
        MyAction('listcomments', 'List Comments, Notes and Referrals', ''),
        MyAction('listchildcare', 'List Childcare Requests', ''),

        MyAction('listpeople', 'List People Registered', '[all]: list everyone, not just this event.'),
        MyAction('search', 'Search for Dating Entity',''),
        MyAction('email', 'Make email list of participants (seperates checked folks vs. not)', ''),
        MyAction('calcpay', 'Calc number of registered folks, total dollars collected, etc.', '' ),
        MyAction('emailpreevent', "Mass information email pre event", ""),
        MyAction('demographics', "Print out demographics of event", 'NotNo/In/All: Who to include from data.' ),
        MyAction('nametags', "Make csv list that can be turned into nametags", "" ),
        MyAction('multibreak', "Break possibility of a match between multiple pairs of PSD IDs", "" ),
        MyAction('updatenotes', "Update the notes field for a bunch of reg records at once", ""),
        MyAction('examinetext', "Examine the usage of the free text question", ""),
        MyAction('paymentpaste', "Paste Paypal records to check off paid", ""),
        "",
        MyAction('maketabletable', "(1) Make an initial table of the dating tables.  Run once.  Will delete old tables.", "" ),
        MyAction('makerecess', "(1b) Make recess rounds for peoples breaks in the dating.", "" ),
        MyAction('checkin', "(2) Check-in participants", '' ),
        MyAction('walkinreg', "(3) Go to walk-in registration page", '' ),

        MyAction('matrix', '(4) Make the dating matrix files', '' ),
        MyAction('plandates', "(5) Figure out who is dating whom when and where", ''),
        MyAction('schedules', "(6) Make pdf of everyone's schedules", '' ),
        MyAction('runevent', "(7) Start and run the event", '' ),
        "",
        MyAction('datematrix', "Print out entire date matrix for event to screen.", '' ),
        MyAction('datesheet', "Enter marked up date sheets into database.", '' ),
        MyAction('countdates', "Count the number of dates everyone has", ''),
        MyAction('listmissingsheets', "List match records for event that are not fully filled in", "" ),
        MyAction('listbadcruises', "List cruise records with psdids that do not exist", "" ),
        MyAction('emailpostevent', "Mass email for matches post event", ""),
        MyAction('subgroupemail', "Email subgroup of an event (possibly with matches)", "" ),
        MyAction('volunteeremail', "Email volunteer email address with cruises", "" ),
        "",

        MyAction('clean', 'Admin: Clean Database (remove Person Records and User accounts without RegRecords)', '' ),
        MyAction('fix', 'Admin: Fix Group Flags - set the "group" flag based on number of people listed on regrecord', ''),
        MyAction('dropmissingsheets', "Remove match records for event that are not fully filled in", "" ),
        MyAction('testEmail', 'Admin: Test whether system can send email.', '' )
        )





@staff_member_required
def check_in_driver(request, event_name, show_all=False):

    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request, 'error.html', {'message' : "Sorry.  You are trying to do check-in for an event that does not exist or is closed.  Please try again." })

    to_update = []
    to_warn = []
    if request.method == 'POST':
        here_list = request.POST.getlist('here')
        RegRecord.objects.filter(event=event_name, id__in=here_list).update(here=True)

        cancel_list = request.POST.getlist('cancelled')
        RegRecord.objects.filter(id__in=cancel_list).update(cancelled=True)

        id_list = request.POST.getlist('paid')
        for x in id_list:
            if x in here_list or x in cancel_list:
                to_update.append(x)
            else:
                to_warn.append(x)
        RegRecord.objects.filter(id__in=to_update).update(paid=True)

    regs = RegRecord.objects.filter( event=event_name ).order_by('nickname')
    viewable = regs.filter(here__exact=False, cancelled__exact=False)
    warnable = regs.filter(id__in=to_warn)
    return render(request, 'checkin.html', {'regs': viewable, 'warnings': warnable})





@staff_member_required
def check_in_old(request, event_name ):

    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request, 'error.html', {'message' : "Sorry.  You are trying to do check-in for an event that does not exist or is closed.  Please try again." },
                              )

    to_update = []
    to_warn = []
    if request.method == 'POST':
        here_list = request.POST.getlist('here')
        print "here list: %s" % (here_list, )

        RegRecord.objects.filter(event=event_name, id__in=here_list).update(here=True)

        cancel_list = request.POST.getlist('cancelled')
        RegRecord.objects.filter(id__in=cancel_list).update(cancelled=True)

        id_list = request.POST.getlist('paid')
        for x in id_list:
            if x in here_list or x in cancel_list:
                to_update.append(x)
            else:
                to_warn.append(x)
        RegRecord.objects.filter(id__in=to_update).update(paid=True)

    regs = RegRecord.objects.filter( event=event_name ).order_by('nickname')
    viewable = regs.filter(here__exact=False, cancelled__exact=False)
    warnable = regs.filter(id__in=to_warn)
    viewable = sorted(viewable, key=lambda reg: reg.nickname.lower() )
    return render(request, 'checkin.html', {'regs': viewable, 'warnings': warnable})


@staff_member_required
def check_in(request, event_name ):

    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request,  'error.html', {'message' : "Sorry.  You are trying to do check-in for an event that does not exist or is closed.  Please try again." })

    checked_in = []
    to_update = []

    warnings = []

    # Grab everyone from the event.
    regs = RegRecord.objects.filter( event=event_name )

    if request.method == 'POST':

        # handle any undo actions
        undo_list = request.POST.getlist('undo')
        #print "here list: %s" % (here_list, )
        #print "undo list: %s" % (here_list, )
        if len( undo_list ) > 0:
            print "Undoing check-in for %s" % ( undo_list, )
            undos = regs.filter( event=event_name, id__in=undo_list )
            undos.update(here=False)
            for reg in undos:
                reg.message = "Undid check-in for %s (%s).  %s now marked as NOT HERE!" % (reg.nickname, reg.psdid, reg.nickname)
                warnings.append( reg )
        else:
            undos = None

        # handle any check-in actions
        here_list = request.POST.getlist('here')
        if len( here_list ) > 0:
            checked_in = regs.filter( event=event_name, id__in=here_list )
            checked_in.update(here=True)
        else:
            checked_in = None

        id_list = request.POST.getlist('paid')
        for x in id_list:
            if x in here_list:
                to_update.append(x)
            else:
                x.psdid = x
                x.message = "Warning: %s just mrked as paid, but not marked as here."
                x.nickname = x.psdid
                warnings.append( x )
        RegRecord.objects.filter(id__in=to_update).update(paid=True)

    # decide who to show on form
    viewable = regs.filter(cancelled__exact=False)
    viewable = viewable.filter(here__exact=False)    # optional.... good idea?

    viewable = sorted(viewable, key=lambda reg: reg.psdid.lower() )
    return render(request, 'checkin.html', {'regs': viewable, 'warnings': warnings, 'checked_in':checked_in, 'event_name':event_name })




@staff_member_required
def edit_text_responses(request, event_name ):

    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(render, 'error.html', {'message' : "Sorry.  You are trying to do check-in for an event that does not exist or is closed.  Please try again." },)

    checked_in = []
    to_update = []

    warnings = []

    # Grab everyone from the event.
    regs = RegRecord.objects.filter( event=event_name )
    peeps = [p for r in regs for p in r.members]

    if request.method == 'POST':

        # handle any check-in actions
        here_list = request.POST.getlist('here')
        if len( here_list ) > 0:
            checked_in = regs.filter( event=event_name, id__in=here_list )
            checked_in.update(here=True)
        else:
            checked_in = None

        id_list = request.POST.getlist('paid')
        for x in id_list:
            if x in here_list:
                to_update.append(x)
            else:
                x.psdid = x
                x.message = "Warning: %s just mrked as paid, but not marked as here."
                x.nickname = x.psdid
                warnings.append( x )
        RegRecord.objects.filter(id__in=to_update).update(paid=True)

    # decide who to show on form
    viewable = regs.filter(cancelled__exact=False)

    #viewable = sorted(viewable, key=lambda reg: reg.psdid.lower() )
    return render(request, 'edit_text_responses.html', {'regs': viewable, 'warnings': warnings, 'checked_in':checked_in, 'event_name':event_name })






@staff_member_required
def multi_break( request, event_name ):
    """
    Handle form with multiple breaks listed.  Enter them into database
    """
    BreakFormset = formset_factory(BreakForm, extra=10, max_num=10)

    if request.method == 'POST':
        print "At post"
        pformset = BreakFormset(request.POST)
        rform = MultiBreakForm(request.POST)
        if pformset.is_valid() and rform.is_valid():

            rzn = rform.cleaned_data['reason']
            print "General reason: " + str(rzn)

            for form in pformset.forms:
                    if not form.cleaned_data:
                        continue
                    pcd = form.cleaned_data
                    p = BreakRecord(**pcd)
                    if p.notes == None or p.notes=="":
                        p.notes = rzn
                    break_a_match( p.psdid, p.other_psdid, p.notes )
        #else:
        #    return render(request,  'error.html', {'message' : "Sorry.  Forms invalid. Please try again." },
        #                           context_instance=RequestContext(request)  )
    else:
        pformset = BreakFormset()
        rform = MultiBreakForm()

    return render(request, 'dashboard/multi_break.html', {'pformset': pformset, 'rform': rform, 'event_name':event_name })


class WordRec(object):

    def __init__(self, word, wc):
        self.word = word
        self.isC = wc[0]
        self.isNotC = wc[1]
        self.seekC = wc[2]
        self.seekNotC = wc[3]
        self.totC = wc[4]
        self.base_word = None
        self.isBase = False
        self.isMapped = False
        self.synonyms = []

    def augment(self, other_wr ):
        print "augmenting!"
        if not self.word == other_wr.word:
            self.isC += other_wr.isC
            self.isNotC += other_wr.isNotC
            self.seekC += other_wr.seekC
            self.seekNotC += other_wr.seekNotC
            self.totC += other_wr.totC
            self.isBase = True
            self.synonyms.append( other_wr.word )

    def word_string(self):
        if len(self.synonyms) > 0:
            syns = ", ".join( self.synonyms )
            return self.word + " (" + syns + ")"
        else:
            return self.word

    def toggle(self, base_word ):
         self.isMapped = True
         self.base_word = base_word


class CheckPhraseForm( forms.Form ):
    snippit = forms.CharField(widget=forms.TextInput(attrs={'size':50}), initial="")


@staff_member_required
def make_text_translation( request, event_name ):
    """
    Link different ways of saying the same thing
    """
    error_message = ""
    #trans_set = formset_factory(TranslationForm, extra=10, max_num=40)
    explore_result = None
    #import pdb; pdb.set_trace()

    if request.method == 'POST':
        base_word = request.POST[ "base_word" ]
        word = request.POST[ "word" ]
        if "translate" in request.POST:

            brcs = TranslationRecord.objects.filter( synonym=base_word )
            if len(brcs) > 0:
                error_message = "%s is already linking to %s.  Can't point to it." % (base_word, brcs[0].base_word, )

            brcs2 = TranslationRecord.objects.filter( base_word=word )
            if len( brcs2 ) > 0:
                error_message += "  %s is being linked to by %s.  It can't point to anything." % (word, brcs2[0].synonym )

            if len(error_message) == 0:
                rcs = TranslationRecord.objects.filter( synonym=word )
                if len(rcs) == 0:
                    if len( base_word ) > 0:
                        tr = TranslationRecord( base_word = base_word.lower(), synonym=word.lower() )
                        tr.save()
                    else:
                        error_message += "  Warning: Mapping to empty string ignored."
                else:
                    tr = rcs[0]
                    if len( base_word ) > 0:
                        tr.base_word = base_word.lower()
                        tr.save()
                    else:
                        print "deleting!"
                        tr.delete()

        elif "delete" in request.POST:
            rcs = TranslationRecord.objects.filter( synonym=word )
            for tr in rcs:
                tr.delete()

        else:
            snip = None
            free_form=False
            if "explore" in request.POST:
                snip = request.POST[ "word" ]

            if "explore_submit" in request.POST:
                checkform = CheckPhraseForm( request.POST )
                if checkform.is_valid():
                    # explore snippit
                    print "Got check"
                    print request.POST
                    snip = checkform.cleaned_data['snippit']
                    free_form=True

            if snip:
                explore_result = textwrangler.get_text_with( event_name, snip, free_form )
                for (key, value) in explore_result.items():
                    print "%s %s" % (key, value )


    checkform = CheckPhraseForm()

    # make table of current words and so forth
    words = textwrangler.gen_text_table( event_name )

    syns = TranslationRecord.objects.all()
    syns = dict( [(w.synonym,w.base_word) for w in syns] )
    for s in syns:
        print s

    for w in words.keys():
        wr = WordRec( w, words[w] )
        words[w] = wr

    for w in words.keys():
        if w in syns:
            print "Yay!  %s -> %s" % (w, syns[w])
            if syns[w] in words:
                words[ syns[w] ].augment( words[w] )
            else:
                words[ syns[w] ] = WordRec( syns[w], [0,0,0,0,0] )
            words[w].toggle( syns[w] )

    # sort words, putting the mapped words at the end.
    words = sorted(words.items(), key=lambda flk: (flk[1].isMapped, flk[0]) )

    return render(request, 'dashboard/text_translation.html', locals(), context_instance=RequestContext(request))




@staff_member_required
def list_comments(request, event_name, acts):
    """List all comments, notes and referrals made by people registering for specified event.
     Useful for generating who knows whom."""

    regs = RegRecord.objects.filter(event=event_name, cancelled=False).order_by( '-id' )

    return render(request, 'dashboard/list_comments.html', {'regs': regs, 'event_name':event_name, 'actions':acts})



@staff_member_required
def list_childcare(request, event_name, acts):
    """List all childcare requests made by people registering for specified event.
     Useful for generating who knows whom."""

    regs = RegRecord.objects.filter(event=event_name, cancelled=False).order_by( '-id' )

    return render(request, 'dashboard/list_childcare.html', {'regs': regs, 'event_name':event_name, 'actions':acts})



@staff_member_required
def list_people(request, event_name, acts, all_people=False):
    """List all people and comments made by people registering for specified event"""

    if all_people:
        regs = RegRecord.objects.all().order_by( '-id' )
    else:
        regs = RegRecord.objects.filter(event=event_name, cancelled=False).order_by( '-id' )

    return render(request, 'dashboard/list_people.html', {'regs': regs, 'event_name':event_name, 'actions':acts})


@staff_member_required
def list_users(request, acts ):
    """
    List all users, their email, and how many regrecords they have.

    TODO: Finish this method, make template, and wire it up into the command thing
    """

    users = User.objects.all().order_by( '-id' )
    for u in users:
        ln = RegRecord.objects.filter( psdid=u.username ).count()
        u.num_records = ln
        print u'%s,%s,%s,%s,%s' % (u.id,u.username,u.email,u.first_name.encode('ascii','replace'),ln)

    return render(request, 'dashboard/list_users.html', {'users': u, 'actions':acts})





@staff_member_required
def generate_email_list(request, event_name, acts):
    """Generate mailing list for the event"""

    regs = RegRecord.objects.filter(event=event_name)

    return render(request, 'dashboard/email_list.html', {'regs': regs, 'event_name':event_name, 'actions':acts})





def clean_database():
    """
    Delete person records with no regrecords.
    Delete users with no regrecords that are not staff level
    List regrecords that have no user account.
    """

    results = unicode("")
    users = User.objects.all()
    events = Event.objects.all()
    eventlist = [x.event for x in events]
    
    all_rr_ids= set()
    allfolk = set()
    results += "Event List = %s" % ( eventlist )
    results += "\nID List: "
    
    rrs = RegRecord.objects.all()
    rr_deleted = 0
    for rr in rrs:
        if not rr.event in eventlist:
            rr.delete()
            results += "delete orphan RR " + rr.psdid + "\n" + res

            rr_deleted += 1
            
    
    rrs = RegRecord.objects.all()
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
    # RR deleted = %s
    # People deleted = %s
    # users deleted = %s
    Details: %s
    </pre><br>
    All rrs: %s""" % (rr_deleted, people_deleted, users_deleted, results, all_rr_ids )


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



def list_bad_cruises_iter( event_name ):

    dr = CruiseRecord.objects.filter( event=event_name ).order_by( 'psdid' )

    yield( """List of bad cruise records (and all other records by the same person).  Bad cruise records have been removed from the database.<table>""")
    for d in dr:
        rr = fetch_regrecord( event_name, d.other_psdid )
        if rr == None:
            d.delete()
            yield "<tr><td>%s<td><td>" % (d,)
            for xx in CruiseRecord.objects.filter( event=event_name, psdid=d.psdid ):
                yield str(xx.other_psdid) + " "
            yield "</tr>"

    yield( "</table>" )




def drop_missing_datesheets_iter( event_name, drop_records = False ):

    dr = DateRecord.objects.filter( event=event_name ).order_by( 'psdid' )

    if not drop_records:
        yield """Match Records with missing data"""
    else:
        yield """Dropping the following Match Records with missing data."""
    yield( """<table>""")
    for d in dr:
        if d.said_yes == None or d.they_said_yes == None:
            strg = "<tr><td>%s<td></tr>\n" % (d,)
            if drop_records:
                d.delete()
            yield strg

    #yield "<tr><td>Next block<hr></td></tr>"

#    dr = dr.order_by( 'other_psdid' )
#    for d in dr:
#        if d.they_said_yes == None:
#            strg = "<tr><td>%s<td></tr>\n" % (d,)
#            d.delete()
#            yield strg
#            yield "<tr><td>%s<td></tr>\n" % (d,)

    yield( "</table>" )





@staff_member_required
def schedule_form(request, event_name):
    evt = Event.objects.get(event=event_name)
    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        if form.is_valid():
            trials = form.cleaned_data["trials"]
            rounds = form.cleaned_data["rounds"]
            evt.numrounds = rounds
            evt.save()
            who_incl = form.cleaned_data["include"]

            #date_scheduler.schedule( event_name, rounds, trials, who_include=who_incl )
            print "Going to schedule"
            sch_func = partial( date_scheduler.schedule, event_name, rounds, trials, who_include=who_incl )

            #sch_func()

            yield_gen = async_print_text_response( sch_func )
            #for r in yield_gen:
            #    print r
                #yield_gen()
            return HttpStreamTextResponse( yield_gen, event_name, ACTIONS=ACTIONS )
            #return HttpStreamTextResponse( "done", event_name, ACTIONS=ACTIONS )

    form = ScheduleForm( initial = {'rounds':evt.numrounds} )
    return render(request, 'dashboard/command_arg_form.html', {'form': form, 'event': evt, 'command_title':'Generate Dating Schedule', 'button_name':'Start Scheduling'}, context_instance=RequestContext(request) )



@staff_member_required
def print_schedules_form(request, event_name):
    evt = Event.objects.get(event=event_name)
    if request.method == 'POST':
        form = PrintSchedulesForm(request.POST)
        if form.is_valid():
            who_incl = form.cleaned_data["include"]
            #results = 'Make with psdmanage.py command.  Then go to [root url to django]/schedules/%s to have schedules rendered.' % (event_name, )
            return HttpResponseRedirect( reverse( "print-schedules", kwargs={'event_name':event_name,'include_code':who_incl} ) )

    form = PrintSchedulesForm()
    return render(request, 'dashboard/command_arg_form.html', {'form': form, 'event': evt, 'command_title':'Print PDF of Schedules',
                                                        'button_name':'Render Schedules'},
                               context_instance=RequestContext(request) )





@staff_member_required
def potential_matches( request, event_name, psdid ):
    try:
        peep = RegRecord.objects.get( event=event_name, psdid=psdid )
    except:
         return HttpResponseNotFound('<h1>event %s or psdid  %s not real?</h1>' % (event_name, psdid, ) )

    recs = MatchRecord.objects.filter( psdid1=psdid, event=event_name )
    recs2 = MatchRecord.objects.filter( psdid2=psdid, event=event_name )

    likes = dict( [(r.psdid2, r) for r in recs ] )
    likeds = dict( [(r.psdid1, r) for r in recs2 ] )

    alls = set(likes.keys()).union( likeds.keys() )
    matchlist = []

    mutuals = set(likes.keys()).intersection( likeds.keys() )
    crushes = set(likes.keys()).difference( likeds.keys()  )
    stalkers = set(likeds.keys()).difference( likes.keys() )

    for psdid2 in itertools.chain( mutuals, crushes, stalkers ):
        if likes.has_key(psdid2):
            lh = likes[psdid2]
        else:
            lh = None
        if likeds.has_key(psdid2):
            rh = likeds[psdid2]
        else:
            rh = None

        yay = not( lh == None or rh == None )

        try:
            person2 = RegRecord.objects.get( event=event_name, psdid=psdid2 )
            try:
                date_record = DateRecord.objects.get( event=event_name, psdid=psdid, other_psdid=psdid2 )
            except:
                date_record = None
        except:
            person2 = 'psdid %s for %s not found in reg records?' % (psdid2, event_name)

        matchlist.append( {'psdid2':psdid2, 'like':lh, 'liked':rh, 'person2':person2, 'yay':yay, 'date':date_record } )

    return render(request,  'dashboard/potential_matches.html', locals(),
                                 context_instance=RequestContext(request)  )





@staff_member_required
def payment_paste( request, event_name ):
    results = []
    err_message = None
    if request.method == 'POST':
        form = PaymentPasterForm(request.POST)
        if form.is_valid():
            payments = form.cleaned_data["payments"]
            override = form.cleaned_data["override"]
            results.append( "Override status = '%s'" % (override, ) )
            payments = payments.splitlines()
            psdids = []
            for p in payments:
                rs = "* %s" % (p, )
                got_psdid = re.findall( r'\((.*)\)', p )
                if len( got_psdid ) > 0:
                    got_psdid = got_psdid[0]
                    rs = rs + "\n   Turning to '%s-%s'" % (event_name, got_psdid, )
                    try:
                        rr = RegRecord.objects.get( event=event_name, psdid=got_psdid )
                        if not override and rr.paid:
                            rs = rs + "\n  Already marked as paid" 
                        else:
                            newnote = "Automarked paid. TID: %s" % (p, )
                            rr.addNote( newnote )
                            rr.paid = True
                            rs = rs + "\n   %s marked paid. Note now reads:\n   %s" % (rr.psdid, rr.notes, )
                            rr.save()
                    except RegRecord.DoesNotExist:
                        rs = rs + "\n   PSD '%s' not found" % ( got_psdid, )
                else:
                    rs = rs + "\n    No PSDID located\n"
                results.append( rs )
    else:
        form = PaymentPasterForm()


    rTor = render(request,  "dashboard/payment_paster_form.html", { 'form':form,
                                                          'event':event_name,
                                                          'event_name':event_name,
                                                          'results':results, 'err_message':err_message },
                                                          context_instance=RequestContext(request) )

    return rTor





@staff_member_required
def update_notes( request, event_name ):
    results = None
    err_message = None
    if request.method == 'POST':
        form = UpdateNotesForm(request.POST)
        if form.is_valid():
            psdids = form.cleaned_data["psdids"].upper()
            psdids = re.split('\\W+', psdids)
            rs = "Got %s ids of %s" % (len(psdids), psdids )
            note = form.cleaned_data["note"]
            results = [ rs ]
            regs = RegRecord.objects.filter( event=event_name, psdid__in=psdids )
            for rr in regs:
                if note in rr.notes:
                    results.append( "%s: Note already contains string (%s)" % ( rr.psdid, rr.notes, ) )
                else:
                    rr.notes = "%s ; \n%s" % (rr.notes, note )
                    results.append( "%s: Note now reads %s" % (rr.psdid, rr.notes, ) )
                    rr.save()
    else:
        form = UpdateNotesForm()


    rTor = render(request,  "dashboard/update_notes_form.html", { 'form':form,
                                                          'event':event_name,
                                                          'event_name':event_name,
                                                          'results':results, 'err_message':err_message },
                                                          context_instance=RequestContext(request) )

    return rTor








def check_id( psdid, event ):
    drs = DateRecord.objects.filter( psdid=psdid, event=event, said_yes=None )
    return len(drs) > 0


@staff_member_required
def gen_next_date_sheet_form( request, event_name, just_submitted=False, submitted_psdid=None, dates=None, err_message=None ):
    """
    Make the data entry page which lists all the PSDIDs left to enter into the system.
    :param request:
    :param event_name:
    :param just_submitted:
    :param submitted_psdid:
    :param dates:
    :param err_message:
    :return:
    """
    form = NextSheetForm()
    nextids = list(r.psdid for r in RegRecord.objects.filter( event=event_name, here=True ) )
    if len(nextids) > 0:
        nextids.sort()
        needs = [ psdid for psdid in nextids if check_id( psdid, event_name)  ]
        per = 101 * len(needs) / len(nextids)
        print( "%s - %s = %s" % ( len(needs), len(nextids), per, ) )
        progressbar = ""
        for x in range(0,100):
            if x < per:
                progressbar += "X"
            else:
                progressbar += "_"
    else:
        needs = []
        progressbar = "No date sheets found"

    return render(request,  "dashboard/next_sheet_form.html", {'form':form, 'event':event_name, 'just_submitted':True, 'dates':dates,
                                                 'submitted_psdid':submitted_psdid, 'err_message':err_message, 'nextids':nextids,
                                                 'progressbar':progressbar, 'needs': needs, 'event_name':event_name },
                                                 context_instance=RequestContext(request) )


@staff_member_required
def next_date_sheet(request, event_name):
    evt = Event.objects.get(event=event_name)
    if request.method == 'POST':
        form = NextSheetForm(request.POST)
        if form.is_valid():
            psdid = form.cleaned_data["psdid"].upper()
            rev = reverse("date-sheet", kwargs={'event_name':event_name,'psdid':psdid} )
            return HttpResponseRedirect( rev )

    else:
        return gen_next_date_sheet_form( request, event_name )






@staff_member_required
def date_sheet(request, event_name, psdid, detailed=False ):

    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request,  'error.html', {'message' : "Sorry.  You are trying to do date list for an event '%s' that does not exist.  Please try again." % (event_name,)},
                                   context_instance=RequestContext(request)  )

    try:
        rr = RegRecord.objects.get(psdid=psdid, event=event_name)
    except RegRecord.DoesNotExist:
        return render(request,  'error.html', {'message' : "Sorry.  You are trying to do date list for a PSDID '%s' that does not exist.  Please try again." % (psdid,) },
                                   context_instance=RequestContext(request)  )

    #CruiseFormset = modelformset_factory(CruiseRecord, exclude=('psdid','event_name',), extra=3, max_num=5)
    CruiseFormset = formset_factory(CruiseForm, extra=3, max_num=5)

    if request.method == 'POST':
        cformset = CruiseFormset(request.POST)

        if cformset.is_valid():
            err_message = ""
            for form in cformset.forms:
                if not form.cleaned_data:
                    continue
                #pcd = form.cleaned_data
                #p = CruiseRecord(**pcd)
                #p.psdid = psdid
                #p.event = event_name
                opsdid = form.cleaned_data['other_psdid'].upper()
                if RegRecord.objects.filter(psdid=opsdid, event=event_name).count() == 0:
                    err_message = err_message + "<br>Bad Cruise - '%s'" % (opsdid,)

                # make CruiseRecord if it does not exist.
                if CruiseRecord.objects.filter(psdid=psdid,event=event_name,other_psdid=opsdid).count() == 0:
                        p = CruiseRecord( psdid=psdid, event=event_name, other_psdid=opsdid)
                        p.save()

            yeses = request.POST.getlist('yes')
            dates = DateRecord.objects.filter( event=event_name, psdid=psdid ).order_by('round')
            for d in dates:
                d2 = DateRecord.objects.get(psdid=d.other_psdid, event=event_name, other_psdid=psdid)
                if not (d.other_psdid in yeses):
                    d.said_yes = False
                    d2.they_said_yes = False
                else:
                    d.said_yes = True
                    d2.they_said_yes = True
                d.save()
                d2.save()

            return gen_next_date_sheet_form( request, event_name, just_submitted=True, submitted_psdid=psdid,
                                             dates=dates, err_message=err_message )
        # else bad form:
        #     fall through.  just repost the original and try again.

    queryset=CruiseRecord.objects.filter(psdid=psdid,event=event_name)
    cformset = CruiseFormset(initial=queryset.values())

    dates = get_date_schedule( psdid, event_name )
    if detailed:
        return render(request, 'dashboard/datesheetdetailed.html', {'dates': dates, 'rr': rr, 'event':event, 'event_name':event.event, 'cformset':cformset } )
    else:
        return render(request, 'dashboard/datesheet.html', {'dates': dates, 'rr': rr, 'event':event, 'event_name':event.event, 'cformset':cformset } )




# @staff_member_required
# def date_sheet_rescue_attempt(request, event_name, psdid, detailed=False ):
#
#     try:
#         event = Event.objects.get(event=event_name)
#     except Event.DoesNotExist:
#         return render(request,  'error.html', {'message' : "Sorry.  You are trying to do date list for an event '%s' that does not exist.  Please try again." % (event_name,)},
#                                    context_instance=RequestContext(request)  )
#
#     try:
#         rr = RegRecord.objects.get(psdid=psdid, event=event_name)
#     except RegRecord.DoesNotExist:
#         return render(request,  'error.html', {'message' : "Sorry.  You are trying to do date list for a PSDID '%s' that does not exist.  Please try again." % (psdid,) },
#                                    context_instance=RequestContext(request)  )
#
#     #CruiseFormset = modelformset_factory(CruiseRecord, exclude=('psdid','event_name',), extra=3, max_num=5)
#     CruiseFormset = formset_factory(CruiseForm, extra=3, max_num=5)
#
#     MatchFormset = formset_factory(ManualDateForm, extra=14, max_num=14 )
#
#     if request.method == 'POST':
#         cformset = CruiseFormset(request.POST)
#
#         if cformset.is_valid():
#             err_message = ""
#             for form in cformset.forms:
#                 if not form.cleaned_data:
#                     continue
#                 #pcd = form.cleaned_data
#                 #p = CruiseRecord(**pcd)
#                 #p.psdid = psdid
#                 #p.event = event_name
#                 opsdid = form.cleaned_data['other_psdid'].upper()
#                 if RegRecord.objects.filter(psdid=opsdid, event=event_name).count() == 0:
#                     err_message = err_message + "<br>Bad Cruise - '%s'" % (opsdid,)
#
#                 # make CruiseRecord if it does not exist.
#                 if CruiseRecord.objects.filter(psdid=psdid,event=event_name,other_psdid=opsdid).count() == 0:
#                         p = CruiseRecord( psdid=psdid, event=event_name, other_psdid=opsdid)
#                         p.save()
#
#             yeses = request.POST.getlist('yes')
#             dates = DateRecord.objects.filter( event=event_name, psdid=psdid ).order_by('round')
#             for d in dates:
#                 d2 = DateRecord.objects.get(psdid=d.other_psdid, event=event_name, other_psdid=psdid)
#                 if not (d.other_psdid in yeses):
#                     d.said_yes = False
#                     d2.they_said_yes = False
#                 else:
#                     d.said_yes = True
#                     d2.they_said_yes = True
#                 d.save()
#                 d2.save()
#
#             return gen_next_date_sheet_form( request, event_name, just_submitted=True, submitted_psdid=psdid,
#                                              dates=dates, err_message=err_message )
#         # else bad form:
#         #     fall through.  just repost the original and try again.
#
#     queryset=CruiseRecord.objects.filter(psdid=psdid,event=event_name)
#     cformset = CruiseFormset(initial=queryset.values())
#
#     queryset2= DateRecord.objects.filter(psdid=psdid,event=event_name)
#     qformset = MatchFormset(initial=queryset2.values())
#
#
#     #dates = get_date_schedule( psdid, event_name )
#     if detailed:
#         print "detailed!"
#         return render(request, 'datesheetdetailed.html', {'dates': dates, 'rr': rr, 'event':event, 'event_name':event.event,
#                                                         'cformset':cformset } )
#     else:
#         return render(request, 'dashboard/datesheet2.html', { 'rr': rr, 'event':event, 'event_name':event.event,
#                                                             'cformset':cformset,
#                                                             'dformset':qformset }  )
#








@staff_member_required
def get_dating_matrix(request, event_name ):
    """
    Print out all the matches in an event in a web page.
    """
    print "Here we go!"

    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request,  'error.html', {'message' : "Sorry.  You are trying to generate the date matrix for an event '%s' that does not exist.  Please try again." % (event_name,)},
                                   context_instance=RequestContext(request)  )

    rr = RegRecord.objects.filter(event=event_name, cancelled=False)
    rr = sorted(rr, key=lambda reg: reg.psdid )

    mxrnd = 0
    for r in rr:
        dates = get_date_schedule( r.psdid, event_name )
        r.dates = dates
        if len(dates) > 0:
            mxrnd = max( dates[-1].round, mxrnd )

    return render(request, 'datematrix.html', {'rr': rr, 'event':event, 'event_name':event.event, 'rounds':range(1,mxrnd+1) } )




@staff_member_required
def view_user( request, event_name, psdid ):
    try:
        rr = RegRecord.objects.get(event=event_name, psdid=psdid)
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request,  'error.html', {'message' : "Sorry.  You are trying to edit a regrecord (or event) that does not exist  Please try again." },
                                   context_instance=RequestContext(request)  )

    recs = MatchRecord.objects.filter( psdid1=psdid, event=event_name )

    for r in recs:
        try:
            r.person2 = RegRecord.objects.get( event=event_name, psdid=r.psdid2 )
        except:
          r.person2 = '<h1>psdid %s for %s not found in reg records?</h1>' % (r.psdid2, event_name)

    date_sheet = register.views.contact.generate_date_sheet( event, rr )
    match_text = register.views.contact.generate_match_text( event, rr ) #, "", True )
    return render(request, 'dashboard/user_blurb.html',
                  {'rr': rr, 'event': event, 'recs': recs, 'match_text': match_text, 'date_sheet' : date_sheet,
                   'opts': RegRecord._meta, 'change': True, 'is_popup': False, 'save_as': False,
                   })



@staff_member_required
def edit_user( request, event_name, psdid ):
    try:
        regrec = RegRecord.objects.get(event=event_name, psdid=psdid)
    except RegRecord.DoesNotExist:
        return render(request,  'error.html', {'message' : "Sorry.  You are trying to edit a regrecord that does not exist  Please try again." },
                                   context_instance=RequestContext(request)  )

    rev = reverse("admin:register_regrecord_change", args=(regrec.id,))
    return HttpResponseRedirect( rev )


@staff_member_required
def edit_person( request, psdid ):
    #import pdb; pdb.set_trace()
    try:
        regrec = Person.objects.get(psdid=psdid)
    except Person.DoesNotExist:
        return render(request,  'error.html', {'message' : "Sorry.  You are trying to edit a person record that does not exist  Please try again." },
                                   context_instance=RequestContext(request)  )

    rev = reverse("admin:register_person_change", args=(regrec.id,))
    return HttpResponseRedirect( rev )



@staff_member_required
def edit_event( request, event_name ):
    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request,  'error.html', {'message' : "Sorry.  You are trying to edit an event that does not exist.  Please try again." },
                                   context_instance=RequestContext(request)  )

    rev = reverse("admin:register_event_change", args=(event.id,))
    return HttpResponseRedirect( rev )


def gen_set_from_string( string ):
    """
    Given a string of numbers and number ranges, generate set of all those numbers
    """
    if string:
        statOK = set()
        for x in string.split(","):
            x = x.split("-")
            if len(x) > 1:
                statOK.update( range( int(x[0]), int(x[1])+1 ) )
            else:
                statOK.add( int(x[0]) )
    else:
        statOK = set()

    return statOK



@staff_member_required
def make_table_table_view(request, event_name):
    evt = Event.objects.get(event=event_name)
    information = ""
    if request.method == 'POST':
        form = MakeTableTableForm(request.POST)
        if form.is_valid():
            N = form.cleaned_data["N"]
            statOK = form.cleaned_data["statOK"]
            groupOK = form.cleaned_data["groupOK"]
            posh = form.cleaned_data["posh"]
            crap = form.cleaned_data["crap"]

            try:
                statOK = gen_set_from_string( statOK )
                groupOK = gen_set_from_string( groupOK )
                posh = gen_set_from_string( posh )
                crap = gen_set_from_string( crap )
                res = make_table_table(event_name, N, statOK, groupOK, posh, crap)
                results = "<br>".join( ( str(x) for x in res ) )
            except Exception as inst:
                results = "Error with input---probably string formatting in statOK or groupOK<br>%s" % (inst,)

    else:
        form = MakeTableTableForm()
        results = ""
        try:
            oldrec = TableListRecord.objects.get( event=event_name )
            information = "<h3>Current Table List</h3><pre>\n" + oldrec.describe() + "\n</pre>";
        except TableListRecord.DoesNotExist:
            information = "No table list currently in database for event %s" % (event_name, )


    return render(request, 'dashboard/command_arg_form.html', {'form': form, 'event': evt, 'command_title':'Make Table of Physical Tables',
                                                        'button_name':'Delete Old Tables and Make New Ones',
                                                        'results':results, 'information':information},
                               context_instance=RequestContext(request) )



@staff_member_required
def hand_date_sheet(request, event_name, psdid ):
    evt = Event.objects.get(event=event_name)
    rr = RegRecord.objects.get(event=event_name, psdid=psdid)

    CruiseFormset = formset_factory(CruiseForm, extra=3, max_num=5)

    if request.method == 'POST':
        cformset = CruiseFormset(request.POST)
        if cformset.is_valid():
            err_message = ""
            for form in cformset.forms:
                if not form.cleaned_data:
                    continue
                opsdid = form.cleaned_data['other_psdid'].upper()
                if RegRecord.objects.filter(psdid=opsdid, event=event_name).count() == 0:
                    err_message = err_message + "<br>Bad Cruise - '%s'" % (opsdid,)

                # make CruiseRecord if it does not exist.
                if CruiseRecord.objects.filter(psdid=psdid,event=event_name,other_psdid=opsdid).count() == 0:
                        p = CruiseRecord( psdid=psdid, event=event_name, other_psdid=opsdid)
                        p.save()

            form = HandMatchesForm(request.POST)
            if form.is_valid():
                yesses = form.cleaned_data["yesses"]
                noes = form.cleaned_data["noes"]
                results = ""
                try:
                    yesses = [x.strip() for x in yesses.split(',')]
                    results += "<br>" + update_hand_matches( event_name, psdid, yesses, True )
                    noes = [x.strip() for x in noes.split(',')]
                    results += "<br>" + update_hand_matches( event_name, psdid, noes, False )
                except Exception as inst:
                    results = "Error with input---probably string formatting in yesses or noes<br>%s" % (inst,)
    
            dates = DateRecord.objects.filter( event=event_name, psdid=psdid )
            return gen_next_date_sheet_form( request, event_name, just_submitted=True, submitted_psdid=psdid,
                                                     dates=dates, err_message=results )

    queryset=CruiseRecord.objects.filter(psdid=psdid,event=event_name)
    cformset = CruiseFormset(initial=queryset.values())

    form = HandMatchesForm()
    results = ""
    information = "Sorry, no friend date recording.  Just make everything a normal date"
    return render(request, 'dashboard/command_arg_form_hand.html', {'form': form, 'event': evt, 'command_title':'Hand enter date sheet for %s' % (rr, ),
                                                        'button_name':'Enter records',
                                                        'results':results, 'information':information,
                                                        'cformset':cformset},
                               context_instance=RequestContext(request) )

        #return render(request, 'dashboard/handdatesheet.html', { 'rr': rr, 'event':evt, 'event_name':evt.event }  )



def update_hand_matches( event_name, psdid, id_list, said_yes ):
    print "Updating %s-%s with %s saying %s" % ( event_name, psdid, id_list, said_yes )

    reslist = ""
    for id in id_list:

        rr = RegRecord.objects.filter(event=event_name,psdid=id).count()
        if rr != 1:
            reslist += "<br> ERROR: '%s' is not valid psdid" % ( id, )
            continue

        dates = DateRecord.objects.filter( event=event_name, psdid=psdid, other_psdid=id )
        print dates
        if len( dates ) == 0:
            date = DateRecord(psdid=psdid, other_psdid=id, round=1, said_yes=said_yes, they_said_yes=None,
                              event=event_name, friend_date=False)
            date.save()
            reslist += "<br>   added DR %s" % ( date, )
        else:
            print "Updating %s" % (dates[0], )
            dates[0].said_yes = said_yes
            dates[0].save()
            reslist += "<br> Updated DR to %s" % ( dates[0], )

        dates = DateRecord.objects.filter( event=event_name, other_psdid=psdid, psdid=id )
        print dates
        if len( dates ) == 0:
            date = DateRecord(psdid=id, other_psdid=psdid, round=1, said_yes=None, they_said_yes=said_yes,
                              event=event_name, friend_date=False)
            date.save()
            reslist += "<br>   added flip DR %s" % ( date, )
        else:
            dates[0].they_said_yes = said_yes
            dates[0].save()
            reslist += "<br> Updated flip DR to %s" % ( dates[0], )

    return reslist







def make_recess_rounds( event_name, kind, breaktext ):
    """
    Given a name (kind) and event, turn rows of text into recess records
    Each row is a comma-seperated list of rounds
    """
    RecessRecord.objects.filter(kind=kind, psdid="template", event=event_name ).delete()
    txt = breaktext.split("\n")
    for t in txt:
        if t != "":
            r = RecessRecord()
            r.kind = kind
            r.psdid="template"
            r.rounds = t
            r.event=event_name
            r.save()




@staff_member_required
def make_recess_view(request, event_name):
    evt = Event.objects.get(event=event_name)
    if request.method == 'POST':
        form = MakeRecessForm(request.POST)
        if form.is_valid():
            kind = form.cleaned_data["kind"]
            txt = form.cleaned_data["breaktext"]
            make_recess_rounds( event_name, kind, txt )
    else:
        form = MakeRecessForm()

    brlist = RecessRecord.objects.filter( psdid="template", event=event_name )
    breaks = {}
    for b in brlist:
        if b.kind in breaks:
            breaks[b.kind].append( b )
        else:
            breaks[b.kind] = [b]
    num_breaks = len(breaks)
    print "Got %s breaks " % (num_breaks,)
    return render(request, 'dashboard/recess_creator.html', locals(),
                               context_instance=RequestContext(request) )





@staff_member_required
def run_event(request, event_name):
    evt = Event.objects.get(event=event_name)

    if request.method == 'POST':
        form = RunEventForm(request.POST)
        err_message = ""
        if form.is_valid():
            round = form.cleaned_data["round"]
            roundlength = form.cleaned_data["roundlength"]
            if round < 0:
                err_message = "Cannot have negative round"
            elif round == 0:
                err_message = "Stopping event.  Setting form default to last round."
                form = RunEventForm(initial={'round': 1})
                evt.curround = 0
                evt.save()

            elif evt.curround == 0:
                # check if it is ok to start the event
                err_message = ""
                #if not evt.regclosed:
                #    err_message = "Need to close registration before starting event."
                if evt.numrounds == 0:
                    err_message = "Need to schedule dates before starting event."
                #if err_message != "":
                elif round > evt.numrounds:
                    err_message = "Cannot start event by jumping to round beyond number of rounds in event!"
                else:
                    if round == 1:
                        err_message = "Event started! Now on round 1"
                    else:
                        err_message = "Event started!  Jumping ahead to round %d" % ( round, )
                    evt.curround = round
                    evt.curroundend = datetime.datetime.now() + datetime.timedelta(minutes=roundlength)
                    evt.save()

                    form = RunEventForm( initial={'round':round+1} )

            elif round > evt.numrounds:
                err_message = "On round past the final round: Event is now over!"
                evt.curround = round
                evt.save()

            else:
                if round < evt.curround:
                    err_message = "Going back to prior round"
                elif evt.curround - round == 0:
                    err_message = "Round not changed"
                elif evt.curround - round > 1:
                    err_message = "Skipping some rounds!"
                else:
                    err_mesage = "Round advanced"

                evt.curround = round
                evt.curroundend = datetime.datetime.now() + datetime.timedelta(minutes=roundlength)
                evt.save()

                print "Got round %s" % (round + 1, )
                form = RunEventForm( initial={'round':round+1} )
                #forms.IntegerField(widget=forms.TextInput(attrs={'size': 5}), initial=0)
                #form.fields['round'].initial = round + 1
                #print( form.round )

                if evt.curround == evt.numrounds:
                    err_message = err_message + "<p>Currently on the final round of the event!"

        else:
            err_message = "Form not valid; please repair."
    else:
        form = RunEventForm( initial={'round':evt.curround+1} )

    return render(request, 'dashboard/event_runner.html', locals(),
                               context_instance=RequestContext(request) )





def person_search( request ):

    search_made = False
    if request.method == 'POST':
        form = PersonSearchForm(request.POST)
        if form.is_valid():
            psdid = form.cleaned_data.get("psdid")
            email = form.cleaned_data.get("email")
            name = form.cleaned_data.get("name")

            users = set()
            rrs = set()
            precs = set()

            # look for psdid
            if psdid != "":
                users.update( User.objects.filter( username__icontains=psdid ) )
                rrs.update( RegRecord.objects.filter( psdid__icontains=psdid ) )
                precs.update( Person.objects.filter( psdid__icontains=psdid ) )

            if email != "":
                users.update( User.objects.filter( email__icontains=email ) )
                rrs.update( RegRecord.objects.filter( email__icontains=email ) )

            if name != "":
                users.update( User.objects.filter( first_name__icontains=name ) )
                rrs.update( RegRecord.objects.filter( nickname__icontains=name ) )
                precs.update( Person.objects.filter( first_name__icontains=name ) )
                precs.update( Person.objects.filter( last_name__icontains=name ) )

            search_made = True
            return render(request, 'dashboard/person_search.html', locals(), context_instance=RequestContext(request) )
    else:
        form = PersonSearchForm()

    return render(request, 'dashboard/person_search.html', locals(), context_instance=RequestContext(request) )



def walk_in_reg( request, event_name ):
    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request,  'error.html', {'message' : "Sorry.  You are trying to do walk-in reg for an event that does not exist.  Please try again." },
                               context_instance=RequestContext(request)  )

    if request.method == 'POST':
        form = PSDIDorEmailForm(request.POST)
        if form.is_valid():
            usr = form.cleaned_data.get("user")
            rev = reverse( "walk-in-update", kwargs={"event_name":event.event, "psdid":usr.username } )
            return HttpResponseRedirect( rev )
    else:
        form = PSDIDorEmailForm()

    return render(request, 'dashboard/walkin_menu.html', locals(), context_instance=RequestContext(request) )


def make_table_table( event_name, N, statOKs, groupOKs, posh=set(), crap=set() ):
    """
    statOKs, groupOKs both sets of table numbers
    """
    try:
        oldrec = TableListRecord.objects.get( event=event_name )
        TableRecord.objects.filter( group=oldrec ).delete()
        oldrec.delete()
    except TableListRecord.DoesNotExist:
        pass
    grp = TableListRecord( event=event_name )
    grp.save()
    cyc = itertools.cycle( (0,1,2,1) )
    res = []

    for k in range(1,N+1):
        tb = TableRecord(group=grp, name="Table " + str(k), quality=10+cyc.next(), groupOK=False, statOK=False )
        if k in posh:
            tb.quality += 5
        if k in crap:
            tb.quality -= 5
        if k in groupOKs:
            tb.groupOK = True
        if k in statOKs:
            tb.statOK = True

        tb.save()
        res.append(tb)

    return res




def calc_pay_numbers( event_name ):
    totalfolks = 0
    pendings = 0
    paidcount = 0
    cancelled = 0
    comped = 0
    paypal = 0
    refunded = 0
    here = 0
    paidNoShow = 0
    door = 0
    doorString = ""
    regs = RegRecord.objects.filter( event=event_name ).order_by( 'psdid' )
    lists = {'cancelled':[], 'comped':[], 'nopaypal':[], 'refunded':[], 'pending':[], 'paidnoshow':[], 'herenopay':[], 'weirdpaypal':[] }
    for r in regs:
        totalfolks = totalfolks + r.size
        notefield = r.notes.lower()
        if r.paid:
            if "paypal transation id" in notefield:
                paypal = paypal + r.size
                paidcount = paidcount + r.size
            elif "comp" in notefield and not "Need companion" in notefield:
                comped = comped + r.size
                lists['comped'].append( r )
            else:
                paidcount = paidcount + r.size
                lists['nopaypal'].append(r)
        else:
            if "paypal transation id" in notefield and not "refunded" in notefield.lower():
                lists['weirdpaypal'].append(r)

        if r.pending and not r.cancelled:
            lists['pending'].append(r)
            pendings = pendings + r.size

        if r.cancelled:
            cancelled = cancelled + r.size
            lists['cancelled'].append(r)

        if "refunded" in notefield.lower() and not r.paid:
            refunded = refunded + r.size
            lists['refunded'].append(r)

        if r.here:
            here = here + r.size
            if not r.paid:
                lists['herenopay'].append( r )

        if r.paid and not r.here:
            paidNoShow = paidNoShow + r.size
            lists['paidnoshow'].append(r)

        if "door" in notefield:
            door = door + r.size
            if doorString == "":
                doorString = r.notes
            else:
                doorString += "; " + r.notes

    headstr = """
    total = %s
    paid = %s
    comped = %s       (based on finding "comp" in notes field)
    pending = %s
    cancelled = %s
    paypal = %s    (based on finding "paypal transaction id" in notes field.
    refunded = %s   (based on "paypal transaction id" and no paid flag, or "refunded" in notes field)
    here = %s
    paid no show = %s  (paid, not here)
    door = %s  (door mentioned)
         Remarks are: %s
    """ % ( totalfolks, paidcount, comped, pendings, cancelled, paypal, refunded, here, paidNoShow, door, doorString)

    for (ltype,lst) in lists.iteritems():
        headstr += "\n** %s **" % (ltype, )
        for rec in lst:
            headstr += "\n\t%s (%s) - %s" % (rec.nickname, rec.psdid, rec.notes.replace("\n", "\t\t; ") )

    return headstr + "\n"

@staff_member_required
def event_manager( request, event_name, action=None, extraArg=None ):
    """
    This method redirects a bunch of calls to a bunch of different functions.
    It also prints out a list of commands you can do with these calls.
    """
    logger.info( "*** Starting Event Management '%s'/'%s' ***" % ( action, extraArg, ) )
    if action=="" or action=="main":
        results="""Click on action desired."""
    elif action=="editevent":
        return edit_event( request, event_name )
    elif action=="allevents":
        rev = reverse("admin:register_event_changelist")
        return HttpResponseRedirect( rev )
    elif action=="regrecords":
        rev = reverse("admin:register_regrecord_changelist")
        return HttpResponseRedirect( rev )
    elif action=="listcomments":
        return list_comments(request, event_name, ACTIONS)
    elif action== "listchildcare":
        return list_childcare(request, event_name, ACTIONS)
    elif action=="listpeople":
        list_all = extraArg=="all"
        return list_people(request, event_name, ACTIONS, list_all)
    elif action=="clean":
        results=clean_database()
    elif action=="fix":
        results=fix_group_codes()
    elif action=="search":
        return person_search( request )
    elif action=="matrix":
        try:
            event = Event.objects.get(event=event_name)
        except Event.DoesNotExist:
            return render(request,  'error.html', {'message' : "Sorry.  You are trying to make matrix for an event that does not exist." },
                                       context_instance=RequestContext(request)  )
        updateProc = updateMatchRecords_async(event)
        return HttpStreamTextResponse( updateProc, event_name, ACTIONS=ACTIONS )
    elif action=="walkinreg":
        return walk_in_reg( request, event_name )
    elif action=="email":
        results = generate_email_list(request,event_name,ACTIONS)
        return results
    elif action=="countdates":
        resp = HttpStreamTextResponse(register.demographics.date_distribution_iter(event_name), content_type='text/plain')
        resp['Content-Disposition'] = 'attachment; filename=datecounts.csv'
        return resp
    elif action=="schedules":
        return print_schedules_form( request, event_name )
    elif action=="runevent":
        return run_event( request, event_name )
    elif action=="demographics":
        if extraArg==None:
            extraArg="NotNo"
        return HttpStreamTextResponse( print_demographics_async( event_name, who_print=extraArg ), event_name, head_string="<p>Demographics for %s with '%s' included</p>" % (event_name, extraArg) )
    elif action=="nametags":
        resp = HttpResponse(register.demographics.name_tag_iter(event_name), content_type='text/plain')
        resp['Content-Disposition'] = 'attachment; filename=nametags.csv'
        return resp
    elif action=="multibreak":
        return multi_break( request, event_name )
    elif action=="updatenotes":
        return update_notes( request, event_name )
    elif action=="paymentpaste":
        return payment_paste( request, event_name )
    elif action=="examinetext":
        return make_text_translation( request, event_name )
    elif action=="plandates":
        return schedule_form( request, event_name )
    elif action=="maketabletable":
        return make_table_table_view( request, event_name )
    elif action=="makerecess":
        return make_recess_view( request, event_name )
    elif action=="listmissingsheets":
        return HttpStreamTextResponse( drop_missing_datesheets_iter( event_name, False), event_name, ACTIONS=ACTIONS)
    elif action=="dropmissingsheets":
        return HttpStreamTextResponse( drop_missing_datesheets_iter( event_name, True), event_name, ACTIONS=ACTIONS)
    elif action=="listbadcruises":
        return HttpStreamTextResponse( list_bad_cruises_iter( event_name ), event_name, ACTIONS=ACTIONS )
    elif action=="emailpostevent":
        return HttpResponseRedirect( reverse( "email-post-event", kwargs={'event_name':event_name} ) )
    elif action=="subgroupemail":
        return HttpResponseRedirect( reverse( "subgroup-email", kwargs={'event_name':event_name} ) )
    elif action=="volunteeremail":
        return HttpResponseRedirect( reverse( "volunteer-email", kwargs={'event_name':event_name} ) )
    elif action=="emailpreevent":
        return HttpResponseRedirect( reverse( "email-pre-event", kwargs={'event_name':event_name} ) )
    elif action=="checkin":
        return HttpResponseRedirect( reverse( "check-in", kwargs={'event_name':event_name} ) )
    elif action=="calcpay":
        return HttpStreamTextResponse( calc_pay_numbers(event_name), event_name, head_string="<p>Computing Pay Statistics</p>" )
    elif action=="datesheet":
        return HttpResponseRedirect( reverse( "next-date-sheet", kwargs={'event_name':event_name} ) )
    elif action=="datematrix":
        return HttpResponseRedirect( reverse( "date-matrix", kwargs={'event_name':event_name} ) )
    elif action=="testEmail":
        return HttpResponseRedirect( reverse( "test-email", kwargs={'event_name':event_name} ) )
    else:
       results="Action '%s' not understood." % (action,)

    if not results == """Click on action desired.""":
        results = "<b>RESULT:</b><p>" + results

    return render(request,  'dashboard/event_manager.html', {'event_name':event_name,
                                   'actions':ACTIONS,
                                   'results':results } )



