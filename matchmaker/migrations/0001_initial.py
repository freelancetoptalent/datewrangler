# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-07-10 03:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='MatchRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('psdid1', models.CharField(max_length=30, verbose_name=b"subject's PSDID")),
                ('psdid2', models.CharField(max_length=30, verbose_name=b"object's PSDID")),
                ('event', models.CharField(blank=True, max_length=15)),
                ('match', models.PositiveIntegerField(verbose_name=b'Likability')),
                ('gay_ok', models.BooleanField(verbose_name=b'Gay Round Okay')),
                ('str_ok', models.BooleanField(verbose_name=b'Straight Round Okay')),
            ],
        ),
    ]