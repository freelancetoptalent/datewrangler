import random
from register.models import RegRecord, Person, BreakRecord, DateRecord, CruiseRecord, DateSheetNote, RecessRecord, LinkRecord
from django.db import connection, transaction
from django.contrib.auth.models import User
from django_docopt_command import DocOptCommand
from matchmaker.models import MatchRecord


def name_generator(first_name, last_name):
    # TO DO: replace this with http://faker.readthedocs.io/en/latest/

    lets = ["K","M","R","D","N","P","W", "F", "Qu", "Z", "R", "T", "L"]
    mem = ["ag","erf","ook","unly","astor","uncle","ian","izze", "ack", "erry", "ark", "endy", "ancis"]
    #color = ["Red","Blue","Black","White","Orange","Green","Yellow","Purple"]
    tool = ["age","icky","arn","ettle","ragon","olf","ummingbird","uster","azzle","uulit"]
    let1 = random.randrange(0,len(lets))
    let2 = random.randrange(0, len(lets))
    randomNumber1 = random.randrange(0,len(mem))
    randomNumber2 = random.randrange(0,len(tool))
    #name = color[randomNumber1] + " " + tool[randomNumber2]
    #return (first_name[0]+mem[randomNumber1],last_name[0]+tool[randomNumber2])
    return (lets[let1]+mem[randomNumber1],lets[let2]+tool[randomNumber2])


class Command(DocOptCommand):
    docs = """Delete identifying information from database to turn it into a test database. Generate fake names.
Note: THIS WILL KILL YOUR DATABASE!!!!

Usage: cleandatabase

Options:
    -h --help     Show this screen.
"""
    def handle_docopt(self, arguments):
        counter = 500
        psdid_table = {}

        print( "Wiping peoples names and generating new PSD IDs" )
        obj = Person.objects.all()
        for p in obj:
            if len(p.psdid) <= 1:
                print "Weird record ", p, "# '", p.psdid, "'"
                p.psdid = "XXX" + random.randrange(1000,2000)
            if p.psdid in psdid_table:
               print "Duplicate PSDID (now deleted) in original database: %s" %( p.psdid, )
               p.delete()
            else:
                (p.first_name, p.last_name) = name_generator(p.psdid[0], p.psdid[1])
                oldpsdid = p.psdid
                p.psdid = p.first_name[0] + p.last_name[0] + str(counter)
                counter = counter + 13
                psdid_table[oldpsdid] = p.psdid
                p.save()

        print( "Wiping regrecord nicknames and emails" )
        obj = RegRecord.objects.all()
        rrtable = {}
        for r in obj:
            oldpsdid = r.psdid
            if not oldpsdid in psdid_table:
                rpsdid = r.members[0].psdid.split("-")[0]

                if r.is_group:
                    rpsdid = rpsdid + "G"
                psdid_table[oldpsdid] = rpsdid
            r.psdid = psdid_table[r.psdid]

            r.nickname = r.minicode( no_extra=True )
            r.email = "PSD_" + r.psdid + "@" + "vzvz.org"
            if r.referred_by != "":
                r.referred_by = "someone"
            if r.comments != "":
                r.comments = "some comments"
            if r.notes != "":
                r.notes = "some admin notes"
            rrtable[ r.psdid ] = r
            r.save()


        print( "Wiping user emails and changing user names to match new PSD IDs" )
        obj = User.objects.all()
        for u in obj:
            if not u.is_staff:
                if u.username in psdid_table:
                    u.username = psdid_table[u.username]
                    u.email = "PSD_" + u.username + "@" + "vzvz.org"
                    u.first_name = rrtable[ u.username ].firstnames
                    u.last_name = ""
                    u.set_password( u.username )
                    u.save()
                else:
                    print "Username %s not found in PSDID table who is not staff. Deleting" % (u.username,)
                    u.delete()


        print( "Converting date records" )
        obj = DateRecord.objects.all()
        for u in obj:
            try:
                u.psdid = psdid_table[ u.psdid ]
                u.other_psdid = psdid_table[ u.other_psdid ]
                u.save()
            except Exception as e:
                print "%s - Failed date record conversion %s" % ( e, u, )
                u.delete()


        print("Converting break records")
        obj = BreakRecord.objects.all()
        for u in obj:
            try:
                u.psdid = psdid_table[u.psdid]
                u.other_psdid = psdid_table[u.other_psdid]
                u.save()
            except Exception as e:
                print "%s - Failed break record %s" % (e, u,)
                u.delete()

        print("Converting match records")
        obj = MatchRecord.objects.all()
        for u in obj:
            try:
                u.psdid1 = psdid_table[u.psdid1]
                u.psdid2 = psdid_table[u.psdid2]
                u.save()
            except Exception as e:
                print "%s - Failed match record %s" % (e, u,)
                u.delete()


        print("Converting cruise records")
        obj = CruiseRecord.objects.all()
        for u in obj:
            try:
                u.psdid = psdid_table[u.psdid]
                u.other_psdid = psdid_table[u.other_psdid]
                u.save()
            except Exception as e:
                print "%s - Failed cruise record %s" % (e, u,)
                u.delete()

        print("Converting link records")
        obj = LinkRecord.objects.all()
        for u in obj:
            try:
                u.psdid = psdid_table[u.psdid]
                u.psdid_alias = psdid_table[u.psdid_alias]
                u.save()
            except Exception as e:
                print "%s - Failed link record %s" % (e, u,)
                u.delete()

        print("Converting datesheetnote records")
        obj = DateSheetNote.objects.all()
        for u in obj:
            try:
                u.psdid = psdid_table[u.psdid]
                u.save()
            except Exception as e:
                print "%s - Failed datesheetnote record %s" % (e, u,)
                u.delete()

        print("Deleting all recess templates.")
        for rr in RecessRecord.objects.all():
            rr.delete()


        cursor = connection.cursor()

        with transaction.atomic():
            print( "Wiping admin logs table" )
            cursor.execute("DELETE FROM django_admin_log" )

        with transaction.atomic():
            print( "Wiping django_session table" )
            cursor.execute( "DELETE FROM django_session" )

