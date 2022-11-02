#
# Check that the basic event manager functions don't immediately crash the system and give back pdfs, or whatever,
# as they should.
#

from functools import partial
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from register.system_models import Event
from register.schedule_models import DateRecord
from psd.management.commands.testdb import makeTestDB
from register.forms import MakeTableTableForm, PSDIDorEmailForm, ScheduleForm, PrintSchedulesForm
from matchmaker import date_scheduler
from tests.tests_register import FactoryRecordMixin
from mock import patch
import io


class BaseManagerTestCase(TestCase):

    def setUp(self):
        makeTestDB("testing1", True, False, verbose=False)
        self.event = Event.objects.get(event="testing1")
        self.user = User.objects.create_user(username='bob', email='bob@bobs.com', password='pass')
        self.user.is_staff = True
        self.user.save()
        self.client.login(username='bob', password='pass')


class TestMaketabletable(BaseManagerTestCase):


    def setUp(self):
        super(TestMaketabletable, self).setUp()
        self.url = reverse('event-action', args=(self.event.event, 'maketabletable'))

    def test_get_return_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], MakeTableTableForm)
        self.assertTemplateUsed(response, 'dashboard/command_arg_form.html')

    def test_post_call(self):
        with patch('register.views.dashboard.make_table_table') as make_table_mock:
            response = self.client.post(self.url, {'N': '75', 'statOk': '1-10', 'groupOK': '5-15, 18', 'posh':'1-5', 'crap':'13,15,3'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Error', response.content)
        make_table_mock.assert_called_once_with(u'testing1', 75, set([]), set([5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 18]), set([1,2,3,4,5]), set([3,13,15]) )






class TestCheckin(BaseManagerTestCase):

    def setUp(self):
        super(TestCheckin, self).setUp()
        self.url = reverse('check-in', args=(self.event.event,))

    def test_page_render(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkin.html')


class TestWalkinreg(BaseManagerTestCase):

    def setUp(self):
        super(TestWalkinreg, self).setUp()
        self.url = reverse('event-action', args=(self.event.event, 'walkinreg'))

    def test_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], PSDIDorEmailForm)
        self.assertTemplateUsed(response, 'dashboard/walkin_menu.html')


class TestMatrix(BaseManagerTestCase):

    def setUp(self):
        super(TestMatrix, self).setUp()
        self.url = reverse('event-action', args=(self.event.event, 'matrix'))

    def test_page_render(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        rsp = "".join(response.streaming_content)
        self.assertIn('Generating match records', rsp)


class TestSchedule(BaseManagerTestCase):

    def setUp(self):
        super(TestSchedule, self).setUp()
        self.url = reverse('event-action', args=(self.event.event, 'plandates' ))

    def test_get_return_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], ScheduleForm)
        self.assertTemplateUsed(response, 'dashboard/command_arg_form.html')

    def test_post_everyone_not_cancelled(self):
        with patch('register.views.dashboard.partial') as partial_mock:
            partial_mock.side_effect = partial
            response = self.client.post(self.url, {'rounds': 12, 'trials': 1, 'include': 'NotNo'})
        self.assertEqual(response.status_code, 200)
        rsp = "".join(response.streaming_content)
        self.assertIn('Finished scheduling', rsp)
        partial_mock.assert_called_once_with(date_scheduler.schedule, u'testing1', 12, 1, who_include=u'NotNo')


class TestSchedulePDF(BaseManagerTestCase, FactoryRecordMixin):

    def setUp(self):
        super(TestSchedulePDF, self).setUp()
        self.url = reverse('event-action', args=(self.event.event, 'schedules'))
        self.url_print = reverse('print-schedules', args=(self.event.event, 'NotNo'))

    def test_get_return_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], PrintSchedulesForm)
        self.assertTemplateUsed(response, 'dashboard/command_arg_form.html')

    def test_post_redirect(self):
        DateRecord.objects.create(event=self.event.event, round=1)
        DateRecord.objects.create(event=self.event.event, round=1)
        response = self.client.post(self.url, {'include': 'NotNo'})
        self.assertRedirects(response, self.url_print)

    def test_print_returns_pdf(self):
        DateRecord.objects.create(event=self.event.event, round=1)
        DateRecord.objects.create(event=self.event.event, round=1)
        self.make_person("SSM", "M", 42, "W", 18, 42)
        self.make_person("SSW", "W", 42, "M", 18, 42)
        response = self.client.get(self.url_print)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.content[:8], '%PDF-1.4')
        self.assertEqual(response._headers.get('content-type'), ('Content-Type', 'application/pdf'))


