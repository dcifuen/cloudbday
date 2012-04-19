from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import direct_to_template

import birthday.urls

handler500 = 'djangotoolbox.errorviews.server_error'

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    ('^_ah/warmup$', 'djangoappengine.views.warmup'),    
    (r'^dojango/', include('dojango.urls')),
    url(r'^tasks/birthday/send/$', 'birthday.views.send_daily_birthday_messages', name='send_daily_birthday_messages'),
    url(r'^tasks/profile/sync/$', 'birthday.views.sync_with_profile', name='sync_with_profile'),
    url(r'^tasks/calendar/sync/$', 'birthday.views.sync_with_calendar', name='sync_with_calendar'),
    url(r'^openid/login/', 'birthday.views.login_redirect', name='login'),
    url(r'^a/(?P<domain>(?:[\w](?:[\w-]{0,61}[\w])?\.)+(?:[A-Za-z]{2,6}\.?|[\w-]{2,}\.?))/logout/', 'birthday.views.sign_out', name='logout'),
    url(r'^a/(?P<domain>(?:[\w](?:[\w-]{0,61}[\w])?\.)+(?:[A-Za-z]{2,6}\.?|[\w-]{2,}\.?))/openid/', include('django_openid_auth.urls')),
    url(r'^a/(?:[\w](?:[\w-]{0,61}[\w])?\.)+(?:[A-Za-z]{2,6}\.?|[\w-]{2,}\.?)/administracion/', include(admin.site.urls)),
    url(r'^a/(?P<domain>(?:[\w](?:[\w-]{0,61}[\w])?\.)+(?:[A-Za-z]{2,6}\.?|[\w-]{2,}\.?))/oauth/', include('oauth.urls')),
    url(r'^a/(?P<domain>(?:[\w](?:[\w-]{0,61}[\w])?\.)+(?:[A-Za-z]{2,6}\.?|[\w-]{2,}\.?))/', include(birthday.urls)),
    url(r'^$', direct_to_template, {'template':'enter_login_domain.html'}),
)
