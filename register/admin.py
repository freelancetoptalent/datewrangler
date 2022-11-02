"""
Overrides for the important objects in the DateWrangler system so the Django admin interface gets customized and easier to use.

These overrides will define, for example, what fields are available for editing when browsing RegRecord objects.
"""

from django.contrib import admin
from register.system_models import Organization, Event, TranslationRecord
from register.schedule_models import LinkRecord, CruiseRecord, DateRecord, BreakRecord
from register.matchq_models import MatchQuestion, MatchChoice, Response
from register.models import Person, RegRecord
from register.table_models import TableListRecord, TableRecord, RecessRecord
from register.forms import PersonForm, RegRecordForm, DateRecordForm, EventForm
from matchmaker.models import MatchRecord, MatchRecordForm

import re
#from batchadmin.admin import BatchModelAdmin
from django.core.urlresolvers import reverse
import sys
import logging
logger = logging.getLogger('register.admin')


## For some reason, using 'gender' in list_display shows the full name ('man', 'woman')
## if a person has one gender, and 'None' if they have several. This works better.
def gender(p):
    return p.gender

class MyPerson(admin.ModelAdmin):
    form = PersonForm
    list_display = (unicode, 'psdid', 'age', gender)
    list_filter = ('gender',)
    search_fields = ['psdid', 'first_name', 'last_name']

class MyDateRecord(admin.ModelAdmin):
    form = DateRecordForm
    search_fields = ['psdid']
    list_filter = ('event', 'friend_date')
    list_display = ('psdid', 'other_psdid', 'round','__unicode__', 'filled', 'table')
    fields = ('psdid', 'other_psdid', 'friend_date', 'said_yes', 'they_said_yes', 'event', 'table', 'round', 'notes')


class MyMatchRecord(admin.ModelAdmin):
    form = MatchRecordForm
    search_fields = ['psdid1','psdid2']
    list_filter = ('event',)



#see https://docs.djangoproject.com/en/dev/ref/contrib/admin/#inlinemodeladmin-objects
# class PersonInline(admin.StackedInline):
#    model = RegRecord.people.through
#    extra = 0




class MyReg(admin.ModelAdmin):
    form = RegRecordForm
    list_filter = ('paid','cancelled','here','event','matches')
    search_fields = ['psdid', 'email']
    exclude = ('matches', 'oneway','people',)
    list_display = ('__unicode__', 'matches', 'oneway', 'pending', 'cancelled', 'paid', 'here')
    fieldsets = [(None, {'fields':['event','psdid','nickname','email']}),
              ('Admin', {'fields':['add_to_mailings', 'here', 'paid', 'pending', 'cancelled','stationary', 'is_staff']}),
              ('Children',{'fields':['wants_childcare','children'], 'classes':['collapse']}),
                 ('Other', {'fields':['groups_match_all', 'volunteers_ok']} ),
              (None, {'fields':['comments','notes','referred_by']}) ]
    #    inlines = [PersonInline]
    actions = ['mark_as_paid','mark_as_cancelled']

    def mark_as_paid(self, request, queryset):
        rows_up = queryset.update(paid=True)
        if rows_up == 1:
            message_bit = "1 record marked as paid"
        else:
            message_bit = "%s records marked as paid" % rows_up
        self.message_user(request, message_bit)


    def mark_as_cancelled(self, request, queryset):
        rows_up = queryset.update(cancelled=True)
        if rows_up == 1:
            message_bit = "1 record marked as cancelled"
        else:
            message_bit = "%s records marked as cancelled" % rows_up
        self.message_user(request, message_bit)





class MyEvent(admin.ModelAdmin):
    form = EventForm
    search_fields = ('event', 'longname',)
    list_display = (unicode, 'manage_link', 'event', 'longname', )
    list_filter = ('date',)

    actions = ['duplicate_event']

    def manage_link(self,obj):
        #print "Got %s" % (obj, )
        try:
            manage_link = reverse( "event-manager", kwargs={'event_name':obj.event} )
            return '<a href="%s">Manage</a>' % ( manage_link, )
        except:
            logger.error( "manage_link failure: %s " % (obj, ) )
            logger.error( "     error: %s" % (sys.exc_info()[0], ) )
            return 'Link Broken'
    manage_link.allow_tags = True
    manage_link.short_description = 'Manage this event'


  #  domain_link.allow_tags = True
  #  domain_link.short_description = "short description of some sort"

    def duplicate_event(self, request, queryset):
        for obj in queryset:
            obj.id = None
            epts = re.split( '(\d+)', obj.event )
            if len(epts) > 1:
                epts[ len( epts) - 2 ] = str( int(epts[ len( epts) - 2 ]) + 1)
                obj.event = ''.join( epts )
            else:
                obj.event = obj.event + "2"

            obj.save()
        message_bit = "%s events duplicated.  Be sure to configure " % len(queryset)
        self.message_user(request, message_bit )
    duplicate_event.short_description = "Duplicate selected events"

   # def __init__(self,*args,**kwargs):
   #     super(MyEvent, self).__init__(*args, **kwargs)
   #     self.list_display_links = (None, )


# class PersonInline(admin.StackedInline):
#    model = Person
#    extra = 3
#
# class RegRecAdmin(admin.ModelAdmin):
# inlines = [PersonInline]
# fieldsets = [
#     (None,               {'fields': ['question']}),
#     ('Date information', {'fields': ['pub_date'], 'classes': ['collapse']}),
# ]

#admin.site.register(RegRecord, RegRecAdmin)


class MatchChoiceInline(admin.TabularInline):
    model = MatchChoice
    extra = 6

class MatchQuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'question_code', 'num_choices')
    inlines = [MatchChoiceInline]
    search_fields = ['question']


#class MyTableAdmin(BatchModelAdmin):
#   list_filter = ('event','statOK','groupOK')
#   list_display = ('event', '__unicode__', 'statOK', 'groupOK')

class MyTableInline(admin.TabularInline):
    model = TableRecord
    extra = 10
#list_filter = ('event','statOK','groupOK')
 #  list_display = ('event', '__unicode__', 'statOK', 'groupOK')

class MyTableListAdmin(admin.ModelAdmin):
    inlines=[MyTableInline]


class MyTranslationRecord(admin.ModelAdmin):
    model = TranslationRecord


admin.site.register(TranslationRecord, MyTranslationRecord)
admin.site.register(Organization)
admin.site.register(Person, MyPerson)
admin.site.register(RegRecord, MyReg)
admin.site.register(DateRecord, MyDateRecord)
admin.site.register(MatchRecord, MyMatchRecord)
admin.site.register(BreakRecord)
admin.site.register(CruiseRecord)
admin.site.register(LinkRecord)
admin.site.register(TableListRecord, MyTableListAdmin)
admin.site.register(Event, MyEvent)
admin.site.register( MatchQuestion, MatchQuestionAdmin )
admin.site.register( MatchChoice )
admin.site.register(RecessRecord)
admin.site.register(Response)
