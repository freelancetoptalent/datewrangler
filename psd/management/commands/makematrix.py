from register.models import Event
from django_docopt_command import DocOptCommand
from matchmaker.matrix_maker import updateMatchRecords


class Command(DocOptCommand):
    docs = """Make and save matrix of who can date whom

Note: you can do this in django.  This, however, gives more output on process.

Usage: makematrix <eventname>

Arguments:
    <eventname>   The event's short identifier

Options:
    -h --help     Show this screen.
"""

    def handle_docopt(self, arguments):
        event_name = arguments['<eventname>']
        try:
            event = Event.objects.get(event=event_name)
        except Event.DoesNotExist:
            print "Failed to obtain event object '%s'" % (event_name, )
            return

        res = updateMatchRecords(event, verbose=True)
        print("Results of makeMatrix: %s\n" % (res,))
