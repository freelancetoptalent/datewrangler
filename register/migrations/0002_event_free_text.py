# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-05-28 15:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='free_text',
            field=models.BooleanField(default=False, verbose_name=b'Have the free text question for matching?'),
        ),
    ]
