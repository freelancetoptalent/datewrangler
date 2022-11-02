"""
Code for emailing people.

Includes code for dynamically making the final date sheet with results that gets added to post event emails.

For mass emails, we generate a list of email addresses and iterate down that list, emailing each person individually.
"""

from django.contrib.auth.models import User
from django.template import Context, RequestContext
from django.template.loader import get_template
from django.shortcuts import render
from django.conf import settings

from register.models import RegRecord
from register.system_models import Event
from register.schedule_models import CruiseRecord, DateRecord
from register.forms import PostEmailForm, FeedbackForm, SubgroupEmailForm, TestEmailForm, VolunteerCruiseEmailForm
from register.views.util import HttpStreamTextResponse
from django.template import Template
import re
import django.core.mail
import itertools
import logging
from register.views.date_schedule import get_date_schedule
import time
import random

logger = logging.getLogger('register.contact')


# def pre_email_body(reg, evt):
#    t = get_template('email/pre_event_email.txt')
#    c = Context({'rr': reg, 'event': evt})
#    return t.render(c)

# def pre_email(event_name):
#    regs = RegRecord.objects.filter(event=event_name).exclude(cancelled=True)
#    evt = Event.objects.get(event=event_name)
#    for r in regs:
#        u = User.objects.get(username=r.psdid)
#        if u:
#            u.email_user("important Poly Speed Dating info!", pre_email_body(r, evt), evt.info_email )
#        else:
#            print("Something went wrong with reg %s" % r)

def their_info(date):
    them = RegRecord.objects.get(event=date.event, psdid=date.other_psdid)
    d = {'their_email': them.email, 'their_nick': them.nickname, 'their_psdid': them.psdid}
    if hasattr(date, 'round'):
        d['round'] = date.round
    return d


def cruiser_info(event_name, psdid):
    try:
        me = RegRecord.objects.get(event=event_name, psdid=psdid)
        d = {'their_email': me.email, 'their_nick': me.nickname, 'their_psdid': me.psdid}
    except RegRecord.DoesNotExist as e:
        # d = {'their_email': "unknown", 'their_nick': "unknown entity", 'their_psdid': psdid}
        raise type(e)(e.message + "(#'%s')" % (psdid,))
        # raise e
    return d


def public_info(event, psdid):
    try:
        me = RegRecord.objects.get(event=event, psdid=psdid)
        d = {'nick': me.nickname, 'psdid': me.psdid}
    except Exception as inst:
        logger.error("Error in public_info(%s, %s): %s\n" % (event, psdid, inst))
        d = {'nick': "Not Found", 'psdid': psdid}
    return d


def generate_match_text(evt, rr):
    """
    Generate text string for matching results and return it.
    """
    logger.info("Going to render match text")
    try:
        if len(DateRecord.objects.filter(psdid=rr.psdid, event=evt.event, said_yes=None)) > 0:
            message = "Please note: Unfortunately, your date sheet was missing, so we marked all your dates as 'No.'  If this is not what you wish, please contact us."
        else:
            message = None

        matches = DateRecord.objects.filter(psdid=rr.psdid, said_yes=True, they_said_yes=True, event=evt.event,
                                            friend_date=False)
        matches = [their_info(m) for m in matches]

        fmatches = DateRecord.objects.filter(psdid=rr.psdid, said_yes=True, they_said_yes=True, event=evt.event,
                                             friend_date=True)
        fmatches = [their_info(m) for m in fmatches]

        you_cruised = set(x.other_psdid for x in CruiseRecord.objects.filter(event=evt.event, psdid=rr.psdid))
        they_cruised = set(x.psdid for x in CruiseRecord.objects.filter(event=evt.event, other_psdid=rr.psdid))

        cruises = [cruiser_info(evt.event, x) for x in they_cruised if x not in you_cruised]

        cmatches = [cruiser_info(evt.event, x) for x in they_cruised if x in you_cruised]

        you_cruised = [public_info(evt.event, x) for x in you_cruised]
        c = Context(
            {'message': message, 'send_matches': True, 'matches': matches, 'fmatches': fmatches, 'cmatches': cmatches,
             'cruises': cruises,
             'tried_friends': rr.friend_dates, 'event': evt, 'rr': rr, 'you_cruised': you_cruised,
             'cruised_any': (len(you_cruised) > 0)})
        # t = find_template_source( 'email/match_section.txt' )[0]
        # email_template = Template( t )
        email_template = get_template('email/match_section.txt')
        body = email_template.render(c)
        return body
    except Exception as inst:
        return "[Problem rendering match text for %s / %s]" % (rr, inst,)


def generate_date_sheet(evt, rr):
    """
    Generate text string for a person's date sheet (e.g., to email to them).
    """
    logger.info("Going to render date sheet")
    try:
        dates = get_date_schedule(rr.psdid, evt.event)
        import ipdb;
        ipdb.set_trace()
        # matches = DateRecord.objects.filter(psdid=rr.psdid, event=evt.event)
        if (len(dates) == 0):
            message = "No dates scheduled or date sheet found"
        else:
            message = ""
        c = Context({'message': message, 'dates': dates, 'event': evt, 'rr': rr})

        email_template = get_template('email/date_sheet.txt')
        body = email_template.render(c)
        return body
    except Exception as inst:
        return "[Problem rendering date sheet for %s / %s]" % (rr, inst,)


def send_email(evt, rr, subject, body, really_email=False):
    """
    Send email to given person as indicated by RegRecord 'rr'.
    'body' is the entire text of the email.
    Return: the text of email sent, or the problem with sending it, if there was one.
    """
    try:
        # logger.info( "Emailing user associated with %s" % (rr, ) )
        u = User.objects.get(username=rr.psdid)
        # make sure user has right email
        if u.email != rr.email:
            logger.info("Permanently Changing email of %s to %s from %s" % (rr.psdid, rr.email, u.email))
            u.email = rr.email
            u.save()
        if really_email:
            u.email_user(subject, body, evt.info_email)
        return body
    except Exception as inst:
        prob = "Something went wrong with reg %s / %s" % (rr, inst)
        logger.info(prob)
        return prob


def send_formatted_email(evt, rr, subject, body_template, send_matches, really_email=False):
    """
    Send email to given person as indicated by RegRecord 'rr'.
    Uses the "your_matches.txt" template.  'body' holds the email body.  Will
    be prefaced by Dear BLAH and ended with "love PSD Robot #4."
    """

    # additional variables generated on the fly (not great)
    if rr.matches < 5:
        rr.flagged = True
    else:
        rr.flagged = False

    if send_matches:
        match_text = generate_match_text(evt, rr)
    else:
        match_text = ""

    logger.info("Going to render body")
    try:
        email_template = Template(body_template)
        email_text = email_template.render(
            Context({'rr': rr, 'event': evt, 'send_matches': send_matches, 'match_text': match_text}))
    except Exception as inst:
        return "<p>Problem rendering email body for %s / %s" % (rr, inst,)

    while '\n\n\n' in email_text:
        email_text = email_text.replace('\n\n\n', '\n\n')

    logger.info("Generated email, now sending it")
    return send_email(evt, rr, subject, email_text, really_email)


def email_handler_iter(form, event, regs):
    """
    Send form letter to everyone in the list of regrecords 'regs'
    """
    logger.info("Post Email Handling for %s" % (event,))
    event_name = event.event
    subject = form.cleaned_data['subject']
    body = form.cleaned_data['body']
    skip_flagged = form.cleaned_data.get('skip_flagged', False)
    send_matches = form.cleaned_data['send_matches']
    really_send = form.cleaned_data['really_send']
    if type(form) is PostEmailForm:
        start_at = form.cleaned_data['start_at']
    else:
        start_at = 1
    if start_at is None:
        start_at = 1

    evt = Event.objects.get(event=event_name)

    yield """send_matches = %s    really_send = %s
    Sending %s records right now...
    """ % (send_matches, really_send, len(regs))

    yield "Starting at #%s in a list of %s records" % (start_at, len(regs))

    smptxt = ""
    cntr = start_at
    for r in regs[(cntr - 1):]:
        logger.info("Next reg... %s/%s" % (cntr, len(regs)))
        smptxt = ""
        try:
            if not start_at is None and cntr < start_at:
                logger.info("Skipping... #%s: %s" % (cntr, r.psdid))
                smptxt = "Skipped email"
            else:
                if skip_flagged and r.flagged_NMSMSS:
                    logger.info("Skipping (due to flag)... #%s: %s" % (cntr, r.psdid))
                    smptxt = "Skipped email because record flagged"
                elif send_matches and r.here and r.cancelled:
                    logger.info("Skipping (due to being dater who cancelled mid-event)... #%s: %s" % (cntr, r.psdid))
                    smptxt = "Skipped due to being dater who cancelled mid-event"
                elif send_matches and r.date_sheet_pending():
                    logger.info("Skipping (due to being dater without a fully filled in date sheet)... #%s: %s" % (cntr, r.psdid))
                    smptxt = "Skipping (due to being dater without a fully filled in date sheet)"
                else:
                    logger.info("Sending... #%s: %s" % (cntr, r.psdid))
                    smptxt = send_formatted_email(evt, r, subject, body, send_matches, really_send)
                    logger.info("Sent #%s: %s" % (cntr, r.psdid))
            yield "\n<hr>#%s: %s<hr>\n" % (cntr, r.psdid) + smptxt
            if really_send:
                time.sleep(random.randint(0, 3) * random.randint(0, 3) )
        except Exception as inst:
            prob = "Something went wrong with email_handler_iter for %s / %s" % (r, inst)
            logger.info(prob)
            yield "\n<hr>#%s: ERROR on %s\nError is: %s\nGenerated Text (not sent):\n%s\n" % (
            cntr, r.psdid, inst, smptxt)
        logger.info("Done loop.")
        cntr += 1

    yield "<p><hr><h3>Finished!</h3>"
    logger.info("Finished email_handler_iter")


# def email_staff_thingy():
#                staff = User.objects.filter(is_staff=True)
#            preamble = """Hello, PSD staff person! PSD daters were just sent a mass email. Below
# the line is an example of an email that one dater received.
#
# Beep boop,
# PSD Robot #5
#
#
# """
#            for s in staff:
#                s.email_user(subject, preamble + body, evt.info_email)
#                if send_matches:
#                    ## Just use the last reg from the previous loop!
#                    s.email_user("Poly Speed Dating results", preamble + post_email_body(r, evt), evt.info_email)


def load_email_template(template_name):
    try:
        # import ipdb; ipdb.set_trace()

        # t = find_template_source( ['email/email_reminder_%s.txt' % (event_name, ), 'email/email_reminder.txt' ] )[0]
        t = get_template(template_name)
        source = open(t.origin.name, 'r').read()
        return source
    except:
        return "error: default template '%s' not found" % (template_name,)


def pre_email(request, event_name):
    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request, 'error.html', {
            'message': "Sorry.  You are trying to email for an event that does not exist.  Please try again."})

    if request.method == 'POST':
        form = PostEmailForm(request.POST)
        if form.is_valid():
            logger.info("Going to email reminders")
            regs = RegRecord.objects.filter(event=event.event, cancelled=False)
            logger.info("Emailing %s reg records" % (len(regs),))
            email_gremlin = email_handler_iter(form, event, regs)
            return HttpStreamTextResponse(email_gremlin, event.event)
    else:
        t = load_email_template("email/email_reminder.txt")
        initial = {'event_name': event_name, 'subject': "Reminder of upcoming PSD event---you are registered!",
                   'body': t, 'skip_flagged': True}
        form = PostEmailForm(initial=initial)

    return render(request, 'dashboard/pre_event_email.html', {'form': form, 'event': event, 'event_name': event_name})


def post_email(request, event_name):
    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request, 'error.html', {
            'message': "Sorry.  You are trying to email for an event that does not exist.  Please try again."})

    if request.method == 'POST':
        form = PostEmailForm(request.POST)
        if form.is_valid():
            regs = RegRecord.objects.filter(event=event_name, here=True, cancelled=False)  # type: QuerySet
            email_gremlin = email_handler_iter(form, event, regs)
            return HttpStreamTextResponse(email_gremlin, event.event)

    else:
        t = load_email_template("email/match_email_template.txt")
        initial = {'event_name': event_name, 'subject': "Your PSD Matches", 'body': t}
        form = PostEmailForm(initial=initial)

    return render(request, 'dashboard/post_event_email.html', {'form': form, 'event': event, 'event_name': event_name})


def individual_email(request, event_name, psdid, from_comments=False):
    """
    Send letter to given psdid from given event
    """
    print "Emailing %s for event %s" % (psdid, event_name,)
    if request.method == "POST":
        ret = subgroup_email(request, event_name)
        return ret
    else:
        try:
            event = Event.objects.get(event=event_name)
        except Event.DoesNotExist:
            return render(request, 'error.html', {
                'message': "Sorry.  You are trying to email for an event that does not exist.  Please try again."})

        default_text = "Enter text here"
        if from_comments:
            sub = "Reply to your comments from PSD"
            rr = RegRecord.objects.get(event=event_name, psdid=psdid)
            default_text = "In response to your registration comment:\n> %s" % (rr.comments,)
        else:
            sub = "A note from your PSD Organizers"
        initial = {'event_name': event_name, 'subject': sub, 'body': default_text,
                   'psdids': psdid, 'really_send': True}
        form = SubgroupEmailForm(initial=initial)

    return render(request, 'dashboard/subgroup_contact_email.html',
                  {'form': form, 'event': event, 'event_name': event_name})


def subgroup_email(request, event_name):
    """
    Send form letter, possibly with matches, to list of psdids
    psdid list comes from form as char string, 'psdids'

    """
    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request, 'error.html', {
            'message': "Sorry.  You are trying to email for an event that does not exist.  Please try again."})

    if request.method == 'POST':
        form = SubgroupEmailForm(request.POST)
        if form.is_valid():
            psdids = form.cleaned_data['psdids']
            psdids.upper()
            psdids = re.split('; |, ', psdids)
            regs = RegRecord.objects.filter(event=event_name, psdid__in=psdids)
            got_psdids = set([r.psdid for r in regs])
            missed = set(psdids) - got_psdids
            email_gremlin = email_handler_iter(form, event, regs)
            who_send = "Sending to %s\nFailed to send to %s\n" % (", ".join(got_psdids), ", ".join(missed))
            return HttpStreamTextResponse(itertools.chain((who_send,), email_gremlin), event.event)
    else:
        try:
            # TODO Fix this template load.  doesn't do right thing.
            # t = find_template_source( ['email/email_reminder_%s.txt' % (event_name, ), 'email/email_reminder.txt' ] )[0]
            default_text = find_template_source('email/match_email_template.txt')[0]
        except:
            default_text = "Enter text here (default template not found)"

        # try:
        #    t = find_template_source('email/your_matches.txt')[0]
        # except:
        #    t="error: default template not found"
        initial = {'event_name': event_name, 'subject': "Your PSD Matches", 'body': default_text}
        # initial = { 'event_name': event_name, 'subject':"PSD Matches.", 'body':t }
        form = SubgroupEmailForm(initial=initial)

    return render(request, 'dashboard/subgroup_contact_email.html',
                  {'form': form, 'event': event, 'event_name': event_name})


def email_volunteer_cruises(request, event_name):
    """
    Send form letter to a volunteer with a list of cruise contact info
    """
    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request, 'error.html', {
            'message': "Sorry.  You are trying to email for an event that does not exist.  Please try again."})

    if request.method == 'POST':
        form = VolunteerCruiseEmailForm(request.POST)
        if form.is_valid():
            results = ""
            really_send = form.cleaned_data['really_send']

            psdids = form.cleaned_data['psdids']
            psdids.upper()
            psdids = re.split('[;,\*\n ]+', psdids)
            try:
                cruises = [cruiser_info(event_name, x.strip()) for x in psdids]
            except RegRecord.DoesNotExist as e:
                results = "Failed to look up all PSDIDs---please check (message = %s)<br>(Auto-setting 'really_send' to False)<br>" % (
                e.message,)
                cruises = []
                really_send = False
            message = ""
            c = Context({'message': message, 'cruises': cruises,
                         'event': event, 'have_cruises': (len(cruises) > 0)})
            email_template = get_template('email/cruise_section.txt')
            body = email_template.render(c)

            logger.info("Valid form.  About to send email")
            subject = form.cleaned_data["subject"]
            body = form.cleaned_data["body"] + "\n" + body
            email = form.cleaned_data["volunteer_email"]
            results = results + "<br><br>Email Sent to '%s':<br><pre>---------\nsubject=%s\n\n%s\n------------</pre>\n<br>" % (
            email, subject, body)
            logger.info(results)

            if really_send:
                logger.info("About to send email")
                try:
                    succ = django.core.mail.send_mail(subject, body, event.info_email, [email])
                    logger.info("Succ = %s" % (succ,))
                    logger.info("Sent email")
                    logger.info("Attempted to send mail to '%s'.  Got success code '%s'" % (email, succ,))
                    results = results + "\n<br>\n<br>Sent mail, we think, to given email address.  Result = %s" % (
                    succ,)
                except Exception as inst:
                    logger.error("Failed: Exception is %s" % (inst,))
                    results = results + "\n<br>Error in sending mail: %s" % (inst,)
            else:
                results = results + "\n(But did not send email)\n"

    else:
        default_text = "Enter text here."
        results = ""
        initial = {'event_name': event_name, 'subject': "You got cruised!", 'body': default_text}
        form = VolunteerCruiseEmailForm(initial=initial)

    return render(request, 'dashboard/volunteer_cruise_email_form.html',
                  {'form': form, 'event': event, 'event_name': event_name, 'results': results})


def test_email(request, event_name):
    """
    Send form letter, possibly with matches, to list of psdids
    psdid list comes from form as char string, 'psdids'

    """
    logger.info("test_email called")
    print "Test email"
    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request, 'error.html', {
            'message': "Sorry.  You are trying to email for an event that does not exist.  Please try again."})

    results = ""
    if request.method == 'POST':
        form = TestEmailForm(request.POST)
        if form.is_valid():
            logger.info("Valid check email form.  About to send email")
            subject = form.cleaned_data["subject"]
            body = form.cleaned_data["body"]
            email = form.cleaned_data["email"]
            results = "email = %s\n<br>subject=%s\n<br>body='%s'\n<br>" % (subject, body, email)
            results = results + "PROJECT_APP_PATH = '%s'\n<br>LOG_DIR = '%s'\n<br>" % (
            settings.PROJECT_APP_PATH, settings.LOG_DIR,)
            results = results + "STATIC_URL = '%s'\n<br>STATIC_ROOT = '%s'\n<br>" % (
            settings.STATIC_URL, settings.STATIC_ROOT)
            logger.info(results)

            logger.info("About to send email")
            try:
                results = results + "\n<br> info email = %s" % (event.info_email,)
                results = results + "\n<br> EMAIL_HOST = '%s'\n<br>   EMAIL_PORT = '%s'\n<br>  EMAIL_HOST_USER = '%s'" % (
                settings.EMAIL_HOST, settings.EMAIL_PORT, settings.EMAIL_HOST_USER)
                succ = django.core.mail.send_mail(subject, body, event.info_email, [email])
                logger.info("Succ = %s" % (succ,))
                logger.info("Sent email")
                logger.info("Attempted to send mail to '%s'.  Got success code '%s'" % (email, succ,))
                # staff = User.objects.filter(is_staff=True)
                # body = "Test Email Sent Alert: " + body
                # subject = "Test Sending Email (%s) to %s" % ( subject, email, )
                # for s in staff:
                #    s.email_user(subject, body, event.info_email )
                results = results + "\n<br>\n<br>Sent mail, we think, to staff and given email address.  Result = %s" % (
                succ,)
            except Exception as inst:
                logger.error("Failed: Exception is %s" % (inst,))
                results = results + "\n<br>Error in sending mail: %s" % (inst,)
    else:
        default_text = "Enter text here"
        initial = {'event_name': event_name, 'subject': "Testing Email", 'body': default_text}
        form = TestEmailForm(initial=initial)

    return render(request, 'dashboard/command_arg_form.html',
                  {'form': form, 'event': event, 'command_title': 'Test Sending of Email',
                   'button_name': 'Send Test Email',
                   'is_popup': False,
                   'title': "test email and variables",
                   'information': "Unknown",
                   'has_permission': True,
                   'results': results}, )


def contact_us(request, event_name):
    evt = Event.objects.get(event=event_name)
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            subject = "PSD website feedback"
            if form.cleaned_data['psdid']:
                subject += ' from %s' % form.cleaned_data['psdid']
            t = get_template('email/feedback.txt')
            c = Context({'cd': form.cleaned_data, 'event': evt})
            body = t.render(c)

            staff = User.objects.filter(is_staff=True)
            for s in staff:
                s.email_user(subject, body, evt.info_email)
        return render(request, 'feedback_received.html', {'event': evt})

    else:
        form = FeedbackForm()
    return render('feedback.html', {'form': form, 'event': evt})
