#-*- coding: utf-8 -*-
# vim: set fileencoding=utf-8

import httplib2
from apiclient.discovery import build
import mandrill
from oauth2client.client import Credentials, OAuth2WebServerFlow

from birthday import app

import csv


class OAuthDanceHelper:
    """ OAuth dance helper class"""
    flow = None

    def __init__(self, redirect_uri='', approval_prompt='auto', scope=''):
        self.flow = OAuth2WebServerFlow(
            client_id=app.config.get('OAUTH2_CLIENT_ID'),
            client_secret=app.config.get(
                'OAUTH2_CLIENT_SECRET'),
            scope=scope,
            redirect_uri=redirect_uri,
            approval_prompt=approval_prompt)

    def step1_get_authorize_url(self):
        return self.flow.step1_get_authorize_url()

    def step2_exchange(self, code):
        return self.flow.step2_exchange(code)

    def get_credentials(self, credentials_json):
        return Credentials.new_from_json(credentials_json)


class OAuthServiceHelper:
    """ OAuth services base helper class"""

    credentials = None
    service = None

    def __init__(self, credentials_json, refresh_token=None):
        oauth_helper = OAuthDanceHelper()
        self.credentials = oauth_helper.get_credentials(credentials_json)
        if refresh_token and self.credentials.refresh_token is None:
            self.credentials.refresh_token = refresh_token
        self.http = self.credentials.authorize(httplib2.Http())


class DirectoryHelper(OAuthServiceHelper):
    """ Google Directory API helper class"""

    def __init__(self, credentials_json, customer_id=None, refresh_token=None):
        OAuthServiceHelper.__init__(self, credentials_json, refresh_token)
        self.service = build('admin', 'directory_v1', http=self.http)
        self.customer_id = customer_id

    def get_customer_id(self, email):
        user_document = self.service.users().get(
            userKey=email,
            fields="customerId"
        ).execute()
        if "customerId" in user_document:
            self.customer_id = user_document["customerId"]
            return user_document["customerId"]
        return None


class CSVHelper():
    """ TODO: CSV processing helper class """
    def __init__(self, file_data):
        self.rows = [row for row in csv.reader(
            file_data.splitlines())]






class MandrillHelper:
    """ Mandrill transactional email API helper class"""
    mandrill = None

    def __init__(self, api_key):
        self.mandrill = mandrill.Mandrill(api_key, debug=app.config['DEBUG'])

    @staticmethod
    def build_message(merge_dict, subject, from_email, from_name, to_email,
                      to_name, tags=[]):
        merge_vars = []
        for key, value in merge_dict:
            merge_vars.append({
                'name': key,
                'content': value
            })

        return {
            'subject': subject,
            'from_email': from_email,
            'from_name': from_name,
            'to': [
                {
                    "email": to_email,
                    "name": to_name,
                    "type": "to"
                }
            ],
            'headers': {'Reply-To': from_email},
            'tags': tags,
            "global_merge_vars": merge_vars
        }

    def send(self, message, template_name):
        additional_info = {
            'important': True,
            'track_opens': True,
            'track_clicks': True,
            'merge': True
        }
        message.update(additional_info)

        return self.mandrill.messages.send_template(
            template_content=[],
            template_name=template_name,
            message=message,
            async=False,
            ip_pool='Main Pool'
        )
