import sys
from register.models import RegRecord
from django_docopt_command import DocOptCommand



class Command(DocOptCommand):
    docs = """Go through registration and list all straight folks who have a regrecord id after cut_id

Usage:
  liststraight <eventname> <cut_id>

Arguments:
  <eventname>   The event's short identifier
  <cut_id>      Django database id of the record (an integer), NOT the psdid

Options:
  -h --help     Show this screen.
"""

    def handle_docopt(self, arguments):
        event = arguments['<eventname>']
        cut_id = arguments['<cut_id>']

        regs = RegRecord.objects.filter( event=event, id__gte=cut_id )
        emails = []
        print "Going to search through the %s reg forms" % (len(regs), )
        for r in regs:
            if "!Need companion!" in r.notes:
                print "%s\n\t%s\n\tcomments: %s\n\treferral %s\n\tnotes: %s\n" %( str(r), r.geekcode(), r.comments, r.referred_by, r.notes )
                print "Check PSDID  (or [F]flag email)?\n> ",
                s = sys.stdin.readline()
                s = s.strip().upper()
                while s!="":
                    if s == "F":
                        emails.append( r.email )
                        print "Appending %s to list and adding note to file" % (r.email,)
                        r.addNote( "!DEMOG! (Flag as not-balanced demographic)" )
                        r.save()
                        s = ""
                    else:
                        print "Looking for '%s'" % (s, )
                        r2 = RegRecord.objects.filter( psdid=s )
                        print "Found: ", r2
                        for rr in r2:
                            print "%s: %s\nref:\t%s\n\tnotes: %s" % (rr.psdid, rr.comments, rr.referred_by, rr.notes )
                        print "Check PSDID  (or [F]flag email)?\n> ",
                        s = sys.stdin.readline()
                        s = s.strip().upper()
        print "Email of non-balanced folks"
        for em in emails:
            print em
