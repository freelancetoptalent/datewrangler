from django.conf import settings
from django.contrib.sites.models import Site
from django_docopt_command import DocOptCommand
from register.system_models import Organization


def checkOrganization():
    # Make Organization object if there isn't one
    orgs = Organization.objects.all()
    if not orgs:
        print "Making new organization objects and updating sites to use them"
        sites = Site.objects.all()
        for asite in sites:
            org = Organization(site=asite, info_email="error@needorganizationset.com",
                            mailing_list_url="no mailing list found. need organization set",
                            homepage_url="no home page found. need organization set")
            org.save()
            print("Making organization %s for site %s" % (org, asite))
            print("   Be sure to update in Organization in the admin interface")

    else:
        print "%s organization objects found." % (len(orgs),)

    print "Checking Site IDS"
    sites = Site.objects.all()
    for asite in sites:
        if asite.id != settings.SITE_ID:
            print("WARNING: Site '%s' is found.  SITE_ID in settings.py should be set to '%s' to correspond with this site." % (asite, asite.id),)
        else:
            print("Site %s corresponds to SITE_ID %s in settings.py" % (asite, asite.id))


class Command(DocOptCommand):
    docs = """check organization code to sync with setup.py

Usage: checkorganization

Options:
    -h --help     Show this screen.
"""

    def handle_docopt(self, arguments):
        checkOrganization()
