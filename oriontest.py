import json
import os
import requests

from bson.json_util import loads
from optparse import make_option
from pprint import pprint
from pymongo import MongoClient
from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.urlresolvers import reverse

from docengine.mongoutils.models import Log

from project.fiware.orion import *


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
         make_option('--callback_host', '-c',
                     dest='callback_host',
                     help='host IP/name where to post back subscribed notifications.',
                     default=get_local_host(),
                     ),
     )

    help = "Runs through the Orion cycle"

    def handle(self, *args, **options):


        HEADERS = get_headers()  #calls get_token too

        domain = options['callback_host']
        if (not domain.startswith('http://')) and (not domain.startswith('https://')):
            if settings.DEBUG:
                domain = "http://" + domain
            else:
                domain = "https://" + domain

        print "1. Get the Orion version"
        data = get_version()
        print data

        # print "2. Query a sensor in Santander"
   #      curl orion.lab.fiware.org:1026/v1/contextEntities/urn:smartsantander:testbed:357 \
   # -X GET -s -S --header 'Content-Type: application/json'  --header 'Accept: application/json' \ 
   # --header  "X-Auth-Token: $AUTH_TOKEN" | python -mjson.tool

        # data = fetch_entity("urn:smartsantander:testbed:357")
        # pprint(data)

        print
        print "2. Create a node, race with 37 starters"
        MY_ENTITY = "opentrack:race:943da5d6-c160-4991-88cf-5e31d3f3dc5d"

        RACE = dict(
            race_name="Sunday Fun Run",
            start_list=[
                dict(bib="001", name="Tom"),
                dict(bib="002", name="Dick"),
                dict(bib="003", name="Harry"),
            ]
        )
        
        created = create_entity(MY_ENTITY, RACE, typ="race")

        print
        print "3. Query the node's start LIST"
        START_LIST = fetch_attribute(MY_ENTITY, "start_list")
        pprint(START_LIST)

        print
        print "4. Set up notification to call localhost on this race"
        print domain
        stuff = setup_notification(
            MY_ENTITY,
            attributes=["race_name", "start_list"],
            callback_url= "%s%s" % (domain, reverse('fw-orion-notify'))
            )
        print stuff
        subscr_id = stuff['subscribeResponse']['subscriptionId']

        print
        print "5. Replace the start list, add one more"
        NEW_START_LIST = START_LIST + [dict(bib="005", name="Walt")]
        ua = update_attribute(MY_ENTITY, "start_list",  NEW_START_LIST)
        if ua == True:
            print "updated start list"
        else:
            print ua

        print
        print "6. Query the node's start LIST to check"
        START_LIST_AGAIN = fetch_attribute(MY_ENTITY, "start_list")
        print START_LIST_AGAIN

        print
        print "7. Delete the race"
        deleted = delete_entity(MY_ENTITY)
        if deleted:
            print "    deleted"

        print "8. Query the node after deletion"
        attr = fetch_attribute(MY_ENTITY, "start_list")
        print attr

        print
        print "9. Check notification in the Log"
        sleep(3)
        latest = Log.objects.order_by('-time').first()
        content = json.loads(latest.message)
        print "original ID: %s == received: %s" % (subscr_id, content['subscriptionId'])
        #print(latest.message)

        print
        print "10. cancel Susbscription"
        unsubscribe = cancel_subscription(subscr_id)
        print unsubscribe

        print
        print "11. Extend start list again"
        NEW_START_LIST = START_LIST + [dict(bib="007", name="James")]
        ua = update_attribute(MY_ENTITY, "start_list",  NEW_START_LIST)
        if ua == True:
            print "updated start list"
        else:
            print ua

    # curl localhost:1026/v1/contextEntities/E1 -s -S \
    # --header 'Content-Type: application/json' \
    # --header 'Accept: application/json' -X DELETE        
