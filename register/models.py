"""
Code for all of the various objects that are stored in the database.

This is one of the primary files of the project.

The regrecord and person objects are primary objects of note.
They have the code that calculates how good a match between two RegRecords is.

"""

from django.db import models
import sys
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from register import describe
from register.decorators import memoized_property
from register.textquestion import TextResponse
from register.schedule_models import DateRecord, BreakRecord
from register.matchq_models import Response, MatchQuestion
from matchmaker.models import MatchRecord
from register.system_models import Event, getTextTranslationTable
from .psdcheckbox import getPSDCheckboxOptions, genSeekAndPrefs, ModelSetupError


import logging
logger = logging.getLogger('register.models')


# TODO: Fix global variable thing here.
# These are cut-offs for match-horror.
MATCH_NO = 10000
MATCH_NO_NAME = "no"
MATCH_GOOD = 1500
MATCH_GOOD_NAME = "good"
MATCH_GOODNESS_BUMP = 50
MATCH_POOR_NAME = "poor"

MATCH_START = 100
MATCH_THRESHOLD = 1990       # Cutoff for acceptable date.

RESPONSE_CACHE = {}



def fetch_regrecord( event_name, psdid ):
    """ Get a regrecord, if there is one """
    try:
         per = RegRecord.objects.get( event=event_name, psdid=psdid )
         return per
    except ObjectDoesNotExist:
        logger.error( "Failed to find RR '%s-%s'." % ( event_name, psdid, ) )
        return None

def fetch_matchrecord( psdid1, psdid2, event_name ):
    try:
        mr = MatchRecord.objects.get( psdid1 = psdid1, psdid2 = psdid2, event=event_name )
        return mr
    except:
        return None


def augment( explain, note ):
    """
    For the explain methods
    """
    if note != ():
        explain.append( note )


def match_category( horror ):
    """
    Return gross category of match quality being good, poor, or no match
    """
    if horror <= MATCH_GOOD:
        return MATCH_GOOD_NAME
    elif horror <= MATCH_THRESHOLD:
        return MATCH_POOR_NAME
    else:
        return MATCH_NO_NAME




class Person(models.Model):
    GENDERS = None
    TEXT_TRANSLATION = None

    first_name = models.CharField(max_length=30, verbose_name="First Name")
    last_name = models.CharField(max_length=30, verbose_name="Last Name")
    pronoun_slug = models.CharField(max_length=30, default="", verbose_name="Pronoun Slug", blank=True)
    gender = models.CharField(max_length=40, verbose_name="Gender")
    seek_gender = models.CharField(max_length=50, verbose_name="Genders Sought")
    age = models.PositiveIntegerField(verbose_name="Age")

    seek_age_min = models.PositiveIntegerField(verbose_name="Minimum Age Wanted")
    seek_age_max = models.PositiveIntegerField(verbose_name="Maximum Age Wanted")
    psdid = models.CharField(max_length=12, blank=True) # unique=TRUE

    # These are for the free text matching.  Two fields, one for "am" type entries and one for "seek" type entries.
    text_match = models.TextField(blank=True, verbose_name="Match Criterion")
    text_match_seek = models.TextField(blank=True, verbose_name="Match Criterion for Seek")


    def genderOptions(self):
        """
        This should be a class method.
        Fetch list of locations from database and stash in local variable to avoid
        making too many database hits.
        """
        if Person.GENDERS == None:
            #print( "Loading gender options and setting GENDER variable in Person" )
            logger.debug( "Loading gender options and setting GENDER variable in Person" )
            Person.GENDERS = getPSDCheckboxOptions( "Gender" )
            #logger.debug( "Got " + str( Person.GENDERS ) )
        return Person.GENDERS

    def textTranslationTable(self):
        if Person.TEXT_TRANSLATION == None:
            #print "**\n**Building text translation table now\n**"
            logger.debug( "Building text translation table and setting in Person" )
            Person.TEXT_TRANSLATION = getTextTranslationTable()
        return Person.TEXT_TRANSLATION


    def __unicode__(self):
        return self.first_name + ' ' + self.last_name

    @memoized_property
    def gender_set(self):
        res = describe.csv_to_set(self.gender)
        return res

    @memoized_property
    def seek_gender_set(self):
        res = genSeekAndPrefs(self.seek_gender)[0]
        return set(res)

    @memoized_property
    def pref_gender_set(self):
        res = genSeekAndPrefs(self.seek_gender)[1]
        return set(res)

    def has_gender(self, g):
        return g in self.gender_set

    def wants_gender(self, g):
        return g in self.seek_gender_set

    def wants_men(self):
        overlaps = self.seek_gender_set & set("CM","TM", "M")
        return len(overlaps) > 0

    def wants_women(self):
        overlaps = self.seek_gender_set & set("CW","TW", "W")
        return len(overlaps) > 0

    @memoized_property
    def my_answers(self):
        answers = Response.objects.filter(owner=self)
        return dict((a.question.id, a) for a in answers)

    @memoized_property
    def tag_permission(self):
        """
        :return: True if it is okay for matches to see matched text.
        """
        answers = [x for x in self.my_answers.values() if x.question.question_code == 'tagconsent']
        return answers and answers[0].said_yes

    @memoized_property
    def my_text_answer(self):
        tr = TextResponse( self.text_match, self.text_match_seek )
        ttable = self.textTranslationTable()
        tr.translate_words( ttable )
        return tr


    @memoized_property
    def responses(self):
        my_resps = Response.objects.filter(owner=self)
        return dict((r.question.id, r) for r in my_resps)


    def response_for(self, question):
        """
        Given an extra question object, get our response to it
        Returns a Response object.
        """
        if isinstance( question, basestring ):
            try:
                question = MatchQuestion.objects.get( question_code = "tagconsent" )
            except:
                logger.warning( "Failed to find question %s in response_for." % ( question, ) )
                return None

        if question.id in self.responses:
            return self.responses[question.id]
        else:
            return None
        #my_resp = Response.objects.filter(question=question, owner=self)
        #if len( my_resp ) == 1:
        #    return my_resp[0]
        #else:
        #    logger.error( "Failed to get answer.  Got %s answers instead: %s" % ( len(my_resp), my_resp) )
        #return None



    def set_responses_from(self, target, source):
        """
        target is a Response Object's ManyToMany field (answers or seek_answers).

        Depending on question type, source might be one answer, or might be a list.

        Add all the elements in source to target as answers.
        """
        if source is None:
            return
        if not isinstance(source, (list, tuple)):
            source = [source]
        for x in source:
            if x != '':
                target.add(x)

    def set_response(self, q, rsp, seek_rsp = [] ):
        """
        Set the response of this person to question q to (rsp, seek_rsp)
        :param q: Question
        :param rsp:
        :param seek_rsp:
        :return:
        """
        # delete old answer (if any)
        Response.objects.filter(owner=self, question=q).delete()
        r = Response(owner=self, question=q)

        if not isinstance(rsp, (list, tuple)):
            rsp = [rsp]

        # Save first to make many2many field work.
        r.save()

        if q.isYN:
            # not being checked corresponds to "No"
            if len(rsp) == 0:
                rsp = "%s" % (q.no_choice.id, )
            self.set_responses_from(r.answers, rsp)
        else:
            self.set_responses_from(r.answers, rsp)

        # If ask_about_seek then put the seek answers in, but if not ask_about_seek then
        # use the users answers in the seek side.
        prefix = 'seek_' if q.ask_about_seek else ''
        seek_field = prefix + q.question_code
        self.set_responses_from(r.seek_answers, seek_rsp)

        r.save()


    @memoized_property
    def fullname(self):
        return self.first_name + " " + self.last_name

    def geekcode(self):
        return describe.geekcode(self)

    def minicode(self):
        return describe.minicode(self)



    @memoized_property
    def is_man(self):
        return self.has_gender('M') or self.has_gender("TM") or self.has_gender("CM")

    @memoized_property
    def is_woman(self):
        return self.has_gender('W') or self.has_gender("TW") or self.has_gender("CW")

    @memoized_property
    def is_man_only(self):
        return self.is_man and not self.is_woman

    @memoized_property
    def is_woman_only(self):
        return self.is_woman and not self.is_man

    @memoized_property
    def only_alt_gendered(self):
        return not (self.is_man or self.is_woman)

    @memoized_property
    def wants_mf(self):
        return self.wants_m and self.wants_f

    @memoized_property
    def wants_m(self):
        return self.wants_gender('M') or self.wants_gender('TM') or self.wants_gender('CM')

    @memoized_property
    def wants_f(self):
        return self.wants_gender('W') or self.wants_gender('TW') or self.wants_gender('CW')




    def deprecated_explain_will_date_gender_trigender( self, other ):
        """
        Will this person date the other purely based on the genders?

        Logic:
        Rule 1: If looking for just Women, then must mean either Cis or Trans women
        Rule 2: If looking for Cis and trans women, then must be looking for women in general.
        Rule 3: If looking for Cis women only, then must be looking for Cis women who also checked Women
        Rule 4: Rule 3 for trans
        Rule 5: Rules 1-4 for men too.

        Idea:
        Judiciously expand the seek set.  Don't expand the identity set.  This makes more matches.
        """
        def quick_gen(genderset):
            return '/'.join(genderset)
        sk = self.seek_gender_set
        am = other.gender_set

        if ("CW" in sk and "CW" in am) or ("TW" in sk and "TW" in am):
            sk.add( "W" )
        if ("CM" in sk and "CM" in am) or ("TM" in sk and "TM" in am):
            sk.add( "M" )
        if "W" in sk and not "TW" in sk and not "CW" in sk:
            sk.add( "TW" )
            sk.add( "CW" )
        if "M" in sk and not "TM" in sk and not "CM" in sk:
            sk.add( "TM" )
            sk.add( "CM" )
        if "TM" in sk and "CM" in sk:
            sk.add( "M" )
        if "TW" in sk and "CW" in sk:
            sk.add( "W" )
        if am.issubset(sk):
            return True, ()
        elif am.intersection(sk):
            return False, ('gender', 'overlap', quick_gen(other.gender_set),
                                                quick_gen(self.seek_gender_set))
        return False, ('gender', 'no overlap', quick_gen(other.gender_set),
                                                   quick_gen(self.seek_gender_set))

    def will_date_gender( self, other ):
        """
        Will this person date the other purely based on the genders?
        """

        def quick_gen(genderset):
            return '/'.join(genderset)
        sk = self.seek_gender_set
        am = other.gender_set

        if other.gender_set.issubset(sk):
            return True, ()
        elif other.gender_set.intersection(sk):
            return False, ('gender', 'overlap', quick_gen(other.gender_set),
                                                quick_gen(self.seek_gender_set))
        return False, ('gender', 'no overlap', quick_gen(other.gender_set),
                                                   quick_gen(self.seek_gender_set))





    def match_horror_full(self, other, event = None, verbose=False ):
        """
                Return how horrifying a match between self and Person other is.   Big numbers mean
        more horrifying.  A score of 0 is the perfect match.  A 100 is an unremarkable match

        Basic idea: Start at 100.  Go through each question and
        adjust down if things look good.  Adjust up if things look bad.

        :param other:  a Person object
        :param event:   an Event object
        :return:
        """


        assert type(other) is Person
        if not event is None:
            assert type(event) is Event


        explain = []

        basic, explainA = self.will_date_basic(other)
        augment( explain, explainA )

        if not basic:
            if verbose:
                augment( explain, "(Failed basic screen)")
            return MATCH_NO, explain

        answer = MATCH_START

        bha = self.basic_horror_adjustment(other)
        if verbose:
            augment( explain, " basic: %s" % (bha, ) )
        answer += bha

        aug, explainA = self.match_questions_horror(other, event)
        answer += aug
        augment( explain, explainA )

        if event is None or event.free_text:
            aug = self.text_questions_horror( other )
            if verbose:
                augment( explain, "text: %s" % (aug, ) )
            answer += aug


        # beyond perfection!
        if answer < 0:
            if verbose:
                augment( explain, "Thresholded at 0" )
            answer = 0


        return answer, explain


    def match_horror(self, other, event = None, verbose=False ):
        return self.match_horror_full(other, event, verbose )[0]


    def basic_horror_adjustment(self, other):
        bonus = 0

        if other.age >= self.seek_age_min+5 and \
           other.age <= self.seek_age_max-5:
            bonus += 5

        if len( self.pref_gender_set.intersection(other.gender_set) ) > 0:
            bonus += 5

        return -bonus




    def match_questions_horror(self, other, event = None):
        reason = []
        horror = 0
        if event is None:
            questions = [rsp.q for rsp in self.responses]
        else:
            questions = event.cached_extra_questions

        for question in questions:
            horror_bump, explain = self.single_question_horror( other, question )
            if horror_bump != 0:
                augment( reason, explain )
                horror += horror_bump

        return horror, reason




    def single_question_horror(self, other, question):
        """
        How much do I want to date other, with regards to specific question
        :param other: A Person object
        :param question: The question to compare self and other on
        :return: Integer amount of horror to be added to a running total.  1000 will be a hard match failure.
        """
        horror = 0
        assert type(other) is Person
        assert type(question) is MatchQuestion

        # Get our responses
        my_resp = self.my_answers.get(question.id, None)
        your_resp = other.my_answers.get(question.id, None)

        # if either missing question, we just return 0 (for no modification)
        if my_resp is None or your_resp is None:
            return 0, ("someone missing question")

        if question.hard_match and not my_resp.will_accept(your_resp):
            horror += 1000
            return horror, (question.question_code, your_resp.short_answer, my_resp.short_seek_answer)

        if question.yes_only:
            if my_resp.said_yes and your_resp.said_yes:
                return horror - MATCH_GOODNESS_BUMP, (question.question_code, "mutual yes" )
            else:
                return 0, ()
        else:
            my_seek = set(my_resp.cached_seek)
            your_answers = set(your_resp.cached_answers)
            # TODO: "Either" will not register as match here, correct?
            return horror - 5*len(my_seek & your_answers), ()



    def will_date_basic(self, other):
        """
        Hard matching on whether there is compatability due to age and gender.
        :param other: A person
        :return: True or False, depending.
        """
        i_seek_their_genders, expl = self.will_date_gender(other)
        if not i_seek_their_genders:
            return False, expl
        elif self.seek_age_min > other.age:
            if self.seek_age_min - other.age < 3:
                return False, ('age', 'too young', 'slightly', self.seek_age_min - other.age)
            else:
                return False, ('age', 'too young', 'fully', self.seek_age_min - other.age)
        elif self.seek_age_max < other.age:
            if other.age - self.seek_age_max < 3:
                return False, ('age', 'too old', 'slightly', other.age - self.seek_age_max)
            else:
                return False, ('age', 'too old', 'fully', other.age - self.seek_age_max)

        return True, ()


    def text_questions_horror(self, other ):
        return -5 * self.my_text_answer.match_quality( other.my_text_answer )





    def mutual(self, other, event, threshold):
        """
        Will the match horror of this date be less than the threshold?
        """
        return self.match_horror(other, event) <= threshold and other.match_horror(self, event) <= threshold




    def least_mutual_match_horror(self, group, event ):
        """
        What is the best possible scenario of us being matched with someone
        in a given group of folks (group is regrecord with, we presume, multiple folks)?

        Note this does _MUTUAL_ matching to deal with the following: Consider a group of two gay women
        and a group of a SM and a SW.  The gay women want the SW.  The SM wants the gay women.  This would
        be a match without mutual matching considerations.
        """
        return min( max( self.match_horror(o, event), o.match_horror( self, event ) ) for o in group.cached_members)





class RegRecord(models.Model):
    LOCATION = None

    nickname = models.CharField(max_length=30, verbose_name="Nickname")
    email = models.EmailField(verbose_name="Email")
    add_to_mailings = models.BooleanField(default=True, verbose_name="Join Our Mailing List (Y/N)")
    seek_groups = models.BooleanField(verbose_name="Date Groups (Y/N)")

    groups_match_all = models.BooleanField( default=True, verbose_name="All Group Members Must Match (Y/N)")
    #groups_match_all = models.BooleanField( default=True, editable=False )

    volunteers_ok = models.BooleanField( default=False, verbose_name="Dating volunteers and staff is OK (Y/N)")
    #only_groups = models.BooleanField( verbose_name="Only Date Groups if Dating Groups (Y/N)" )
    friend_dates = models.BooleanField(verbose_name="Friend Dates (Y/N)", default=False)
    referred_by = models.CharField(max_length=80, blank=True, verbose_name="Referred By")
    pals = models.TextField(blank=True, verbose_name="Friends")
    location = models.CharField(max_length=30, blank=True, verbose_name="Location")
    wants_childcare = models.BooleanField(verbose_name="Need Childcare (Y/N)", default=False)
    children = models.TextField(blank=True, verbose_name="Children")
    comments = models.TextField(blank=True, verbose_name="Comments")
    event = models.CharField(max_length=15, blank=True)

    people = models.ManyToManyField(Person, blank=True)

    #user = models.OneToOneField(User, null=True, blank=True)
    psdid = models.CharField(max_length=12, blank=True) # 8 for triads
    paid = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)
    pending = models.BooleanField(default=False)
    here = models.BooleanField(default=False)
    stationary = models.BooleanField(default=False)
    is_group = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    matches = models.IntegerField(blank=True, null=True, default=0)
    oneway = models.IntegerField(blank=True, null=True, default=0)



    @memoized_property
    def is_indiv(self):
        return not self.is_group

    @property
    def members(self):
        return self.people.all()

    @memoized_property
    def cached_members(self):
        return self.people.all()

    @memoized_property
    def size(self):
        return self.people.count()

    @memoized_property
    def ev(self):
        return Event.objects.get(event=self.event)



    def num_events(self):
        """
        How many times has this person attended an event?
        """
        rrs = RegRecord.objects.filter( psdid=self.psdid, here=True )
        return len(rrs)


    def locationOptions(self):
        """
        This should be a class method.
        Fetch list of locations from database and stash in local variable to avoid
        making too many database hits.
        """

        if RegRecord.LOCATION == None:
            logger.debug( "Loading location options and setting LOCATION variable in regrecord" )
            RegRecord.LOCATION = getPSDCheckboxOptions( "Location" )
            #logger.debug( "Got " + str( RegRecord.LOCATION ) )
        return RegRecord.LOCATION


    def hasNotes( self ):
        if self.notes == "":
           return False
        else:
           return True

    def addNote(self, note ):
        """ append note to field """
        if self.hasNotes():
            self.notes = self.notes + ";\n" + note
        else:
            self.notes = note
        self.save()

    def date_sheet_pending(self):
        drs = DateRecord.objects.filter(psdid=self.psdid, event=self.event, said_yes=None)
        return len(drs) > 0

    def date_sheet_ever_said_yes(self):
        drs = DateRecord.objects.filter(psdid=self.psdid, event=self.event, said_yes=True)
        return len(drs) > 0

    def num_dates(self):
        drs = DateRecord.objects.filter( psdid=self.psdid, event=self.event, friend_date=False )
        return len( drs )


    def __unicode__(self):
        try:
            return "RR(%s) %s-%s-%s" % (self.id, self.event, self.psdid, '+'.join(unicode(s) for s in self.members))
        except:
            logger.error( sys.exc_info()[0] )
            return "[ERROR - Contact Sys Admin]"

    def full_names(self):
        try:
            return "%s" % ( '+'.join(unicode(s) for s in self.members ), )
        except:
            logger.error( sys.exc_info()[0] )
            return "[ERROR - Contact Sys Admin]"

    def integrity_ok(self):
        if self.is_group:
            if self.size > 1:
                return False
        else:
            if self.size != 1:
                return False

        return True

    @memoized_property
    def indiv(self):
        assert not self.is_group
        assert self.size == 1, self
        return self.members[0]

#    def all_like(self, whom):
#        ''' Do everyone in this group like a person? '''
#        return all(p.will_date(whom) for p in self.people)
#
#    def all_liked_by(self, whom):
#        ''' Is everyone in this group liked by a person? '''
#        return all(whom.will_date(p) for p in self.people)
#
#    def any_like_all(self, other):
#        ''' Does anyone in this group like everyone in another group? '''
#        return any(other.all_liked_by(p)  for p in self.people)

    def any_match_someone(self, other):
        '''
        Does anyone in this group _mutually_ match someone in another group? (other is a RegRecord)
        Return the best match score for any members of self to someone in the other group
        '''
        return min(p.least_mutual_match_horror(other, self.ev) for p in self.cached_members)

    def all_match_someone(self, other):
        '''
        Does everyone in this group _mutually_ match someone in another group?
        Return the worst match score for any members of self to someone in the other group
        '''
        return max(p.least_mutual_match_horror(other, self.ev) for p in self.cached_members)


    @memoized_property
    def location_set(self):
        return describe.csv_to_set(self.location)

    @memoized_property
    def genders(self):
        return set(g for p in self.cached_members for g in p.gender_set)

    @memoized_property
    def seek_genders(self):
        return set(g for p in self.cached_members for g in p.seek_gender_set)

    def has_gender(self, g):
        return g in self.genders

    def wants_gender(self, g):
        return g in self.seek_genders


    @memoized_property
    def is_man(self):
        return self.has_gender('M') or self.has_gender("TM") or self.has_gender("CM")

    @memoized_property
    def is_woman(self):
        return self.has_gender('W') or self.has_gender("TW") or self.has_gender("CW")

    @memoized_property
    def is_man_only(self):
        return self.is_man and not self.is_woman

    @memoized_property
    def is_woman_only(self):
        return self.is_woman and not self.is_man

    @memoized_property
    def only_alt_gendered(self):
        return not (self.is_man or self.is_woman)

    @memoized_property
    def wants_mf(self):
        return self.wants_m and self.wants_f

    @memoized_property
    def wants_m(self):
        return self.wants_gender('M') or self.wants_gender('TM') or self.wants_gender('CM')

    @memoized_property
    def wants_f(self):
        return self.wants_gender('W') or self.wants_gender('TW') or self.wants_gender('CW')

    def mf_gender_match(self, other):
        """
        Return if there are overlapping genders (gayness)
        """
        return (self.is_man and other.is_man) or (self.is_woman and other.is_woman)

    def mf_gender_cross(self, other):
        return (self.is_man and other.is_woman) or (self.is_woman and other.is_man)


    def location_overlap(self, other):
        return bool(self.location_set & other.location_set)

    def will_date(self, other):
        return self.match_horror( other ) <= MATCH_THRESHOLD



    def match_horror_full(self, other, verbose=True ):
        """
        This is the core matching method.
        :param other: A RegRecord to see if we like.
        :return: Pair of (1) Number capturing how good the regrecord matches 'other' (i.e., how much we want them)
                and (2) explanation (vector of strings) for the score.
        """

        if other.is_staff and (not self.volunteers_ok):
            return MATCH_NO, ('volunteer', 'will not date staff')

        if other.is_group and (not self.seek_groups):
            return MATCH_NO, ('group', 'too groupy')

        horror = 0
        explain = []

        if self.is_group:
            # I'm a group: we need to focus on mutual matches so we don't get case of
            # one member of us likes 'other', and 'other' likes the other member of the group

            if self.groups_match_all:
                horror, explain = self.all_match_someone(other), ('group',)
            else:
                horror, explain = self.any_match_someone(other), ('group',)
        elif other.is_group:
            # I'm not a group, but they are

            if self.groups_match_all:
                worst_match = 0
                worst_reason = ()
                for o in other.cached_members:
                    match, reason = self.indiv.match_horror_full(o, self.ev, verbose)
                    if match >= worst_match:
                        worst_match = match
                        worst_reason = reason
                horror, explain = worst_match, worst_reason
            else:
                best_match = 2*MATCH_NO
                best_reason = ()
                for o in other.cached_members:
                    match, reason = self.indiv.match_horror_full(o, self.ev, verbose)
                    if match < best_match:
                        best_match = match
                        best_reason= reason
                # if they can't date anyone, arbitrarily give the reason of the
                # closest person they don't match
                horror, explain = best_match, best_reason
        else:
            # Individual-individual matching
            horror, explain = self.indiv.match_horror_full(other.indiv, self.ev, verbose)

        if not type(horror) is int:
            import ipdb;
            ipdb.set_trace()

        # Location is a RegRecord level match question.
        if self.location_overlap(other):
            horror -= 10

        # TODO: Why is this here?
        if self.is_group and self.groups_match_all and not other.is_group:
            horror -= 3

        return horror, explain

    def match_horror(self, other, verbose=True ):
        return self.match_horror_full(other, verbose)[0]



    @memoized_property
    def treat_as_man(self):
        return self.is_man

    @memoized_property
    def treat_as_woman(self):
        return not self.treat_as_man


    @memoized_property
    def straightish_male(self):
        #return self.is_man and not self.wants_gender('CM')
        return self.is_man_only and not self.wants_gender('CM')

    @memoized_property
    def is_NMSMSS(self):
        """
        Is this someone who _could_ be flagged as NMSMSS?  (This does not say they are so flagged.)
        :return: True or False
        """
        return self.is_man and not self.wants_m


    @memoized_property
    def flagged_NMSMSS(self):
        """
        Has unit been flagged as needing companion?
        """
        nts = self.notes.upper()
        if "!NEED COMPANION!" in nts:
            return True
        return False

    def ok_gay_match(self, other):
        """ Return true if person is not bi or the match would be a "gay" match"""
        if not self.wants_mf:
            return True
        return (self.treat_as_woman and other.treat_as_woman) or \
               (self.treat_as_man and other.treat_as_man)


    def ok_str_match(self, other):
       if not self.wants_mf:
            return True
       return (self.treat_as_woman and other.treat_as_man) or \
               (self.treat_as_man and other.treat_as_woman)


#     def matrix_score(self, other, matrix_type):
#         if ( matrix_type == 'gay' and not self.ok_gay_match( other ) ) \
#            or ( matrix_type == 'str' and not self.ok_str_match( other ) ):
#             return 0
#
#         return self.interest_score(other)
#
#     def ok_match(self, other, matrix_type ):
#         return self.matrix_score(other,matrix_type) > 0

    def all_past_dates(self, exclude_event=None):
        """ Return all past dates person has had (possibly excluding some specified event) """
        if exclude_event == None:
            drs = DateRecord.objects.filter(psdid=self.psdid)
        else:
            drs = DateRecord.objects.filter(psdid=self.psdid).exclude( event=exclude_event )
        drids = set(c.other_psdid for c in drs)

        return drids

#    def all_additionals_old(self):
#        """ Return list of all additional folks to not date"""
#        from django.db import connection, transaction
#        cursor = connection.cursor()
#
#        cursor.execute("SELECT MatchA,MatchB from additionals WHERE MatchA=%s OR MatchB=%s", [self.psdid, self.psdid] )
#        psdids = cursor.fetchall()
#        psdids = set(c[c[0]==self.psdid] for c in psdids)
#        return psdids

    def all_additionals(self):
        """
        Return list of all additional folks to not date (from breakrecords)
        """
        drs = BreakRecord.objects.filter( psdid=self.psdid )
        drids = set(c.other_psdid for c in drs)

        odrs = BreakRecord.objects.filter(other_psdid=self.psdid)
        drids ^= set(c.psdid for c in odrs)

        return drids

    @memoized_property
    def namestring(self):
        pnames = ', '.join( c.fullname for c in self.members )
        return self.nickname + ": " + pnames

    @memoized_property
    def firstnames(self):
        pnames = ' & '.join( c.first_name for c in self.members )
        return pnames

    def geekcode(self):
        return describe.rr_geekcode(self, False, self.ev )

    def minicode(self, no_look=False, no_extra=False):
        return describe.rr_minicode(self, no_look, no_extra)

    def htmlcode(self):
        return describe.rr_geekcode(self, True, self.ev )

    def registration_flag(self):
        """
        Flag to put up in the check-in list, if any
        """
        flg = []
        if self.matches <= 4:
            flg.append( "LOW" )

        nts = self.notes.upper()
        if "DRINK" in nts:
            flg.append( "DRINK" )
        if "SEE ME" in nts or "FLAG" in nts or "CHECK" in nts:
            flg.append( "CHECK" )
        if "!NEED COMPANION!" in nts:
            flg.append( "SSM" )
        if "!" in nts and not "!NEED COMPANION!" in nts:
            flg.append( "READ" )

        return ",".join( flg )



    def get_matches(self):
        """
        Get list of all matches for this regrecord
        """
        liked = set( [r.psdid1 for r in MatchRecord.objects.filter( event=self.event, psdid2=self.psdid ) ])
        matches = MatchRecord.objects.filter( event=self.event, psdid1= self.psdid ).order_by('psdid2')

        for m in matches:
            try:
                p2 = RegRecord.objects.get( psdid=m.psdid2, event=self.event )
                m.namestring = p2.namestring
                m.mutual = m.psdid2 in liked
            except:
                logger.error( "Failed to find the RegRecord for '%s-%s'" % (self.event, m.psdid2 ) )
                m.namestring = "[Error: Failed to Find]"

        return matches



    def get_date_sheet(self):
        """
        Get sequence of dates for this regrecord
        Used for printing to django templates

        Returns list of dictionaries corresponding to dates
        """
        print "Getting date schedule for %s at %s" % (self.psdid, self.event )
        dates = DateRecord.objects.filter( event=self.event, psdid=self.psdid ).order_by('round')

        gots = [x.round for x in dates]
        if len(gots) > 0:
            mx = max( gots )
            miss = set( range(1,mx+1)).difference(gots)

            datedict = {}

            for d in dates:
                d.other_person = fetch_regrecord( self.event, d.other_psdid )
                if not d.other_person == None:
                    d.other_code = d.other_person.minicode()
                else:
                    d.other_code = "missing person"

                d.match = fetch_matchrecord( d.psdid, d.other_psdid, self.event )
                datedict[ d.round ] = d

            for rnd in miss:
                datedict[ rnd ] = { 'round':rnd, 'other_person':"no date", 'other_code':"" }

            dates = [ datedict[x] for x in range(1,mx+1) ]
        else:
            print "No found dates"
            dates = []

        return dates






