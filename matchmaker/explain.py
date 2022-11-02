import os
import sys

from collections import defaultdict

os.environ['DJANGO_SETTINGS_MODULE'] = 'psd.settings'

import sys
from register.models import Person, RegRecord, Event

from matchmaker.matrix_maker import match_category


def explain_all( event_name ):
    regs = RegRecord.objects.filter(event=event_name)
    for r in regs:
        print "\n**\n** Explaining %s in %s\n**\n" % (r, event_name )
        print "%s\nMinicode: %s\nDescription: %s\n" % ( r, r.minicode(), r.geekcode() )
        #explain( event_name, r.psdid )
        print_matches( event_name, r.psdid )


def sort_by_field(lines, idx):
    d = defaultdict(list)
    for k, v in lines:
        d[v[idx]].append((k, v))
    return d


def print_match_list( matchlist ):
    for m in matchlist:
        print "%s:\t%s\t%s\n" % m


def print_matches( event_name, psdid ):
    regs = RegRecord.objects.filter(event=event_name)
    ev = Event.objects.get(event=event_name)
    me = RegRecord.objects.get(event=event_name, psdid=psdid)
    answers = defaultdict(list)

    all_folks = []

    for x in regs:
        if x.psdid == psdid:
            continue
        answer, reason = me.explain_match_horror(x, ev, verbose=True )
        all_folks.append( (answer,x,reason) )

        answers[match_category(answer)].append((x.psdid, answer, reason))

    print "All good matches:"
    print_match_list( answers[ "good" ] )
    print "All poor matches:"
    print_match_list( answers[ "poor" ] )
    print "All failed matches:"
    print_match_list( answers[ "no" ] )



def explain(event_name, psdid):
    regs = RegRecord.objects.filter(event=event_name)
    ev = Event.objects.get(event=event_name)
    me = RegRecord.objects.get(event=event_name, psdid=psdid)
    liked = []

    print "Explaining %s\nMinicode: %s\nDescription: %s\n" % ( me, me.minicode(), me.geekcode() )

    answers = defaultdict(list)
    all_folks = []

    for x in regs:
        if x.psdid == psdid:
            continue
        answer, reason = me.explain_match_horror(x, ev)
        all_folks.append( (answer,x,reason) )

        answers[match_category(answer)].append((x.psdid, reason))
        if match_category(answer) != "no":
            liked.append(x)

    all_folks.sort()
    for f in all_folks:
        if f[2]:
            rsn = f[2][0]
        else:
            rsn = "none"
        print "%s\t%s\t%s" % (f[0], rsn ,f[1].minicode(True))

    print "%s approved of %s people:" % (me.nickname, len(answers["good"]))
    print "  " + ', '.join(x[0] for x in answers["good"])
    print


    print "%s tolerated %s people:" % (me.nickname, len(answers["poor"]))
    print "  " + ', '.join(x[0] for x in answers["poor"])
    print

    print "Here's why %s rejected people..." % me.nickname
    rejects = answers["no"]
    explain_rejections(rejects)

    answers = defaultdict(list)
    for x in regs:
        if x.psdid == psdid:
            continue
        answer, reason = x.explain_match_horror(me, ev)
        answers[match_category(answer)].append((x.psdid, reason))
    print "%s was approved of by %s people overall:" % (me.nickname, len(answers["good"]))
    print "  " + ', '.join(x[0] for x in answers["good"])
    print

    print "%s was tolerated by %s people overall:" % (me.nickname, len(answers["poor"]))
    print "  " + ', '.join(x[0] for x in answers["poor"])
    print

    print "Here's why people rejected %s..." % me.nickname
    rejects = answers["no"]
    explain_rejections(rejects)

    answers = defaultdict(list)
    for x in liked:
        answer, reason = x.explain_match_horror(me, ev)
        answers[match_category(answer)].append((x.psdid, reason))
    print "%s was approved of by %s people they liked:" % (me.nickname, len(answers["good"]))
    print "  " + ', '.join(x[0] for x in answers["good"])
    print
    print "%s was tolerated by %s people they liked:" % (me.nickname, len(answers["poor"]))
    print "  " + ', '.join(x[0] for x in answers["poor"])
    print
    print "Here's why people %s liked rejected %s..." % (me.nickname, me.nickname)
    rejects = answers["no"]
    explain_rejections(rejects)



def explain_rejections(rejects):
    print "Why Rejections: "

    #for rj in rejects:
    #    print "%s\n" % (rj, )
    #

    d = sort_by_field(rejects, 0)

    for kk in d:
        print "Key = %s" % (kk, )

    if d['gender']:
        print "%s rejections because of gender:" % len(d['gender'])
        d2 = sort_by_field(d['gender'], 1)
        print "  %s with no overlap:" % len(d2['no overlap']),
        print ", ".join("%s (%s)" % (k[0], k[1][2]) for k in d2['no overlap'])
        print "  %s with some overlap:" % len(d2['overlap']),
        print ", ".join("%s (%s)" % (k[0], k[1][2]) for k in d2['overlap'])
        print

    if d['age']:
        print "%s rejections because of age:" % len(d['age'])
        d2 = sort_by_field(d['age'], 1)
        print "  %s too young:" % len(d2['too young'])
        d3 = sort_by_field(d2['too young'], 2)
        print "    %s slightly:" % len(d3['slightly']),
        print ", ".join("%s (%s)" % (k[0], k[1][3]) for k in d3['slightly'])
        print "    %s fully:" % len(d3['fully']),
        print ", ".join("%s (%s)" % (k[0], k[1][3]) for k in d3['fully'])

        print "  %s too old:" % len(d2['too old'])
        d3 = sort_by_field(d2['too old'], 2)
        print "    %s slightly:" % len(d3['slightly']),
        print ", ".join("%s (%s)" % (k[0], k[1][3]) for k in d3['slightly'])
        print "    %s fully:" % len(d3['fully']),
        print ", ".join("%s (%s)" % (k[0], k[1][3]) for k in d3['fully'])
        print

    if d['kink']:
        print "%s rejections because of kink:" % len(d['kink'])
        print ("%s:" % (d['kink'][0][1][1])),
        print ", ".join(k[0] for k in d['kink'])
        print

    if d['monog']:
        print "%s rejections because of monogamy:" % len(d['monog']),
        print ", ".join(k[0] for k in d['monog'])
        print


    return

if __name__ == '__main__':
    print "\n\t == EXPLAINING SOME THINGS ==\n\n"
    explain(sys.argv[1], sys.argv[2])
