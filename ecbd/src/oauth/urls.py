from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('oauth.views',
  url(r'^get_oauth_token/$', 'get_oauth_token', name='get_oauth_token'),
  (r'^get_access_token/$', 'get_access_token'),  
) 
