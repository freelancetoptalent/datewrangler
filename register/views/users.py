"""
User facing webpage wrangling

This code displays the registration confirmation page and other things that individual registered users logging into the system
might want to look at.
"""

import pdb

from datetime import date

import django.http
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.shortcuts import render
from django.forms.formsets import formset_factory
from django.conf import settings
from django.http import HttpResponseRedirect

from register.models import RegRecord
from register.system_models import Organization, Event
from register.schedule_models import CruiseRecord, DateRecord
from register.forms import CruiseForm
from register.views.date_schedule import get_date_schedule

import logging
logger = logging.getLogger('register.users')


def list_events( request ):
    """
    List all events and links to their registration pages
    """

    today = date.today()
    open_events = Event.objects.filter( date__gte=today )

    old_events = Event.objects.filter( date__lt=today )
    return render_to_response( 'list_events.html', locals(), context_instance=RequestContext(request) )



@login_required
def show_me_all(request, psdid=None):
    """
    This renders the profile page for a user so they can see what they registered
    for and what is upcoming.

    Also provides links to future events that they have not registered for.
    """

    if request.user.is_staff:
        staff_call = True
        if psdid is None:
            return HttpResponseRedirect( "admin/" )
        else:
            reg_list = RegRecord.objects.filter(psdid=psdid)
    elif psdid == None:
        user = request.user
        reg_list = RegRecord.objects.filter(psdid=user.username)
        staff_call = False
    else:
        return django.http.HttpResponseForbidden()

    # Sort events into ones of past and ones currently open.
    # so ugly!
    today = date.today()
    reg_list_running = []
    reg_list_cur = []
    reg_list_past = []
    regged_evts = set()
    for r in reg_list:
        r.eventrec = Event.objects.get(event=r.event)
        if r.eventrec.date < today:
            reg_list_past.append( r )
        elif r.ev.running or r.ev.completed:
            reg_list_running.append( r )
        else:
            r.info_email = r.ev.info_email  # stash variable for template
            reg_list_cur.append(r)
        regged_evts.add( r.event )

    # get all open events (that user has not registered for)
    evts = Event.objects.all()
    open_events = []
    for evt in evts:
        if evt.date >= today and not evt.event in regged_evts:
            open_events.append( evt )

    if reg_list:
        if reg_list[0].is_group:
            group_or_individual = "group"
        else:
            group_or_individual = "individual"
    else:
        group_or_individual = "individual"

    # Stripe code attempt (for payment system)
    stripe_key = settings.STRIPE_KEY
    stripe_product = settings.STRIPE_PRODUCT
    #print "Captured '%s' with key '%s'" % (stripe_product, stripe_key )

    return render_to_response('show_me_all.html', locals(),
                                  context_instance=RequestContext(request))







@login_required
def user_date_sheet(request, event_name ):
    """
    Post the date sheet with any "yesses" checked off and cruises displayed. If submitted, update and repost the same form.
    :param request: The HTML request object
    :param event_name: String name of the event, from the url
    :return: new webpage, updated.
    """
    user = request.user
    psdid = user.username
    messages = []

    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request,  'error.html', {'message' : "Sorry.  You are trying to do date list for an event '%s' that does not exist.  Please try again." % (event_name,)},
                                   context_instance=RequestContext(request)  )

    if event.numrounds == None or event.numrounds == 0:
        return render(request,  'error.html', {'message' : "Sorry.  You are trying to view the date schedule for an event, %s, that has yet to be scheduled." % (event_name,)},
                                   context_instance=RequestContext(request)  )

    try:
        rr = RegRecord.objects.get(psdid=psdid, event=event_name)
    except RegRecord.DoesNotExist:
        return render(request,  'error.html', {'message' : "Sorry.  You, '%s', are trying to look up a data sheet for an event, '%s', that you are not registered for." % (psdid, event_name )},
                                   context_instance=RequestContext(request)  )

    CruiseFormset = formset_factory(CruiseForm, extra=3, max_num=5)

    if request.method == 'POST':
        cformset = CruiseFormset(request.POST)

        if cformset.is_valid():
            for form in cformset.forms:
                if not form.cleaned_data:
                    continue
                #pcd = form.cleaned_data
                #p = CruiseRecord(**pcd)
                #p.psdid = psdid
                #p.event = event_name
                opsdid = form.cleaned_data['other_psdid'].upper()
                if RegRecord.objects.filter(psdid=opsdid, event=event_name).count() == 0:
                    messages.append( "The Cruise of %s is not a recognized PSD ID, please try again." % (opsdid,) )

                # make CruiseRecord if it does not exist.
                if CruiseRecord.objects.filter(psdid=psdid,event=event_name,other_psdid=opsdid).count() == 0:
                        p = CruiseRecord( psdid=psdid, event=event_name, other_psdid=opsdid)
                        p.save()
                        messages.append( "New cruise of '%s' added." % (opsdid, ) )

            yeses = request.POST.getlist('yes')
            dates = DateRecord.objects.filter( event=event_name, psdid=psdid ).order_by('round')
            for d in dates:
                d2 = DateRecord.objects.get(psdid=d.other_psdid, event=event_name, other_psdid=psdid)
                if not (d.other_psdid in yeses):
                    if d.said_yes:
                        messages.append( "Changed a Yes for %s to a No." % (d.other_psdid, ) )
                    d.said_yes = False
                    d2.they_said_yes = False
                else:
                    if not d.said_yes:
                        messages.append( "Marked %s as a Yes!" % (d.other_psdid, ) )
                    d.said_yes = True
                    d2.they_said_yes = True
                d.save()
                d2.save()


    queryset=CruiseRecord.objects.filter(psdid=psdid, event=event_name)
    cformset = CruiseFormset(initial=queryset.values())

    dates = get_date_schedule( psdid, event_name )
    return render(request, 'userdatesheet.html', {'dates': dates, 'rr': rr,
                                                  'event':event, 'event_name':event.event,
                                                  'messages':messages,
                                                  'cformset':cformset } )







def about_page(request, what=None):
    """
    Return about pages (such as info pages regarding gender) rendered with log-in
    links and whatnot.
    """

    # about pages are (not yet) event specific.
    try:
        event = Organization.objects.get( site=Site.objects.get_current() )
    except:
        logger.warning( "No event or organization object found for about page lookup" )
        event = None

    return render_to_response( ['about/%s.html' % what, 'about/notfound.html'], locals(),
                               context_instance=RequestContext(request))


