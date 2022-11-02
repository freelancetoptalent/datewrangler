"""
Code to assess success of matching and who is registered and so forth.

This code will print out tallies of who is registered, for example.

Nametags:
It also has the code for making the csv file that can be merged into making nametags.
 
"""

import pandas
from register.models import fetch_regrecord, RegRecord
from register.schedule_models import DateRecord
from register.system_models import Event


BINARY_GENDERS = set(['W', 'M', 'TW', 'TM', 'CW', 'CM' ])


def grab_folks( event_name, who_print ):
    """
    :param event_name: Name of event (as a string)
    :param who_print: String, Here or NotNo or blank
    :return:
    """
    folks = RegRecord.objects.filter( event=event_name )
    if who_print == "Here":
        folks = folks.filter( here=True )
    elif who_print=="NotNo":
        folks.filter( cancelled=False )
    return folks




####### Code to get descriptive strings for Person's gender and gender preferences ##########


def person_gender( p ):
    """
    Make a string gender for the passed Person object
    :param p: PersonRecord
    :return:
    """
    if p.only_alt_gendered:
        return "Other"
    if p.is_man_only:
        return "Men"
    if p.is_woman_only:
        return "Women"
    return "Both"


def gay_str_bi( p ):
    """
    Return a string of what genders the person is after.
    :param p:
    :return:
    """
    if p.wants_mf:
        return "bi"
    elif not p.is_man_only and not p.is_woman_only:
        if p.wants_m:
            return "wM"
        elif p.wants_f:
            return "wW"
        else:
            return "wO"
    elif (p.wants_m and p.is_man_only) or (p.wants_f and p.is_woman_only):
        return "gay"
    else:
        return "str"


def want_string( p ):
    if p.wants_mf:
        return "wMW"
    elif p.wants_m:
        return "wM"
    elif p.wants_f:
        return "wW"
    else:
        return "wO"

def is_trans(self):
        return self.has_gender("TW") or self.has_gender("TM")

def wants_trans(self):
    return self.wants_gender('TW') or self.wants_gender('TM')


def wants_alt(self):
        sg = self.seek_gender_set - BINARY_GENDERS
        return len(sg) > 0

def is_pansexual(self):
        return self.wants_mf and wants_trans(self) and wants_alt(self)

def complex_gender(p):
    sg = p.gender_set - BINARY_GENDERS
    alts = len(sg) > 0
    stt = ""
    if p.only_alt_gendered:
        return "O"
    if p.has_gender('M'):
        stt += "M"
    if p.has_gender('W'):
        stt += "W"
    if is_trans(p):
        stt = "T" + stt
    if alts:
        stt += "A"
    return stt

def complex_seek_gender(p):
    sg = p.seek_gender_set - BINARY_GENDERS
    alts = len(sg) > 0
    stt = ""
    if is_pansexual(p):
        return "Pan"

    if p.only_alt_gendered:
        return "O"
    if p.wants_gender('M'):
        stt += "M"
    if p.wants_gender('W'):
        stt += "W"
    if wants_trans(p):
        stt = "T" + stt
    if alts:
        stt += "A"
    return stt



############ Code to tally folks #############

def make_date_count_table( event_name, who_in="NotNo" ):
    """
    Event to tally matches for
    """
    folks = grab_folks( event_name, who_in )

    psdids = [r.psdid for r in folks ]
    df = pandas.DataFrame( index = psdids )

    df[ 'minicode' ] = [r.minicode() for r in folks  ]
    df[ 'gender' ] = [person_gender(r) for r in folks  ]
    df[ 'gstring' ] = [gender_string(r) for r in folks  ]
    df[ 'desire' ] = ['/'.join(r.seek_genders) for r in folks  ]
    df[ 'bi' ] = [gay_str_bi(r) for r in folks  ]
#    df[ 'num.M' ] = [0 for r in folks  ]
#    df[ 'num.W' ] = [0 for r in folks  ]
#    df[ 'num.G' ] = [0 for r in folks  ]
#    df[ 'num.O' ] = [0 for r in folks  ]
#    df[ 'num.Fr' ] = [0 for r in folks  ]

    numM = []
    numW = []
    numG = []
    numO = []
    numFr = []

    for f in folks:
        countdict = { "M":0, "W":0, "G":0, "Friend":0, "O":0 }
        for dt in DateRecord.objects.filter(event=event_name,psdid=f.psdid ):
            dt_rr = fetch_regrecord( event_name, dt.other_psdid )
            if dt.friend_date:
                countdict["Friend"] += 1
            elif dt_rr.is_group:
                countdict["G"] += 1
            elif dt_rr.is_man_only:
                countdict["M"] += 1
            elif dt_rr.is_woman_only:
                countdict["W"] += 1
            else:
                countdict["O"] += 1

            numM.append(countdict["M"] )
            numW.append(countdict["W"] )
            numG.append(countdict["G"] )
            numO.append(countdict["O"] )
            numFr.append(countdict["Friend"] )

    df[ 'num.M' ] = numM
    df[ 'num.W' ] = numW
    df[ 'num.G' ] = numG
    df[ 'num.O' ] = numO
    df[ 'num.Fr' ] = numFr

    return df



def make_demographics_table( folks ):
    import pandas
    psdids = [r.psdid for r in folks for p in r.members ]
    df = pandas.DataFrame( index = psdids )
    df[ 'name' ] = [p.fullname for r in folks for p in r.members]
    df[ 'group' ] = [r.is_group for r in folks for p in r.members ]
    df[ 'stationary' ] = [r.stationary for r in folks for p in r.members ]
    df[ 'age' ] = [ int(p.age) for r in folks for p in r.members ]
    df[ 'gstring' ] = [p.gender for r in folks for p in r.members ]
    df[ 'gender' ] = [person_gender(p) for r in folks for p in r.members ]
    df[ 'is_trans' ] = [is_trans(p) for r in folks for p in r.members ]
    df[ 'is_pan' ] = [is_pansexual(p) for r in folks for p in r.members ]
    df[ 'seek' ] = [want_string(r) for r in folks for p in r.members ]
    df[ 'seek_trans'] = [wants_trans(p) for r in folks for p in r.members ]
    df[ 'gen_comp'] = [complex_gender(p) for r in folks for p in r.members ]
    df[ 'seek_comp' ] = [complex_seek_gender(p) for r in folks for p in r.members ]
    df[ 'num_events' ] = [r.num_events() for r in folks for p in r.members ]
    return df


def get_answer_both( extra_Q, peep ):
    rsp = peep.response_for( extra_Q )
    if extra_Q.ask_about_seek:
        return "%s/%s" % (rsp.short_answer(), rsp.short_seek_answer())
    else:
        return "%s" % (rsp.short_answer(), )

def get_answer( extra_Q, peep ):
    rsp = peep.response_for( extra_Q )
    if rsp is None:
        return "Miss"
    else:
        return rsp.short_answer

def get_seek_answer( extra_Q, peep ):
    rsp = peep.response_for( extra_Q )
    if rsp is None:
        return "Miss"
    else:
        return rsp.short_seek_answer



def augment_demographics_table( df, folks, ext ):
    nm = ext.question_code
    
    #if ext.question_code=="spanish":
    #    import ipdb; ipdb.set_trace()

    df[ nm ] = [get_answer(ext,p) for r in folks for p in r.members ]

    if ext.ask_about_seek:
        nm_seek = "%s-seek" % ( nm, )
        df[ nm_seek ] = [get_seek_answer(ext,p) for r in folks for p in r.members ]

    return df




def print_demog_table( df ):
    print df.to_string()


def gender_table( df ):
    import pandas
    return pandas.pivot_table( df, "name", index=["group","gender"], columns="seek", aggfunc=len, margins=True )


def gender_age_table( df ):
    import pandas
    df[ 'decade' ] = pandas.cut( df[ 'age' ], bins=[0,20,25,30,35,40, 45,50,60,70,1000] ).astype(str)

    #import ipdb;
    #ipdb.set_trace()

    #print "\nCut age!\n"
    return pandas.pivot_table( df, "name", index=["gender"], columns="decade", aggfunc=len, margins=True )
    #return df.groupby(['gender', 'decade']).size()


def gender_string( rr ):
    if rr.is_group:
        return "group"
    elif rr.is_man_only:
        return "man"
    elif rr.is_woman_only:
        return "woman"
    else:
        return "other"




def date_distribution_iter( event_name, who_print="NotNo" ):

    df = make_date_count_table( event_name, who_print )
    yield df.to_string()



def date_distribution_iter_old( event_name, who_print="NotNo" ):

    folks = grab_folks( event_name, who_print )
    df = make_date_count_table( event_name, who_print )

    # header
    yield "PSDID,minicode,gender,desire,bi,num.M,num.W,num.G,num.O,num.Fr\n"
    for f in folks:
        countdict = { "M":0, "W":0, "G":0, "Friend":0, "O":0 }
        for dt in DateRecord.objects.filter(event=event_name,psdid=f.psdid ):
            dt_rr = fetch_regrecord( event_name, dt.other_psdid )
            if dt.friend_date:
                countdict["Friend"] += 1
            elif dt_rr.is_group:
                countdict["G"] += 1
            elif dt_rr.is_man_only:
                countdict["M"] += 1
            elif dt_rr.is_woman_only:
                countdict["W"] += 1
            else:
                countdict["O"] += 1
        outstr = ','.join( [f.psdid, f.minicode(), gender_string(f), '/'.join(f.seek_genders), gay_str_bi(f), str(countdict["M"]), str(countdict["W"]), str(countdict["G"]), str(countdict["O"]), str(countdict["Friend"]) ] )
        yield outstr + "\n"







def name_tag_iter( event_name ):
    """
    Iterate through all regrecords and make a nametag for each
    person for each regrecord.
    Sort by regrecord nickname, alphabetically case-insensitive.
    """
    # header
    yield "pubname,PSDID,first_name,last_name,pronoun,email\n"

    # all folks
    folks = RegRecord.objects.filter( event=event_name, cancelled=False )
    #folks = sorted( folks, key=lambda flk: flk.nickname.lower() )
    folks = sorted( folks, key=lambda flk: flk.psdid )

    print "Generating nametags for %s folks for event '%s'" % ( len(folks), event_name, )
    for f in folks:
        peeps = f.members
        for p in peeps:
            yield "%s,%s,%s,%s,%s,%s\n" % (f.nickname,f.psdid,p.first_name,p.last_name,p.pronoun_slug,f.email )



def make_demog_from_event( event_name, who_print="NotNo" ):
    """
    Make a table of descriptive stats for an event.
    :param event_name: Name of event (String)
    :param who_print: String describing what subset of folks to print info for.
    :return:
    """
    folks = grab_folks( event_name, who_print )

    if len( folks ) == 0:
        return None
    else:
        df = make_demographics_table( folks )

        event = Event.objects.get(event=event_name)
        for ext in event.cached_extra_questions():
            df = augment_demographics_table( df, folks, ext )

        return df



def make_demog_table( event_name, who_print="NotNo" ):
    """
    Make a text String that has all the demographic information
    """
    df = make_demog_from_event( event_name, who_print )

    return df.to_string()


def print_demographics_async( event_name, who_print="All" ):
    import pandas

    folks = RegRecord.objects.filter( event=event_name )
    if who_print == "Here" or who_print =="In":
        folks = folks.filter( here=True )
    elif who_print=="NotNo":
        folks = folks.filter( cancelled=False )

    yield "Demographic Summary for Event '%s', selection flag %s\n" % (event_name, who_print )

    if len( folks ) == 0:
        yield "No reg records for %s with %s\n" % (event_name, who_print)
    else:
        date_units = len(folks)
        num_groups = len( folks.filter( is_group=True ) )
        num_stationary = len( folks.filter( stationary=True ) )
        num_assigned_tables = 999 #len( [f for f in folks if f.has_assigned_table()] )

        df = make_demographics_table( folks )
        num_people = len(df)
        pandas.set_option('precision', 0)

        yield """
        Some totals:
        # Units: %s
        # Groups: %s
        # Stationary: %s
        # Special Tables: %s
        # People: %s""" % ( date_units, num_groups, num_stationary, num_assigned_tables, len(df), )

        pt = pandas.pivot_table( df, "name", index=["group","gender"], columns="num_events", aggfunc=len, margins=True )
        yield "\n\nVeteran Status of Attendees\n%s" % (pt.to_string(na_rep="."), )

        pt = pandas.pivot_table( df, "name", index=["group"], columns="gender", aggfunc=len, margins=True )
        yield "\n\nGroup by Gender Breakdown\n%s" % (pt.to_string(na_rep='.'), )

        yield "\n\nGender by Desire Breakdown (by Group Status)\n%s" % (gender_table( df ).to_string( na_rep='.'), )

        gat = gender_age_table(df).round()
        yield "\n\nGender by Age Breakdown (by Group Status)\n%s" % ( gat.to_string( na_rep="." ), )
        #yield "\n\nNEED TO FIX: Gender by Age breakdown broken due to more recent Pandas package\n\n"

        pt = pandas.pivot_table( df, "name", index=["group",'is_trans'], columns="seek_trans", aggfunc=len, margins=True )
        yield "\n\nCount of Transgender (by Group Status)\n%s" % (pt.to_string(na_rep='.'), )

        pt = pandas.pivot_table( df, "name", index=["group",'gen_comp'], columns="seek_comp", aggfunc=len, margins=True )
        yield "\n\nCounts for Expanded Gender (by Group Status)\n%s" % (pt.to_string(na_rep='.'), )


        try:
            event = Event.objects.get(event=event_name)
        except Event.DoesNotExist:
            yield "Sorry.  You are trying to do demographics for an event that does not exist or is closed.  Please try again."

        yield "\n\nDiving into extra questions for event '%s'\n" % ( event, )

        #yield "(# extra questions = %s)" % (len(event.cached_extra_questions), )
        for ext in event.cached_extra_questions:
            yield "\n\n**************************************************\nExtra Question: %s" % (ext, )
            df = augment_demographics_table( df, folks, ext )

            if ext.ask_about_seek:
                nm_seek = "%s-seek" % (ext.question_code,)
                pt = pandas.pivot_table( df, "name", index=["group", ext.question_code], columns=nm_seek, aggfunc=len, margins=True )
                yield "\n\nGroup and '%s' by seek %s Breakdown\n%s" % (ext.question_code, ext.question_code, pt.to_string(na_rep='.'), )

            pt = pandas.pivot_table( df, "name", index=["group", ext.question_code], columns="gender", aggfunc=len, margins=True )
            yield "\n\nGroup and '%s' by Gender Breakdown\n%s" % (ext.question_code, pt.to_string(na_rep='.'), )





#def date_count_iter( event_name ):
#    """
#    Print out the number of matches each dater got
#    """
#
#    folks = RegRecord.objects.filter( event=event_name )
#
#    # header
#    yield "PSDID,minicode,gender,desire,bi,date.PSDID,date.type,round,match,their.match\n"
#
#    for f in folks:
#        for dt in DateRecord.objects.filter(event=event_name,psdid=f.psdid ):
#            outstr = ','.join( [f.psdid, f.minicode(), gender_string(f), '/'.join(f.seek_genders), gay_str_bi(f) )
#
#            outstr += dt.friend_date + "," + dt.round + "," + dt.
#            #dt_rr = fetch_regrecord( event_name, dt.other_psdid )
#            yield outstr + "\n"




