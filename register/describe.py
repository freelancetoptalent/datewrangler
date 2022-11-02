"""
Generate human-readable descriptions of the RegRecord objects.

There are two types of description.  One is the longer description that reads sort of like a personal ad.
The second is a "geekcode" which is a more cryptic, short string.
"""

import sys

from string import lower

from register.psdcheckbox import get_preference_for
#from register.models import MatchQuestion
# TODO: How to import this?
from django.utils.safestring import mark_safe

import logging
logger = logging.getLogger('register.models')


def csv_to_set(s):
    """
    >>> csv_to_set('a,b')
    set(['a', 'b'])
    >>> csv_to_set('')
    set([])
    """
    return set(s.split(',') if s else [])



def hasCisTransAndGeneral(gs):
    """
    This checks the full gender set 'gs' to see if we have Cis and Trans categories for
    both men and women AS WELL AS the general category.
    True means we have Cis, Trans, and General.  False means we do not.
    Will give warning if coding is inconsistent.
    """
    gs = dict( gs )
    if "CW" in gs and "TW" in gs and "W" in gs:
        if "CM" in gs and "TM" in gs and "M" in gs:
            # Only if both sides have all three do we say yes
            return True
        else:
            logger.error( "Inconsistent cis-trans flags in gender MatchQuestion configuration" )
    else:
        if "CM" in gs and "TM" in gs and "M" in gs:
            logger.error( "Inconsistent cis-trans flags in gender MatchQuestion configuration" )
    return False


def isVagueM( person ):
    """
    If we have general gender, can we say if the person is specifically cis or trans?
    """
    p = person.gender_set
    if "M" in p:
        if not ("CM" in p) and not ("TM" in p):
            return True
    if "CM" in p and "TM" in p:
        if not "M" in p:
            return True
    return False


def isVagueW( person ):
    """
    If we have general gender, can we say if the person is specifically cis or trans?
    """
    p = person.gender_set
    if "W" in p:
        if not ("CW" in p) and not ("TW" in p):
            return True
    if "CW" in p and "TW" in p:
        if not "W" in p:
            return True
    return False

def augmentGenderOptions( person, genderOpts ):
    if not isinstance( genderOpts, dict ):
        genderOpts = dict( genderOpts )
    if isVagueM( person ):
        genderOpts["M"] = "men (including trans and cis men)"
    if isVagueW( person ):
        genderOpts["W"] = "women (including trans and cis women)"
    return genderOpts



##
## Auto-gen sentence clause for matches
##

def getReadableStringFromMatchQuestion(obj, match_question, tagFunction, conjunction="and"):
    """
    tagFunction is a function that takes a matchchoice code and returns boolean value of whether
    'obj' has checked that box or not.  E.g., atLoc.

    It can also take a function that returns a 0,1,2 weight, in which case the 2 weights
    are marked with a "*" to denote extra interest.  E.g., prefG

    match_question is a list of code-text pairs or a dictionary of the code->text

    """


    if isinstance( match_question, dict ):
        match_question = match_question.items()

    match_question = list(match_question)

    def is_na(x):
        return x[0] == 'NA'

    match_question.sort(key=is_na)

    hits = []
    for k, text in match_question:
        val = tagFunction( obj, k )
        if val == 2:
            hits.append( text + "*" )
        elif val:
            hits.append( text )


    if len(hits) == 0:
        return ""
    elif len(hits) == 1:
        return hits[0]
    elif len(hits) == 2:
        return hits[0] + " " + conjunction + " " + hits[1]
    else:
        ss = hits[0]
        for lo in hits[1:-1]:
            ss = ss + ", " + lo

        ss = ss + ", " + conjunction + " " + hits[-1]

        return ss




def getReadableStringFromTextResponse( mrlist , conjunction="and"):
    """
    mflist is a dict of strings to MatchFeatures
    """
    #print mrlist

    hits = mrlist

    if len(hits) == 0:
        return ""
    elif len(hits) == 1:
        return hits[0]
    elif len(hits) == 2:
        return hits[0] + " " + conjunction + " " + hits[1]
    else:
        ss = hits[0]
        for lo in hits[1:-1]:
            ss = ss + ", " + lo

        ss = ss + ", " + conjunction + " " + hits[-1]

        return ss





def isG(p, gen):
    """
    Check if Person p is of given gender
    """
    if gen in csv_to_set(p.gender):
        return True
    else:
        return False


def lookG(p, gen):
    gs = p.seek_gender_set
    if gen in gs:
        return True
    else:
        return False



def atLoc(rr, loc):
    """
    Is RegRecord rr interested in dating at location loc (a code)
    """
    gs = csv_to_set(rr.location)
    if loc in gs:
        return True
    else:
        return False




def prefG(p, gen):
    return get_preference_for(p.seek_gender, gen) > 1

def genderDesc(p):
    try:
        gops = p.genderOptions()

        ss = getReadableStringFromMatchQuestion(p, gops, isG)
        if ss == "":
            return "No preference given (so anyone could match)"
        else:
            return ss.strip()

    except Exception as inst:
        logger.error( "Caught error" )
        logger.error( str(inst) )
        logger.error( "ouch" )

    return "FAILED in genderDesc()"




def genderLookDesc(p):
    try:
        gops = p.genderOptions()
        ## cis-trans hack
        if hasCisTransAndGeneral(gops):
            gops = augmentGenderOptions( p, gops )
        ss = getReadableStringFromMatchQuestion( p, gops, lookG, conjunction="and/or" )
        if ss == "":
            return "nothing (which will prevent all matches)"
        else:
            return ss
        return ss.strip()
    except Exception as inst:
        logger.error( "Caught error in genderLookDesc" )
        logger.error( str(inst) )
        logger.error( "ouch" )

    return "FAILED in genderLookDesc()"



def genderPrefDesc(p):
    try:
        ## cis-trans hack
        gops = p.genderOptions()
        ss = getReadableStringFromMatchQuestion(p, gops, prefG, conjunction="and")
        if ss == "":
            return ""
        else:
            return ss
        return ss.strip()
    except Exception as inst:
        logger.error( "Caught error" )
        logger.error( str(inst) )
        logger.error( "ouch" )

    return "FAILED in genderPrefDesc()"





def minicode( p, no_look = False ):
    """Short string to describe person's dating characteristics"""
    s = str(p.age) + ' ' + p.gender.replace(",","/")
    if not no_look:
        s = s + "->" + str(p.seek_age_min) + "-" + str(p.seek_age_max)\
                     + ' ' + p.seek_gender.replace(",","/")
    return s #.tolower()


def extra_question_minicode( question, p, no_look=False ):
    respobj = p.response_for(question=question)
    if not respobj is None:
        my_resp = [x.choice_code for x in respobj.cached_answers]
        my_seek = [x.choice_code for x in respobj.cached_seek]
    else:
        my_resp = []
        my_seek = []
    s = question.question_code + ":" + "/".join( my_resp )
    if not no_look:
        s += "->" + "/".join( my_seek )
    return s


def minicodeextra(p, event, bracket=False, no_look=False ):
    """
    Return string for all extra questions for the event for the given person p

    Will always return a string, but possibly an empty one if no extra
    questions exist.
    """
    questions = [x for x in event.cached_extra_questions]
    if questions:
        ss = ";\t ".join( extra_question_minicode( q, p, no_look ) for q in questions)
        if bracket:
            return " [" + ss + "]"
        else:
            return ss
    else:
        return ""


def conjunction_fragment( my_resp, conj="and" ):
    if len(my_resp) == 0:
        return None
    elif len(my_resp) == 1:
        return str( my_resp[0] )
    elif len(my_resp) == 2:
        return str( my_resp[0] ) + " " + conj + " " + str( my_resp[1] )
    else:
        frg = ', '.join( [str(x) for x in my_resp[:-1] ] )
        return frg + ", " + conj + " " + str(my_resp[-1])


def extra_question_code_nameless( question, p ):
    """
    Generate extra question string _without_ using the name of the question.
    """
    respobj = p.response_for(question=question)
    if not respobj is None:
        my_resp = [x for x in respobj.cached_answers]
        my_seek = [x for x in respobj.cached_seek]
    else:
        my_resp = []
        my_seek = []
    ident = conjunction_fragment(my_resp, "and" )

    if not question.ask_about_seek:
        if ident is None:
            return ''
        else:
            return 'You said %s.' % ( ident, )

    if not ident is None:
        if question.hard_match:
            frag2 = "that your dates be open to dating %s" % (ident, )
        else:
            frag2 = "your dates to be looking for %s" % (ident, )

    look = conjunction_fragment(my_seek, "and" )

    if ident is None and look is None:
        return ''

    if look is None:
        if question.hard_match:
            frag3 = "were not open to any of these things."
        else:
            frag3 = "expressed no preferences in what you were looking for."
    else:
        if question.hard_match:
            frag3 = "said you were open to dating %s." % (look, )
        else:
            frag3 = "want to be matched with %s." % (look, )

    if ident is None:
        if question.hard_match:
            return 'You made no constraints on what people be open to.  You %s' % ( question.question, frag3 )
        else:
            return 'You %s' % ( frag3 )
    else:
        if question.hard_match:
            return 'You require %s.  You %s' % ( frag2, frag3 )
        else:
            return 'You want %s.  You %s' % ( frag2, frag3 )




def extra_question_code_YN( question, p ):
    """
    This renders YN questions where people say they are or are not something, and whether they will date those who
    are, are not or are both.

    NOTE: a missing answer means "NO"
    """

    respobj = p.response_for(question=question)

    choices = question.choices
    yes_choice = question.yes_choice
    no_choice =  question.no_choice

    if not respobj is None:
        my_resp = [x for x in respobj.cached_answers]
        my_seek = [x for x in respobj.cached_seek]
    else:
        my_resp = []
        my_seek = []

    did_answer = len(my_resp) > 0
    said_yes = False
    if did_answer and my_resp[0].id == yes_choice.id:
        resp_string = "checked the box"
        said_yes = True
    else:
        resp_string = "didn't check the box"
        said_yes = False

    if not question.ask_about_seek:
        if question.yes_only:
            if said_yes:
                return 'Regarding %s, you checked the box (and will be preferentially matched to others who also checked the box).' % ( question.question, )
            else:
                return "Regarding %s, you didn't check the box." % ( question.question, )
        return 'Regarding %s, you said %s (and will date only those who said %s).' % ( question.question, resp_string, resp_string,  )

    if len(my_seek) == 0:
        frag2 = "and didn't indicate what you felt about others"
    elif my_seek[0].id == yes_choice.id:
        frag2 = "and strongly prefer to date those who checked the box"
    elif no_choice and my_seek[0].id == no_choice.id:
        frag2 = "and strongly prefer to date those who did not check the box"
    else:
        frag2 = "and expressed no preference for others' responses"

    return 'Regarding %s, you %s, %s.' % ( question.question, resp_string, frag2 )





def text_consent_response( p ):
    """
    For the tag consent question

    NOTE: a missing answer means "NO"
    """

    respobj = p.response_for(question="tagconsent")
    if respobj is None:
        return "You have not opted out of your dates seeing any matching free-text words you have between you."
    elif respobj.said_yes:
        return "You are okay with your dates seeing any matching free-text words you have between you."
    else:
        return "You are NOT okay with your dates seeing any matching free-text words you have between you."



def extra_question_code( question, p ):

    if question.question_code == "tagconsent":
        return "ERROR: tagconsent question treated as extra question."

    if question.isYN:
        return extra_question_code_YN( question, p )

    if not question.include_name:
        return extra_question_code_nameless( question, p )

    respobj = p.response_for(question=question)
    if not respobj is None:
        my_resp = [x for x in respobj.cached_answers]
        my_seek = [x for x in respobj.cached_seek]
    else:
        my_resp = []
        my_seek = []
    ident = conjunction_fragment(my_resp, "and" )

    if not question.ask_about_seek:
        if ident is None:
            return 'Regarding %s, you said nothing.' % ( question.question, )
        else:
            return 'Regarding %s, you said %s.' % ( question.question, ident )

    if not ident is None:
        if question.hard_match:
            frag2 = "that your dates be open to dating %s" % (ident, )
        else:
            frag2 = "your dates to want %s" % (ident, )

    look = conjunction_fragment(my_seek, "and" )

    if ident is None and look is None:
        return 'Regarding %s, you did not check off any options.' % (question.question, )

    if look is None:
        if question.hard_match:
            frag3 = "were not open to any of these things."
        else:
            frag3 = "expressed no preferences in what you were looking for."
    else:
        if question.hard_match:
            frag3 = "said you were open to dating %s." % (look, )
        else:
            frag3 = "prefer to be matched with %s." % (look, )

    if ident is None:
        if question.hard_match:
            return 'Regarding %s, you made no constraints on what people be open to.  You %s' % ( question.question, frag3 )
        else:
            return 'Regarding %s, you %s' % ( question.question, frag3 )
    else:
        if question.hard_match:
            return 'Regarding %s, you require %s.  You %s' % ( question.question, frag2, frag3 )
        else:
            return 'Regarding %s, you prefer %s.  You %s' % ( question.question, frag2, frag3 )


def extra_question_paragraph( p, event, sep ):
    questions = [x for x in event.cached_extra_questions if not x.question_code == "tagconsent" ]
    if questions:
        return sep.join( extra_question_code( q, p ) for q in questions)
    else:
        return None


def text_geek_code( tr, sep ):
    """
    Give nice english text for tr, a text response object
    """
    id_as = getReadableStringFromTextResponse( tr.ident_string_list(), "and" )
    seek = getReadableStringFromTextResponse( tr.seek_string_list(), "and" )
    txt = ""
    if len(id_as) > 0 and len(seek) > 0:
        txt = "You identify as: " + id_as + "." + sep + "You're seeking: " + seek + "."
    elif len(id_as) > 0:
        txt = "You are not specifically seeking anything but you identify as: " + id_as + "."
    elif len(seek) > 0:
        txt = "You didn't indicate that you identify as anything but you're seeking: " + seek + "."
    return txt



def geekcode(p, asGroupMember=True, html=False, event=None):
    """
    p is Person object

    Generates a personal description of the given person.
    """
    if asGroupMember:
        sep = '  '
    else:
        sep = '<p><p>' if html else '\n\n'

    try:
        s = ""
        if p.pronoun_slug == "":
            #s = "a %s year old (no given pronouns)" % (p.age, )
            s = "a %s year old" % (p.age, )
        else:
            s = "a %s year old (%s pronouns)" % (p.age, p.pronoun_slug, )

        s += " looking for " + str(p.seek_age_min) + "-" + str(p.seek_age_max) + " yr old"

        s += " " + genderLookDesc(p)

        s += "."
        gp = genderPrefDesc(p)
        if ( len(gp) > 0 ):
            gp = gp[0].capitalize() + gp[1:]
            s += "  " + gp + " are preferred."

        s += sep + "Your dates must be willing to date all of the following: " + genderDesc(p) + "."


        if event != None:
            ext = extra_question_paragraph( p, event, sep )
            if ext != None:
                s += sep + ext

        tgc = text_geek_code( p.my_text_answer, sep )
        if tgc != None and len(tgc) > 0:
            s += sep + tgc + sep + text_consent_response(p)

        print "Got geekcode %s\n" % (s, )

        return s
    except Exception as inst:
            import traceback
            traceback.print_exc()
            logger.error( "Unexpected error:", sys.exc_info()[0] )
            logger.error( "%s\n%s\n%s" % ( type(inst), inst.args, inst ) )
            logger.error( "geekcode() for person failed" )
            return "some person or other (ERROR)"




def rr_minicode(rr, no_look=False, no_extra=False):
    """Short string to describe record's dating characteristics
    param no_look  True means drop what person is _looking_ for
    param no_extra True means drop extra question stuff
    """

    if not rr.is_group:
        s = minicode(rr.indiv, no_look=no_look)
    else:
        s = "GRP"
        peeps = rr.members
        for p in peeps[0:]:
                s += "; " + minicode(p, no_look=no_look)
                if not no_extra:
                    s += minicodeextra(peeps[0], rr.ev,bracket=True)

        if not no_look:
            if True:
            #if rr.groups_match_all:
                s += "-all"

    if not no_look:
        if not rr.seek_groups:
            s += ""
        #elif rr.groups_match_all:
        elif True:
            s += "-all"
        else:
            s += "-any"

        if rr.friend_dates:
            s += "-F"

        if rr.stationary:
            s += "(S)"

    #    s += ' loc=' + rr.location.replace(",","/")
    if not no_extra:
        if not rr.is_group:
            ext = minicodeextra(rr.indiv, rr.ev, no_look=no_look)
            if not (ext is None):
                s += " " + ext

    return s


def rr_geekcode(rr, html=False, event=None ):
    """
    Generate a several-line string describing a RegRecord rr.  These read like long personal ads.
    """
    try:
        numPeeps = rr.size

        if not rr.is_group:
            s = "You are " + geekcode(rr.indiv, False, html, event)
        else:
            peeps = rr.members
            s = "You all are a group of the following " + str(numPeeps) + " people:\n1) " + geekcode(peeps[0], True, html, event )
            for (k,p) in enumerate( peeps[1:] ):
                    s += "\n%s) %s" % (k+2, geekcode(p, True, html, event))

            #if not rr.groups_match_all:
            #    s += "\n\nHaving dates that match only one of you is fine."
            #else:
            #    s += "\n\nDates must be compatible with all of you."

        s += "\n\n"

        if not rr.seek_groups:
            s += "You are not interested in dating groups."
        #elif rr.groups_match_all:
        elif True:
            if numPeeps > 1:
                s += "You are interested in dating groups if everyone in each group is compatible with someone in the other group."
            else:
                s += "You are interested in dating groups if you match everyone in the group."
        else:
            s += "You are interested in dating groups if you match at least one person in the group."

        if rr.friend_dates:
            s += "  Friendship dates are okay."
        else:
            s += "  You do not want friendship dates."

        if rr.stationary:
            s += "  During dating, you need to stay in the same spot as much as possible."

        try:
            ss = getReadableStringFromMatchQuestion( rr, rr.locationOptions(), atLoc, conjunction="or" )
            if ss == "":
                s += "  No location match preferences given."
            else:
                s += "  We will try to match you with people from " + ss + "."
        except Exception as inst:
            logger.error( "Unexpected error: %s\n%s\n%s\n%s" % ( sys.exc_info()[0], type(inst), inst.args, inst ) )
            s += "  From (location lookup fail)"
        except:
            logger.error( "Really weird error --- help!" )

        if rr.volunteers_ok:
            s += "  You consent to be on dates with volunteers and staff."
        else:
            s += "  You did not consent to be on dates with volunteers and staff."
            
        if html:
            return s.replace( "\n", "<p>" )
        else:
            return mark_safe(s)
    except:
        logger.error( "rr_geekcode() regrecord failed" )
        return "error-some dating group or other"



    #    def pronoun(g):
#        if not isinstance(g, list):
#            g = g.split(',')
#        if 'Q' in g or ('M' in g and 'W' in g) or ('TM' in g and 'TW' in g): return "Zie"
#        elif 'TM' in g: return "He"
#        elif 'TW' in g: return "She"
#        elif 'M' in g: return "He"
#        elif 'W' in g: return "She"
#        else: return "Zie"
#        ## This last case should be impossible, but...


