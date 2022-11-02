"""
Admin functions to explore the text being used in the text-matching questions

Makes printouts of what text is used, and also implements the linker that allows different versions of the same
concept to be linked to count as a single concept to increase the number of matches.
"""

from register.models import RegRecord
from register.textquestion import *


def get_all_text( event_name ):

    regs = RegRecord.objects.filter(event=event_name, cancelled=False)

    txt = [ p.text_match for r in regs for p in r.members  ]

    return txt



def check_entries( event_name ):
    """
    Return dict mapping PSD ID to bad text of member
    """
    regs = RegRecord.objects.filter(event=event_name, cancelled=False)
    baddies = {}
    for r in regs:
        for p in r.members:
            tm = p.text_match
            tr = TextResponse( tm )
            if not tr.valid_entry:
                baddies[r] = tr

    return baddies


def print_bad_entries( event_name ):
    baddies = check_entries( event_name )
    for (r, tr) in baddies.iteritems():
        print( "\nInvalid Entry from %s" % (r,) )
        tr.print_table()
    return baddies


def gen_text_table( event_name ):
    """
    Return dict of word mapping to count of word usage
    """
    txt = get_all_text( event_name )

    words = {}
    for c in txt:
        tr5 = TextResponse( c )
        if not tr5.valid_entry:
            print( "\n" )
            tr5.print_table()
        for wr in tr5.identities().values():
            w = wr.word
            dd = words.get( w, [0,0,0,0,0] )
            if wr.notFlag:
                dd[1] += 1
            else:
                dd[0] += 1
            words[w] = dd
        for wr in tr5.seeks().values():
            w = wr.word
            dd = words.get( w, [0,0,0,0,0] )
            dd[2 + wr.notFlag] += 1
            words[w] = dd
        for w in tr5.words():
            dd = words.get( w, [0,0,0,0,0] )
            dd[4] += 1
            words[w] = dd

    return words


def get_text_with( event_name, snippit, free_form=False ):
    """
    Return dict of person records to text response objects that contain snippit
    """
    regs = RegRecord.objects.filter(event=event_name, cancelled=False)
    baddies = {}
    for r in regs:
        for p in r.members:
            tm = p.text_match
            tr = TextResponse( tm )
            if (free_form and snippit in tm.lower()) or snippit in tr.words():
                baddies[p] = tr

    return baddies



def print_text_table( event_name ):

    words = gen_gext_table( event_name )

    print "\n\n\nList of Words:"
    print "Is\tIsNot\tSeek\tSeekNot\tTotal\tWord"
    ww = [w for w in words.keys()]
    ww.sort()
    for w in ww:
        cnt = words[w]
        print "%d\t%d\t%d\t%d\t%d\t%s" % ( cnt[0], cnt[1], cnt[2], cnt[3], cnt[4], w )

    print "\n\n"
    for w in ww:
        print "%s" % (w, )







"""
Debugging:

import register.views.textwrangler as tw
tw.print_text_table( "locale3" )
tw.check_entries( "locale3" )
"""
