import factory
from register.models import Person, RegRecord
from register.system_models import Event
from register.views.registration import set_psdid_ids
from register.views.registration import create_user
from datetime import date, datetime, timedelta


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'auth.User'  # Equivalent to ``model = myapp.models.User``
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: 'joedoe%d' % n)


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Event
        django_get_or_create = ('event',)

    event = factory.Sequence(lambda n: "testing_%d" % n)
    longname = factory.Sequence(lambda n: "The testing event %d" % n)
    location = 'x'
    address = 'y'
    locationURL = 'h'
    accessdetails = '-'
    cost = 50  #
    doorcost = 60
    payment_systems = 'paypal'
    paypal_email = 'pay@me.com'
    wepay_email = 'pay@me.com'
    info_email = 'pay@me.com'
    mailing_list_url = 'http'
    homepage_url = 'http'

    # extra_questions = models.ManyToManyField(MatchQuestion, blank=True)
    date = date.today() + timedelta(days=7)
    starttime = datetime.now().time()
    deadlinetime = (datetime.now() + timedelta(hours=2)).time()
    stoptime = (datetime.now() + timedelta(hours=4)).time()


class PersonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Person

    first_name = factory.Sequence(lambda n: 'Joe%d' % n)
    last_name = factory.Sequence(lambda n: 'Doe%d' % n)
    gender = 'M'
    seek_gender = 'W'
    age = 20
    seek_age_min = 18
    seek_age_max = 40



class RegRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RegRecord

    nickname = factory.Sequence(lambda n: "joedoe%d" % n)
    email = factory.LazyAttribute(lambda r: '%s@example.com' % r.nickname)
    seek_groups = False

    friend_dates = False
    wants_childcare = False

    @factory.post_generation
    def set_event(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            if isinstance(extracted, basestring):
                event = EventFactory(event=extracted)   # get or create
            else:
                event = extracted
            self.event = event.event
            self.save()


    @factory.post_generation
    def people(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of people were passed in, use them
            for person in extracted:
                self.people.add(person)
            if len(extracted) != 1:
                self.is_group = True
                self.save()
        else:
            self.people.add(PersonFactory())

    @factory.post_generation
    def set_psdid(self, create, extracted, **kwargs):
        if not create:
            return

        set_psdid_ids(self, extracted)
        create_user(self.psdid, self.nickname, self.email)
