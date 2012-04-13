# vim: set fileencoding=utf-8

from dojango import forms
from birthday.fields import ListFormField
from birthday.models import Client 

def make_client_form(domain_):
    
    class _ClientForm(forms.ModelForm):
        #css styles
        required_css_class = 'required'
        domain = forms.CharField(initial=domain_, widget=forms.TextInput(attrs={'readonly':'readonly'}))
        
        administrators = ListFormField(required=True, 
                                   help_text="Whom will be in change of managing CloudBDay. Use the admin email address and comma character to separate multiple entries",
                                   widget=forms.ListInput(attrs={
                                            'regExpGen': 'dojox.validate.regexp.emailAddress',
                                            'useAnim': False,
                                            'submitOnlyValidValue': True,
        }))
        
        class Meta:
            model = Client
            fields = (
                'name',
                'domain',
                'administrators',
                'apps_edition',
                'subject',
                )
            
    return _ClientForm
