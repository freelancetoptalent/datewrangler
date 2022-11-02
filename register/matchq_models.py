"""
Models used to to hold the extra match questions
"""


from django.db import models
import sys
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from register import describe
from register.decorators import memoized_property
from register.textquestion import TextResponse
from matchmaker.models import MatchRecord
from .psdcheckbox import getPSDCheckboxOptions, genSeekAndPrefs, ModelSetupError

import logging
logger = logging.getLogger('register.matchqmodels')




class Response(models.Model):
    """
    A Person's recorded response to one of the extra match questions
    """
    owner = models.ForeignKey('Person')
    question = models.ForeignKey('MatchQuestion')
    answers = models.ManyToManyField('MatchChoice')

    # If the question does not have a "ask_about_seek" structure, the answers in 'answers' will be copied over to
    # 'seek_answers' during registration.
    seek_answers = models.ManyToManyField('MatchChoice', related_name='seek_response_set')

    @memoized_property
    def cached_answers(self):
        return list(self.answers.all())
        # return self.answers.all()

    @memoized_property
    def cached_seek(self):
        return list(self.seek_answers.all())
        # return self.seek_answers.all()

    @memoized_property
    def said_no(self):
        return self.has_answer & (self.cached_answers[0] == self.question.no_choice)

    @memoized_property
    def said_yes(self):
        return self.has_answer & (self.cached_answers[0] == self.question.yes_choice)

    def will_accept(self, other):
        """
        other is a Response as well.
        This determines if this response views the other response as compatable.
        (But not necessarily vice-versa.)

        returns: True or False
        """
        if not other.cached_answers:
            # print "will_accept: other has no answers: %s" % (other,)
            return True
        if not self.cached_seek:
            # print "will_accept: no seek answers '%s'" % (self, )
            return True

        if self.question.isYN:
            other_choice = other.cached_answers[0]
            our_choice = self.cached_seek[0]
            if self.question.ask_about_seek:
                if (our_choice == self.question.either_choice or our_choice == other_choice):
                    return True
                else:
                    return False
            else:
                return (our_choice == other_choice)
        else:
            my_seek = set(self.cached_seek)
            your_answers = set(other.cached_answers)

            if self.question.strict_subset_match:
                your_bad_answers = your_answers - my_seek
                ## Controversial! If it's a strict subset question, and
                ## you marked nothing at all for yourself, do you meet
                ## my criteria? This implementation says yes.
                return not bool(your_bad_answers)
            else:
                your_good_answers = your_answers & my_seek
                return bool(your_good_answers)

    @memoized_property
    def short_answer(self):
        shortanswer = '/'.join(x.choice_code for x in self.cached_answers)
        return shortanswer

    @memoized_property
    def has_answer(self):
        return len(self.cached_answers) > 0

    @memoized_property
    def short_seek_answer(self):
        shortseek = '/'.join(x.choice_code for x in self.cached_seek)
        return shortseek

    def __unicode__(self):
        return "(%s)%s:%s seeks %s" % (
        self.owner.psdid, self.question.question_code, self.short_answer, self.short_seek_answer)



class MatchQuestion(models.Model):
    question = models.CharField(max_length=200)
    explanation = models.CharField(max_length=200, null=True)
    internal_comment = models.CharField(max_length=200, null=True)
    absolute_match = models.BooleanField(default=False)
    hard_match = models.BooleanField(default=False)
    strict_subset_match = models.BooleanField(default=False)
    checkbox = models.BooleanField(default=False)
    ask_about_seek = models.BooleanField(default=False)
    include_name = models.BooleanField(default=False)
    question_code = models.CharField(max_length=15)
    is_YN = models.BooleanField(default=False)
    yes_only = models.BooleanField(default=False)

    # can a user say they want to strongly match "no"s for a YN question?  (i.e., NOT spanish speaker strongly prefered)
    seek_no_allowed = models.BooleanField(default=True)

    #    render_string = models.CharField(max_length=100, default="Looking for <LOOK>.  Registered as <AM>")
    #    render_conjunction = models.CharField(max_length=100, default="and")
    #    render_seek_conjunction = models.CharField(max_length=100, default="or")

    # double check boxes?
    allow_preferences = models.BooleanField(default=False)

    @memoized_property
    def choices(self):
        return list(MatchChoice.objects.filter(question=self.id))

    @memoized_property
    def seek_choices(self):
        seekset = self.matchchoice_set

        if not self.seek_no_allowed:
            return seekset.exclude(choice_code='N')
        else:
            return seekset

    def get_choice(self, choice_code):
        chc = self.choices
        chcs = [c.choice_code for c in chc]
        if choice_code in chcs:
            return chc[chcs.index(choice_code)]
        else:
            raise ModelSetupError("get_choice called for '%s' when no '%s' is listed choice of question '%s'" % (
            choice_code, choice_code, self.question_code,))

    def default_choice(self):
        chc = self.choices
        if len(chc) == 0:
            raise ModelSetupError("No choices for matchquestion %s" % (self.question_code,))

        if self.is_YN:
            chcs = [c.choice_code for c in chc]
            if 'EI' in chcs:
                return chc[chcs.index('EI')]
            else:
                return chc[0]
        else:
            return chc[0]

    @memoized_property
    def yes_choice(self):
        if not self.is_YN:
            raise ModelSetupError("yes_choice called for non yn question")
        return self.get_choice('Y')  # self.choices[1]

    @memoized_property
    def no_choice(self):
        if not self.is_YN:
            raise ModelSetupError("no_choice called for non yn question")
        return self.get_choice('N')

    @memoized_property
    def either_choice(self):
        if not self.is_YN:
            raise ModelSetupError("either_choice called for non yn question")
        return self.get_choice('EI')  # self.choices[1]

    def num_choices(self):
        return len(self.choices)

    @memoized_property
    def isYN(self):
        """
        Should this question be represented as a Y/N checkbox for the "ask" part
        With the options listed as options for the seek part (if any)
        (With a dropdown for the seek side of things)
        """
        return self.is_YN

    def __unicode__(self):
        return self.question


class MatchChoice(models.Model):
    question = models.ForeignKey(MatchQuestion)
    choice = models.CharField(max_length=200)
    choice_code = models.CharField(max_length=2)

    def __unicode__(self):
        # return "[" + self.choice_code + "]: " + self.choice
        return self.choice


