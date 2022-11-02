# views.py
"""
Code for dynamic streaming output to a webpage

Ideally this code allows some of her iterators which, for example, calculate matches for records, record by record,
to print out status as the iterator goes down the list in real time so that administrators can monitor progress.
"""

import pdb, itertools
import register.demographics
import traceback

from functools import partial
from Queue import Queue
from threading import Thread
import time
import sys

from django.shortcuts import render_to_response
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.template import RequestContext

from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound

from register.models import Person, RegRecord, fetch_regrecord
from register.schedule_models import BreakRecord, DateRecord, CruiseRecord
from register.system_models import Event
from register.table_models import TableRecord

from register.views.printouts import make_schedules
# from psd.RcodeHooks import print_demographics, print_demographics_async, schedule_async
from django.core.urlresolvers import reverse
from register.forms import ScheduleForm, NextSheetForm
from django.forms.models import modelformset_factory
from django.forms.formsets import formset_factory
from register.forms import BreakForm, MultiBreakForm, CruiseForm

import register.views.contact


from django.http import HttpResponse, StreamingHttpResponse


def HttpStreamTextResponse( yield_generator, event_name, headers=True, head_string="", ACTIONS=None ):
    """
    Wrap the output from a yield_generator of text with some html so it renders pretty
    We use  'yield' generator so we can have django render the html to the screen as it
    is generated, so the user does not worry about it never showing up.
    Use async_print_text_response to get a async yeild-generator so this works, if the process
    can take awhile.
    """

    head = ( "<h1>Streaming Function Call Wrangler</h1>\noutput should appear on screen as it is generated<hr>",
             head_string,
             "<pre>", )
    act_menu = render_to_response( 'dashboard/event_manager_actions.txt', {'event_name':event_name, 'actions':ACTIONS} )
    tail = ( "</pre><hr>\n", act_menu.content, "\n<hr>\n" )

    if yield_generator != None:
        if headers:
            return StreamingHttpResponse( itertools.chain( head, yield_generator, tail ) )
        else:
            return StreamingHttpResponse( yield_generator )
    else:
        return HttpResponse( itertools.chain( head, ["Failure to launch/call process.\n", "Sorry"], tail ) )







def async_print_text_response(f):
    """
    Wraps a no-argument python function that prints to the console, and
    returns those results as an iterator of strings via yield
    """

    class WritableObject:
        def __init__(self, the_q):
            self.q = the_q
        def write(self, string):
            self.q.put(string)

    def daemon_func(q):
        #sys.stderr.write( "Daemon func\n" )
        printed = WritableObject(q)
        sys.stdout = printed
        try:
            f()
        except Exception as inst:
            #sys.stderr.write( "\nFAIL!\n\t'%s'\n\n" % (inst, ) )
            q.put( "Daemon_Func f's Exception '%s'" % (inst, ) )
            traceback.print_exc()
            #print traceback.format_exec()
        q.put( "*END PROCESS*")
        # clean up
        sys.stdout = sys.__stdout__

    q = Queue()
    thr = Thread(target=daemon_func, args=(q,) )
    thr.start()
    sys.stderr.write( "Thread started\n" )
    done = False
    while not done:
        #sys.stderr.write( "waiting for thread\n" )
        str = q.get()
        if str == "*END PROCESS*":
            done = True
        else:
            yield str #['<br>' if c == '\n' else c for c in str ]



def HttpStreamTextResponsePrint( f, event_name, headers=True, head_string="", ACTIONS=None ):
    """
    Wrap the output from the function f (no arguments) with some html so it renders pretty
    We use the 'yield' generator so we can have django render the html to the screen as it
    is generated, so the user does not worry about it never showing up.
    """

    head = ( "<h1>Streaming Function Call Wrangler</h1>\noutput should appear on screen as it is generated<hr>",
             head_string,
             "<pre>", )
    act_menu = render_to_response( 'event_manager_actions.txt', {'event_name':event_name, 'actions':ACTIONS} )
    tail = ( "</pre><hr>\n", act_menu.content, "\n<hr>\n" )

    if f != None:
        if headers:
            return HttpResponse( itertools.chain( head, async_print_text_response(f), tail ) )
        else:
            return HttpResponse( async_print_text_response(f) )
    else:
        return HttpResponse( itertools.chain( head, ["Failure to launch/call process.\n", "Sorry"], tail ) )






def console_test():
    def playprintpipe():
        for i in range(30):
            print "line %s\n" % (i, )
            time.sleep(1)

    tk = async_print_text_response( playprintpipe )
    a = tk()
    for x in a:
        sys.stderr.write( x )






def print_http_response(f):
    """
    A Decorator
    Wraps a python function that prints to the console, and
    returns those results as a HttpResponse (HTML)
    """

    class WritableObject:
        def __init__(self):
            self.content = []
        def write(self, string):
            self.content.append(string)

    def new_f(*args, **kwargs):
        printed = WritableObject()
        sys.stdout = printed
        f(*args, **kwargs)
        sys.stdout = sys.__stdout__
        return HttpResponse(['<br>' if c == '\n' else c for c in printed.content ])
    return new_f


@print_http_response
def test_function_http_resp(request):
       print "some output here"
       for i in [1, 2, 3]:
          print i


def playpipe():
    for i in range(30):
        yield "line %s\n" % (i, )
        time.sleep(1)


def test_function(request):
       return HttpResponse( playpipe() )


