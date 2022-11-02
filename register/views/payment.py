# views.py

"""
This code contains the Paypal connection stuff.
"""

import re
from django.contrib.auth.models import UserManager, User
from django.contrib.auth import login, authenticate
from django.forms.formsets import formset_factory
from django.shortcuts import render
from django.core.mail import mail_managers
from django.template import RequestContext
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from register.forms import PersonForm, augment_person_form, RegRecordForm, InitializeUserForm
import urllib
import json

import logging
viewslogger = logging.getLogger('payment')

# from register.forms import PersonForm, RegRecordForm, augment_person_form, InitializeUserForm
from register.models import Person, RegRecord
from register.matchq_models import Response
from register.system_models import Event

from django.conf import settings



class StripeWebhook:
    # TODO: verify the call came from Stripe, using their Python libraries
    # per https://stripe.com/docs/payments/checkout/fulfillment#webhooks
    # TODO: more/better error/failure handling
    def __call__(self, request):
        viewslogger.info("\n\nBeginning stripe webhook\n\n")
        
        viewslogger.debug( "StripeWebhook called request_meth = %s" % request.method )
        json_dict = None
        try:
            json_dict = json.loads(request.body)
        except Exception as err:
            viewslogger.error( "Failed to unpack json loading" )
            viewslogger.error( "Error is %s" % (err, ) )
            return HttpResponse(status=500)
        
        viewslogger.debug( "from %s with request dict %s ", request.get_host(), json_dict )
        data = json_dict['data']
        object = data['object']
        viewslogger.info( "Retrieved object is '%s'" % (object, ) )

        ec = object.get('client_reference_id', None)
        if ec is None:
            viewslogger.error( "Got empty client reference id.  NOT GOOD" )
            return HttpResponse(status=500)

        viewslogger.debug( "ec %s", ec )
        ec = ec.split( '-' )
        if len(ec) == 2:
            data['psdid'] = ec[1]
            data['event'] = ec[0]

            #find regrecord for psdid and event:
            viewslogger.debug(" getting regrecord for %s, %s", ec[1], ec[0])
            paidreg = RegRecord.objects.filter(psdid=ec[1], event=ec[0])
            if len(paidreg) == 0:
                # no regrecord found or invalid psdid.
                viewslogger.error(" could not find regrecord for %s", data)
                mail_managers( 'Stripe Failure: could not find psdid for payment', 'Data object %s' % data )
            else:
                viewslogger.info(" updating regrecord for %s", ec[1])
                rr = paidreg[0]
                rr.paid = True
                rr.addNote( "stripe payment intent: " + object['payment_intent'] )
                rr.save()
                viewslogger.info( "Successfull processing. Trying to send mail to managers about this transaction" )
                try:
                    email_bod=render(request, 'email/payment_email.txt', locals())
                    mail_managers( 'Stripe Payment for %s' % (ec[1]), email_bod.content )
                    viewslogger.debug( "manager email sent" )
                except Exception as ex:
                    viewslogger.warning("could not send due to %s" % ex)
        else:
            viewslogger.warning("invalid custom field")
            mail_managers( 'Stripe Failure: invalid custom field (or no custom field)', 'Data object %s' % data )

        viewslogger.info( "Finished processing Stripe payment of %s" % ( ec, ) )
        return HttpResponse(status=204)


    
class PaypalPaymentEndpoint:

    verify_url = "https://www.paypal.com/cgi-bin/webscr"

    def __call__(self, request):
        viewslogger.debug( "PayPalPaymentEndpoint called request_meth = %s" % (request.method, ) )
        ret = None
        #data = { 'apple':20, 'pear':'banana'}
        if request.method == 'POST':
            data = dict(request.POST.items())
            viewslogger.debug( "got post from %s with data %s ", request.get_host(), data )
            # We need to post that BACK to PayPal to confirm it
            args = { 'cmd': '_notify-validate', }
            args.update(data)

            viewslogger.debug( "Validating ipn with Paypal at %s", self.verify_url)

            if data.get('case_type') == 'chargeback':
                viewslogger.debug( "Chargeback request with data %s", args )
                mail_managers( 'PayPal ChargeBack Request', 'Data object %s' % (data,) )
                ret = self.invalid_ipn(data)
            elif urllib.urlopen(self.verify_url, urllib.urlencode(args)).read() == 'VERIFIED':
                cstring = "NO CUSTOM"
                if 'custon' in data:
                    cstring = data['custom']
                payemail = "NO PAYER EMAIL"
                if 'payer_email' in data:
                    payemail = data['payer_email']

                viewslogger.debug( "Got VERIFIED from paypal for %s with custom: %s", payemail, cstring )
                ret = self.valid_ipn(data)
            else:
                #TODO: email someone?
                viewslogger.debug( "Invalid IPN from paypal with data %s", args )
                mail_managers( 'PayPal Failure', 'Data object %s' % (data,) )
                ret = self.invalid_ipn(data)

        if ret:
            return ret
        else:
            #data['valid'] = False
            #data['custom'] = 'uptown1-TB119'
            #data['txn_id'] = 'TEST_TXN_!00'
            #return self.valid_ipn(data)
            #render_to_response('finished.html', {'data': data} )
            return HttpResponse('Nothing to see here!')


    def valid_ipn(self, data):
        """
        data has something like: (See: https://cms.paypal.com/us/cgi-bin/?cmd=_render-content&content_ID=developer/e_howto_admin_IPNIntro#id091F0M006Y4 )
            {
                'business': 'info@polyspeeddating.com',
                'charset': 'windows-1252',
                'cmd': '_notify-validate',
                'first_name': '',
                'last_name': '',
                'mc_currency': 'USD',
                'mc_fee': '0.01',
                'mc_gross': '0.01',
                'notify_version': '2.6',
                'payer_business_name': '...',
                'payer_email': 'payer@example.com',
                'payer_id': 'paypal id',
                'payer_status': 'verified',
                'payment_date': '11:45:00 Jan 30, 2011 PDT',
                'payment_fee': '',
                'payment_gross': '',
                'payment_status': 'Completed',
                'payment_type': 'instant',
                'receiver_email': 'info@polyspeeddating.com',
                'receiver_id': 'S8XGHLYDW9T3S',
                'residence_country': 'US',
                'txn_id': '61E67681CH3238416',
                'txn_type': 'express_checkout',
                'verify_sign': 'AtkOfCXbDm2hu0ZELryHFjY-Vb7PAUvS'
                'custom': 'uptown1-LM101'
            }
        """
        # do something with all this data.
        viewslogger.debug("paypal hit--using data: %s", data)

        if 'custom' in data:
            status = data['payment_status']
            if status != 'Completed':
                viewslogger.debug(" got non-completed paypal IPN with status: %s", status)
                return HttpResponse('Ignoring ' + status + ' response from paypal.')

            ec = data['custom']
            ec = ec.split( '-' )
            if len(ec) == 2:
                data['psdid'] = ec[1]
                data['event'] = ec[0]

                #find regrecord for psdid and event:
                viewslogger.debug(" getting regrecord for %s, %s", ec[1], ec[0])
                paidreg = RegRecord.objects.filter(psdid=ec[1], event=ec[0])
                if len(paidreg) == 0:
                    # no regrecord found or invalid psdid.
                    viewslogger.debug(" could not find regrecord for %s", data)
                    mail_managers( 'PayPal Failure: could not find psdid for payment', 'Data object %s' % (data,) )
                else:
                    viewslogger.debug(" updating regrecord for %s", ec[1])
                    rr = paidreg[0]
                    rr.paid = True
                    rr.addNote( "paypal transation id: " + data['txn_id'] )
                    rr.save()
                    viewslogger.debug( "going to send mail to managers about this transaction" )
                    email_bod=render(request, 'email/payment_email.txt', locals())
                    mail_managers( 'PayPal Payment for %s' % (rr.psdid,), email_bod.content )
            else:
                viewslogger.debug("invalid custom field")
                mail_managers( 'PayPal Failure: invalid custom field (or no custom field)', 'Data object %s' % (data,) )
        else:
            viewslogger.debug("missing custom field")
            mail_managers( 'PayPal Failure: invalid custom field (or no custom field)', 'Data object %s' % (data,) )

        return render(request, 'register/finished.html', {'data': data, 'valid':True})



    def invalid_ipn(self, data):
        # Log and bring out Reason?.
        return render(request, 'register/finished.html', {'data': data, 'valid':False})




