# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2019-08-29 23:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0009_matchquestion_yes_only'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='pronoun_slug',
            field=models.CharField(default=b'', max_length=30, verbose_name=b'Pronoun Slug'),
        ),
    ]
