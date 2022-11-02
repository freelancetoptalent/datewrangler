# URLS file

import django.contrib.auth.views
from django.contrib.auth.views import password_reset
from django.contrib.auth.views import password_reset_done
from django.contrib.auth.views import password_reset_confirm
from django.contrib.auth.views import password_reset_complete
from django.contrib.auth.views import password_change
from django.contrib.auth.views import password_change_done

from django.conf.urls import url, include
from django.views.generic.base import TemplateView
from register.views.registration import do_sign_up, do_match, sign_up_user, registration_note
from django.views.decorators.csrf import csrf_exempt
from register.views.contact import contact_us
from register.views.dashboard import (check_in, event_manager, potential_matches, next_date_sheet,
                                      date_sheet, hand_date_sheet, get_dating_matrix)
from register.views.admin_regrecord import break_matches

import os
import sys
from django.conf import settings

import register.views.users
import register.views.contact
import register.views.payment

from django.conf.urls.static import static

#from register.views.users import current_datetime
#from playpen.views import current_datetime

# Uncomment the next two lines to enable the admin:
from django.contrib import admin

admin.autodiscover()

urlpatterns = [
    # ('^.*','django.views.generic.simple.direct_to_template', {'template': 'maintenance.html'})

    # Participant user screens
    url(r'^', include('django.contrib.auth.urls')),
    url('^accounts/login/$', django.contrib.auth.views.login, name='account-login'),
    url('^accounts/login$', django.contrib.auth.views.login),
    url('^accounts/logout/$',  django.contrib.auth.views.logout, {'next_page':'/'}, name='account-logout'),
    url('^view/$', register.views.users.show_me_all, name="account-view-orig"),  # their reg record screen
    url('^sheet/(?P<event_name>[0-9A-Za-z]+)$', register.views.users.user_date_sheet, name="user-date-sheet"),

    # various info screens
    url('^about/(?P<what>[0-9A-Za-z]+)$', register.views.users.about_page, name="about-page"),

    # handling password changes and resets
    url('^reset/$', password_reset, {'email_template_name':'registration/password_reset_email.html'}, name="password-reset"),
    url('^reset/done/$', password_reset_done, name='password_reset_done'),
    url('^reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', password_reset_confirm, name='password_reset_confirm'),
    url(r'^reset/complete/$', password_reset_complete,name='password_reset_complete'),
    url('^accounts/changepw/$', password_change, name="password-change"),
    url('^accounts/changepw/done$', password_change_done, name='password-change-done'),

    # Registration for the event
    url('^regnote/(?P<event_name>[0-9A-Za-z]+)$', registration_note, name="registration-note"),
    url('^individual/(?P<event_name>[0-9A-Za-z]+)$', do_sign_up, name="individual-registration"),
    url('^group/(?P<event_name>[0-9A-Za-z]+)$', do_sign_up, {'group_form':True}, name="group-registration"),
    url('^extra/(?P<event_name>[0-9A-Za-z]+)$', do_sign_up, {'group_form':False, 'reg_override':True}, name="additional-registration"),
    url('^user/(?P<event_name>[0-9A-Za-z]+)', sign_up_user, name="user-registration"),
    url('^individual$', TemplateView.as_view(template_name='no_event_specified.html')),
    url('^group$', TemplateView.as_view(template_name='no_event_specified.html')),
    # simple feedback form for the event
    url('^feedback/(?P<event_name>[0-9A-Za-z]+)', contact_us, name="feedback"),

    # Link for PayPal to talk to us
    #url(r'^endpoint/$', register.views.paypalPaymentEndpoint(), name="paypal-endpoint"),
    # Link for Stripe to talk to us
    url(r'^stripe$', csrf_exempt(register.views.payment.StripeWebhook()), name="stripe-webhook"),

    # ADMIN LINKS
    url('^manage/(?P<event_name>[0-9A-Za-z]+)/reply/(?P<psdid>[0-9A-Za-z]+)', register.views.contact.individual_email, name="comment-email",
        kwargs={'from_comments':True}),
    url('^manage/(?P<event_name>[0-9A-Za-z]+)/datematrix', get_dating_matrix, name="date-matrix" ),
    url('^manage/(?P<event_name>[0-9A-Za-z]+)/edit/(?P<psdid>[0-9A-Za-z]+)', do_sign_up, name="update-reg"),
    url('^manage/(?P<event_name>[0-9A-Za-z]+)/match/(?P<psdid>[0-9A-Za-z]+)', do_match, name="match-reg"),
    url('^manage/(?P<event_name>[0-9A-Za-z]+)/walkin/rereg/(?P<psdid>[0-9A-Za-z]+)', do_sign_up, {'mark_as_here':True}, name="walk-in-update" ),
    url('^manage/(?P<event_name>[0-9A-Za-z]+)/walkin/individual', do_sign_up, {'mark_as_here':True}, name="walk-in-reg-individual"),
    url('^manage/(?P<event_name>[0-9A-Za-z]+)/walkin/group', do_sign_up, {'mark_as_here':True, 'group_form':True}, name="walk-in-reg-group"),
    url('^manage/(?P<event_name>[0-9A-Za-z]+)/(?P<action>[a-zA-Z]*)/(?P<extraArg>[0-9a-zA-Z]*)$', event_manager),
    url('^manage/(?P<event_name>[0-9A-Za-z]+)/(?P<action>[a-zA-Z]*)$', event_manager, name="event-action"),
    url('^manage/(?P<event_name>[0-9A-Za-z]+)$', event_manager, {'action':""}, name="event-manager" ),
    url('^manage/?$', event_manager, {'event_name':'', 'action':"allevents"}, name="event-lister" ),
    url('^admin/checkin/(?P<event_name>[0-9A-Za-z]+)$', check_in, name="check-in"),
    url('^admin/multibreak$', register.views.dashboard.multi_break ),

    # Scheduling and making the pdf of schedules
    url('^admin/schedules/(?P<event_name>[0-9A-Za-z]+)', register.views.dashboard.schedule_form, name="make-schedules"),
    url('^admin/printschedules/(?P<event_name>[0-9A-Za-z]+)/(?P<include_code>[A-Za-z]+)', register.views.printouts.make_schedules, name="print-schedules"),
    url('^admin/printschedules/(?P<event_name>[0-9A-Za-z]+)', register.views.printouts.make_schedules),

    # emailing folks
    url('^admin/post_event/(?P<event_name>[0-9A-Za-z]+)', register.views.contact.post_email, name="email-post-event"),
    url('^admin/email/(?P<event_name>[0-9A-Za-z]+)/(?P<psdid>[0-9A-Za-z]+)', register.views.contact.individual_email, name="individual-email"),
    url('^admin/email/(?P<event_name>[0-9A-Za-z]+)', register.views.contact.subgroup_email, name="subgroup-email"),
    url('^admin/volunteeremail/(?P<event_name>[0-9A-Za-z]+)', register.views.contact.email_volunteer_cruises, name="volunteer-email"),
    url('^admin/pre_event/(?P<event_name>[0-9A-Za-z]+)', register.views.contact.pre_email, name="email-pre-event"),
    url('^admin/testemail/(?P<event_name>[0-9A-Za-z]+)', register.views.contact.test_email, name="test-email"),

    # user management
    url('^view/(?P<event_name>[0-9A-Za-z]+)/(?P<psdid>[0-9A-Za-z]+)', register.views.dashboard.view_user, name="view-user" ),
    url('^edit/(?P<event_name>[0-9A-Za-z]+)/(?P<psdid>[0-9A-Za-z]+)', register.views.dashboard.edit_user, name="edit-user" ),
    url('^editperson/(?P<psdid>[0-9A-Za-z\-]+)', register.views.dashboard.edit_person, name="edit-person" ),
    url('^edit/(?P<event_name>[0-9A-Za-z]+)', register.views.dashboard.edit_event, name="edit-event" ),
    url('^listevents$', register.views.users.list_events, name="list-events"),

    url('^profile/(?P<psdid>[0-9A-Za-z]+)$', register.views.users.show_me_all, name="admin-account-view"),  # their reg record screen
    url('^matches/(?P<event_name>[0-9A-Za-z]+)/(?P<psdid>[0-9A-Za-z]+)$', potential_matches, name="potential-matches"),
    url('^break/(?P<event_name>[0-9A-Za-z]+)/(?P<psdid>[0-9A-Za-z]+)$', break_matches, name="admin-break-matches"),
    url('^datesheet/(?P<event_name>[0-9A-Za-z]+)/(?P<psdid>[0-9A-Za-z]+)$', date_sheet, name="date-sheet"),
    url('^handdatesheet/(?P<event_name>[0-9A-Za-z]+)/(?P<psdid>[0-9A-Za-z]+)$', hand_date_sheet, name="hand-date-sheet"),
    url('^detaileddatesheet/(?P<event_name>[0-9A-Za-z]+)/(?P<psdid>[0-9A-Za-z]+)$', date_sheet, name="detailed-date-sheet", kwargs={'detailed':True} ),
    url('^nextdatesheet/(?P<event_name>[0-9A-Za-z]+)/$', next_date_sheet, name="next-date-sheet"),

    # Django documentation stuff
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),

    url('^$', register.views.users.show_me_all, name="account-view")

    # some testing
    #('^test', test_function),
    #    (r'^now/$', current_datetime )
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# This is dirty dirty dirty!
# if 'runserver' in sys.argv or 'runserver_plus':
#     urlpatterns += [url(r'^media/(.*)$', 'django.views.static.serve', kwargs={'document_root': os.path.join(settings.PROJECT_PATH, 'media')})]
#     urlpatterns += [url(r'^(.*)$', 'django.views.static.serve', kwargs={'document_root': settings.WEBSITE_PATH})]
    #print "urlpatterns supplemented!"

#print "project path='%s'" % (psd.settings.PROJECT_PATH, )



