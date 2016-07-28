#!/usr/bin/python

'''
Copyright 2016 - CANARIE Inc. All rights reserved

Synopsis: simple python script that checks the status of a software service or    
          platform registered on science.canarie.ca and	returns	the result to
          a Nagios monitoring system

Blob Hash: $Id$

-------------------------------------------------------------------------------

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, 
   this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, 
   this list of conditions and the following disclaimer in the documentation 
   and/or other materials provided with the distribution.

3. The name of the author may not be used to endorse or promote products 
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY CANARIE Inc. "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF 
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.


Theory of Operations:

This module is intended to be called from the Nagios nrpe service in response to
a request from a Nagios head end. Command line arguments provided by the Nagios
head end are parsed to determine 

a) whether information is being requested for a service (ie. RPI) or platform; 
b) the science.canarie.ca id for that service or platform.

This information is used to build up an appropriate URL to retrieve information
from the RESTful web service that returns service/platform status information. A 
GET request is issued to this URL and the results are converted to the format
expected by Nagios and returned. The rules are as follows:

1) Nagios expects the exit code of this script to be one of the values defined in
   'codelist' below.
   
2) Nagios expects additional (ie. human readable) information about the status
   of the service/platform to be written to stdout. The format is a textual
   indicator of the status (ie. one of the keys from 'codelist' below) followed
   by a hyphen, followed by a string describing the current service/platform
   state.
   
3) If the web service request can't be completed due to a communications error,
   a CRITICAL status is returned.
   
4) If the web service requests results in an HTTP return code other than 200,
   a CRITICAL status is returned.
   
5) If the HTTP transaction is successful, but the returned data is not JSON-
   encoded, a CRITICAL status is returned.
   
6) If JSON is returned, but the 'status' element is missing, a CRITICAL status
   is returned.
   
7) If status from the web service is UNKNOWN, a WARNING status is returned. This
   indicates the service/platform has not yet been polled.
   
8) If either the lastUpdate or pollingInterval items are missing from the web
   service response, a WARNING status is returned (assuming the status is OK). 
   This is likely a version mismatch.
   
'''

import requests
import argparse
import httplib

# URL of the web service we need to call. Conveniently defined at the top of this file
urlbase = "https://science.canarie.ca/researchsoftware/rs/"


# These are the various exit codes we support, along with human-readable strings.
# Exit codes are returned to the Nagios daemon
codelist = {'DEPENDENT':4, 'UNKNOWN':3, 'OK':0, 'WARNING':1, 'CRITICAL':2}

def check_status(response):
    ''' Ensure that the 'status' element is present in the JSON response from the web service
    
        If present, it must be set to 'OK' or 'UNKNOWN'. If status is set to
        something else or missing altogether, set our exit code to 'CRITICAL', If
        the status is set to UNKNOWN, set exit code to WARNING to indicate to
        Nagios that there may be a problem.
    '''
    
    code = 'CRITICAL'
    if ('status' in response):
        if (response['status'] == 'OK'):
            code = 'OK'

        elif (response['status'] == 'UNKNOWN'):
            code = 'WARNING'

    # If the status in response was 'ERROR', there is something wrong with the
    # service and we leave the return code at 'CRITICAL'

    return (code)
	
	
	
def check_response (response, code, msg):
    ''' Check the lastUpdate and pollingInterval JSON elements
    
        If they're both there, exit code is OK. If one or both are missing,
        it's not a fatal error but something is mis-configured so set exit code
        to WARNING. Of course, if the exit code was already set to CRITICAL as a
        result of checking the status element of the JSON response, don't
        change it. 
        
        While we're checking these fields, add information to the human-readable
        message we're writing to stdout for Nagios to display.
    '''

    retcode = 'OK'

    if ('lastUpdate' in response):
        msg = msg + ' - Last update: ' + response['lastUpdate']
    else:
        retcode = 'WARNING';
			
    if ('meta' in response):
        if ('pollingInterval' in response['meta']):
            msg = msg + ' - Polling: ' + response['meta']['pollingInterval']
        else:
            retcode = 'WARNING';

    else:
        retcode = 'WARNING'

    # There will be a message in the response if the service has not yet been
    # polled
    if ('message' in response):
        msg = msg + ' - Details: ' + response['message']

		
    # If the exit code has previously been set to something other than OK, don't change it.
    if (code == 'CRITICAL'):
        retcode = 'CRITICAL'
    elif (code == 'WARNING'):
        retcode = 'WARNING'
		
    return (retcode, msg)
	


# Build up the URL used to retrieve status information"
def main():

    code = 'CRITICAL'   # assume badness until we learn otherwise
    timeout_sec = 5
    message = 'Research Software'

    try:
        # Build up command line parser
        parser = argparse.ArgumentParser()
        parser.add_argument("id", type=int, help="numeric identifier of the resource of interest")

        args = parser.parse_args()
    
        url = urlbase + "resource/" + str(args.id) + "/status"

    
        # If we get this far, we know the component type and id. Add them to the
        # human readable message we're returning to the Nagios daemon in stdout
        message = message + ' resource ' + str(args.id)

        # Make a request to the web service that tells us about the status of 
        # the specified software component (ie. service or platform).
        r = requests.get(url, timeout=timeout_sec)
   
        # If the HTTP transaction was successful ...
        if r.status_code == httplib.OK:
            
            # Set exit code based on status field returned in the JSON response.
            # The call to r.json() will raise a ValueError exception if the response
            # does not contain valid JSON
            code = check_status (r.json())
	    	    
            # Adjust the exit code as necessary based on the other fields in
            # the JSON response and add to the human-readable message we'll
            # be returning via stdout.
            code, message = check_response (r.json(), code, message)

        else:
            # Bad HTTP response code. Update message on stdout appropriately
            message = message + ' - HTTP response status code {0}'.format(r.status_code) 	  


    # Catch any exceptions raised during the above processing and adjust the
    # outgoing human readable message accordingly.
    except SystemExit:
	    message = message + " - Usage error"      # raised by argparse
	    code = 'WARNING'

    except ValueError:
        message = message + ' - Invalid response' # raised by requests.get

    except requests.exceptions.ConnectionError:
        message = message + ' - Connection error'

    except requests.exceptions.Timeout:
        message = message + ' - Timeout'

    except requests.exceptions.TooManyRedirects:
        message = message + ' - Too many redirects'	

    except requests.exceptions.HTTPError:
        message = message +' - HTTP error'

    except requests.exceptions.RequestException: 
        message = message + ' - Unknown communications error'    # catch all
  
  
    print(code + ' - {0} '.format(message))
    exit(codelist[code])

# -----------------------------------------------------------------------------
if  __name__ =='__main__':
    main()
