"""
Code for the checkbox object that translates checkbox checks to strings that can be stored in the database.

Also implements the preferential checkbox object that has two checkboxes for indicating strong preference.

For these objects, the options listed from the checkbox are pulled from the database. There is code in this
module to pull that information based on the name of the MatchQuestion.
"""

from django.utils.encoding import force_unicode
from itertools import chain
from django.forms.widgets import CheckboxInput
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django import forms

import logging
logger = logging.getLogger(__name__)


def get_preference_for(code_str, gen):
    """
    Return 1 if gen is one of the preference codes in code_str
    which is a csv seperated string with possible "-X" attached.  If "gen-X"
    found then return X
    """
    if not code_str:
        return 0

    gs = code_str.split( ",")
    for x in gs:
            sp = x.split("-")
            if sp[0] == gen:
                if len(sp) > 1:
                    return int(sp[1])
                else:
                    return 1

    return 0



def genSeekAndPrefs( code_str ):
    """
    Take coded preference string, e.g. "M-2,W,TF,Q-2" and
    turn it into a list of the codes, followed by those codes with
    weights greater than 1.

    If all codes have weights greater than one, renormalize.  Nothing
    is preferred if everything is.
    """
    if not code_str:
        return [[], []]

    new_value = [ x.split("-") for x in code_str.split(",") ]
    seeks = [ x[0] for x in new_value]
    prefs = [x[0] for x in new_value if len(x) > 1]
    #print "seeks", seeks
    #print "prefs", prefs
    if len(seeks) == len(prefs):
        prefs = []

    return [seeks, prefs]


def genCodeForSeekAndPrefs( seeks, prefs ):
    """
    Given two lists of gender codes, generate a new list of union of all codes
    with each code followed
    by "-2" if it appears in both lists.
    """
    pref_int = set(seeks).intersection(prefs)
    seek_un = set(seeks).union( prefs )
    seeks = []
    for s in seek_un:
            if s in pref_int:
                seeks.append( s + "-2" )
            else:
                seeks.append( s )

    return ",".join(seeks)




class PSDMultipleChoiceField(forms.MultipleChoiceField):
    def to_python(self, value):
        return value.split(",")

    def clean(self, value):
        return ",".join(value)

    def validate(self, value):
        pass

    def run_validators(self, value):
        pass




class PSDMultipleChoiceWithPrefField(forms.MultipleChoiceField):
    def to_python(self, value):
        #print "to python we go?", value
        return value.split(",")

    def clean(self, value):
        #print "Cleaning PSD with Pref"
        seeks = value[0]
        prefs = value[1]
        return genCodeForSeekAndPrefs( seeks, prefs )

    def validate(self, value):
        pass

    def run_validators(self, value):
        pass



class PSDYNCheckbox(forms.CheckboxInput):

    def render_to_list(self, name, value, attrs=None, choices=(), keep_desc=True):
        """
        Return list of HTML strings for each checkbox
        Param: value -- either a list of checkboxes to check off or a comma-seperated string of list checkboxes to check off.
        """
        print "PSD YN check: render_to_list(%s) value: %s\t\tattrs=%s\n\tchoices=%s" % (name, value, attrs, choices)

        if value is None: value = []
        if not isinstance(value, list):
            if isinstance(value,int):
                value = [value]
            else:
                value = value.split(",")

        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        #print "\tfinal_attrs = %s" % ( final_attrs, )
        output = []
        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])
        print "\tstr_values = %s" % ( str_values, )

        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = u' for="%s"' % final_attrs['id']
            else:
                label_for = ''

            cb = CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            rendered_cb = cb.render(name, option_value)
            if keep_desc:
                option_label = conditional_escape(force_unicode(option_label))
            else:
                option_label = ""
            #print "option_value", option_value
            #print "rendered_cb", rendered_cb
            #print "label_for", label_for
            output.append(u'<label%s>%s%s</label>' % (label_for, rendered_cb, option_label))

        return output

    def render(self, name, value, attrs=None, choices=() ):
        #print "render(%s) value: %s\t\tattrs=%s\n\tchoices=%s" % (name, value, attrs, choices)

        lst = self.render_to_list( name, value, attrs, choices )
        output = []
        for s in lst:
            output.append( "<li>" + s + "</li>" )

        op = u'<ul style="list-style: none;">\n' + u'\n'.join(output) + "\n</ul>"
        return mark_safe( op )


#
# class PSDSelect(forms.Select):
#
#     def __init__(self, attrs=None, choices=()):
#         super(Select, self).__init__(attrs)
#         # choices can be any iterable, but we may need to render this widget
#         # multiple times. Thus, collapse it into a list so it can be consumed
#         # more than once.
#         self.choices = list(choices)
#
#     def render(self, name, value, attrs=None, choices=()):
#         if value is None:
#             value = ''
#         final_attrs = self.build_attrs(attrs, name=name)
#         output = [format_html('<select{0}>', flatatt(final_attrs))]
#         options = self.render_options(choices, [value])
#         if options:
#             output.append(options)
#         output.append('</select>')
#         return mark_safe('\n'.join(output))
#
#     def render_option(self, selected_choices, option_value, option_label):
#         if option_value is None:
#             option_value = ''
#         option_value = force_text(option_value)
#         if option_value in selected_choices:
#             selected_html = mark_safe(' selected="selected"')
#             if not self.allow_multiple_selected:
#                 # Only allow for a single selection.
#                 selected_choices.remove(option_value)
#         else:
#             selected_html = ''
#         return format_html('<option value="{0}"{1}>{2}</option>',
#                            option_value,
#                            selected_html,
#                            force_text(option_label))
#
#     def render_options(self, choices, selected_choices):
#         # Normalize to strings.
#         selected_choices = set(force_text(v) for v in selected_choices)
#         output = []
#         for option_value, option_label in chain(self.choices, choices):
#             if isinstance(option_label, (list, tuple)):
#                 output.append(format_html('<optgroup label="{0}">', force_text(option_value)))
#                 for option in option_label:
#                     output.append(self.render_option(selected_choices, *option))
#                 output.append('</optgroup>')
#             else:
#                 output.append(self.render_option(selected_choices, option_value, option_label))
#         return '\n'.join(output)




class PSDCheckboxSelectOneOnly(forms.CheckboxSelectMultiple):
    """
    This class only renders one of a possible set of checkboxes so as to get the "kinky" y/n checkbox with
    dropdownlist for seek

    It is a total hack and I am not happy.  Note the exit out of the for loop after the first pass!!!
    Not sure the correct way to do this and keep the ids being passed for match answers

    The first option is considered to be yes everywhere, btw.
    """

    def render_to_list(self, name, value, attrs=None, choices=(), keep_desc=False):
        """
        Return list of HTML strings for each checkbox
        Param: value -- either a list of checkboxes to check off or a comma-seperated string of list checkboxes to check off.
        """
        #print "render_to_list(%s) value: %s\t\tattrs=%s\n\tchoices=%s" % (name, value, attrs, choices)

        if value is None: value = []
        if not isinstance(value, list):
            if isinstance(value,int):
                value = [value]
            else:
                value = value.split(",")

        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        #print "\tfinal_attrs = %s" % ( final_attrs, )
        output = []
        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])
        #print "\tstr_values = %s" % ( str_values, )

        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = u' for="%s"' % final_attrs['id']
            else:
                label_for = ''
            #print( "Final attrs = '%s'" % (final_attrs,) )
            cb = CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            #print( "name = '%s' / option_value = '%s'" % (name, option_value,) )
            rendered_cb = cb.render(name, option_value)
            if keep_desc:
                option_label = conditional_escape(force_unicode(option_label))
            else:
                option_label = ""
            #print "option_value", option_value
            #print "rendered_cb", rendered_cb
            #print "label_for", label_for
            output.append(u'<label%s>%s%s</label>' % (label_for, rendered_cb, option_label))
            break

        return output

    def render(self, name, value, attrs=None, choices=() ):
        #print "render(%s) value: %s\t\tattrs=%s\n\tchoices=%s" % (name, value, attrs, choices)

        lst = self.render_to_list( name, value, attrs, choices )
        #print "Returning html of '%s'" % (lst, )
        return mark_safe( lst[0] )




class PSDCheckboxSelectMultiple(forms.CheckboxSelectMultiple):

    def render_to_list(self, name, value, attrs=None, choices=(), keep_desc=True):
        """
        Return list of HTML strings for each checkbox
        Param: value -- either a list of checkboxes to check off or a comma-seperated string of list checkboxes to check off.
        """
        #print "render_to_list(%s) value: %s\t\tattrs=%s\n\tchoices=%s" % (name, value, attrs, choices)

        if value is None: value = []
        if not isinstance(value, list):
            if isinstance(value,int):
                value = [value]
            else:
                value = value.split(",")

        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        #print "\tfinal_attrs = %s" % ( final_attrs, )
        output = []
        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])
        #print "\tstr_values = %s" % ( str_values, )

        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = u' for="%s"' % final_attrs['id']
            else:
                label_for = ''

            cb = CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            rendered_cb = cb.render(name, option_value)
            if keep_desc:
                option_label = conditional_escape(force_unicode(option_label))
            else:
                option_label = ""
            #print "option_value", option_value
            #print "rendered_cb", rendered_cb
            #print "label_for", label_for
            output.append(u'<label%s>%s%s</label>' % (label_for, rendered_cb, option_label))

        return output

    def render(self, name, value, attrs=None, choices=() ):
        #print "render(%s) value: %s\t\tattrs=%s\n\tchoices=%s" % (name, value, attrs, choices)

        lst = self.render_to_list( name, value, attrs, choices )
        output = []
        for s in lst:
            output.append( "<li>" + s + "</li>" )

        op = u'<ul style="list-style: none;">\n' + u'\n'.join(output) + "\n</ul>"
        return mark_safe( op )



class PSDPrefCheckboxWidget(forms.MultiWidget):
    """
    A widget that gives two checkboxes for each option.
    """
    def __init__(self,  attrs=None, choices=()):
        #print "Constructor of PSDPrefCheckboxWidget"
        #print "\tchoices", choices
        #print "\tattrs", attrs
        choices = getPSDCheckboxOptions("Gender")
        widgets = (PSDCheckboxSelectMultiple(attrs=attrs, choices=choices),
                    PSDCheckboxSelectMultiple(attrs=attrs, choices=choices))
        super(PSDPrefCheckboxWidget, self).__init__(widgets, attrs)

    def compress(self,value):
        #print "compressing", value
        return value

    def decompress(self, value):
        #print "decompressing", value
        return genSeekAndPrefs( value )


    def render(self, name, value, attrs=None):
        # value is a list of values, each corresponding to a widget
        # in self.widgets.
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        mx = len(self.widgets)
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
            output.append(widget.render_to_list(name + '_%s' % i, widget_value, final_attrs, keep_desc=(i==mx-1)))
        return mark_safe(self.format_output(output))
    
    

    def format_output(self, rendered_widgets):
        """
        Given a list of rendered widgets (as strings), returns a Unicode string
        representing the HTML for the whole lot.

        This hook allows you to format the HTML design of the widgets, if
        needed.
        """
        output = []
        for (i, wid1) in enumerate(rendered_widgets[0]):
            output.append( "<li>" + rendered_widgets[0][i] + rendered_widgets[1][i] + "</li>" )

        op = u'<ul style="list-style: none;">\n' + u'\n'.join(output) + "\n</ul>"
        #print op
        return op


class ModelSetupError(Exception):
    """
    Used when a model is not what it should be due to admin configurations
    """
    def __init__(self, value, response_object = None):
        self.value = value
        self.response = response_object

    def __str__(self):
        return repr(self.value)


def getSeekFormField(quest):
    from register.matchq_models import MatchQuestion   # avoid circular import
    try:
        locs = MatchQuestion.objects.get( question=quest )
        if locs.allow_preferences:
            #print "returning preference checkbox"
            return PSDMultipleChoiceWithPrefField(choices=lambda: getPSDCheckboxOptions(quest), widget=PSDPrefCheckboxWidget, label=quest+" Sought")
        else:
            #print "returning no-preference checkbox"
            return PSDMultipleChoiceField(choices=lambda: getPSDCheckboxOptions(quest), widget=PSDCheckboxSelectMultiple, label=quest+" Sought")
    except Exception:
        logger.error( "Failed to load %s field in getSeekFormField()" % (quest,) )
        # raise
    logger.warning( "Attempting to return default of no preference for seek" )
    return PSDMultipleChoiceWithPrefField(choices=lambda: getPSDCheckboxOptions(quest), widget=PSDPrefCheckboxWidget, label=quest+" Sought")


def getPSDCheckboxOptions( quest, no_desc=False ):
    """
    This method fetches all the possible responses to a given question as defined by 'quest'
    It looks up this info in the MatchQuestion object.  Each MatchChoice connected to it has a
    (up to) two-letter code and a longer string for the response.   Can make defaults using the
    psdmanage.py code in toplevel

    Param no_desc: don't return any description strings.
    
    Returns: list of pairs of (code,description)
    """
    from register.matchq_models import MatchQuestion   # avoid circular import
    try:
        locs = MatchQuestion.objects.get(question=quest)
    except Exception:
        return (('UK', 'Unknown'), ('ML', 'Make "%s" match question' % (quest,)), ('SR', 'Sorry for the ugly'))

    locchoice = locs.matchchoice_set.all()

    if no_desc:
        tups = [(loc.choice_code, "") for loc in locchoice]
    else:
        tups = [(loc.choice_code, loc.choice) for loc in locchoice]

    return tups










