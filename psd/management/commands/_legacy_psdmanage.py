import sys


from datetime import datetime, time

from django.core.management import setup_environ
from django.core.mail import mail_managers
from django.core.management import setup_environ

import settings
setup_environ(settings)

from django.forms.formsets import formset_factory
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.models import UserManager, User
from django.contrib.auth import login, authenticate

from psd import RcodeHooks
from psd.matchmaker import date_scheduler
from psd.matchmaker import table_matcher
from psd.register.models import *
from psd.matchmaker.matrix_maker import updateMatchRecords
from psd.matchmaker.models import MatchRecord

import debugtools as dt
from psd.matchmaker import explain


def emailReminder( rr, event ):
    if rr.matches < 5:
        rr.flagged = True
    else:
        rr.flagged = False
    email_body = render_to_response( 'email/email_reminder.txt',
                                         {'rr' : rr , 'event':event } )
    user = User.objects.get( username=rr.psdid )

    user.email_user( "PSD Tomorrow! Reminder for %s" % (rr.psdid,), email_body.content )
    #print email_body.content
    print "Email sent to %s at %s!" % (user.username, user.email,)


def emailNoPay( rr, event ):
    email_body = render_to_response( 'email/email_nopay.txt',
                                         {'rr' : rr , 'event':event } )
    user = User.objects.get( username=rr.psdid )

    user.email_user( "PSD Payment Question Regarding %s." % (rr.psdid,), email_body.content )
    print "Email sent to %s at %s!" % (user.username, user.email,)


def emailReminders( event_name ):
    regs = RegRecord.objects.filter( event=event_name )
    event = Event.objects.get( event=event_name )
    for r in regs:
        if not r.cancelled and not "!DEMOG!" in r.notes and not "!NO PAY!" in r.notes:
            emailReminder( r, event )


def testEmail( to_whom ):
    print "Test Email to %s" % (to_whom,)
    regs = RegRecord.objects.filter( psdid=to_whom )
    regs = regs[0]
    print "Going to send: %s for event %s" % (regs, regs.ev)
    emailReminder( regs, regs.ev )





def listIDInfo( event_name ):
    regs = RegRecord.objects.filter( event=event_name ).order_by( 'psdid' )
    cntr = 1

    for r in regs:
        if not r.cancelled:
            print "%s\t%s\t%s" % ( cntr, r.psdid, r.namestring )
            cntr = cntr+1



def listNoPay( event_name ):
    regs = RegRecord.objects.filter( event=event_name )
    event = Event.objects.get( event=event_name )
    flaggedregs = []
    for r in regs:
        if not r.cancelled and not r.paid and not r.pending:
            print "\n**********************************************\n%s\n\t%s\n\tcomments: %s\n\treferral %s\n\tnotes: %s\n" %( str(r), r.geekcode(), r.comments, r.referred_by, r.notes )
            print "<enter> to flag email, [S] to skip, or mark as [P]aid or [W]ill Pay (Pending)?\n> ",
            s = sys.stdin.readline()
            s = s.strip().upper()
            if s == "S":
                print "Skipped!"
            elif s == "W":
                r.pending = True
                r.save()
            elif s == "P":
                r.paid = True
                r.save()
            else:
                flaggedregs.append( r )
                print "Appending %s to list and adding note to file" % (r.email,)
                if not "!NO PAY!" in r.notes:
                    r.addNote( "!NO PAY! (Flag as not having made pay arrangements)" )
                r.save()
                s = ""

    for fr in flaggedregs:
        print fr.email
    print "Email list above?\n> ",
    s = sys.stdin.readline( )
    s = s.strip().upper()
    if ( s == "Y" ):
        for fr in flaggedregs:
            emailNoPay( fr, event )



def listStraightMales( event, cut_id=339 ):
    regs = RegRecord.objects.filter( event=event, id__gte=cut_id )
    emails = []
    print "Going to search through the %s reg forms" % (len(regs), )
    for r in regs:
        if "!Need companion!" in r.notes:
            print "%s\n\t%s\n\tcomments: %s\n\treferral %s\n\tnotes: %s\n" %( str(r), r.geekcode(), r.comments, r.referred_by, r.notes )
            print "Check PSDID  (or [F]flag email)?\n> ",
            s = sys.stdin.readline()
            s = s.strip().upper()
            while s!="":
                if s == "F":
                     emails.append( r.email )
                     print "Appending %s to list and adding note to file" % (r.email,)
                     r.addNote( "!DEMOG! (Flag as not-balanced demographic)" )
                     r.save()
                     s = ""
                else:
                    print "Looking for '%s'" % (s, )
                    r2 = RegRecord.objects.filter( psdid=s )
                    print "Found: ", r2
                    for rr in r2:
                        print "%s: %s\nref:\t%s\n\tnotes: %s" % (rr.psdid, rr.comments, rr.referred_by, rr.notes )
                    print "Check PSDID  (or [F]flag email)?\n> ",
                    s = sys.stdin.readline()
                    s = s.strip().upper()
    print "Email of non-balanced folks"
    for em in emails:
        print em


def makeMatrix( event_name ):
    try:
        event = Event.objects.get( event=event_name )
    except Event.DoesNotExist:
        print "Failed to obtain event object '%s'" % (event_name, )
        return

    res = updateMatchRecords(event, verbose=True)
    print( "Results of makeMatrix: %s\n" % (res, ) )




def name_generator(first_name, last_name):
    import random
    mem = ["ag","erf","ook","unly","astor","uncle"]
    #color = ["Red","Blue","Black","White","Orange","Green","Yellow","Purple"]
    tool = ["age","icky","arn","ettle","ragon","olf","ummingbird"]
    randomNumber1 = random.randrange(0,len(mem))
    randomNumber2 = random.randrange(0,len(tool))
    #name = color[randomNumber1] + " " + tool[randomNumber2]
    return (first_name[0]+mem[randomNumber1],last_name[0]+tool[randomNumber2])



def cleanDatabase():
    print( "Wiping peoples names" )
    obj = Person.objects.all()
    for p in obj:
        if len(p.psdid) > 1:
            (p.first_name, p.last_name) = name_generator(p.psdid[0], p.psdid[1])
        else:
            print "Weird record ", p, "# '", p.psdid, "'"
            (p.first_name, p.last_name) = name_generator("X","X")
        p.save()


    print( "Wiping regrecord nicknames and emails" )
    obj = RegRecord.objects.all()
    for r in obj:
        r.nickname = r.minicode()
        r.email = "PSD_" + r.psdid + "@" + "vzvz.org"
        if r.referred_by != "":
            r.referred_by = "someone"
        if r.comments != "":
            r.comments = "some comments"
        if r.notes != "":
            r.notes = "some admin notes"
        r.save()

    print( "Wiping user emails" )
    obj = User.objects.all()
    for u in obj:
        u.email = "PSD" + u.username + "@" + "vzvz.org"
        u.save()

    from django.db import connection, transaction
    cursor = connection.cursor()

    print( "Wiping admin logs table" )
    cursor.execute("DELETE FROM django_admin_log" )
    transaction.commit_unless_managed()

    print( "Wiping django_session table" )
    cursor.execute( "DELETE FROM django_session" )
    transaction.commit_unless_managed()


def clearMatchQuestion( question_code, verbose=True ):
    ques = MatchQuestion.objects.filter( question_code=question_code )
    if len(ques) > 0:
        print( "Going to remove old Match Question '%s'" % (question_code, ) )
        for q in ques:
            q.delete()
#    else:
#        if verbose:
#            print( "Initializing new question '%s'" % (question_code,) )




def checkOrganization():
    # Make Organization object if there isn't one
    orgs = Organization.objects.all()
    if len( orgs ) == 0:
        print "Making new organization objects and updating sites to use them"
        sites = Site.objects.all()
        for asite in sites:
            org = Organization( site=asite, info_email="error@needorganizationset.com",
                            mailing_list_url="no mailing list found. need organization set",
                            homepage_url="no home page found. need organization set")
            org.save()
            print( "Making organization %s for site %s" % (org, asite) )
            print( "   Be sure to update in Organization in the admin interface" )

    else:
        print "%s organization objects found." % (len(orgs),)

    print "Checking Site IDS"
    sites = Site.objects.all()
    for asite in sites:
        if asite.id != settings.SITE_ID:
            print( "WARNING: Site '%s' is found.  SITE_ID in settings.py should be set to '%s' to correspond with this site." % (asite, asite.id), )
        else:
            print( "Site %s corresponds to SITE_ID %s in settings.py" % (asite, asite.id ) )


def setupExtraQuestions(evt=None, do_quest=None ):
    """
    Make new questions.  Add to event if evt is not none.
    Warning: will erase old questions of same name.
    """

def setupMatchQuestions(do_quest = None, verbose=True, trigender=False ):

    if do_quest is None or "location" in do_quest:
        clearMatchQuestion( "location", verbose )
        loc = MatchQuestion( question="Location" )
        loc.checkbox = True
        loc.explanation="Locations willing to meet folks."
        loc.internal_comment = "Warning: Do not select as extra question.  Also, most flags will not impact system."
        loc.question_code = "location"
        loc.save()
        loc.matchchoice_set.create( choice="Somewhere Else", choice_code="SE" )
        loc.matchchoice_set.create( choice="Unknown", choice_code="UK" )
        loc.save()


    if do_quest is None or "gender" in do_quest:
        clearMatchQuestion( "gender" )
        gen = MatchQuestion( question="Gender" )
        gen.ask_about_seek = True
        gen.checkbox = True
        gen.hard_match = True
        gen.question_code = "gender"
        gen.strict_subset_match = True
        gen.allow_preferences = True
        gen.explanation = "Gender/Identity core matching question."
        gen.internal_comment = "Gender default question.  Do not select as extra question.  Also, most flags will not impact system."
        gen.save()
        if trigender:
            gen.matchchoice_set.create( choice="women", choice_code="W" )
            gen.matchchoice_set.create( choice="men", choice_code="M" )
        gen.matchchoice_set.create( choice="trans women", choice_code="TW" )
        gen.matchchoice_set.create( choice="trans men", choice_code="TM" )
        gen.matchchoice_set.create( choice="cis women", choice_code="CW" )
        gen.matchchoice_set.create( choice="cis men", choice_code="CM" )
        gen.matchchoice_set.create( choice="genderqueer, genderfluid, or gender bending people", choice_code="GQ" )
        #gen.matchchoice_set.create( choice="butch people", choice_code="BU" )
        #gen.matchchoice_set.create( choice="androgynous people", choice_code="AN" )
        #gen.matchchoice_set.create( choice="femme people", choice_code="FE" )
        #gen.matchchoice_set.create( choice="queer people", choice_code="Q" )
        gen.matchchoice_set.create( choice="people who prefer to not be categorized or cannot be categorized by the above", choice_code="NA" )
        gen.save()

    if do_quest is None or "kinky" in do_quest:
        clearMatchQuestion( "kinky" )
        kink = MatchQuestion( question="the Kinky Question" )
        kink.question_code = "kinky"
        kink.explanation = "Do you identify as kinky and are you wanting to date kinky people?"
        kink.ask_about_seek = True
        kink.internal_comment = "Whether folks are kinky or not."
        kink.checkbox = True
        kink.is_YN = True
        kink.hard_match = False
        kink.include_name = True
        kink.hard_match = True
        kink.strict_subset_match = False

        kink.save()
        kink.matchchoice_set.create( choice="I strongly prefer dates with kinky people", choice_code="K" )
        kink.matchchoice_set.create( choice="I strongly prefer dates with non-kinky people", choice_code="NK" )
        kink.matchchoice_set.create( choice="I have no strong preference", choice_code="EI" )
        kink.save()

    if do_quest is None or "primary" in do_quest:
        clearMatchQuestion( "primary" )
        kink = MatchQuestion( question="the Primary Question", question_code="primary", ask_about_seek=True )
        kink.explanation = "I am not currently in a primary relationship, but potentially interested in one."
        kink.checkbox = True
        kink.is_YN = True
        kink.hard_match = False
        kink.include_name = True
        kink.hard_match = True
        kink.strict_subset_match = False
        kink.save()
        kink.matchchoice_set.create( choice="I strongly prefer being matched with those open to forming a primary relationship", choice_code="P" )
        kink.matchchoice_set.create( choice="I strongly prefer not being matched with those looking for primary relationships", choice_code="NP" )
        kink.matchchoice_set.create( choice="I have no strong preference", choice_code="EI" )
        kink.save()

    if do_quest is None or "identity" in do_quest:
        clearMatchQuestion( "identity" )
        if verbose:
            print "Making the identity question"
        petsQ = MatchQuestion( question="the Identity Question", question_code="identity",ask_about_seek=True )
        petsQ.checkbox = True
        petsQ.hard_match = False
        petsQ.explanation = "What, if anything, do you prefer in your matches, and how do you identify?  (This question is optional and these are preferences, not hard constraints.)"
        petsQ.internal_comment = "For soft-match tweaking on identity."
        petsQ.strict_subset_match = False
        petsQ.question_code = "identity"
        petsQ.save()
        petsQ.matchchoice_set.create( choice="butch people", choice_code="BU" )
        petsQ.matchchoice_set.create( choice="femme people", choice_code="FE" )
        petsQ.matchchoice_set.create( choice="androgynous people", choice_code="AN" )
        petsQ.matchchoice_set.create( choice="queer people", choice_code="QU" )
        petsQ.save()

    if do_quest is None or "asexual" in do_quest:
        clearMatchQuestion( "asexual" )
        if verbose:
            print "Making the asexual question"
        petsQ = MatchQuestion( question="the Asexual Question", ask_about_seek=True )
        petsQ.checkbox = True
        petsQ.is_YN = True
        petsQ.explanation = "I prefer to have asexual relationships."
        petsQ.include_name = True
        petsQ.hard_match = True
        petsQ.internal_comment = "Augmented boston form."
        petsQ.strict_subset_match = False
        petsQ.question_code = "asexual"
        petsQ.save()
        petsQ.matchchoice_set.create( choice="I strongly prefer being matched with asexual people", choice_code="Y" )
        petsQ.matchchoice_set.create( choice="I strongly prefer not being matched with asexual people", choice_code="N" )
        petsQ.matchchoice_set.create( choice="I have no strong preference", choice_code="EI" )
        petsQ.save()

    if do_quest is None or "monog" in do_quest:
        clearMatchQuestion( "monog" )
        if verbose:
            print "Making the monogomy question"
        petsQ = MatchQuestion( question="the Monogomy Question", question_code="monog",ask_about_seek=True )
        petsQ.checkbox = True
        petsQ.is_YN = True
        petsQ.hard_match = False
        petsQ.explanation = "I prefer to have a relationship with only one person at a time (i.e. am monogamous)."
        petsQ.include_name = True
        petsQ.hard_match = True
        petsQ.internal_comment = "For USD/Rainbow Speed Dating."
        petsQ.strict_subset_match = False
        petsQ.question_code = "monog"
        petsQ.save()
        petsQ.matchchoice_set.create( choice="I strongly prefer those who can enjoy monogamous relationships", choice_code="Y" )
        petsQ.matchchoice_set.create( choice="I strongly prefer those who do not enjoy monogamous relationships", choice_code="N" )
        petsQ.matchchoice_set.create( choice="I have no strong preference", choice_code="EI" )
        petsQ.save()

    if not do_quest is None and "funk" in do_quest:
        clearMatchQuestion( "funk" )
        if verbose:
            print "Making the funkiness question"
        funkQ = MatchQuestion( question="the Funkiness Question", question_code="funk", ask_about_seek=True )
        funkQ.checkbox = True
        funkQ.explanation = "How funky are you?"
        funkQ.internal_comment = "Sample question"
        funkQ.question_code = "funk"
        funkQ.save()
        funkQ.matchchoice_set.create( choice="totally funky", choice_code="TF" )
        funkQ.matchchoice_set.create( choice="kind of funky", choice_code="KF" )
        funkQ.matchchoice_set.create( choice="not funky", choice_code="NF" )
        funkQ.save()

    if not do_quest is None and "hot" in do_quest:
        clearMatchQuestion( "hot" )
        if verbose:
            print "Making the hotness question"
        hotQ = MatchQuestion( question="the Hotness Question", question_code="hot" )
        hotQ.checkbox = False
        hotQ.explanation = "Are you hot?"
        hotQ.explanation = "Sample question"
        hotQ.question_code = "hot"
        hotQ.save()
        hotQ.matchchoice_set.create( choice="Yes", choice_code="Y" )
        hotQ.matchchoice_set.create( choice="No", choice_code="N" )
        hotQ.save()




def makeTestDB( event_name, simple_event=False, extra_extra_questions=True, trigender=False, verbose=True ):
    """
    add_to_event - true means add some sample questions.   false means no.
    """

    setupMatchQuestions( verbose=verbose, trigender=trigender )

    events = Event.objects.filter( event=event_name )
    if len(events) > 0:
        print( "Warning: Already have a testing1 event.  Going to re-use it." )
        evt = events[0]
    else:
        evt = dt.makeTestEvent(event_name)
        evt.save()

    if not simple_event:
        evt.extra_questions.clear()
        evt.save()
        evt.extra_questions.add( MatchQuestion.objects.get(question_code="primary") )
        evt.extra_questions.add( MatchQuestion.objects.get(question_code="kinky") )
        evt.extra_questions.add( MatchQuestion.objects.get(question_code="monog") )
        evt.extra_questions.add( MatchQuestion.objects.get(question_code="asexual") )

        if extra_extra_questions:
            evt.extra_questions.add( MatchQuestion.objects.get(question_code="funk") )
            evt.extra_questions.add( MatchQuestion.objects.get(question_code="hot") )
            evt.extra_questions.add( MatchQuestion.objects.get(question_code="identity") )
        evt.save()



def convertCode( code_str ):
        """
        Now depreciated.  To convert old coding to new.
        """
        new_str = ""
        new_value = [ x.split("-") for x in code_str.split(",") ]
        for x in new_value:
            if x[0] == "F":
                x[0] = "W"
            if x[0] == "TF":
                x[0] = "TW"
            if len(x) > 1:
                new_str = new_str + x[0] + "-" + x[1] + ","
            else:
                new_str = new_str + x[0] + ","

        new_str = new_str[0:-1]
        print( "%s -> '%s'" % (code_str, new_str,) )
        return new_str


def convertGenderStrings():
    """
    Used because we used to do "F" and "TF" for Female, etc., to "W" and "TW"
    """
    peeps = Person.objects.all()
    for p in peeps:
        p.gender = convertCode( p.gender )
        p.seek_gender = convertCode( p.seek_gender )
        p.save()



def convertSEtoSFCode( code_str ):
        new_str = ""
        new_value = code_str.split(",")
        for (k, val) in enumerate(new_value):
            if val=="SE":
                new_value[k] = "SF"
                break

        return ",".join(new_value)


def convertLocations():
    """
    Used when I accidentally had "san francisco coded as "SE" just like "Somewhere Else" --Luke
    """
    rrs = RegRecord.objects.filter( event='queer1' )
    for rr in rrs:
        loc = convertSEtoSFCode( rr.location )
        print "%s -> '%s'" % (rr.location, loc )
        rr.location = loc
        rr.save()




if __name__ == '__main__':
    print_usage = False

    if len(sys.argv) >= 2:
        action = sys.argv[1].lower()

        # These are non-event specific commands
        if action=="help" or action=="-h" or action=="--help":
            print_usage = True
        elif action=="cleandatabase":
            cleanDatabase()
        elif action=="matchquestions" and len(sys.argv) == 2:
            setupMatchQuestions()
            checkOrganization()
        elif action=="testdb":
            makeTestDB("testing1", False, False )
            #makeTestDB( "kink1", False, True )
            checkOrganization()
        elif action=="checkorganization":
            checkOrganization()
        elif action=="convertlocations":
            convertLocations()
        elif action=="convertgenderstrings":
            convertGenderStrings()
        elif ( len(sys.argv) >= 3 ):
                # these are all event specific
                event = sys.argv[2]
                if action=="testemail":
                    testEmail( event )
                elif action=="matchquestions":
                    setupMatchQuestions( set( sys.argv[2:] ) )
                elif action=="makematrix":
                    makeMatrix( event )
                elif action=="listmatrix":
                    #res = listMatchRecords(event, verbose=True)
                    #print( "Results of makeMatrix: %s\n" % (res, ) )
                    print "Option missing"
                elif action=="liststraight":
                    listStraightMales( event , cut_id = sys.argv[3] )
                elif action=="nopay":
                    listNoPay( event )
                elif action=="emailreminders":
                    emailReminders( event )
                elif action=="listid":
                    listIDInfo( event )
                elif action=="calcpay":
                    print "Option missing"
                    #calcPayNumbers( event )
                elif action=="demographics":
                    RcodeHooks.print_demographics( event )
                elif action=="makenametags":
                    RcodeHooks.makeNametags( event )
                elif action=="explain":
                    if len(sys.argv) >= 4:
                        print "\n\t == EXPLAINING SOME THINGS ==\n\n"
                        explain.explain( event, sys.argv[3] )
                    else:
                        explain.explain_all( event )
                elif action=="schedule":
                    if len(sys.argv) >= 4:
                        if len(sys.argv) >= 6:
                            who_include = sys.argv[5]
                        else:
                            who_include = "In"
                        if len(sys.argv) >= 5:
                            num_trials = int(sys.argv[4])
                        else:
                            num_trials = 1

                        date_scheduler.schedule( event, rounds=int(sys.argv[3]), trials=num_trials, who_include=who_include)
                    else:
                        print """
schedule [eventname] [rounds] [trials] [who include]- make a schedule for [rounds] rounds of dating.
     Note: Will do random starts [trials] times (higher numbers means more time trying to find
     good schedule).

     who include can be "In" or "All" or "NotNo" or "Paid"
"""
                else:
                    print "Unrecognized action %s\n" % (action, )
                    print_usage = True
        else:
             print "Unrecognized action or missing arguments for %s\n" % (action, )
             print_usage = False
    else:
        print_usage = True

    if print_usage:
        print """
    This program is to help you manage PSD admin things of various descriptions

    Usage: matcher.py command [eventname] [cutid]


    ** Various Commands **
        PAYMENT AND REGISTRATION TRACKING
        nopay [eventname] - list folks who haven't paid

        liststraight [eventname] [cutid] - go through registration and list all straight folks who have a regrecord id after cut_id
              Note 'cut_id' is the django database id of the record (an integer), NOT the psdid

        calcpay [eventname] - calculate the number of folks who paid and registered.

        emailreminders [eventname] - email reminders to everyone, flagging those with few
             dates.  RUN MATRIX MAKER FIRST!

        listID [eventname] - list all folks IDs for an event


        DATING RELATED
        makematrix [eventname]  - make and save matrix of who can date whom
             Note: you can do this in django.  This, however, gives more output on process.

        explain [eventname] [psdid] - explain why psdid does/does not get dates at eventname

        R COMMANDS TO RUN EVENT:
        demographics [eventname] - print all registered folks for this event that have not explicitly canceled

        makenametags [eventname] - make a file that can be used to make nametag labels (duplicating groups, etc)

        schedule [eventname] [rounds] [trials] [who include]- make a schedule for [rounds] rounds of dating.
             Note: Will do random starts [trials] times (higher numbers means more time trying to find good schedule).
                   who include can be "In" or "All" or "NotNo" or "Paid"


        OTHER
        cleandatabase - delete identifying information from database to turn it into a test database.  Generate fake names.
              Note: THIS WILL KILL YOUR DATABASE!!!!

        convertgenderstrings - fix F and TF to W and TW

        matchquestions [question names] - make MatchQuestions for Gender, Kinkiness, and Location so those combo boxes work right.
              Also make Organization object for all Django sites for non-event links (if none found).
              Note: Call without arguments when setting up a new database.

              Can also add question names to reset those questions only.

        testdb - make a test database with a fake event.  Calls 'matchquestions' then adds more.

        checkorganization - check organization code to sync with setup.py
        """
