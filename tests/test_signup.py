# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.core import mail
from django_webtest import WebTest
from register.models import Person, RegRecord
from register.system_models import Event
from psd.management.commands.testdb import makeTestDB

# This is a sample comment.

class BaseManagerTestCase(WebTest):

    def setUp(self):
        makeTestDB("testing1", True, False, verbose=False)
        self.event = Event.objects.get(event="testing1")


class TestIndividualSignup(BaseManagerTestCase):

    def setUp(self):
        super(TestIndividualSignup, self).setUp()
        self.url = reverse('individual-registration', args=(self.event.event,))

    def test_form_fields(self):
        response = self.app.get(self.url)
        form = response.form
        self.assertTemplateUsed(response, 'register/registerIndiv.html')
        #print "test_form_field debug:"
        #print form.fields.keys()
        self.assertTrue( all( x in form.fields.keys() for x in [u'nickname', u'first_name',
                         u'last_name', u'email', u'age', u'seek_age_min', u'seek_age_max',
                          u'gender'] ) ) # u'seek_gender_0', u'seek_gender_1',
        

        # self.assertEqual(form.fields.keys(), [u'csrfmiddlewaretoken',
                # u'first_name', u'last_name', u'nickname', u'email', u'add_to_mailings', u'age',
                # u'seek_age_min', u'seek_age_max', u'seek_gender_0', u'seek_gender_1', u'gender',
                # u'seek_groups', u'groups_match_all', u'location', u'friend_dates', u'referred_by',
                # u'wants_childcare', u'children', u'comments', u'Submit_Indiv'
            # ]
        # )

    def test_post_valid_form(self):
        form = self.app.get(self.url).form
        form['nickname'] = 'messi10'
        form['first_name'] = 'lionel'
        form['last_name'] = 'messi'
        form['email'] = u'messi@barça.com'
        form['age'] = '27'
        form['seek_age_min'] = '18'
        form['seek_age_max'] = '55'

        #form.get('seek_gender_0', index=0).checked = True
        #seek_gender_0 = form.get('seek_gender_0', index=0).value

        #form.get('seek_gender_1', index=0).checked = True
        #seek_gender_1 = form.get('seek_gender_1', index=0).value
        form.get('gender', index=0).checked = True
        gender = form.get('gender', index=0).value

        # with newer webtest we can assign this:
        # form['gender'] = [u'W', u'M']

        # form['text_match'] = 'bear, andro seeks not andro, nerd'
        # form['seek_groups'] = True
        # form['groups_match_all'] = True
        # form['location'] = [u'SE', u'UK']
        # form.get('location', index=0).checked = True
        # form.get('location', index=1).checked = True
        # form['friend_dates'] = True
        # form['add_to_mailings'] = True
        # form['referred_by'] = 'Luke'
        # form['wants_childcare'] = True
        # form['children'] = 'thiago and benjamin'
        # form['stationary'] = True
        # form['comments'] = 'thanks!'

        assert Person.objects.count() == 0
        assert User.objects.count() == 0
        assert RegRecord.objects.count() == 0

# TODO Fix the submit() so the rest can be checked
#         response = form.submit()
#         self.assertIn('You have completed Step 1 of registration', response.content)
# 
#         messi = Person.objects.get()       # there is just one
# 
#         self.assertEqual(messi.fullname, 'lionel m')
#         self.assertEqual(messi.gender, gender)
#         # self.assertEqual(messi.text_match, 'bear; andro seeks not andro; nerd')
#         self.assertEqual(messi.age, 27)
# 
#         # user whas created
#         messi_user = User.objects.get()    # there is just one
# 
#         self.assertEqual(messi_user.email, u'messi@barça.com')
#         self.assertTrue(messi_user.is_authenticated())
# 
#         reg = RegRecord.objects.get()      # there is just one
#         self.assertEqual(reg.email, u'messi@barça.com')
# 
#         # check email sents
#         self.assertEqual(len(mail.outbox), 2)
#         self.assertEqual(mail.outbox[0].subject, 'Registration confirmation for MES001.')
#         self.assertEqual(mail.outbox[0].to, [u'messi@barça.com'])
#         self.assertTrue( "Registration for MES001" in mail.outbox[1].subject )
#         #self.assertEqual(mail.outbox[1].to, ['luke_boston_psd@vzvz.org'])

    def test_post_invalid_form(self):

        form = self.app.get(self.url).form
   # TODO Fix submit
   #     response = form.submit()  # empty form
   #     self.assertIn('The Problems Found', response.content)
   #     self.assertTemplateUsed(response, 'register/registration_error.html')
   #     # no mail is sent
   #     self.assertEqual(len(mail.outbox), 0)



# class TestGroupSignup(BaseManagerTestCase):
#
#     def setUp(self):
#         super(TestGroupSignup, self).setUp()
#         self.url = reverse('group-registration', args=(self.event.event,))
#
#     def test_form_fields(self):
#         response = self.app.get(self.url)
#         form = response.form
#         self.assertTemplateUsed(response, 'register/registerGroup.html')
#         print "List of keys in the form."
#         print form.fields.keys()
#         self.assertTrue( all( x in form.fields.keys() for x in [u'csrfmiddlewaretoken', u'nickname', u'email', u'add_to_mailings', u'form-TOTAL_FORMS', u'form-INITIAL_FORMS',
#                                                                 u'form-MIN_NUM_FORMS', u'form-MAX_NUM_FORMS', u'form-0-first_name', u'form-0-last_name', u'form-0-age',
#                                                                 u'form-0-seek_age_min',
#                                                                 u'form-0-seek_age_max', u'form-0-seek_gender_0', u'form-0-seek_gender_1', u'form-0-gender', u'form-1-first_name',
#                                                                 u'form-1-last_name', u'form-1-age', u'form-1-seek_age_min', u'form-1-seek_age_max', u'form-1-seek_gender_0',
#                                                                 u'form-1-seek_gender_1', u'form-1-gender', u'groups_match_all', u'seek_groups'] ) )
                              
                              


# TODO: Fix.  Test code not working, sadly
#     def test_post_valid_form(self):
#         response = self.app.get(self.url)
#         form = response.form
#         form['form-TOTAL_FORMS'] = '2'    # overriden
#         form['nickname'] = 'messi10'
#         form['email'] = u'messi@barça.com'
# 
#         form['form-0-first_name'] = 'lionel'
#         form['form-0-last_name'] = 'messi'
#         form['form-0-age'] = '27'
#         form['form-0-seek_age_min'] = '18'
#         form['form-0-seek_age_max'] = '55'
# 
#         form.get('form-0-seek_gender_0', index=0).checked = True
# 
#         form.get('form-0-seek_gender_1', index=0).checked = True
# 
#         form.get('form-0-gender', index=1).checked = True
#         form_0_gender = form.get('form-0-gender', index=1).value   # M
# 
#         # form['form-0-text_match'] = "argentinians"
# 
#         form['form-1-first_name'] = 'cristiano'
#         form['form-1-last_name'] = 'ronaldo'
#         form['form-1-age'] = '28'
#         form['form-1-seek_age_min'] = '15'
#         form['form-1-seek_age_max'] = '35'
# 
#         form.get('form-1-seek_gender_1', index=1).checked = True
#         # assert form.get('form-1-seek_gender_1', index=1).value == 'M'
# 
#         form.get('form-1-seek_gender_1', index=1).checked = True
#         # assert form.get('form-1-seek_gender_1', index=1).value == 'M'
# 
#         form.get('form-1-gender', index=1).checked = True
#         form_1_gender = form.get('form-0-gender', index=1).value
# 
#         # form['form-1-text_match'] = "top models"
# 
#         form['seek_groups'] = True
#         form['groups_match_all'] = True
#         # form['location'] = [u'SE', u'UK']
#         print "test_post_valid_form debug:"
#         print form
#         
#         form.get('location', index=0).checked = True
#         form.get('location', index=1).checked = True
#         form['friend_dates'] = True
#         form['add_to_mailings'] = True
#         form['referred_by'] = 'Luke'
#         form['wants_childcare'] = True
#         form['children'] = 'thiago and benjamin'
#         # form['stationary'] = True
#         form['add_to_mailings'] = True
#         form['comments'] = 'thanks!'
# 
#         response = form.submit()
#         self.assertIn('You have completed Step 1 of registration', response.content)
# 
#         messi, cristiano = Person.objects.all()       # there is just one
# 
#         self.assertEqual(messi.fullname, 'lionel m')
#         self.assertEqual(messi.gender, form_0_gender)
#         # self.assertEqual(messi.text_match, 'argentinians')
#         self.assertEqual(messi.age, 27)
# 
#         self.assertEqual(cristiano.fullname, 'cristiano r')
#         self.assertEqual(cristiano.gender, form_1_gender)
#         # self.assertEqual(cristiano.text_match, 'top models')
#         self.assertEqual(cristiano.age, 28)
# 
#         # one user whs created
#         messi_user = User.objects.get()    # there is just one
# 
#         self.assertEqual(messi_user.email, u'messi@barça.com')
#         self.assertTrue(messi_user.is_authenticated())
# 
#         reg = RegRecord.objects.get()      # there is just one
#         self.assertEqual(reg.email, u'messi@barça.com')
#         self.assertTrue(reg.is_group)
# 
#         # check email sent
#         self.assertEqual(len(mail.outbox), 2)
#         self.assertEqual(mail.outbox[0].subject, 'Registration confirmation for MES001G.')
#         self.assertEqual(mail.outbox[0].to, [u'messi@barça.com'])
#         self.assertIn("Registration for MES001G", mail.outbox[1].subject)
#         #self.assertEqual(mail.outbox[1].to, ['luke_boston_psd@vzvz.org'])
#         self.assertIsNotNone(mail.outbox[1].to)




    # def test_post_invalid_form(self):
    #     form = self.app.get(self.url).form
    #
    #     response = form.submit()  # empty form
    #     self.assertIn('The Problems Found', response.content)
    #     self.assertTemplateUsed(response, 'register/registration_error.html')
    #     # no mail is sent
    #     self.assertEqual(len(mail.outbox), 0)
