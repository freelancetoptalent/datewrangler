
from django.db import models
from django.forms import ModelForm
from django import forms

import logging
logger = logging.getLogger('psd.matchmaker.models')


class MatchRecord( models.Model ):
    psdid1 = models.CharField(max_length=30, verbose_name="subject's PSDID")
    psdid2 = models.CharField(max_length=30, verbose_name="object's PSDID")
    event = models.CharField(max_length=15, blank=True)
    match = models.PositiveIntegerField(verbose_name="Likability")
    gay_ok = models.BooleanField(verbose_name="Gay Round Okay")
    str_ok = models.BooleanField(verbose_name="Straight Round Okay")

#    def __init__(self,event,psdid1,psdid2,match,gay_ok,str_ok):
#        self.psdid1=psdid1
#        self.psdid2=psdid2
#        self.event=event
#        self.match=match
#        self.gay_ok=gay_ok
#        self.str_ok=str_ok

    def __unicode__(self):
        return self.psdid1 + "-" + self.psdid2 + ": " + self.score_string()

    def score_string(self):
        strg = str(self.match) + "/"
        if self.gay_ok:
            strg += "G"
        if self.str_ok:
            strg += "S"
        return strg








class MatchRecordForm(ModelForm):
    psdid1 = forms.CharField(widget=forms.TextInput(attrs={'side':8}))
    psdid2 = forms.CharField(widget=forms.TextInput(attrs={'side':8}))
#    event = forms.CharField(max_length=15, blank=True)
#    match = forms.PositiveIntegerField(verbose_name="Likability")
#    gay_ok = forms.BooleanField(verbose_name="Gay Round Okay")
#    str_ok = forms.BooleanField(verbose_name="Straight Round Okay")

    class Meta:
        model = MatchRecord
        exclude = []

