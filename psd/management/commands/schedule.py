from matchmaker import date_scheduler
from django_docopt_command import DocOptCommand


class Command(DocOptCommand):
    docs = """Make a schedule for [rounds] rounds of dating.

Will do random starts [trials] times (higher numbers means more time trying to find good schedule).
who include can be "In" or "All" or "NotNo" or "Paid"

Usage: schedule <eventname> <rounds> [--trials=N] [--who-include=(In|All|NotNo|Paid)]

Arguments:
    <eventname>   The event's short identifier
    <rounds>      Number of rounds

Options:
    -h --help     Show this screen.
    --who-include=OPERATOR   [default: In]
    --trials=N      Number of trials [default: 1]
"""
    def handle_docopt(self, arguments):
        event = arguments['<eventname>']
        rounds = int(arguments['<rounds>'])
        trials = int(arguments['--trials'])
        who_include = arguments['--who-include']

        date_scheduler.schedule(event,
                                rounds=rounds,
                                trials=trials,
                                who_include=who_include)

