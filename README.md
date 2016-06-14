# orion-python-client

A python module and examples for using Orion Context Broker

The Orion Context Broker is a powerful means for collecting data 
IoT data in the cloud, and relaying it on.  It combines a ReST front 
end to MongoDB, exposing nice Mongo features like geographical search;
and a publish-subscribe mechanism.   Documents can be created and updated
with simple ReST calls.  Another ReSt call can set up notifications,
so that an app can be POSTed to when something changes.

The documentation is at
     http://fiware-orion.readthedocs.org/
 
The examples in the Orion docs use CURL.  We're using Python, so we made a little 
client with some wrapper functions.  Hopefully this will save time for any Pythonista
wanting to get to grips with Orion.

Make sure you run the CURL examples and get a token using the main Orion tutorial.
 

# Installation

    pip install 

## Running the tests

There are no UNIT tests.  Instead there is a functional test suite which can run
against an Orion instance.   You need to provide a little settings file with
your credentials.  To use the FIWARE Lab, copy 'test_settings.py.example' to a file 
'test_settings.py', add your FIWARE Lab username and password, then run

    python test.py




