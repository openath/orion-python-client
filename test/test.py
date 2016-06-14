"""Simple tests for OrionClient

This script needs an accomanpying module
 test_settings.py
like this:

class settings:
	orion_host_url='https://orion1.reportlab.com'
	orion_host_port=443
	authMethod='fiware-token'
	username='myuserid'
	password='.....................'
	orion_token_url='https://orion1.reportlab.com/token'
settings=settings()

If the server has no password protection then authMethod should be None
A suitable module is in eiger:scripts/test_settings.py

Since we expect people to be lazy and use the FIWARE Lab, we have
prefixed our entity names with ZYX, and hope this is not in use in
the FIWARE Lab!

"""

_data={	u'ZYXMeetingRoom1': {u'pressure': u'1030', u'temperature': u'70'},
		u'ZYXRoom1': {u'pressure': u'731', u'temperature': u'25'},
		u'ZYXRoom10': {u'pressure': u'732', u'temperature': u'23'},
		u'ZYXRoom19': {u'pressure': u'751', u'temperature': u'23'},
		u'ZYXRoom3': {u'pressure': u'732', u'temperature': u'23'},
		u'ZYXRoom31': {u'pressure': u'750', u'temperature': u'19'},
		u'ZYXRoom32': {u'pressure': u'753', u'temperature': u'19'},
		u'ZYXRoom9': {u'pressure': u'732', u'temperature': u'23'},
		u'ZYXRoom91': {u'pressure': u'732', u'temperature': u'23'}}

def test():
	import sys, os
	h=os.path.normpath(os.path.dirname(sys.argv[0]))
	try:
		from orionclient import OrionClient
	except ImportError:
		sys.path.insert(0,os.path.normpath(os.path.join(h,'..','src')))
		from orionclient import OrionClient
	sys.path.insert(0,h)
	del h
	from pprint import pprint
	from test_settings import settings

	client = OrionClient(
				orion_host_url=settings.orion_host_url,
				orion_host_port=settings.orion_host_port,
				authMethod=settings.authMethod,
				username=settings.username,
				password=settings.password,
				orion_token_url=settings.orion_token_url,
				)
	client.token

	print 'version'
	pprint(client.orion_version)

	print 'create a ZYXmeetingroom'
	pprint(client.create_entity('ZYXMeetingRoom1',type_id="ZYXMeetingRoom", temperature=70,pressure=1030))
	print 'create another ZYXmeetingroom'
	pprint( client.create_entity('Room1',type_id="ZYXMeetingRoom", temperature=70,pressure=930))
	for entity_id,attributes in {u'ZYXRoom1': {u'pressure': u'731', u'temperature': u'25'},
		u'ZYXRoom10': {u'pressure': u'732', u'temperature': u'23'},
		u'ZYXRoom19': {u'pressure': u'751', u'temperature': u'23'},
		u'ZYXRoom3': {u'pressure': u'732', u'temperature': u'23'},
		u'ZYXRoom31': {u'pressure': u'750', u'temperature': u'19'},
		u'ZYXRoom32': {u'pressure': u'753', u'temperature': u'19'},
		u'ZYXRoom9': {u'pressure': u'732', u'temperature': u'23'},
		u'ZYXRoom91': {u'pressure': u'732', u'temperature': u'23'}}.iteritems():
		print 'create room', entity_id,' ',
		pprint(client.create_entity(entity_id,type_id='Room',**attributes))

	print 'all entities of type ZYXRoom'
	#would be dangerous to query all enttities on the main FIWARE Lab
	pprint(client.fetch_entity(type_id='ZYXRoom'))

	print 'updating Room91.temperature-->33'
	pprint(client.update_attribute('ZYXRoom91','temperature',33))
	print 'updating Room31.temperature-->12 pressure-->1000 extra="why"'
	pprint(client.update_entity('ZYXRoom31',temperature=12,pressure=1000,extra="why"))

	print 'all Rooms'
	pprint(client.fetch_entity(type_id='ZYXRoom'))

	print 'entity Room1'
	pprint(client.fetch_entity('ZYXRoom1'))

	print 'Room pressures'
	pprint(client.fetch_entity(type_id='ZYXRoom',attribute='pressure'))

	print 'Room temperatures'
	pprint(client.fetch_entity(type_id='ZYXRoom',attribute='pressure'))


	#delete what we created - two enttiy types
	for ent_type in ['ZYXMeetingRoom', 'ZYXRoom']:
		for entity_id in client.fetch_entity(type_id=ent_type):
			print 'deleting',entity_id,' ',
			pprint(client.delete_entity(entity_id))
		print 'all entities of type %s after deletion' % ent_type
		pprint(client.fetch_entity(type_id=ent_type))

if __name__=='__main__':
	test()
