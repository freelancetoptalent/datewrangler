from django_docopt_command import DocOptCommand

from register.demographics import print_demographics_async

class Command(DocOptCommand):
    docs = """print all registered folks for the given event that have
not explicitly canceled

Usage: demographic <eventname>

Arguments:
    <eventname>   The event's short identifier

Options:
    -h --help     Show this screen.
"""
    def handle_docopt(self, arguments):
        event = arguments['<eventname>']
        for ln in print_demographics_async( event ):
            print ln
        print "(Finished printout)\n"
