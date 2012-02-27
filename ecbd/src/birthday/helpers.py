# -*- coding: utf-8 -*-

import logging
import mimetypes
import re
import datetime

#This is backwards compatibility when lxml is not present
try:
    from lxml import etree
except ImportError:
    from xml.etree import ElementTree as etree

from StringIO import StringIO
from oauth.views import ACCESS_TOKEN
from urlparse import urlparse
from gdata.apps.service import AppsForYourDomainException
import atom.data
import gdata.auth
import gdata.acl.data
import gdata.calendar.client
import gdata.sites.client
import gdata.sites.data
import gdata.apps.groups.service as groups_service

from django.core.cache import cache
from django.template import Template, Context

import settings

SOURCE_APP_NAME = getattr(settings, 'SOURCE_APP_NAME')
GDATA_DATE_FORMAT = getattr(settings, 'GDATA_DATE_FORMAT')
CONSUMER_KEY = getattr(settings, 'OAUTH_CONSUMER_KEY')
CONSUMER_SECRET = getattr(settings, 'OAUTH_CONSUMER_SECRET')
SCOPE = getattr(settings, 'OAUTH_SCOPE')
SIG_METHOD = gdata.auth.OAuthSignatureMethod.HMAC_SHA1

__author__ = 'desarrollo@eforcers.com'

class CalendarHelper:
    """A Google Calendar helper class"""

    def __init__(self):
        self.client = gdata.calendar.client.CalendarClient(source=SOURCE_APP_NAME)

    def check_email(self, user):
        """Performs basic validation of the supplied email address as outlined
        in http://code.google.com/googleapps/marketplace/best_practices.html
        """
        domain = urlparse(user.federated_identity()).hostname
        m = re.search('.*@' + domain, user.email())
        if m:
            return True
        else:
            return False


    def setup_token(self, user=None):

        access_token = gdata.gauth.AeLoad(ACCESS_TOKEN)
        self.client.http_client.debug = True
        self.client.auth_token = gdata.gauth.OAuthHmacToken(CONSUMER_KEY, CONSUMER_SECRET,
                                                       access_token.token, access_token.token_secret,
                                                       gdata.gauth.ACCESS_TOKEN, next=None, verifier=None)

    def get_user_events(self, user):

        if not user and self.check_email(user):
            return None

        self.setup_token(user)
        feed = self.client.GetCalendarEventFeed()

        if len(feed.entry):
            return feed.entry
        else:
            return None

    def create_event(self, calendar_id, guests_list, event_title, start_date, end_date):
        """ 
        Create a new single-occurrence event in the given calendar with all the 
        parameters.
        @param calendar_id: calendar ID
        @param guests_list: list of email addresses to be added as guests
        @param event_title: title of the event to create
        @param start_date: python datetime object with the activity start date
        @param end_date: python datetime object with the activity end date
        """
        self.setup_token()
        event = gdata.calendar.data.CalendarEventEntry()
        event.title = atom.data.Title(text=event_title)
        #Format datetime objects in Atom XML friendly format
        event.when.append(gdata.calendar.data.When(start=start_date.strftime(GDATA_DATE_FORMAT),
                                                   end=end_date.strftime(GDATA_DATE_FORMAT)))
        for guest in guests_list:
            event.who.append(gdata.calendar.data.EventWho(value=guest))
        #Events are locked and guest cannot see other guests
        event.guests_can_invite_others = gdata.calendar.data.GuestsCanInviteOthersProperty(value='false')
        event.guests_can_modify = gdata.calendar.data.GuestsCanModifyProperty(value='false')
        event.guests_can_see_guests = gdata.calendar.data.GuestsCanSeeGuestsProperty(value='false')
        #TODO: Put data in the content and where sections of the event as well as in custom properties
        insert_uri = self.client.get_calendar_event_feed_uri(calendar=calendar_id)
        new_event = self.client.InsertEvent(event, insert_uri)
        return new_event

    def create_calendar(self, title, summary='', color='#2952A3',
                        timezone='America/Bogota', location='Bogota', hidden='false'):

        # create the CalendarEntry
        self.setup_token()
        entry = gdata.calendar.data.CalendarEntry()
        entry.title = atom.data.Title(text=title)
        entry.summary = atom.data.Summary(text=summary)
        entry.color = gdata.calendar.data.ColorProperty(value=color)
        entry.where.append(gdata.calendar.data.CalendarWhere(value=location))
        entry.timezone = gdata.calendar.data.TimeZoneProperty(value=timezone)
        entry.hidden = gdata.calendar.data.HiddenProperty(value=hidden)

        # Insert the new Calendar
        new_calendar = self.client.InsertCalendar(new_calendar=entry)
        return new_calendar


    def share_calendar(self, calendar_id, viewer, viewer_type='user', viewer_role='read'):
        '''
        Add a user to a calendar's access control list
        @param calendar_id: the calendar Id
        @param viewer: the viewer email
        @param viewer_type: the viewer type ('default' | 'domain' | 'user')
        @param viewer_role: the viewer role ('freebusy' | 'read' | 'owner' | 'editor')
        '''
        self.setup_token()
        rule = gdata.calendar.data.CalendarAclEntry()
        rule.scope = gdata.acl.data.AclScope(value=viewer, type=viewer_type)
        roleValue = 'http://schemas.google.com/gCal/2005#%s' % (viewer_role)
        rule.role = gdata.acl.data.AclRole(value=roleValue)
        aclUrl = 'https://www.google.com/calendar/feeds/%s/acl/full' % calendar_id

        new_rule = self.client.InsertAclEntry(rule, aclUrl)
        return new_rule


class SitesHelper:
    """A Google Sites helper class"""

    def __init__(self, site_name=None, site_domain=None, debug=False):
        mimetypes.init()
        self.client = gdata.sites.client.SitesClient(source=SOURCE_APP_NAME, site=site_name, domain=site_domain)
        self.client.http_client.debug = debug
        self.setup_token()

    def check_email(self, user):
        """Performs basic validation of the supplied email address as outlined
        in http://code.google.com/googleapps/marketplace/best_practices.html
        """
        domain = urlparse(user.federated_identity()).hostname
        m = re.search('.*@' + domain, user.email())
        if m:
            return True
        else:
            return False

    def setup_token(self, user=None):
        access_token = gdata.gauth.AeLoad(ACCESS_TOKEN)
        self.client.http_client.debug = True
        self.client.auth_token = gdata.gauth.OAuthHmacToken(CONSUMER_KEY, CONSUMER_SECRET,
                                                       access_token.token, access_token.token_secret,
                                                       gdata.gauth.ACCESS_TOKEN, next=None, verifier=None)

    def get_site_by_name(self, site_name):
        """ 
        Returns the site entry given the name of the site 
        @param site_name: site name
        """
        return self.client.GetEntry(self.client.make_site_feed_uri(site_name),
                                    desired_class=gdata.sites.data.SiteEntry)

    def get_site_by_url(self, site_url):
        """ 
        Returns the site entry given the complete URL of the site 
        @param site_url: site URL
        """
        site_name = site_url.rsplit('/', 2)[1]
        return self.get_site_by_name(site_name)

    def copy_from_template(self, title, description, template):
        '''
        Make a new site result of a copy of a template
        @param title: title of the newly created site
        @param description: description for the newly created site
        @param template: the site name of the template
        '''
        #TODO: Generar la URL del curso basada en el codigo
        copied_site = self.client.CreateSite(title,
                                             description=description,
                                             source_site='https://' + self.client.host + self.client.make_site_feed_uri(template))
        cache.delete('sites-list')
        #TODO: The content of the site (namely gadget URLs) should be updated at this point 
        return copied_site

    def share_site(self, email, scope='user', role='reader', site_name=None):
        '''
        Add a user to a site's access control list
        @param site: the GData site object
        @param email: the email of the person who will have the site shared
        @param scope: the viewer type ('default' | 'invite' | 'domain' | 'group' | 'user')
        @param role: the viewer role ('reader' | 'owner' | 'writer')
        '''
        if site_name:
            self.client.site = site_name
        scope = gdata.acl.data.AclScope(value=email, type=scope)
        acl_role = gdata.acl.data.AclRole(value=role)
        acl = gdata.sites.data.AclEntry(scope=scope, role=acl_role)

        acl_entry = self.client.Post(acl, self.client.MakeAclFeedUri())

    def list_sites(self):
        """Get the list of Sites for the current user"""
        try:
            sites_list = cache.get('sites-list')
        except Exception, err:
            logging.error('Error getting site list from cache %s', type(err))
            sites_list = None
        if sites_list is None:
            feed = self.client.GetSiteFeed()
            if len(feed.entry):
                sites_list = feed.entry
                cache.set('sites-list', sites_list)
            else:
                return None
        return sites_list

    def get_page_content(self, path):
        '''
        Returns the HTML content of the page given its path
        @param path: the relative path of the page, without the site name and domain
        '''
        uri = '%s?path=%s' % (self.client.MakeContentFeedUri(), path)
        feed = self.client.GetContentFeed(uri=uri)
        return feed.entry[0].content.html;

    def get_pages_paths_in_site(self):
        """
        Get the array of page paths within the current site 
        """
        pages_paths = []
        #Query all webpages and get the path to each one, including template pages
        content_uri = '%s?kind=webpage' % self.client.MakeContentFeedUri()
        #TODO: Include templates as well, is causing an error
        #content_uri = '%s-/template|-template?kind=webpage' % self.client.MakeContentFeedUri()
        logging.info('Content URI: %s', content_uri)
        content_feed = self.client.GetContentFeed(uri=content_uri)

        #We need the site root URL to removed later
        site_entry = self.get_site_by_name(self.client.site)
        site_url = site_entry.GetAlternateLink().href

        for entry in content_feed.entry:
            page_path = entry.GetAlternateLink().href.replace(site_url, '')
            pages_paths.append('/%s' % page_path)
            logging.info('Page path found: %s', page_path)
        return pages_paths

    def replace_placeholders_in_page(self, path, context_map):
        '''
        Replace a set of placeholders with actual valued in the HTML content and title of the 
        webpages given its relative path.
        @param context_map: dictionary mapping containing placeholders (or keys) that will be replaced
        by the actual text (or values). This dict works for both title and content
        NOTE: This only works in python 2.7 with lxml
        '''
        context = Context(context_map)
        parser = etree.HTMLParser()
        #TODO: Include templates as well, is causing an error
        #uri = '%s-/template|-template?kind=webpage&path=%s' % (self.client.MakeContentFeedUri(), path)
        uri = '%s?kind=webpage&path=%s' % (self.client.MakeContentFeedUri(), path)
        feed = self.client.GetContentFeed(uri=uri)
        old_entry = feed.entry[0]
        page_title = old_entry.title.text
        try:
            logging.debug('Page [%s] raw HTML content: [%s]' % (page_title, old_entry.content.html.ToString()))
            #Parse the HTML string into lxml
            root_element = etree.parse(StringIO(old_entry.content.html.ToString()), parser).getroot()
            if root_element is None:
                logging.error('Unable to get root HTML node in page [%s]', page_title)
            else:
                #Sites API returns a weird table at the begining, we need to get rid of it
                """
                #TODO Caution: not all pages have the same HTML boilerplate, 7 may be to deep to go
                td_element = root_element[0][0][0][0][0][0][0] 
                #If TD is nothing then take the root as it 
                if td_element is None:
                    td_element = root_element
                    logging.warn('Couldnt find TD element in HTML')
                """
                raw_content_template = etree.tostring(root_element, pretty_print=True, method="html")
                #Gadgets store user preferences encoded in the URL, make them django friendly while we perform replacement 
                raw_content_template = raw_content_template.replace("%7B%7B", "{{")
                raw_content_template = raw_content_template.replace("%7D%7D", "}}")
                #Now that we have the template as a string make it a Django template
                content_template = Template(raw_content_template)
                replaced_content = content_template.render(context)
                logging.debug('Replaced HTML body %s' % replaced_content)
                #We are looking for placeholders in title as well
                title_template = Template(page_title)
                replaced_title = title_template.render(context)
                logging.debug('Replaced title %s' % replaced_title)
                old_entry.title.text = replaced_title
                old_entry.content = atom.data.Content(replaced_content)
                self.client.Update(old_entry)
        except Exception, err:
            logging.error('Error replacing placeholders in page [%s]: [%s]', page_title, str(err))

class GroupsHelper(object):
    """A Google Groups helper class"""

    def __init__(self, domain=None):
        #FIXME: esta cableando el dominio en el constructor
        self.service = groups_service.GroupsService(domain=domain,
                                                    source=SOURCE_APP_NAME)
        self.setup_token()

    def setup_token(self):
        access_token = gdata.gauth.AeLoad(ACCESS_TOKEN)
        self.service.SetOAuthInputParameters(SIG_METHOD, CONSUMER_KEY,
                                             consumer_secret=CONSUMER_SECRET)
        input_params = gdata.auth.OAuthInputParams(
                                            SIG_METHOD, CONSUMER_KEY,
                                            consumer_secret=CONSUMER_SECRET)
        oauth_token = gdata.auth.OAuthToken(key=access_token.token,
                                            secret=access_token.token_secret,
                                            scopes=SCOPE,
                                            oauth_input_params=input_params)
        self.service.SetOAuthToken(oauth_token)

    def add_as_owner(self, user, group_id):
            # First as member then as owner
            # so they show in the admin interface (api bug?)
            self.service.AddMemberToGroup(user, group_id)
            self.service.AddOwnerToGroup(user, group_id)

    def add_as_member(self, user, group_id):
            self.service.AddMemberToGroup(user, group_id)

    def create_group(self, group_id, name, description):
        try:
            return self.service.CreateGroup(
                group_id,
                name,
                description,
                groups_service.PERMISSION_MEMBER)
        except AppsForYourDomainException, err:
            if not hasattr(err, 'reason') or err.reason != 'EntityExists':
                raise

    def update_group_for_course(self, group_id, name, description):
        return self.service.UpdateGroup(
            group_id,
            name,
            description,
            groups_service.PERMISSION_MEMBER)

    def add2group(self, email, group_id):
        self.add_as_member(email, group_id)
