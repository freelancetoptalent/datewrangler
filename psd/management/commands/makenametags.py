from psd import RcodeHooks
from django_docopt_command import DocOptCommand


class Command(DocOptCommand):
    docs = """Make a file that can be used to make nametag labels (duplicating groups, etc)

Usage: makenametags <eventname>

Arguments:
    <eventname>   The event's short identifier

Options:
    -h --help     Show this screen.
"""
    def handle_docopt(self, arguments):
        event = arguments['<eventname>']
        RcodeHooks.makeNametags(event)
