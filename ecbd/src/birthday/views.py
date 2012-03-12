# -*- coding: utf-8 -*-
from birthday.decorators import admin_login_required
from birthday.forms import make_client_form
from birthday.helpers import ProfilesHelper
from birthday.models import Client, User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.signals import user_logged_out
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.generic.list_detail import object_list
from google.appengine.api import namespace_manager
from google.appengine.ext import deferred
from google.appengine.ext.db.metadata import get_namespaces
from oauth.views import ACCESS_TOKEN
import datetime
import gdata.gauth
import logging
import re
import settings


ECBD_SENDER_EMAIL = getattr(settings, 'ECBD_SENDER_EMAIL')

def sign_out(request, domain):
    """
    Removes the authenticated user's ID from the request and flushes their
    session data.
    """    
    user = getattr(request, 'user', None)
    if hasattr(user, 'is_authenticated') and not user.is_authenticated():
        user = None
    user_logged_out.send(sender=user.__class__, request=request, user=user)

    request.session.flush()
    if hasattr(request, 'user'):
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
    return HttpResponseRedirect('/')

@login_required()
def welcome(request, domain):
    access_token = gdata.gauth.AeLoad(ACCESS_TOKEN)
    if not isinstance(access_token, gdata.gauth.OAuthHmacToken):
        return redirect('get_oauth_token', domain)
    try:
        client = Client.objects.get_from_cache()
    except Client.DoesNotExist:
        return redirect('client_setup', domain)
    try:
        user = User.objects.get(email=request.user.email) 
    except User.DoesNotExist:
        #TOOD: Enviar a formulario para crear usuario en bd de birthday plan
        user = None
    if user and user.is_admin:
        return redirect('user_list', domain)
    else:
        # si student_home_url es vacio, se genera un bucle de redireccion
        # se deberia definir una url por defecto en caso de que el cliente
        # no haya configurado esta variable. Por ahora, enviar a eforcers.com
        redirect_url = client.student_home_url or 'http://www.eforcers.com'
        return HttpResponseRedirect(redirect_url)
   
@admin_login_required()
def client_setup(request, domain):
    ClientForm = make_client_form(domain)
    if request.method == 'POST':
        request_copy = request.POST.copy()
        request_copy['administrators'] = request.POST.getlist('administrators')
        form = ClientForm(request_copy)
        if form.is_valid():
            form.save()
            admins = form.cleaned_data['administrators']
            admins_setup(admins)
            return redirect('user_list', domain)
    try:
        client = Client.objects.get_from_cache()
    except Client.DoesNotExist:
        form = ClientForm()
    else:
        form = ClientForm(instance=client)
    return render_to_response('admin_client.html',
                              {'form':form},
                              RequestContext(request))
    
@admin_login_required()
def user_list(request, domain):
    users = User.objects.all()
    return object_list(request, queryset=users,
                       template_name='admin_user_list.html',
                       template_object_name='users')

@admin_login_required()
def clear_cache(request, domain):
    from django.core.cache import cache
    if request.method == 'POST':
        cache.clear()
        return HttpResponse(status=200)
    return HttpResponse(status=400)

def admins_setup(admins):
    for email in admins:
        user = User.objects.get_or_create(email=email)[0]
        user.is_admin = True
        user.save()


def create_users(emails):
    for email in emails:
        User.objects.get_or_create(email=email)

def get_domain_from_path(path):
    regex = re.compile(
        r'^/?a/(?P<domain>(?:[\w](?:[\w-]{0,61}[\w])?\.)+(?:[A-Za-z]{2,6}\.?|'
        r'[\w-]{2,}\.?))/')
    match = regex.match(path)
    if match:
        return match.groupdict()['domain']
    return None

def login_redirect(request):
    domain = get_domain_from_path(request.path_info) or (
               request.GET.get('domain', None) or
               get_domain_from_path(request.GET.get('next', '')))
    if domain:
        url = reverse('openid-login', args=[domain])
        if 'next' in request.GET:
            url += '?next=%s' % request.GET['next']
        logging.info('url: %s ', url)
        return redirect(url)
    return render_to_response('enter_login_domain.html')

def sync_with_profile(request):
    """
    Queries all the profiles getting the birthdate and comparing it with the one
    stored in the datastore (if any). If the user is not present the it creates
    the record.
    @param request:
    """
    current_namespace = namespace_manager.get_namespace()
    for namespace in get_namespaces():
        # Forget about the default empty namespace
        if namespace:
            logging.debug("Doing sync from profiles for namespace %s", namespace)
            namespace_manager.set_namespace(namespace)
            client = Client.objects.get_from_cache()
            profiles_helper = ProfilesHelper()
            #Query all profiles for birthday info 
            #TODO: Ojo con dominios secundarios
            for entry in profiles_helper.get_all_profiles(client.domain):
                username = entry.id.text[entry.id.text.rfind('/')+1:]
                if entry.birthday:
                    logging.debug("Birthday set in profile for user [%s] on day [%s]", 
                                 username, entry.birthday.when)
                    bday_array = entry.birthday.when.split('-')
                    #If field contains year 
                    if len(bday_array) == 3:
                        birth_year = bday_array[0]
                        birth_month = bday_array[1]
                        birth_day = bday_array[2]
                    elif len(bday_array) == 4 and not bday_array[0] and not bday_array[1]:
                        birth_year = None
                        birth_month = bday_array[2]
                        birth_day = bday_array[3]
                    else:
                        logging.error('The birthday date is not in a usual format, unable to parse it, setting all fields to None')
                        birth_year = None
                        birth_month = None
                        birth_day = None
                    logging.debug("Birthday data for [%s] day [%s] month [%s] year [%s]", 
                                 username, birth_day, birth_month, birth_year)
                    user = User.objects.get_or_create(email= "%s@%s" % (username,client.domain))[0]
                    #Save only if something have changed
                    needs_to_save = False
                    if user.birth_day != birth_day:
                        user.birth_day = birth_day
                        needs_to_save = True
                    if user.birth_month != birth_month:
                        user.birth_month = birth_month
                        needs_to_save = True
                    if user.birth_year != birth_year:
                        user.birth_year = birth_year
                        needs_to_save = True
                    if needs_to_save:
                        user.save()

    #Restore to the original namespace
    namespace_manager.set_namespace(current_namespace)
    return HttpResponse(content="Birthday dates were sync from profiles successfully", status=200)

def send_birthday_message(celebrant_pk):
    """
    This is the actual method that sends the email message to the celebrant
    @param celebrant_pk: primary key of the person who is receiving the email
    """
    celebrant = User.objects.get(pk=celebrant_pk)
    client = Client.objects.get_from_cache()
    #TODO: Bring dinamically the HTML content from a Google Site instead of a static template
    body_html = render_to_string('formatted_message_alpina.com.html',
                            {'celebrant': celebrant})
    
    body_txt = render_to_string('unformatted_message_alpina.com.html',
                            {'celebrant': celebrant})
    msg = EmailMultiAlternatives(client.subject, body_txt, ECBD_SENDER_EMAIL, [celebrant.email])
    msg.attach_alternative(body_html, "text/html")
    msg.send()
    

def send_daily_birthday_messages(request):
    """
    It goes through all the namespaces making queries to the datastore for 
    users who have the same birth day and birth month as today
    @param request:
    """
    today = datetime.datetime.now()
    current_namespace = namespace_manager.get_namespace()
    for namespace in get_namespaces():
        # Forget about the default empty namespace
        if namespace:
            logging.debug("Checking celebrants for today day %s month %s namespace %s", today.month, today.day, namespace)
            namespace_manager.set_namespace(namespace)
            celebrants = User.objects.filter(receive_mail=True, birth_month=today.month, birth_day=today.day)
            for celebrant in celebrants:
                logging.debug("Found a celebrant for today! %s", celebrant)
                #Schedule sending email
                deferred.defer(send_birthday_message, celebrant.pk, _queue="mail-queue")
    #Restore to the original namespace
    namespace_manager.set_namespace(current_namespace)
    return HttpResponse(content="Birthday messages were scheduled", status=200)
