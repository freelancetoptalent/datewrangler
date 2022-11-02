import sys
from register.models import RegRecord, Event
from django.contrib.auth.models import User
from django_docopt_command import DocOptCommand
from django.shortcuts import render_to_response


def emailNoPay(rr, event):
    email_body = render_to_response('email/email_nopay.txt',
                                         {'rr' : rr , 'event':event })
    user = User.objects.get(username=rr.psdid)

    user.email_user("PSD Payment Question Regarding %s." % (rr.psdid,), email_body.content)
    print "Email sent to %s at %s!" % (user.username, user.email,)



class Command(DocOptCommand):
    docs = """list folks who haven't paid

Usage: nopay <eventname>

Arguments:
    <eventname>   The event's short identifier

Options:
    -h --help     Show this screen.
"""

    def handle_docopt(self, arguments):
        event_name = arguments['<eventname>']

        regs = RegRecord.objects.filter(event=event_name)
        event = Event.objects.get(event=event_name)
        flaggedregs = []
        for r in regs:
            if not r.cancelled and not r.paid and not r.pending:
                print "\n**********************************************\n%s\n\t%s\n\tcomments: %s\n\treferral %s\n\tnotes: %s\n" %(str(r), r.geekcode(), r.comments, r.referred_by, r.notes)
                print "<enter> to flag email, [S] to skip, or mark as [P]aid or [W]ill Pay (Pending)?\n> ",
                s = sys.stdin.readline()
                s = s.strip().upper()
                if s == "S":
                    print "Skipped!"
                elif s == "W":
                    r.pending = True
                    r.save()
                elif s == "P":
                    r.paid = True
                    r.save()
                else:
                    flaggedregs.append(r)
                    print "Appending %s to list and adding note to file" % (r.email,)
                    if "!NO PAY!" not in r.notes:
                        r.addNote("!NO PAY! (Flag as not having made pay arrangements)")
                    r.save()
                    s = ""

        for fr in flaggedregs:
            print fr.email
        print "Email list above?\n> ",
        s = sys.stdin.readline()
        s = s.strip().upper()
        if (s == "Y"):
            for fr in flaggedregs:
                emailNoPay(fr, event)


