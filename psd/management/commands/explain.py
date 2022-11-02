from matchmaker import explain
from django_docopt_command import DocOptCommand


class Command(DocOptCommand):
    docs = """why psdid does/does not get dates at eventname

Note: you can do this in django.  This, however, gives more output on process.

Usage: explain <eventname> [<psdid>]

Arguments:
    <eventname>   The event's short identifier

Options:
    -h --help     Show this screen.
"""

    def handle_docopt(self, arguments):
        event = arguments['<eventname>']
        psdid = arguments['<psdid>']
        if psdid:
            print "\n\t == EXPLAINING SOME THINGS ==\n\n"
            explain.explain(event, psdid)
        else:
            explain.explain_all(event)
