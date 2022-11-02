import sys
from register.models import RegRecord, Event
from django_docopt_command import DocOptCommand


class Command(DocOptCommand):
    docs = """list all folks IDs for an event

Usage: listid <eventname>

Arguments:
    <eventname>   The event's short identifier

Options:
    -h --help     Show this screen.
"""

    def handle_docopt(self, arguments):
        event_name = arguments['<eventname>']
        regs = RegRecord.objects.filter( event=event_name ).order_by( 'psdid' )
        cntr = 1

        for r in regs:
            if not r.cancelled:
                print "%s\t%s\t%s" % ( cntr, r.psdid, r.namestring )
                cntr = cntr+1
