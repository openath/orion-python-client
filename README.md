# orion-python-client

A python module and examples for using Orion Context Broker

The Orion Context Broker is a powerful means for collecting data 
IoT data in the cloud, and relaying it on.  It combines a ReST front 
end to MongoDB, exposing nice Mongo features like geographical search;
and a publish-subscribe mechanism.   Documents can be created and updated
with simple ReST calls.  Another ReSt call can set up notifications,
so that an app can be POSTed to when something changes.

The Orion documentation is at
     http://fiware-orion.readthedocs.org/
 
The examples in the Orion docs use CURL.  We're using Python, so we made a little 
client with some wrapper functions.  Hopefully this will save time for any Pythonista
wanting to get to grips with Orion.

Make sure you run the CURL examples and get a token using the main Orion tutorial.
 

# Installation

If you just want the code,

    pip install orionclient

To get the tests too, clone this repo.


## Basic use:

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


Read the source for the other methods - it's pretty short ;-)


## Running the tests

There are no UNIT tests.  Instead there is a functional test suite which can run
against an Orion instance.   This is in the Git repo, but 
You need to provide a little settings file with
your credentials.  To use the FIWARE Lab, copy 'test_settings.py.example' to a file 
'test_settings.py', add your FIWARE Lab username and password, then run

    python test.py

The settings file looks like this:

    class settings:
        orion_host_url='http://orion.lab.fiware.org'
        orion_host_port=1026  #or 443
        authMethod='fiware-token'
        username='you@example.com'
        password='SECRET'
        orion_token_url='https://orion.lab.fiware.org/token'
    settings=settings()


Add your own FIWARE Lab credentials, or those fo your own FIWARE instance if you wish.
We run our own Orion environment from Docker, with a lightweight Python server in front
which can serve tokens to us.

