# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2019-01-07 15:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0006_event_numrounds'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='numrounds',
            field=models.IntegerField(default=0, verbose_name=b'Number of dating rounds (0 means unscheduled)'),
        ),
    ]
