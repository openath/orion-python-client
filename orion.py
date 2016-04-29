"""Wrappers around FIWARE Orion ReST API for storing/fetching

Stash a token in the process for an hour.

"""


import json
import logging
import os
import re
import requests
import socket
import time
import urllib

from bson import json_util
from datetime import datetime

from django.conf import settings
from django.contrib.sites.models import Site
from django.http import Http404
from django.utils.http import urlquote

_FIWARE_AUTH_TOKEN = None
_FIWARE_AUTH_EXPIRY = None

logger = logging.getLogger('default')

#This token works for the FIWARE lab.  For a local machine, a wrong token 
#works or even an empty string is fine, so don't vary it. It is NOT the Orion server
ORION_TOKEN_URL = "https://orion.lab.fiware.org/token"
_ORION_HOST = settings.ORION_HOST

if (not _ORION_HOST.startswith('http:')) and (not _ORION_HOST.startswith('https:')):
    #if settings.DEBUG:
        _ORION_HOST = "http://" + settings.ORION_HOST
    #else:
    #   _ORION_HOST = "https://" + settings.ORION_HOST

#this might be a local docker
ORION_ENTITIES_URL = "%s:1026/v1/contextEntities/" % _ORION_HOST
TOS = 10 # TimeOut in Seconds


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%dT%H:%M:%SZ')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

def get_local_host():
    domain = Site.objects.get_current().domain
    if settings.DEBUG or domain=='example.com':
        domain = "http://%s:8000" % '192.168.0.102' #socket.gethostbyname(socket.gethostname())
    else:
        domain = "https://%s" % domain
    return domain

def is_orion_local():
    if _ORION_HOST.startswith('https://'):
        loc = _ORION_HOST[8:]
    else:
        loc = _ORION_HOST[7:]
    return re.match('^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', loc) or False
    

_IS_ORION_LOCAL = is_orion_local()

def get_token(duration=3600):
    #Apparently they last an hour
    global _FIWARE_AUTH_TOKEN, _FIWARE_AUTH_EXPIRY
    if _IS_ORION_LOCAL:
        return u'useless token'

    if _FIWARE_AUTH_TOKEN:
        if _FIWARE_AUTH_EXPIRY > time.time():
            return _FIWARE_AUTH_TOKEN

    r = requests.post(
            ORION_TOKEN_URL,
            json=dict(
                    username=settings.FIWARE_USERNAME,
                    password=settings.FIWARE_PASSWORD,
                ),
            timeout=TOS,
            #,
            #headers = {'Content-type':'application/json'}
        )

    if r.status_code != 200:
        raise ValueError("Cannot get Orion token: %s" % r.text)


    token = r.text
    _FIWARE_AUTH_TOKEN = token
    _FIWARE_AUTH_EXPIRY = time.time() + duration

    return token

def get_headers(exclude_content_type=False):
    HEADERS = {
            'Accept': 'application/json',
            }
    if not exclude_content_type:
        HEADERS['Content-Type'] = 'application/json'
    if getattr(settings, 'ORION_USE_TOKEN', False):
        HEADERS['X-Auth-Token'] = get_token()
    return HEADERS


def pydict_to_orion(d):
    """Convert Python dictionary to the top level format for Orion

    The top level in Orion has to be expanded to name/type/value

    MY_DATA = {
            "attributes": [
                {
                    "name": "race_name",
                    "type": "string",
                    "value": "Sunday Fun Run"
                },
                {
                    "name": "start_list",
                    "type": "T",
                    "value": START_LIST
                }
            ]
        }
    """

    orion_attrs = []

    for key, val in d.iteritems():
        if key != '_about':
            if isinstance(val, int):
                orion_attrs.append(dict(name=key, type="integer", value=val))
            elif isinstance(val, datetime):
                orion_attrs.append(dict(name=key, type="datetime",
                                        value=val.isoformat()))
            elif isinstance(val, bool):
                orion_attrs.append(dict(name=key, type="boolean", value=val))
            elif isinstance(val, basestring):
                orion_attrs.append(dict(name=key, type="string",
                                        #value=urlquote(val)))
                                        value=val))
            elif isinstance(val, float):
                orion_attrs.append(dict(name=key, type="float", value=val))
            elif isinstance(val, (list, dict)):
                orion_attrs.append(dict(name=key, type="T", value=val))
            else:
                raise ValueError("Don't know how to encode top-level attribute %s in orion" % val)
    return dict(attributes=orion_attrs)


def orion_to_pydict(orionstuff):

    pydict = {}

    #Hmmm. We get this extra level with the Santander thing, but not needed if setting
    #ourselved
    if "contextElement" in orionstuff:
        orionstuff = orionstuff["contextElement"]

    for attrdict in orionstuff["attributes"]:
        name = attrdict["name"]
        value = attrdict["value"]
        pydict[name] = value
    return pydict


def get_version():
    url = "%s:1026/version" % _ORION_HOST
    headers = get_headers()
    r = requests.get(
        url,
        verify=False,
        headers=headers,
    )
    if r.status_code == 200:
        return r.json()
    else:
        print "not 200"
        return r.json()

def has_orion_error(content):
    # if the output is not boolean False, there is an error
    if 'orionError' in content:
        err = json.dumps(content['orionError'], indent=4)
        return err 
    return False


def create_entity(entity_id, data, typ=""):
    """Create or replace the given entity in Orion

    The top level in Orion has to be expanded to name/type/value

    MY_DATA = {
            "attributes": [
                {
                    "name": "race_name",
                    "type": "string",
                    "value": "Sunday Fun Run"
                },
                {
                    "name": "start_list",
                    "type": "T",
                    "value": START_LIST
                }
            ]
        }
    """
    entity = pydict_to_orion(data)

    r = requests.post(
        ORION_ENTITIES_URL + entity_id,
        data = json.dumps(entity, cls=DateTimeEncoder),
        verify=False,
        headers = get_headers(),
        timeout=TOS,
    )
    if r.status_code == 200:
        has_errors = has_orion_error(r.json())
        if has_errors:
            return has_errors
        else:
            return True
    else:
        return r.json()


def update_entity(entity_id, data, do_not_orionify=False):
    if not do_not_orionify:
        entity = pydict_to_orion(data)
    else:
        entity = data

    r = requests.post(ORION_ENTITIES_URL + entity_id + "/attributes",
                      data = json.dumps(entity, cls=DateTimeEncoder),
                      headers = get_headers(),
                      verify=False,
                      timeout=TOS,
                     )
    if r.status_code == 200:
        has_errors = has_orion_error(r.json())
        if has_errors:
            return has_errors
        else:
            return True
    else:
        return r.content


def fetch_entity(entity_id):
    ENTITY_URL = ORION_ENTITIES_URL + entity_id
    r = requests.get(ENTITY_URL, headers=get_headers(),
            verify=False, timeout=TOS,
            )
    resp = r.json()
    if 'statusCode' in resp:
        if resp["statusCode"].get("code", None) == u'404':
            return None
    return orion_to_pydict(resp)


def fetch_attribute(entity_id, attribute):
    ATTRIBUTE_URL = ORION_ENTITIES_URL + entity_id + "/attributes/" + attribute
    r = requests.get(ATTRIBUTE_URL, headers=get_headers(),
            verify=False, timeout=TOS,
                    )
    resp = r.json()

    if 'statusCode' in resp:
        if resp["statusCode"].get("code", None) == u'404':
            return None
    return resp["attributes"][0]["value"]


def update_attribute(entity_id, attribute, newdata):
    ATTRIBUTE_URL = ORION_ENTITIES_URL + entity_id + "/attributes"
    data = pydict_to_orion({attribute: newdata,})
    r = requests.put(
        ATTRIBUTE_URL, 
        headers = get_headers(),
        json=data,
        verify=False,
        timeout=TOS,
    )
    if r.status_code == 200:
        has_errors = has_orion_error(r.json())
        if has_errors:
            return has_errors
        else:
            return True
    else:
        return r.content


def delete_entity(entity_id):
    ENTITY_URL = ORION_ENTITIES_URL + entity_id
    r = requests.delete(ENTITY_URL, headers=get_headers(),
            verify=False, timeout=TOS,
                       )
    if r.status_code == 200:
        has_errors = has_orion_error(r.json())
        if has_errors:
            return has_errors
        else:
            return True
    else:
        return r.content


def cancel_subscription(subscr_id):
    msg = {'subscriptionId': subscr_id,}
    url = "%s:1026/v1/unsubscribeContext" % _ORION_HOST
    r = requests.post(url, json=msg, headers=get_headers(),
            verify=False, timeout=TOS,
                     )
    if r.status_code == 200:
        has_errors = has_orion_error(r.json())
        if has_errors:
            return has_errors
        else:
            return r.json()
    else:
        return r.content


def setup_notification(entity_id, attributes=[],
                       callback_url="%s/fw/orion-notify/" % get_local_host(),
                       duration="1M", # defaults to 1 Month
                       poll_period="1S", # defaults to 1 second 
                      ):
    """Register for the Orion server to post change notices on the entity.

    :: duration := follows https://en.wikipedia.org/wiki/ISO_8601, already
                    prefixed with 'P'
    :: poll_period := follows https://en.wikipedia.org/wiki/ISO_8601, already
                    prefixed with 'PT' (we only accept periods below 24h :) )
    """
    if not callback_url.startswith('http'):
        callback_url = "%s%s" % (get_local_host(), callback_url)
    msg = {
            "entities": [
                {
                    "type": "",
                    "isPattern": "false",
                    "id": entity_id,
                }
            ],
            "attributes": attributes,
            "reference": callback_url,
            "duration": "P%s" % duration,
            "notifyConditions": [
                {
                    "type": "ONCHANGE",
                    "condValues": attributes
                }
            ],
            "throttling": "PT%s" % poll_period
        }    

    SUBSCRIBE_URL = "%s:1026/v1/subscribeContext" % _ORION_HOST
    logger.info('Subscribing: %s' % json.dumps(msg))

    r = requests.post(SUBSCRIBE_URL, json=msg, headers=get_headers(),
                      verify=False, timeout=TOS,
                     )
    if r.status_code == 200:
        has_errors = has_orion_error(r.json())
        if has_errors:
            return has_errors
        else:
            return r.json()
    else:
        return r.content

