import warnings

from django import template
from django.template.defaultfilters import stringfilter
from django.conf import settings

register = template.Library()


class AnalyticsNode(template.Node):
    def __init__(self):
        self.code = getattr(settings, 'ECBD_ANALYTICS_CODE', None)
    
    def render(self, context):
        if self.code is None:
            warnings.warn('No Google analytics code found in django settings.'
                          ' No tracking code will be included in the template',
                          UserWarning)
            return ''
        html = """
            <script type="text/javascript">
              var _gaq = _gaq || [];
              _gaq.push(['_setAccount', '%s']);
              _gaq.push(['_trackPageview']);
              (function() {
                var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
                ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
                var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
              })();
            </script>""" % (self.code) 
        return html
 

@register.tag
def analytics_code(parser, token):
    bits = token.contents.split()
    if len(bits)!= 1:
        raise template.TemplateSyntaxError('analytics_code takes no parameters')
    return AnalyticsNode()

@register.filter
@stringfilter
def truncatestring(src, ln):
    ret = src[:ln]
    if len(src) > ln:
        ret = ret[:ln - 3] + '...'
    return ret
