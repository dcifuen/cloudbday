"""
models.py

App Engine NDB datastore models

"""
from datetime import datetime, timedelta
import logging
import re

from google.appengine.api.datastore_errors import BadValueError
from google.appengine.ext import ndb
from google.appengine.api import memcache

from birthday import constants


def validate_email(prop, value):
    value = value if value else None
    if value is None:
        return value
    elif not re.match(constants.EMAIL_REGEXP, value):
        raise BadValueError
    return value.lower()


def validate_name(prop, value):
    """
    Validates the length of the name, change it to title case. Should be
    encoded in UTF8
    """
    if value is None:
        return value
    if len(value) > 60:
        raise BadValueError
    return value.decode('utf-8').title()


def validate_month(property, value):
    #Months should be from January(1) to December(12)
    if value is None or 1 <= value <= 12:
        return value
    raise BadValueError


def validate_current_past_year(property, value):
    #Check that the year is not on the future
    current_year = datetime.now().year
    if value is None or value <= current_year:
        return value
    raise BadValueError


class ExampleModel(ndb.Model):
    """Example Model"""
    example_name = ndb.StringProperty(required=True)
    example_description = ndb.TextProperty(required=True)
    added_by = ndb.UserProperty()
    timestamp = ndb.DateTimeProperty(auto_now_add=True)


class Client(ndb.Model):
    #TODO: validator=validate_domain
    primary_domain_name = ndb.StringProperty(indexed=False)
    administrators = ndb.StringProperty(indexed=False, repeated=True, validator=validate_email)
    from_name = ndb.StringProperty(indexed=False, validator=validate_name)
    subject = ndb.StringProperty(indexed=False)
    reply_to = ndb.StringProperty(indexed=False, validator=validate_email)
    customer_id = ndb.StringProperty(indexed=False)
    #OAuth credentials and token for the domain
    credentials = ndb.TextProperty(indexed=False)
    refresh_token = ndb.StringProperty(indexed=False)
    #Mandrill integration
    mandrill_key = ndb.StringProperty(indexed=False)
    mandrill_template = ndb.StringProperty(indexed=False)
    mandrill_tags = ndb.StringProperty(indexed=False, repeated=True)
    #Google Calendar integration
    calendar_id = ndb.StringProperty(indexed=False)

    @classmethod
    def get_instance(cls):
        """
        Singleton for holding client configuration data
        :return:
        """
        client = memcache.get('client-data')
        if client is None:
            client = Client.get_by_id(1)
            memcache.set('client-data', client)
        return client

    def _post_put_hook(self, future):
        #Always that updates happens, update cache
        client = future.get_result().get()
        memcache.set('client-data', client)

    @classmethod
    def _post_delete_hook(cls, key, future):
        #Always delete cache
        memcache.delete('client-data')


class User(ndb.Model):
    #TODO: email as the key name?
    email = ndb.StringProperty(required=True, validator=validate_email)
    #givenName
    first_name = ndb.StringProperty(indexed=False, validator=validate_name)
    #familyName
    last_name = ndb.StringProperty(indexed=False, validator=validate_name)
    #thumbnailPhotoUrl validator=validate_url
    thumbnail_photo_url = ndb.StringProperty(indexed=False)
    gender = ndb.StringProperty(indexed=False, choices=constants.GENDERS)

    #is_admin = ndb.BooleanProperty(default=False)
    #validator=validate_day
    birth_day = ndb.IntegerProperty()
    birth_month = ndb.IntegerProperty(validator=validate_month)
    birth_year = ndb.IntegerProperty(indexed=False,
                                     validator=validate_current_past_year)
    receive_mail = ndb.BooleanProperty(default=True)
    google_apps_id = ndb.StringProperty(indexed=False)

    @property
    def next_birthday(self):
        #Returns a date object with the user next birthday
        today = datetime.today()
        if self.birth_day < today.day and self.birth_month < today.month:
            return datetime(year=today.year + 1, month=self.birth_month,
                            day=self.birth_day)
        else:
            return datetime(year=today.year, month=self.birth_month,
                            day=self.birth_day)

    @staticmethod
    def add_many_birthdays(birthday_list):
        users_to_put = []
        for birthday_dict in birthday_list:
            email = birthday_dict['email']
            bday_array = birthday_dict['birthday'].split('-')
            #Parse format and check if field contains year
            if len(bday_array) == 3:
                birth_year = int(bday_array[0])
                birth_month = int(bday_array[1])
                birth_day = int(bday_array[2])
            elif len(bday_array) == 4 and not bday_array[0] and not bday_array[1]:
                birth_year = None
                birth_month = int(bday_array[2])
                birth_day = int(bday_array[3])
            elif len(bday_array) == 2:
                birth_year = None
                birth_month = int(bday_array[0])
                birth_day = int(bday_array[1])
            else:
                logging.error('The birthday date is not in a usual format, '
                              'unable to parse it')
                continue
            #Try to retrieve user if exists or create a new one
            user = User.query(User.email == email).get()
            if not user:
                user = User(email=email)
            user.birth_year = birth_year
            user.birth_month = birth_month
            user.birth_day = birth_day
            users_to_put.append(user)
        #Put multi if needed
        if len(users_to_put) > 0:
            ndb.put_multi(users_to_put)

    def _post_put_hook(self, future):
        #When updates happens always update cache
        user = future.get_result().get()
        memcache.delete('birthdays')

    @classmethod
    def get_all_birthdays(cls):
        #Returns a list of user birthdays ordered by closest date
        birthdays = memcache.get('birthdays')
        if not birthdays:
            birthdays = User.query().fetch()
            birthdays.sort(key=lambda x: x.next_birthday)
            memcache.set('birthdays', birthdays, time=86400)
        return birthdays


def get_birthdays(month, day):
    """
    Get users, who are marked as receiving mail, with birthday the given day
    and month
    :param month: month for the birthday
    :param day: day for the birthday
    :return: user objects that match the birthday date
    """
    return User.query(User.birth_month == month,
                      User.birth_day == day,
                      User.receive_mail == True).fetch()
