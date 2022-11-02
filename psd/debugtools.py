"""
This module has some functions to help with shell-based debugging

Some notes:
install iPython as well to get history and ability to paste
doctests.   See, eg.

http://hedgehoglab.com/blog/2008/03/03/django-debug-techniques-and-ipython/

for some tips

"""
import register.models
from datetime import datetime, time


def load_django_models():
    try:
        from django.db.models.loading import get_models
        for m in get_models():
            st = "from %s import %s" % (m.__module__, m.__name__)
            print( st )
            exec st

    except ImportError:
        print "INFO: could not find a django env"




def makePersons():
    bob = register.models.Person(
            first_name = 'Bob',
            gender = 'M',
            age = 42,
            seeking_primary = True,
            kinky = False,
            seek_gender = 'W',
            seek_age_min = 18,
            seek_age_max = 42,
            seek_kinkiness = 'EI',
            psdid = 'BOB1')
    lulu = register.models.Person(
            first_name = "Lulu",
            gender = 'W',
            age = 42,
            seeking_primary = False,
            kinky = True,
            seek_gender = 'M,W,TM,TW,Q',
            seek_age_min = 24,
            seek_age_max = 55,
            seek_kinkiness = 'EI',
            psdid='LULU1')
    gayboy = register.models.Person(
            first_name = 'gayboy',
            gender = 'M',
            age = 52,
            seeking_primary = True,
            kinky = True,
            seek_gender = 'M-2,Q',
            seek_age_min = 18,
            seek_age_max = 42,
            seek_kinkiness = 'EI',
            psdid='GAYBOY1')
    omni1 = register.models.Person(
            first_name="omni",
            gender = 'W,TW',
            age = 42,
            seeking_primary = False,
            kinky = True,
            seek_gender = 'M-2,F,TM-2,TW,Q,GQ,NA,BU,FE,AN',
            seek_age_min = 24,
            seek_age_max = 60,
            seek_kinkiness = 'K',
            psdid='OMNI1')
    omni2 = register.models.Person(
            first_name="omni2",
            gender = 'W,TW',
            age = 42,
            seeking_primary = False,
            kinky = True,
            seek_gender = 'M-2,F,TM-2,TW,Q,GQ,NA,BU,FE,AN',
            seek_age_min = 24,
            seek_age_max = 60,
            seek_kinkiness = 'K',
            psdid='OMNI2')

    return (bob, lulu, gayboy, omni1, omni2 )

def makeTestEvent(event_name="testing1"):
    """
    Make a test event object with all the fields filled in.  No extra questions added.
    """
    return register.models.Event( event=event_name, longname="Fake Testing Event", location="Nowhere", address="1010 Nowhere Ave",
             locationURL="www.nowhere.com", accessdetails="Getting there: Take a bus\n\tSpin around\n\tLook for happiness",
             cost=12, doorcost=20, has_childcare=True, paypal_email="paypal@polyspeeddating.com", info_email="info@polyspeeddating.com",
             mailing_list_url="www.mailinglisturl.com", homepage_url="www.homepageurl.com", regclosed=False, regfrozen=False,
             date=datetime(2012, 8, 1),
             starttime=time( 18 ), deadlinetime=time(19), stoptime=time(22) )

