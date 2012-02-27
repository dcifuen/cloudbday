from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
import gdata.docs.client
import logging
import settings

REQUEST_TOKEN = 'RequestToken'
ACCESS_TOKEN = 'AccessToken'
client = gdata.docs.client.DocsClient(source='Eforcers-CloudBDay')

def get_oauth_token(request, domain):
    
    # 1.) REQUEST TOKEN STEP. Provide the data scope(s) and the page we'll
    # be redirected back to after the user grants access on the approval page.
    CONSUMER_KEY = getattr(settings, 'OAUTH_CONSUMER_KEY')
    CONSUMER_SECRET = getattr(settings, 'OAUTH_CONSUMER_SECRET')
    SCOPE = getattr(settings, 'OAUTH_SCOPE')
    
    oauth_callback_url = 'http://%s:%s/a/%s/oauth/get_access_token/' % (request.META.get('SERVER_NAME'),
                                                                  request.META.get('SERVER_PORT'),
                                                                      domain)
    logging.info("oauth_callback_url [%s]", oauth_callback_url)
        
    request_token = client.GetOAuthToken(SCOPE, oauth_callback_url, CONSUMER_KEY, 
                                         consumer_secret=CONSUMER_SECRET)
    gdata.gauth.AeSave(request_token, REQUEST_TOKEN)
    
    # 2.) APPROVAL STEP.  Redirect to user to Google's OAuth approval page.
    authorization_url = request_token.generate_authorization_url()    
    return HttpResponseRedirect(authorization_url)


def get_access_token(request, domain):
    
    saved_request_token = gdata.gauth.AeLoad(REQUEST_TOKEN)
    request_token = gdata.gauth.AuthorizeRequestToken(saved_request_token, request.build_absolute_uri())
    
    # 3.) Exchange the authorized request token for an access token
    access_token = client.GetAccessToken(request_token)
    
    # If you're using Google App Engine, you can call the AeSave() method to save
    # the access token under the current logged in user's account.
    gdata.gauth.AeSave(access_token, ACCESS_TOKEN)
    
    return HttpResponseRedirect(reverse('welcome', args=[domain]))
