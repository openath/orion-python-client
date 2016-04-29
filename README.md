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
 
The examples use CURL.  We're using Python, so we made a test script with
some wrapper functions.  Hopefully this will save time for any Pythonista
wanting to get to grips with Orion.

Make sure you run the CURL examples and get a token using the main Orion tutorial.
 
This is a module and a test command lifted from a Django project.  It has a
few Django imports.  It is not packaged for deployment nor instantly runnable.  We'll try to make it independently runnable in the next few days.

