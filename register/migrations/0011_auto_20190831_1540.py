# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2019-08-31 19:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0010_person_pronoun_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='pronoun_slug',
            field=models.CharField(blank=True, default=b'', max_length=30, verbose_name=b'Pronoun Slug'),
        ),
    ]