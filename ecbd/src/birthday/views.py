# -*- coding: utf-8 -*-
from birthday.decorators import admin_login_required
from birthday.models import Client, User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.signals import user_logged_out
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from google.appengine.api import namespace_manager
from google.appengine.ext.db.metadata import get_namespaces
from oauth.views import ACCESS_TOKEN
import datetime
import gdata.gauth
import logging
import re

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
            return redirect('course_list', domain)
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

def send_birthday_messages(request):
    """
    It goes through all the namespaces making queries to the datastore for 
    users who have the same birth day and birth month as today
    @param request:
    """
    today = datetime.datetime.now()
    current_namespace = namespace_manager.get_namespace()
    for namespace in get_namespaces():
        # Forget about the default empty namespace
        logging.debug("Checking celebrants for today day %s month %s namespace %s", today.month, today.day, namespace.namespace_name)
        if namespace and namespace.namespace_name:
            namespace_manager.set_namespace(namespace.namespace_name)
        celebrants = User.objects.filter(receive_mail=True, birth_month=today.month, birth_day=today.day)
        for celebrant in celebrants:
            logging.debug("Found a celebrant for today! %s", celebrant)
            #TODO: schedule sending email
    #Restore to the original namespace
    namespace_manager.set_namespace(current_namespace)
    return HttpResponse(content="Birthday messages were scheduled", status=200)
