# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-07-10 03:58
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.CreateModel(
            name='BreakRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('friend_ok', models.BooleanField(default=False, verbose_name=b'Friendship Date Still Okay (Y/N)')),
                ('psdid', models.CharField(blank=True, max_length=12)),
                ('other_psdid', models.CharField(blank=True, max_length=12)),
                ('notes', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='CruiseRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('psdid', models.CharField(blank=True, max_length=7)),
                ('other_psdid', models.CharField(blank=True, max_length=7)),
                ('event', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='DateRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('friend_date', models.BooleanField(default=True, verbose_name=b'Date was a Friendship Date (Y/N)')),
                ('psdid', models.CharField(blank=True, max_length=12)),
                ('other_psdid', models.CharField(blank=True, max_length=12)),
                ('table', models.CharField(blank=True, max_length=12)),
                ('round', models.PositiveIntegerField(verbose_name=b'Dating Round')),
                ('event', models.CharField(max_length=20)),
                ('said_yes', models.NullBooleanField(default=True, verbose_name=b'psdid said YES to other_psdid (Y/N)')),
                ('they_said_yes', models.NullBooleanField(default=True, verbose_name=b'other_psdid said YES to psdid (Y/N)')),
                ('notes', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='DateSheetNote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('psdid', models.CharField(blank=True, max_length=12)),
                ('event', models.CharField(max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event', models.CharField(max_length=20)),
                ('longname', models.CharField(max_length=40)),
                ('location', models.CharField(max_length=100)),
                ('address', models.CharField(max_length=100)),
                ('locationURL', models.CharField(max_length=100)),
                ('accessdetails', models.TextField(max_length=200)),
                ('cost', models.PositiveIntegerField(verbose_name=b'Cost per person')),
                ('doorcost', models.PositiveIntegerField(verbose_name=b'Cost per person at door')),
                ('payment_systems', models.CharField(max_length=40, verbose_name=b'List of payment systems that are turned on')),
                ('paypal_email', models.EmailField(max_length=254, verbose_name=b'Email for paypal account')),
                ('wepay_email', models.EmailField(max_length=254, verbose_name=b'Email for wepay account')),
                ('info_email', models.EmailField(max_length=254, verbose_name=b'Email for asking registration questions')),
                ('mailing_list_url', models.CharField(max_length=100, verbose_name=b'Link to the mailing list for this event')),
                ('homepage_url', models.CharField(max_length=100, verbose_name=b'Link to the home page for this event or event organizers')),
                ('has_childcare', models.BooleanField(default=False, verbose_name=b'Childcare will be provided at the event')),
                ('regclosed', models.BooleanField(default=False, verbose_name=b'Registration is closed---no additions allowed')),
                ('regfrozen', models.BooleanField(default=False, verbose_name=b'Registration is frozen--no updating of registration forms allowed')),
                ('no_ssm', models.BooleanField(default=False, verbose_name=b'Single straight men will be asked to bring a gender-balance companion')),
                ('no_emailing', models.BooleanField(default=False, verbose_name=b'Do not email update emails or admin log emails (check if there is no internet service).')),
                ('date', models.DateField()),
                ('starttime', models.TimeField()),
                ('deadlinetime', models.TimeField()),
                ('stoptime', models.TimeField()),
            ],
        ),
        migrations.CreateModel(
            name='LinkRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('psdid', models.CharField(blank=True, max_length=12)),
                ('psdid_alias', models.CharField(blank=True, max_length=12)),
            ],
        ),
        migrations.CreateModel(
            name='MatchChoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('choice', models.CharField(max_length=200)),
                ('choice_code', models.CharField(max_length=2)),
            ],
        ),
        migrations.CreateModel(
            name='MatchQuestion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=200)),
                ('explanation', models.CharField(max_length=200, null=True)),
                ('internal_comment', models.CharField(max_length=200, null=True)),
                ('hard_match', models.BooleanField(default=False)),
                ('strict_subset_match', models.BooleanField(default=False)),
                ('checkbox', models.BooleanField(default=False)),
                ('ask_about_seek', models.BooleanField(default=False)),
                ('include_name', models.BooleanField(default=False)),
                ('question_code', models.CharField(max_length=15)),
                ('is_YN', models.BooleanField(default=False)),
                ('allow_preferences', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('info_email', models.EmailField(max_length=254, verbose_name=b'Email for asking registration questions')),
                ('mailing_list_url', models.CharField(max_length=100, verbose_name=b'Link to the mailing list for the organization')),
                ('homepage_url', models.CharField(max_length=100, verbose_name=b'Link to the home page for the organization')),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sites.Site')),
            ],
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=30, verbose_name=b'First Name')),
                ('last_name', models.CharField(max_length=30, verbose_name=b'Last Name')),
                ('gender', models.CharField(max_length=40, verbose_name=b'Gender')),
                ('seek_gender', models.CharField(max_length=50, verbose_name=b'Genders Sought')),
                ('age', models.PositiveIntegerField(verbose_name=b'Age')),
                ('seek_age_min', models.PositiveIntegerField(verbose_name=b'Minimum Age Wanted')),
                ('seek_age_max', models.PositiveIntegerField(verbose_name=b'Maximum Age Wanted')),
                ('psdid', models.CharField(blank=True, max_length=12)),
                ('text_match', models.TextField(blank=True, verbose_name=b'Match Criterion')),
            ],
        ),
        migrations.CreateModel(
            name='RecessRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('psdid', models.CharField(blank=True, max_length=12)),
                ('event', models.CharField(max_length=15)),
                ('rounds', models.CharField(max_length=30)),
                ('kind', models.CharField(max_length=20)),
                ('volatile', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='RegRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nickname', models.CharField(max_length=30, verbose_name=b'Nickname')),
                ('email', models.EmailField(max_length=254, verbose_name=b'Email')),
                ('add_to_mailings', models.BooleanField(default=True, verbose_name=b'Join Our Mailing List (Y/N)')),
                ('seek_groups', models.BooleanField(verbose_name=b'Date Groups (Y/N)')),
                ('groups_match_all', models.BooleanField(default=True, verbose_name=b'All Group Members Must Match (Y/N)')),
                ('friend_dates', models.BooleanField(default=False, verbose_name=b'Friend Dates (Y/N)')),
                ('referred_by', models.CharField(blank=True, max_length=30, verbose_name=b'Referred By')),
                ('pals', models.TextField(blank=True, verbose_name=b'Friends')),
                ('location', models.CharField(blank=True, max_length=30, verbose_name=b'Location')),
                ('wants_childcare', models.BooleanField(default=False, verbose_name=b'Need Childcare (Y/N)')),
                ('children', models.TextField(blank=True, verbose_name=b'Children')),
                ('comments', models.TextField(blank=True, verbose_name=b'Comments')),
                ('event', models.CharField(blank=True, max_length=15)),
                ('psdid', models.CharField(blank=True, max_length=12)),
                ('paid', models.BooleanField(default=False)),
                ('cancelled', models.BooleanField(default=False)),
                ('pending', models.BooleanField(default=False)),
                ('here', models.BooleanField(default=False)),
                ('stationary', models.BooleanField(default=False)),
                ('is_group', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True)),
                ('matches', models.IntegerField(blank=True, default=0, null=True)),
                ('oneway', models.IntegerField(blank=True, default=0, null=True)),
                ('people', models.ManyToManyField(blank=True, to='register.Person')),
            ],
        ),
        migrations.CreateModel(
            name='Response',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answers', models.ManyToManyField(to='register.MatchChoice')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='register.Person')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='register.MatchQuestion')),
                ('seek_answers', models.ManyToManyField(related_name='seek_response_set', to='register.MatchChoice')),
            ],
        ),
        migrations.CreateModel(
            name='TableListRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event', models.CharField(blank=True, max_length=15)),
            ],
        ),
        migrations.CreateModel(
            name='TableRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=12)),
                ('statOK', models.BooleanField(default=False, verbose_name=b'Okay for stationary folks (Y/N)')),
                ('groupOK', models.BooleanField(default=False, verbose_name=b'Okay for groups (Y/N)')),
                ('quality', models.PositiveIntegerField(verbose_name=b'Quality')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='register.TableListRecord')),
            ],
        ),
        migrations.CreateModel(
            name='TranslationRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('base_word', models.CharField(blank=True, max_length=50)),
                ('synonym', models.CharField(blank=True, max_length=50)),
            ],
        ),
        migrations.AddField(
            model_name='matchchoice',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='register.MatchQuestion'),
        ),
        migrations.AddField(
            model_name='event',
            name='extra_questions',
            field=models.ManyToManyField(blank=True, to='register.MatchQuestion'),
        ),
    ]