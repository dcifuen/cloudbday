'''
Created on 30/01/2012

@author: eforcers
'''
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from birthday.models import User, Client

def admin_login_required(login_url=None):
    
    """
    Decorator for views that checks that the user is logged in and is an administrator, 
    redirecting to the log-in page if necessary.
    """
    def _is_admin(user):
        try:
            # First time setup
            client = Client.objects.get_from_cache()
        except Client.DoesNotExist:
            return True
        
        if user.is_authenticated() :
            try:            
                ecbd_user = User.objects.get(email=user.email)
                return ecbd_user.is_admin
            
            except User.DoesNotExist:
                return False
        else:
            return False
    
    if not login_url:
        login_url = '/'
    
    actual_decorator = user_passes_test(
        _is_admin,
        login_url=login_url,
        redirect_field_name=REDIRECT_FIELD_NAME
    )
    
    return actual_decorator