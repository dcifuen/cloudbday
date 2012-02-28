# -*- coding: utf-8 -*-

from birthday.fields import ListField
from django.core.cache import cache
from django.db import models

class ClientManager(models.Manager):
    def get_from_cache(self):
        client = cache.get('client-data')
        if client is None:
            client = super(ClientManager, self).get(id=1)
            cache.set('client-data', client)
        return client

class Client(models.Model):
    APPS_STANDARD = 1
    APPS_PREMIER = 2
    APPS_EDU = 3
    APPS_EDITION_CHOICES = (
        (APPS_STANDARD, 'Google Apps (Free)'),
        (APPS_PREMIER, 'Google Apps for Business'),
        (APPS_EDU, 'Google Apps for Education'),
    )
    name = models.CharField(max_length=128, help_text="Name of the organization")
    domain = models.CharField(max_length=128, help_text="Google Apps primary domain of the organization")
    number_of_users = models.IntegerField(null=True, help_text="How many Google Apps users exists in the domain")
    apps_edition = models.IntegerField(choices=APPS_EDITION_CHOICES)
    administrators = ListField(models.EmailField(), help_text="Whom will be in change of creating and managing courses")
    module_template = models.CharField(blank=True, null=True, max_length=128, help_text="Google Site name that will act as the template to use when creating new modules")
    student_home_url = models.URLField(blank=True, null=True, verify_exists=False, help_text="Google Site address that will act as the student home page")
    test_max_tries = models.IntegerField(blank=True, null=True, help_text="Maximum number of chances the student get to do the same test")
    test_percent_to_approve = models.IntegerField(blank=True, null=True, help_text="Minimum score percentage in all test that the student has to get in order to approve")
    default_labels = ListField(models.CharField(max_length=40), help_text="List of tags or labels that will help identify the courses")
    naming_prefix = models.CharField(blank=True, null=True, max_length=128, help_text="Text to be used as prefix of email of groups created for new courses")
    naming_suffix = models.CharField(blank=True, null=True, max_length=128, help_text="Text to be used as suffix of email of groups created for new courses")
    
    #custom manager
    objects = ClientManager()
    
    def __unicode__(self):
        return self.domain
    
    def save(self, *args, **kwargs):
        self.id = 1
        cache.delete('client-data')
        return super(Client, self).save(*args, **kwargs)


class User(models.Model):
    first_name = models.CharField(max_length=40, blank=True, null=True, help_text="User's first or given name")
    last_name = models.CharField(max_length=40, blank=True, null=True, help_text="User's last name or surname")
    email = models.EmailField(help_text="Primary user's email address")
    icon_url = models.URLField(blank=True, null=True, verify_exists=False, help_text="Image URL for the user's avatar")
    is_admin = models.BooleanField(default=False, help_text="Is the user a CloudBDay administrator?")
    birth_day = models.IntegerField(blank=True, null=True, help_text="Day in which the user was born")
    birth_month = models.IntegerField(blank=True, null=True, help_text="Month in which the user was born")
    birth_year = models.IntegerField(blank=True, null=True, help_text="Year in which the user was born")
    receive_mail = models.BooleanField(default=True, help_text="Does the user want to receive email in his birthday?")
            
    def __unicode__(self):
        return self.email
