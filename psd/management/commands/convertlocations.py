from register.models import Person
from django_docopt_command import DocOptCommand


def convertCode(code_str):
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


class Command(DocOptCommand):
    docs = """Fix F and TF to W and TW

Usage: convertgenderstrings

Options:
    -h --help     Show this screen.
"""

    def handle_docopt(self, arguments):
        peeps = Person.objects.all()
        for p in peeps:
            p.gender = convertCode( p.gender )
            p.seek_gender = convertCode( p.seek_gender )
            p.save()

