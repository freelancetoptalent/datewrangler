from psd import debugtools as dt
from register.system_models import Event
from register.matchq_models import MatchQuestion
from django_docopt_command import DocOptCommand
from .matchquestions import setupMatchQuestions
from .checkorganization import checkOrganization


def makeTestDB(event_name, simple_event=False, extra_extra_questions=True, trigender=False, verbose=True):
    """
    add_to_event - true means add some sample questions.   false means no.
    """

    setupMatchQuestions(verbose=verbose, trigender=trigender)

    events = Event.objects.filter(event=event_name)
    if len(events) > 0:
        print("Warning: Already have a testing1 event.  Going to re-use it.")
        evt = events[0]
    else:
        evt = dt.makeTestEvent(event_name)
        evt.save()

    if not simple_event:
        evt.extra_questions.clear()
        evt.save()
        evt.extra_questions.add(MatchQuestion.objects.get(question_code="primary"))
        evt.extra_questions.add(MatchQuestion.objects.get(question_code="kinky"))
        evt.extra_questions.add(MatchQuestion.objects.get(question_code="monog"))
        evt.extra_questions.add(MatchQuestion.objects.get(question_code="asexual"))
        evt.extra_questions.add(MatchQuestion.objects.get(question_code="spanish"))
        evt.extra_questions.add(MatchQuestion.objects.get(question_code="race"))

        if extra_extra_questions:
            evt.extra_questions.add(MatchQuestion.objects.get(question_code="funk"))
            evt.extra_questions.add(MatchQuestion.objects.get(question_code="hot"))
            evt.extra_questions.add(MatchQuestion.objects.get(question_code="identity"))
        evt.save()


class Command(DocOptCommand):
    docs = """make a test database with a fake event.  Calls 'matchquestions' then adds more.

Usage: testdb

Options:
    -h --help     Show this screen.
"""

    def handle_docopt(self, arguments):
        makeTestDB("testing1", False, False)
        checkOrganization()
