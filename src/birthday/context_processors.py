'''
Created on 24/11/2011

@author: daniel.sarmiento
'''

import re

def domain(request):
    domain = 'nodomain.com'
    regex = re.compile(r'^/?a/(?P<domain>(?:[\w](?:[\w-]{0,61}[\w])?\.)+(?:[A-Za-z]{2,6}\.?|[\w-]{2,}\.?))/')
    match = regex.match(request.path_info)
    if match:
        domain = match.groupdict()['domain']
    return {'domain': domain}