from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('birthday.views',
    url(r'^$', 'welcome', name='landing'),
    url(r'^welcome/$', 'welcome', name='welcome'),
            
    url(r'^admin/client/setup/$', 'client_setup', name='client_setup'), 
    url(r'^admin/client/clear_cache/$', 'clear_cache', name='clear_cache'), 
    
)
