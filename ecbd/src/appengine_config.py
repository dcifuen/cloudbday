import os
import logging
import re

regex = re.compile(r'^/?a/(?P<domain>(?:[\w](?:[\w-]{0,61}[\w])?\.)+(?:[A-Za-z]{2,6}\.?|[\w-]{2,}\.?))/')

def namespace_manager_default_namespace_for_request():
    name = None
    path = os.environ.get('PATH_INFO', '')
    match = regex.match(path)
    if match:
        name = match.groupdict()['domain']
    logging.info('namespace: %s', name)
    return name