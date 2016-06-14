__all__ = (
            'OrionClient',
            )
import  json, logging, os, re, requests, socket, time, warnings
from datetime import datetime

__verify__=False
try:
    import certifi
    __verify__ = certifi.where(),  # Path to the Certifi bundle.
except:
    if os.path.isfile("/etc/ssl/certs/ca-certificates.crt"):
        __verify__="/etc/ssl/certs/ca-certificates.crt"

warnings.filterwarnings("ignore", message="^.*Unverified HTTPS request is being made.*$")
warnings.filterwarnings("ignore", message="^.*A true SSLContext object is not available.*$")

class ErrorValue(object):
    def __init__(self,**kwds):
        self.__dict__.update(kwds)
    def __nonzero__(self):
        return False
    def __repr__(self):
        return 'ErrorValue(%s)'% '\n,'.join('%s=%r' % i for i in self.__dict__.iteritems())

class OrionClient(object):
    '''
    OrionClient creates a client for a fiware orion server
    orion_host_url      is the prefix of the orion requests
    orion_token_url     is the token request url
                            eg "https://orion.lab.fiware.org/token"
    username            user id
    password            user password
    authMethod          one of None, 'fiware-token'
    logger              None or the name of a logger to use
    timeout             10 seconds
    verify              None or path to a requests certs folder
    '''
    authMethods = ('fiware-token','inline','request')
    _orion_version_str = 'v1'
    def __init__(self,
            orion_host_url,
            orion_host_port=1026,
            orion_token_url=None,
            username=None,
            password=None,
            authMethod='fiware-token',
            logger=None,
            timeout=10,
            verify=__verify__,
            ):
        if authMethod:
            if authMethod not in self.authMethods:
                raise ValueError('authMethod=%r not in %r' % (authMethod,self.authMethods))
            if None in (username,password):
                raise ValueError('need both username and password for authMethod=%r' % authMethod)
        self.authMethod = authMethod
        self.username = username
        self.password = password
        self.orion_host_url = self.clean_url(orion_host_url)
        self.orion_host_port = orion_host_port
        self.orion_token_url = self.clean_url(orion_token_url)
        self.fiware_auth_token = None
        self.fiware_auth_expiry = None
        self.logger = logging.getLogger(logger) if logger else None
        self.timeout = timeout
        self.verify = verify

    @property
    def token(self,duration=3600):
        '''return an authorisation token from the token request url'''
        if self.fiware_auth_token:
            if self.fiware_auth_expiry > time.time():
                return self.fiware_auth_token

        r = requests.post(
                self.orion_token_url,
                json=dict(
                        username=self.username,
                        password=self.password,
                    ),
                timeout=self.timeout,
                #,
                #headers = {'Content-type':'application/json'}
                )

        if r.status_code != 200:
            raise ValueError("Cannot get Orion token: %s" % r.text)


        token = r.text
        self.fiware_auth_token = token
        self.fiware_auth_expiry = time.time() + duration -1

        return token

    @property
    def orion_host_prefix(self):
        return "%s:%s" % (self.orion_host_url,self.orion_host_port)

    @property
    def orion_entities_url(self):
        return "%s/%s/contextEntities" % (self.orion_host_prefix,self._orion_version_str)

    @property
    def orion_entitytypes_url(self):
        return "%s/%s/contextEntityTypes" % (self.orion_host_prefix,self._orion_version_str)

    @staticmethod
    def _make_url(*args):
        return '/'.join(a.strip('/') for a in args if a is not None)

    @staticmethod
    def clean_url(url):
        if url:
            if (not url.startswith('http://')) and (not url.startswith('https://')):
                url = "http://" + url
            return url.rstrip('/')

    @staticmethod
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
                                            value=val))
                elif isinstance(val, float):
                    orion_attrs.append(dict(name=key, type="float", value=val))
                elif isinstance(val, (list, dict)):
                    orion_attrs.append(dict(name=key, type="T", value=val))
                else:
                    raise ValueError("Don't know how to encode top-level attribute %s in orion" % val)
        return dict(attributes=orion_attrs)

    @staticmethod
    def orion_to_py(orion):
        '''convert a token from orion to python form'''

        if 'contextResponses' in orion:
            return dict((x['contextElement']['id'],OrionClient.orion_to_py(x)) for x in orion['contextResponses'] if 'contextElement' in x)
        #We get this extra level with the Santander thing, but not needed for ourselves
        if "contextElement" in orion:
            orion = orion["contextElement"]
        return dict((attrdict["name"],attrdict["value"]) for attrdict in orion.get("attributes",[]))

    def get_headers(self, exclude_content_type=False):
        HEADERS = {
                'Accept': 'application/json',
                }
        if not exclude_content_type:
            HEADERS['Content-Type'] = 'application/json'
        if self.authMethod=='fiware-token':
            HEADERS['X-Auth-Token'] = self.token
        return HEADERS

    @property
    def orion_version(self):
        '''return the orion version'''
        url = "%s/version" % self.orion_host_prefix
        headers = self.get_headers()
        r = requests.get(
            url,
            verify=self.verify,
            headers=headers,
            )
        return r.status_code,r.json()

    def create_entity(self, entity_id, type_id="", **attributes):
        """Create or replace the given entity in Orion
            create_entity(
                entity_id,  #string id
                type_id=optional_type_id,   #string
                attr0=value0,
                attr1=value1,
                ....
                )

            We send  this
                {
                "type": type_id,    #if specified
                "attributes": [
                            attr0: value0,
                            .....
                            attrk, valuek
                            ....
                            ]
                }
        """
        data =self.pydict_to_orion(attributes)
        if type_id:
            data['type'] = type_id
        return self.do_request(
            'post',
            self._make_url(self.orion_entities_url,entity_id),
            data = json.dumps(data, cls=self.DateTimeEncoder),
            )

    def update_entity(self, entity_id, orionify=True, **kwds):
        '''update a specified entitity
            update_entity(
                        'entity_id',
                        attr0=value0,
                        .....
                        )'''
        return self.do_request(
                        'post',
                        self._make_url(self.orion_entities_url,entity_id,"attributes"),
                         data = json.dumps(self.pydict_to_orion(kwds) if orionify else kwds, cls=self.DateTimeEncoder),
                         )

    def fetch_entity(self, entity_id=None, type_id=None, attribute=None):
        '''fetch some or a specifiied entity
            fetch_entity(
                    entity_id='entity_id',
                    type_id='type_id',
                    attribute='attribute',
                    )
            if entity_id is specified then that specific entity is returned
            else if type_id is specified we return entities of that type.
            If attribute is specified only that attribute will be returned else
            all attributes will be returned.

            In the multiple return case we return a dictionary with keys the entity ids.
            '''
        if entity_id:
            url = (self.orion_entities_url,entity_id)
        elif type_id:
            url = (self.orion_entitytypes_url,type_id)
        else:
            url = (self.orion_entities_url,)
        if attribute:
            url = url + ('attributes',attribute)

        r = self.do_request(
                'get',
                self._make_url(*url),
                )
        if r:
            if 'statusCode' in r:
                if r["statusCode"].get("code", None) == u'404':
                    return None
            return self.orion_to_py(r)
        else:
            return r

    def fetch_attribute(self, entity_id, attribute):
        '''
            fetch_attribute(
                    'entity_id',
                    'attribute'.
                    )
            return the specified attribute from the specified entity.
            '''
        r = self.do_request(
                'get',
                self._make_url(self.orion_entities_url,entity_id,"attributes",attribute),
                )
        resp = r.json()
        if 'statusCode' in resp:
            if resp["statusCode"].get("code", None) == u'404':
                return None
        return resp["attributes"][0]["value"]

    def update_attribute(self, entity_id, attribute, newdata):
        '''update_attribute(
                    'entity_id',
                    'attribute'.
                    )
            update the speficied attribute of the specified entity'''
        return self.do_request(
            'put',
            self._make_url(self.orion_entities_url,entity_id,"attributes",attribute),
            data = json.dumps({"value": newdata}),
            )

    def delete_entity(self, entity_id):
        '''delete_entity('entity_id')
        delete the specified entity'''

        return self.do_request(
                'delete',
                self._make_url(self.orion_entities_url,entity_id),
                )

    def cancel_subscription(self,subscr_id):
        return self.do_request(
                'post',
                "%s/%s/unsubscribeContext" % (self.orion_host_prefix,self._orion_version_str),
                json={'subscriptionId': subscr_id},
                )

    def setup_notification(self, entity_id, attributes=[],
                            callback_url="localhost:8000/fw/orion-notify/",
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

        logger.info('Subscribing: %s' % json.dumps(msg))
        return self.do_request(
                    'post',
                    "%s/%s/subscribeContext" % (self.orion_host_prefix,self._orion_version_str),
                    json=msg,
                    )

    def do_request(self,verb,url,**kwds):
        r = getattr(requests,verb)(
                        url,
                        headers=self.get_headers(),
                        verify=False,
                        timeout=self.timeout,
                        **kwds
                        )
        if r.status_code == 200:
            errors = self.has_orion_error(r.json())
            if errors:
                return ErrorValue(orion_errors=errors)
            else:
                return r.json()
        try:
            return ErrorValue(status_code=r.status_code,json=r.json())
        except:
            return ErrorValue(status_code=r.status_code,content=r.content)

    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.strftime('%Y-%m-%dT%H:%M:%SZ')
            elif isinstance(obj, date):
                return obj.strftime('%Y-%m-%d')
            # Let the base class default method raise the TypeError
            return json.JSONEncoder.default(self, obj)

    @staticmethod
    def has_orion_error(content):
        # if the output is not boolean False, there is an error
        if 'orionError' in content:
            err = json.dumps(content['orionError'], indent=4)
            return err 
        return False
