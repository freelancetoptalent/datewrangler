"""
This holds the code that processes user registrations.
"""

import logging
import re

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import UserManager, User
from django.forms.formsets import formset_factory
from django.shortcuts import render

from register.forms import PersonForm, augment_person_form, RegRecordForm, InitializeUserForm

viewslogger = logging.getLogger('register.views')

from register.models import Person, RegRecord
from register.matchq_models import Response
from register.system_models import Event

from django.conf import settings

from django.contrib.auth import login, authenticate
from django.core.mail import mail_managers

from matchmaker.matrix_maker import updateMatchPairsFor
from django.http import HttpResponse


PersonFormset = formset_factory(PersonForm, min_num=2, extra=0, validate_min=True)


def create_user(psdid, nickname, email):
    if settings.DEBUG:
        ## WARNING: passwords are PSD IDs in debug mode.  Watch this before distribution.
        pw = psdid
    else:
        pw = UserManager().make_random_password()
    viewslogger.debug( "Making new user '%s' '%s'" % (psdid, email,) )
    user = User.objects.create_user(psdid, email, pw)
    user.first_name = nickname
    user.save()

    return (user,pw)




def contact_reg(g, evt, request, email_user = True, new_user=True, auto_login=True ):
    """
    First, get user based on psdid of RegRecord g
    If user not found, then if new_user is True, make such a user.  In this
    case, if auto_login is True, log user into system so they can immediately
    reregister without logging in.

    If user found, update user's email with email in the 'g' object.

    Then, if event has the emailing flag set to True, email user registration information (and
    possibly password, if user was just created).
    """
    viewslogger.debug( "contact_reg called for %s for event %s" % (g, evt, ) )
    pw = 'XXXXX'
    made_user = False

    try:
        user = User.objects.get(username=g.psdid)
        user.email = g.email
        user.save()
    except User.DoesNotExist:
        # no user.  Make one!
        if new_user:
            (user,pw) = create_user(g.psdid, g.nickname, g.email)
            made_user = True
            if auto_login:
                user = authenticate(username=user.username, password=pw)
                login(request, user)
                viewslogger.info( "Auto-log-on for user '%s'" % (user, ) )
        else:
            viewslogger.info( "User not found.  Told not to make one so we fail" )
            raise

    if email_user:
        viewslogger.debug( "Sending register and update emails" )
        email_body = render(request, 'email/registration_email.txt',
                                         {'rr' : g, 'event' : evt, 'newuser' : made_user, 'password' : pw },
                                         )

        user.email_user( "Registration confirmation for %s." % g.psdid, email_body.content, from_email=evt.info_email )
        admin_email_body = render(request, 'email/payment_email.txt', { 'rr': g, 'data':'no data--not from paypal'} )
        mail_managers( 'Registration for %s' % (g.psdid,), admin_email_body.content )
    else:
        viewslogger.debug( "Did not send register and update emails due to email_user flag" )

    viewslogger.debug( "contact_reg finished for RR id=%s psdid='%s' '%s'" % (g.id, g.psdid, g) )




def make_char_code( nickname ):
    """
    Make a PSDID out of a nickname.

    :param nickname: The nickname from the registration form.
    :return:   A PSDID (unique identifier for the entity registered) without the number part at the end.
    """
    nm = ""
    if nickname.count( ' ' ) > 0:
        nms = nickname.split( ' ' )
        nms = [re.sub( '[\W]+', '', c ) for c in nms]
        d = [ x[0] for x in nms if len(x) > 0 and x.upper() != "AND" ]
        nm = ''.join(d)
    else:
        nm = re.sub( '[\W]+', '', nickname )
        if len( nm ) >= 3:
            nm = nm[0:3]
        elif len( nm ) == 0:
            nm = 'ABC'
    return nm.upper()



def mk_entity_id(nickname, is_group, id_num ):
    """
    Make a PSD ID for a dating unit by taking the first three letters of the public name,
    (or first letter of each word in public name)
    following with the passed id_num (padded to make at least a 3 digit number),
    incremented by 0, 1, ...,  until the id is unique.
    id_num is either an event id or the true id of a regrecord, usually.
    For groups, add a following G for group.
    """
    def paddit( evid ):
        evid = str(evid)
        if len(evid) < 2:
            evid = "00" + evid
        elif len(evid) < 3:
            evid = "0" + evid
        return evid

    char_code = make_char_code( nickname )

    if is_group:
        tag = "G"
    else:
        tag = ""

    cur_name = char_code + paddit(id_num) + tag
    while User.objects.filter( username=cur_name ).count() > 0:
        id_num += 1
        cur_name = char_code + paddit(id_num) + tag

    viewslogger.info( "Generated entity id '%s' for nickname %s (group = %s)" % (cur_name, nickname, is_group, ) )
    return cur_name


def psdid_stamp_person(p, entity_id, cntr ):
    """
    Give a PSD ID to the person and enter that into the database
    """
    viewslogger.debug( "Going to generate PSD ID for %s (%s %s)" % (p.id, p.first_name, p.last_name ) )
    mid = entity_id + "-" + str(cntr)
    viewslogger.debug( "PSD ID for %s (%s %s) is %s" % (p.id, p.first_name, p.last_name, mid ) )
    p.psdid = mid
    p.save()


def set_psdid_ids(g, psdid=None):
    """
    Take new RegRecord g and then generate a
    regrecord (and user) PSD ID from the nickname and the event (unless
    one has been passed already)
    Then give all people in the RegRecord their PSD IDs
    """
    if psdid is None:
        mid = mk_entity_id(g.nickname, g.is_group, g.id)
    else:
        mid = psdid

    g.psdid = mid
    g.save()

    if mid[-1] == "G":
        mid = mid[0:-1]

    members = g.people.all()
    for (cntr,p) in enumerate( members ):
        psdid_stamp_person(p, mid, cntr)

    viewslogger.info( "set all regrecord and person IDs for %s" % (g,) )





def set_hidden_reg_fields(rcd, event ):
    """ Initialize various flags for payment and whatnot that users don't directly
        fill out."""
    for field in ['paid', 'cancelled', 'pending', 'here', 'is_group']:
        rcd[field] = False
    #for field in ['notes']:
    #    rcd[field] = ''
    rcd['notes'] = ''
    for field in ['matches', 'oneway']:
        rcd[field] = 0





def get_last_registration( psdid, event_name ):
    """
    Return the last registration made by 'psdid,' for event_name if possible.
    If there is a regrecord for event_name, then return a flag indicating so.

    """
    if psdid == '':
        viewslogger.warning( "Returning None,False since psdid is empty." )
        return (None, False)

    viewslogger.info( "Looking for old registration for user '%s' and event '%s'" % (psdid, event_name) )
    oldreg = RegRecord.objects.filter(psdid=psdid, event=event_name)
    if len(oldreg) == 0:
        oldreg = RegRecord.objects.filter(psdid=psdid).order_by('-id')

    if len(oldreg) == 0:
        return (None, False)
    else:
        oldreg = oldreg[0]
        viewslogger.info( "get_last_registration for %s returned potential registration %s" % (psdid, oldreg) )
        if oldreg.event == event_name:
            return (oldreg, True)
        else:
            return (oldreg, False)


def extract_extra_answers(request):
    """
    Pull out all the extra answers from a form.
    Returns: dict of question_code (note prefix chopped) mapping to responses.
        Note if seek is true, also will have "seek_"+question_code mapping to seek
        responses.
    """
    return request_subdict(request, 'X_')



def extract_multi_extra_answers(request):
    """
    If a request contains a PersonFormset, we want to construct
    dicts that look how they would if this were several
    individuals signing up.
    """
    dicts = [
             request_subdict(request, 'form-0-X_'),
             request_subdict(request, 'form-1-X_'),
             request_subdict(request, 'form-2-X_')
            ]
    ## Drop any empty dicts.
    return [x for x in dicts if x]



def request_subdict(request, prefix):
    """
    Pull out all the extra answers from a form.
    Returns: dict of question_code (note prefix chopped) mapping to responses.
    """
    k = len(prefix)
    return dict((x[k:], y) for x,y in request.lists() if x.startswith(prefix))





def load_extra_answers(p, event):
    """
    p is a Person object.   event is an Event object.

    Return dict of question_code to list of answer _primary key codes_.
    NOTE: if question is checkbox (i.e., multiple answers possible), will return list.  Else singleton.
    Also puts in "seek_"+question_code to answer primary key codes
    """
    dct = dict()
    for q in event.extra_questions.all():
        try:
            ans = Response.objects.get(owner=p, question=q)
        except Response.DoesNotExist:
            dct[q.question_code] = None
        else:
            if q.checkbox:
                dct[q.question_code] = [ x.pk for x in ans.answers.all() ]
                dct[ "seek_" + q.question_code ] = [ x.pk for x in ans.seek_answers.all() ]
            else:
                try:
                    dct[q.question_code] = ans.answers.get()
                except Exception as inst:
                    viewslogger.error( "Failed to get response for question %s and person %s at %s" % (q, p, event ) )
                    viewslogger.error( "Exception is: %s" % (inst, ) )
                    dct[q.question_code] = None
                try:
                    dct[ "seek_" + q.question_code ] = ans.seek_answers.get()
                except Exception as inst:
                    viewslogger.error( "Failed to get response for SEEK side of question %s and person %s at %s" % (q, p, event ) )
                    viewslogger.error( "Exception is: %s" % (inst, ) )
                    dct["seek_" + q.question_code] = None
    return dct


def save_extra_answers(p, extra, event):
    """

    :param p: Person record
    :param extra: extra is the result of an extract_extra_answers call.  It is a dictionary of extra questions to add to the registration.
    :param event: The event (an Event object)
    :return:
    """
    if extra is None:
        viewslogger.warning("Got null 'extra' as parameter in save_extra_answers. Bailing on method call.")
        return

    for q in event.extra_questions.all():

        rsp = extra.get(q.question_code, [])
        seek_field = "seek_%s" % ( q.question_code, )
        seek_rsp = extra.get(seek_field, [])

        p.set_response( q, rsp, seek_rsp )


def update_old_reg( oldreg, rcd  ):
    """
    Delete all fields in a form dictionary that are admin (and not set by the form)
    TODO: Make the form work right and exclude these fields initially so this is unnecessary.
        I.e., how do we find what fields are actually in the form?  The form being built from
        the model seems to add all the model fields to the dictionary.  Or is there a better way
        to do this?   (Because if stationary is not in the form, the old value will be clobbered)
    """
    # remove all fields we don't want to clobber with the form's values (which are default and wrong)
    for field in ['psdid', 'event', 'paid', 'cancelled', 'pending', 'here', 'is_group', 'notes','matches', 'oneway']:
        del rcd[field]
    viewslogger.info( "rcd dictionary is %s" % (rcd, ) )
    oldreg.__dict__.update(rcd)

    oldreg.save()

    return oldreg


class RegistrationError(Exception):
    """
    Used when, e.g., a user is registering with an email for a different regrecord
    when the user is not logged in
    """
    def __init__(self, value, response_object):
        self.value = value
        self.response = response_object
    def __str__(self):
        return repr(self.value)


def enter_group_post(request, event, oldreg, is_reregister, psdid=None, admin_mode = False ):
    viewslogger.info( "POST call for %s" % event.event)
    pformset = PersonFormset(request.POST)
    rform = RegRecordForm(request.POST)

    if pformset.is_valid() and rform.is_valid():
        rcd = rform.cleaned_data

        if oldreg is None:
            ## no user logged in, check if registration already exists
            oldemail = RegRecord.objects.filter(email=rcd['email'], is_group=True).count()
            if oldemail > 0:
                ## email already registered and user not logged in, user needs to login.
                raise RegistrationError( "returning user error",
                        render(request, 'register/returningusererror.html', {'login_required' : 'yes' }))

            oldpeeps = [None] * len(pformset.forms)
        else:
            oldpeeps = oldreg.people.all()
            if len(oldpeeps) > len(pformset.forms):
                    raise RegistrationError( "wrong number of people",
                                            render(request, 'error.html', {'message' : "You are registering fewer people than the last time you registered (%d vs. %d).  This is currently not allowed.  Please log-out, register as a brand new user, and then contact us." % (len(oldpeeps), len(pformset.forms)) }))

        # NEXT LINE SHOULD NOT BE NEEDED!!!!!
        # What the hell is going on????
        del rcd['people']
        if is_reregister:
            r = update_old_reg( oldreg, rcd )
        else:
            set_hidden_reg_fields(rcd, event)
            rcd['event'] = event.event
            r = RegRecord(**rcd)
            r.save()

        extras = extract_multi_extra_answers(request.POST)
        if len( extras ) == 0:
            extras = [{}] * len(pformset.forms)
        extras = extras + [{}]*(len(pformset.forms) - len(extras))
        for (pform, extra, p) in zip( pformset.forms, extras, oldpeeps ):
            if not pform.cleaned_data:
                ## Empty forms are always okay in a fresh registration.
                ## In a re-reg, check if someone is missing.
                if p:
                    raise RegistrationError( "Missing person",
                        render(request,
                               'error.html',
                               {'message' : "Missing person in registration.  You are registering a different number of people than the last time you registered.  This is currently not allowed.  Please log-out, register as a brand new user, and then contact us." }
                              ))
                else:
                    continue

            pcd = pform.cleaned_data
            if p:
                viewslogger.debug( "Found old person %s with id %s and psdid '%s'" % (p, p.id, p.psdid) )
                del pcd['psdid']
                p.__dict__.update(pcd)
            else:
                p = Person(**pcd)
            p.save()
            r.people.add(p)
            p.save()
            save_extra_answers(p, extra, event)

        r.is_group = (r.people.count() > 1)
        r.save()

        if not (oldreg is None):
            r.psdid = oldreg.psdid
            r.save()

        if not is_reregister:
            set_psdid_ids(r, psdid=psdid)
        else:
            # hack.  Need to reload regrecord to get its person records updated
            # TODO: Fix this hack.  How dynamically reload person stuff?
            r = RegRecord.objects.get( id=r.id )

        return r
    else:
        raise RegistrationError( "form error", render(request, 'register/registration_error.html', {'pformset': pformset, 'rform': rform}))



def enter_indiv_post( request, event, oldreg, is_reregister, psdid = None, admin_mode = False ):
    """
    This is the main method for signing up a new registration (for an individual, not group)

    Params:
    Admin mode: we are an administrator doing something to a user.  Do not log in user, etc.
    """
    viewslogger.info( "POST call for %s---going to save RegRecord, etc." % event.event )
    pform = PersonForm(request.POST, initial={'seek_kinkiness': 'EI'})
    rform = RegRecordForm(request.POST)
    if pform.is_valid() and rform.is_valid():
        pcd = pform.cleaned_data
        extra = extract_extra_answers(request.POST)
        rcd = rform.cleaned_data

        if oldreg != None:
            # overwrite associate person object
            p = oldreg.people.all()
            if len(p) > 0:
                    p = p[0]
                    viewslogger.debug( "Loading old person %s with id %s and psdid '%s'" % (p, p.id, p.psdid) )
                    del pcd['psdid']
                    p.__dict__.update(pcd)
            else:
                    viewslogger.warning( "Had old regrecord but couldn't find person record.  Making new person." )
                    p = Person(**pcd)
        else:
            ## user not logged in, check if email already exists, indicating a reregistration
            ## without logging in error  (is_group because group and indiv can reuse same email)
            oldemail = RegRecord.objects.filter(email=rcd['email'], is_group=False).count()
            if oldemail == 0:
                ## no record of email for an individ record - create new person
                p = Person(**pcd)
            else:
                raise RegistrationError( "returning user error",
                        render(request, 'register/returningusererror.html', {'login_required' : 'yes' }))

        p.save()
        save_extra_answers(p, extra, event)

        # NEXT LINE SHOULD NOT BE NEEDED!!!!!
        # What the hell is going on????
        del rcd['people']

        if not is_reregister:
            # make new RegRecord
            rcd['event'] = event.event
            set_hidden_reg_fields(rcd, event)
            r = RegRecord(**rcd)
            r.save()
            r.people.add(p)
            if not (oldreg is None):
                viewslogger.info( "Setting psdid of '%s' to old reg PSD ID of '%s'" % (r, oldreg.psdid, ) )
                r.psdid = oldreg.psdid
            else:
                set_psdid_ids(r, psdid=psdid)
        else:
            r = update_old_reg( oldreg, rcd )
            # hack.  Need to reload regrecord to get its person records updated
            # TODO: Fix this hack.  How dynamically reload person stuff?
            r = RegRecord.objects.get( id=r.id )

        if event.no_ssm and r.is_NMSMSS and not is_reregister:
            r.addNote( "!Need companion!" )

        r.save()

        viewslogger.debug( "Person for rr = %s" % (p.geekcode() ) )
        viewslogger.debug( "Regrecord's geekcode = %s" % (r.geekcode() ))
        return r
    else:
        raise RegistrationError( "form error", render(request, 'register/registration_error.html', {'pform': pform, 'rform': rform}))



def generate_indiv_forms(event, oldreg, initials = None, is_reregister=False ):
    if not oldreg is None:
        viewslogger.info( "Returning auto-filled indiv form for authenticated user." )
        if not (initials is None):
            oldreg.__dict__.update(initials)
        rform = RegRecordForm(initial=oldreg.__dict__)
        oldper=oldreg.people.all()
        if len(oldper) > 0:
            initdict = oldper[0].__dict__
            if not is_reregister:
                viewslogger.warning( "HACK: wiping out gender on a new registration" )
                initdict['seek_gender'] = ""
                initdict['gender'] = ""
            pform = PersonForm(initial=initdict)
            old_answers = load_extra_answers( oldper[0], event )
        else:
            viewslogger.warning( "No people found in old reg record '%s'---going to leave blank" % (oldreg, ) )
            pform = PersonForm(initial={'seek_kinkiness': 'EI'})
            old_answers = {}
    elif not (initials is None):
        viewslogger.info( "Returning empty indiv form with some initial values" )
        pform = PersonForm(initial={'seek_kinkiness': 'EI'})
        rform = RegRecordForm( initial=initials )
        old_answers = {}
    else:
        # make empty form to fill out
        viewslogger.info( "Returning empty indiv form" )
        pform = PersonForm(initial={'seek_kinkiness': 'EI'})
        rform = RegRecordForm()
        old_answers = {}

    pform = augment_person_form(pform, event, old_answers) # add extra/custom questions
    questions = []
    for q in event.extra_questions.all():
        ff = pform['X_' + q.question_code]
        ff2 = pform['X_seek_' + q.question_code] if q.ask_about_seek else None
        q.form_fields = (ff, ff2)
        questions.append(q)

    pform.extra_fields = questions

    return (rform, pform)



def generate_group_forms(event, oldreg, initials = None, is_reregister=False):
    """
    initials: dictionary of initial parameter values for the RegRecord
    """
    # List of old responses to repopulate form if necessary
    old_answers = []

    if not oldreg is None:
        if not (initials is None):
            oldreg.__dict__.update(initials)
        rform = RegRecordForm(initial=oldreg.__dict__)
        oldper=oldreg.people.all()
        inits = []
        for op in oldper:
            initdict = op.__dict__
            if not is_reregister:
                viewslogger.warning( "HACK: wiping out gender on a new registration in group form" )
                initdict['seek_gender'] = ""
                initdict['gender'] = ""
            inits.append(initdict)
            #old_answers[op] = load_extra_answers( oldper[0], event )
            old_answers.append( load_extra_answers( op, event ) )
        pformset = PersonFormset( initial=inits )
    elif not (initials is None):
        pformset = PersonFormset()
        rform = RegRecordForm( initial=initials )
    else:
        pformset = PersonFormset()
        rform = RegRecordForm()

    cntr = 0
    for pform in pformset.forms:
        if len(old_answers) > cntr:
            old_ans = old_answers[cntr]
            cntr = cntr + 1
        else:
            old_ans = {}
        pform = augment_person_form(pform, event, old_ans)
        ## Next seven lines are basically copy-pasted from above...
        ## I'm not sure how to factor that piece out, since we need
        ## to feed the results to render_to_response.
        questions = []
        for q in event.extra_questions.all():
            ff = pform['X_' + q.question_code]
            ff2 = pform['X_seek_' + q.question_code] if q.ask_about_seek else None
            q.form_fields = (ff, ff2)
            questions.append(q)
        pform.extra_fields = questions

    return (rform, pformset)


def get_template_name_for_event( event_name, group_form=False ):
    """
    Return list of templates, first the template for a specific event, then
    the overall, general template.
    Put event-specific templates in the sites/code/register template directory.
    They have names such as "registerGroup_testing1.html"
    """
    if group_form:
        return ['register/registerGroup_%s.html' % event_name, 'register/registerGroup.html' ]
    else:
        return ['register/registerIndiv_%s.html' % event_name, 'register/registerIndiv.html' ]


def check_id_code( psdid, is_group ):
    """
    Is reg record or psdid ID consistent with the passed is_group flag?
    """
    if psdid is None:
        return True
    recs = RegRecord.objects.filter( psdid=psdid )
    if len( recs ) > 0:
        return recs[0].is_group == is_group
    else:
        if psdid[-1] == "G":
            return is_group == True
        else:
            return is_group == False


def do_sign_up(request, event_name, psdid=None, mark_as_here=False, group_form=False, reg_override=False ):
    """
    Called when either Group or Individual Registration form is filled out and submitted.

    When a staff member is logged in, this form acts as a RegRecord editing form for the staff.
    See the auto-set "admin_mode" flag, below.

    Param:
    psdid: The PSD ID to use for this registration.  None means generate or find one depending
        on who is logged in.
        For admin_mode, 'psdid' is a string for reregistration or updating a registration or registering
        a returning dater for a new event.
        (It will try and find the most recent reg record, etc., just as with a user)
    group_form (Flag): Is this the group reg form or individual reg form?
    """
    new_user = False
    the_user = None
    viewslogger.info( "***** do_sign_up called for %s (POST = %s)" % (event_name, (request.method == 'POST') ) )
    viewslogger.info( "      Flags psdid=%s  mark_as_here=%s  group_form=%s" % (psdid, mark_as_here,group_form) )
    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request, 'error.html',
                      {'message' : "Sorry.  You are trying to register for an event that does not exist or is closed.  Please try again." },)

    if request.user.is_authenticated() and request.user.is_staff:
        # we are using this form to do an admin-run walk-in registration or RegRecord edit.
        admin_mode = True
        if psdid is None:
            is_reregister = False
            oldreg = None
            new_user = True
        else:
            (oldreg, is_reregister) = get_last_registration( psdid, event_name )
            if oldreg is None:
                try:
                    the_user = User.objects.get( username=psdid )
                except:
                    return render(request, 'error.html', {'message':'Administration error: trying to register a PSD ID with no prior reg records or user object in database'},
                                         )
            else:
                try:
                    the_user = User.objects.get( username=psdid )
                except:
                    return render(request, 'error.html', {'message':'Administration error: trying to register a PSD ID with no user object in database'},
                                         )
    else:
        admin_mode = False
        if event.regfrozen:
            return render(request, 'register/regclosed.html', {'frozen':True, 'closed':event.regclosed } );

        if request.user.is_authenticated():
            the_user = request.user
            psdid = request.user.username
            viewslogger.info( "User '%s' is authenticated, going to look for old reg records" % (request.user,) )
            (oldreg, is_reregister) = get_last_registration( request.user.username, event_name )
        else:
            oldreg = None
            is_reregister = False
            new_user = True

        # use regrecord PSDID if there is a regrecord
        if not (oldreg is None):
            psdid = oldreg.psdid

        if event.regclosed and not is_reregister and not reg_override:
            return render(request, 'register/regclosed.html', {'frozen':event.regfrozen, 'closed': event.regclosed } )

    viewslogger.info( "Admin Mode = %s     new_user = %s     is_reregister = %s" % (admin_mode, new_user, is_reregister ) )


    if request.method == 'POST':
        try:
            # form aligned with user?  If not, do voodoo
            # by forgetting this is a returning dater or something
            if not check_id_code( psdid, group_form ):
                if admin_mode:
                    # TODO: fix this hack.  group_form flag sometimes switched and/or autodetected
                    # For example, under admin 'manange' option, there is no url id to indicate
                    # whether it is a group form.  So it should get auto-set like it does right here.
                    if is_reregister:
                        group_form = not group_form
                    else:
                        raise RegistrationError( "non-match between user type and form type", render(request, 'error.html', {'message' : "The PSD ID you are registering has not historically registered as the type of entity you are attempting to register them as.  (Ouch)." }) )
                else:
                    oldreg = None
                    is_reregister = False
                    psdid = None

            if group_form:
                r = enter_group_post( request, event, oldreg, is_reregister, psdid=psdid )
            else:
                r = enter_indiv_post( request, event, oldreg, is_reregister, psdid=psdid )

            contact_reg(r, event, request=request,
                            email_user=not event.no_emailing and (not admin_mode or new_user),
                            auto_login=not admin_mode )

            if mark_as_here:
                r.here = True
                r.save()

            if admin_mode:
                return render(request, 'register/adminsubmit.html',
                              {'reg': r, 'event': event, 'mark_as_here': mark_as_here},)
            else:
                r.new_user = new_user
                return render(request, ['register/payment_%s.html'.format(event_name), 'register/payment.html'],
                          {'reg': r, 'event': event, 'reregistered': is_reregister,
                           'stripe_key': settings.STRIPE_KEY, 'stripe_product': settings.STRIPE_PRODUCT})

        except RegistrationError as err:
            viewslogger.debug("Registration Error %s" % (err, ))
            return err.response
    else:
        # override group_form flag.
        # this is to allow, e.g., a hack in the RegRecord admin template to link to an edit.
        # without knowing the regrecord type.
        if not (oldreg is None):
            group_form = oldreg.is_group

        # generate empty (or pre-filled) form for editing and future submission
        if the_user is None:
            initials = None
        elif oldreg:
            initials = { 'psdid':oldreg.psdid,
                         'email':oldreg.email,
                         'nickname':oldreg.nickname}
        else:
            initials = { 'psdid':the_user.username,
                         'email':the_user.email,
                         'nickname':the_user.first_name }


        if group_form:
            (rform, pformset) = generate_group_forms(event, oldreg, initials=initials, is_reregister=is_reregister )
            pform = None
        else:
            (rform, pform) = generate_indiv_forms(event, oldreg, initials=initials, is_reregister=is_reregister )
            pformset = None

        if admin_mode:
            baseregform="register/baseadminregform.html"
        else:
            baseregform = 'register/baseregform.html'

        return render(request, get_template_name_for_event(event_name, group_form=group_form),
                      {'baseregform': baseregform,
                       'event': event,
                       'pform': pform,
                       'pformset': pformset,
                       'rform': rform,
                       'is_reregister': is_reregister,
                       'admin_mode': admin_mode,
                       'mark_as_here': mark_as_here})



@staff_member_required
def do_match(request, event_name, psdid=None ):
    """
    Calculate all matches for specific PSD ID (for quick checking on single people)
    :param request: 
    :param event_name: 
    :param psdid: 
    :return: 
    """

    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request, 'error.html', {'message' : "Sorry.  You are trying to register for an event that does not exist or is closed.  Please try again." })

    try:
        rr = RegRecord.objects.get(psdid = psdid, event=event_name)
    except Event.DoesNotExist:
        return render(request, 'error.html', {'message' : "Sorry.  You are trying to update a regrecord that does not exist.  Please try again." })

    result = updateMatchPairsFor( rr, verbose=True )

    header = "<body>\nUpdated matches for %s at %s\n" % (psdid, event_name )
    print result

    return HttpResponse( "\n%s\n<pre>\n%s\n\n<\\pre>\n<\\body>" % (header, result, ) )



def registration_note(request, event_name="unknown"):
    """Called when note for registration is needed"""

    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request, 'error.html', {'message' : "Sorry.  You are trying to register for an event that does not exist or is closed.  Please try again." })

    return render(request, 'register/registration_note.html', {'event': event, 'event_name': event_name })


def create_user_if_needed( nickname, u_email, is_group, event ):
    """
    Given nickname and email, look for user account with that email.
    If not found, then make one and generate a psd ID for it.
    """

    pw = "XXXXXX"
    made_user = False
    try:
        user = User.objects.get( email=u_email )
        results = "Pre-existing user %s found for '%s' (email %s)." % (user.username, nickname, u_email )
        psdid = user.username
    except User.MultipleObjectsReturned:
        users = User.objects.filter( email=u_email )
        user = users[0]
        unames = [user.username for user in users]
        unames = ','.join( unames )
        results = "Multiple users (%s) already exist with email '%s'.  Using %s." % (unames, u_email, user.username)
        psdid = user.username
    except User.DoesNotExist:
        psdid = mk_entity_id(nickname, is_group, event.id)
        (user,pw) = create_user( psdid, nickname, u_email )
        made_user = True
        results = "User %s created for '%s' (email %s)." % (psdid, nickname, u_email )

    email_body = render(request, 'email/initialize_user_email.txt', {'event' : event, 'user':user, 'newuser' : made_user, 'password' : pw })

    if not event.no_emailing:
        user.email_user( "Please Register for Poly Speed Dating", email_body.content, from_email=event.info_email )
    else:
        email_body.content = "<h3>WARNING: Email not sent due to event no emailing flag check</h3><br>" + email_body.content

    return (results, email_body.content)


@staff_member_required
def sign_up_user(request, event_name ):
    """
    Call to create a user account (without doing any registration).
    Email user telling them to register for the event.
    """

    viewslogger.info( "***** sign_up_user called for %s" % (event_name, ) )
    try:
        event = Event.objects.get(event=event_name)
    except Event.DoesNotExist:
        return render(request, 'error.html', {'message' : "Sorry.  You are trying to register for an event that does not exist.  Please try again." })

    results = ""
    if request.method == 'POST':
        form = InitializeUserForm(request.POST)
        if form.is_valid():
            u_email = form.cleaned_data["email"]
            nickname = form.cleaned_data["nickname"]
            is_group = form.cleaned_data["is_group"]
            (results,body_email) = create_user_if_needed( nickname, u_email, is_group, event )
            try:
                bod = body_email.decode( "utf8" ).encode( "ascii", "xmlcharrefreplace" )
            except Exception as inst:
                print(inst)
                bod = "Email failed to encode due to weird name.   User account still created"
            results += "<pre>\n" + bod + "\n</pre>"

    else:
        form = InitializeUserForm()

    return render(request, 'command_arg_form.html', {'form': form, 'event': event, 'command_title':'Initialize User',
                                                        'button_name':'Create User',
                                                        'results':results})


