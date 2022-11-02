import random
import re
from django.utils.safestring import mark_safe
from django.template.defaultfilters import stringfilter
from django import template

register = template.Library()

@register.filter
def times12(input):
    return 12 * int(input)

@register.filter
def looprange(i):
    return range(1, int(i) + 1)

@register.filter
def randint(i):
    return random.randint(0, i+1)

@register.filter
def randrobot():
    return random.randint(1, 9)



@register.filter
@stringfilter
def paypalrefund(notes):
    if notes is None:
        return None


    (n2,cnt) = re.subn('stripe payment intent: (\w*)', '\g<1>', str(notes) )

    if cnt > 1:
        return "multiple matches"
    elif cnt == 1:
        return mark_safe("https://dashboard.stripe.com/payments/%s" % (n2, ) )
    elif cnt == 0:
        #print( "notes= '%s'" % (notes,) )
        (n2,cnt) = re.subn('paypal transation id: (\w*)', '\g<1>', str(notes) )

        # print( "n2 = '%s'" % (n2,) )
        if cnt == 1:
            return mark_safe("https://www.paypal.com/us/cgi-bin/webscr?cmd=_view-a-trans&id=%s" % (n2,))
        elif cnt > 1:
            return "multiple matches"
        else:
            return None






@register.filter
def cleannotefield(notes):
    return "Boo!"


@register.filter
@stringfilter
def cleannotefield_bad(notes):
    print "chking %s" % (notes, ) 
    if notes is None:
        return None
    
    print re.sub( 'paypal \w+ id: \w+\W+', '', notes )
    return re.sub( 'paypal \w+ id: \w+\W+', '', notes )
    
