from django.contrib.auth.models import User
from django.shortcuts import render_to_response
from register.models import RegRecord, Event
from django_docopt_command import DocOptCommand


def emailReminder(rr, event):
    if rr.matches < 5:
        rr.flagged = True
    else:
        rr.flagged = False
    email_body = render_to_response('email/email_reminder.txt',
                                         {'rr' : rr , 'event':event })
    user = User.objects.get(username=rr.psdid)

    user.email_user("PSD Tomorrow! Reminder for %s" % (rr.psdid,), email_body.content)
    #print email_body.content
    print "Email sent to %s at %s!" % (user.username, user.email,)



class Command(DocOptCommand):
    docs = """email reminders to everyone, flagging those with few dates. RUN MATRIX MAKER FIRST!

Usage:
  emailreminders <eventname>

Arguments:
  <eventname>   The event's short identifier


Options:
  -h --help     Show this screen.
"""

    def handle_docopt(self, arguments):
        event_name = arguments['<eventname>']
        regs = RegRecord.objects.filter(event=event_name)
        event = Event.objects.get(event=event_name)
        for r in regs:
            if not r.cancelled and "!DEMOG!" not in r.notes and "!NO PAY!" not in r.notes:
                emailReminder(r, event )
