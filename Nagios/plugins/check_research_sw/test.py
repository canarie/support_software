'''
Copyright 2014 - CANARIE Inc. All rights reserved

Synopsis: Unit tests for the check_research_sw module

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

'''
import check_research_sw
import unittest
import argparse
from StringIO import StringIO
import sys
import requests

# ------------------------------------------------------------------------------
class TestCommandLineArguments(unittest.TestCase):
    '''Test command line argument processing with invalid argument lists
    
       Valid argument lists are verified by other test cases in this file
    '''
	    
    def test_args(self):
        ''' Test both valid and invalid command line options '''
        
    	# We need to capture standard out to ensure that the correct messages are
    	# being created
    	saved_stdout = sys.stdout
    	out = StringIO()
        sys.stdout = out    	    
        
        # The command lines we're using to test with, along with the values we
        # expect check_research_sw to exit with in each case.
        command_lines  = [dict([('arg_list',['check_research_sw', 'abc',     '49']), ('exit_code', check_research_sw.codelist['WARNING'])]),  # bad type
        	              dict([('arg_list',['check_research_sw', 'service', '3a']), ('exit_code', check_research_sw.codelist['WARNING'])]),  # bad id
        	              dict([('arg_list',['check_research_sw', 'service'      ]), ('exit_code', check_research_sw.codelist['WARNING'])]),  # missing id
                          dict([('arg_list',['check_research_sw',            '49']), ('exit_code', check_research_sw.codelist['WARNING'])]),  # missing type 
                          dict([('arg_list',['check_research_sw'                 ]), ('exit_code', check_research_sw.codelist['WARNING'])]),  # missing both
        	         ]
            
        try:
        	for cmd in command_lines:

                # Python lets you re-write argv - very cool
        	    sys.argv = cmd['arg_list']

                # Arrange to intercept the SystemExit exception so we can
                # examine the exit code that check_research_sw returns
	            with self.assertRaises(SystemExit) as cm:
	            	    check_research_sw.main()
                
                    self.assertEqual(cm.exception.code, cmd['exit_code'])
                    output = out.getvalue()
                    assert "WARNING" in output
                    assert "Usage error" in output
        	

	finally:
	    sys.stdout = saved_stdout


# ------------------------------------------------------------------------------
class TestHTTPErrors(unittest.TestCase):
    ''' Test response to HTTP errors

	    There are three types of errors: In the case of communications errors, an
	    HTTP session cannot be established with the endpoint and the "requests"
	    module raises an exception.
	    
	    In the second case, a connection is established but the HTTP return code
	    is something other than 200, indicating a problem.
	    
	    In the third case, the HTTP return code is 200, but the payload returned
	    is not JSON
    '''
    
    class TestResponse ():
        ''' Simulate the "response" class
        
            In check_research_sw, a call is made to requests.get() to return an
            object of class "response. We replace that class with this one so we
            can control the execution of the calling code. Specifically, this class
            allows us to set the HTTP return code and test the caller with both
            good and bad JSON encoding.
            
            The functions simulate_bad_http_transaction() and simulate_bad_json_transaction()
            below are responsible for delivering objects of this class to check_research_sw.
        '''
    	  
    	def __init__(self,status,is_json):
    	    ''' Set the value of the HTTP return code we should emulate and a
    	        flag indicating whether or not we should emulate a payload 
    	        with or without JSON encoding.
    	    '''
    	    self.status_code = status
    	    self.json_valid = is_json
    	    	    
    	def json(self):
    	    ''' Emulate the json() method in the response class '''
    	    if (self.json_valid != True):
    	        raise ValueError
    	        
    	        
    # ---------------------------------------
    def __init__(self, *args, **kwargs):
        ''' Initializer for TestHTTPErrors
        
            Define an index into the list of exceptions we are emulating
        '''
        super(TestHTTPErrors, self).__init__(*args, **kwargs)
        self.fault_index = 0
       
       
    # List of exceptions we are emulating   
	self.fault_list = [ requests.exceptions.ConnectionError, 
        	            requests.exceptions.Timeout, 
        	            requests.exceptions.TooManyRedirects,
        	            requests.exceptions.HTTPError,
        		        requests.exceptions.RequestException ]

	
    # -------------------------------------------------
    def simulate_http_failure(self, url, timeout): 
    	'''Simulate HTTP communiciations failures
    	       
    	   Specifically, errors where the communications link cannot be
    	   established so that we get an execption from the "requests"
    	   module and no HTTP return code
    	'''
    	raise self.fault_list[self.fault_index]


    # -------------------------------------------------
    def simulate_bad_http_transaction(a,b, timeout):
    	''' Simulate a bad (ie. not 200) HTTP return code '''
    	
    	r = TestHTTPErrors.TestResponse(401,True)    	    
    	return r
    	    
    	    
    # -------------------------------------------------
    def simulate_bad_json_transaction(a,b, timeout):
    	'''Simulate the case where we get a valid HTTP response, but it does not include a JSON payload'''
    	
        r = TestHTTPErrors.TestResponse(200,False)    	    
        return r
    	    
	
    # -------------------------------------------------------------------------    	
    def test_http_error(self):    
        ''' Test errors raised by the Python HTTP get handler
        
            We do this by replacing requests.get() with the function defined
            above called simulate_http_failure(). This function raises all
            of the types of exceptions that the real requests.get() does.
        '''
    	
        # As we need to check stdout, we redirect it to our own StringIO object
    	saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out

        try:
            # Replace requests.get, which is used in check_research_sw, by our
            # own handler, which raises the same exceptions that requests.get does
            requests.get = self.simulate_http_failure
            
            # A valid command line, so the command line parser doesn't fail
            sys.argv = ["check_research_sw", "service", "49"]
            
            # For each of the faults that the original requests.get() can generate 
            for self.fault_index in range (0,len(self.fault_list)):
	    	
                # Call check_research_sw and capture the SystemExit exception
                with self.assertRaises(SystemExit) as cm:
                    check_research_sw.main()
	    	
                # Done. Make sure the system exit code is as expected
	    	    self.assertEqual(cm.exception.code, check_research_sw.codelist['CRITICAL'])

                # Validate what was written to stdout
                output = out.getvalue().strip()
                assert "CRITICAL" in output
                assert "Connection error" in output
 
        finally:
            # Put stdout back the way we found it
	        sys.stdout = saved_stdout

    # -------------------------------------------------------------------------
    def test_http_return_codes (self):
        ''' Test return code response in cases where HTTP transaction is successful
        
        '''

        # As we need to check stdout, we redirect it to our own StringIO object
        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out

        try:
	        
            # A valid command line, so the command line parser doesn't fail
            sys.argv = ["check_research_sw", "service", "49"]

            # Test HTTP transaaction where we get a non-200 response code. We do
            # this by replacing requests.get() with our own function.
            requests.get = self.simulate_bad_http_transaction
            with self.assertRaises(SystemExit) as cm:
                check_research_sw.main()

            # Done. Make sure the system exit code is as expected
            self.assertEqual(cm.exception.code, check_research_sw.codelist['CRITICAL'])
            
            # Validate what was written to stdout
            output = out.getvalue().strip()
            assert "CRITICAL" in output
            assert "HTTP response status code 401" in output
            
            
            # Test HTTP transaction where we get a status of 200 but the
            # return value is not valid JSON
            out.truncate(0)
            
            # Replace requests.get() with our own function
            requests.get = self.simulate_bad_json_transaction
            with self.assertRaises(SystemExit) as cm:
                check_research_sw.main()
	    	
            # Done. Make sure the system exit code is as expected
            self.assertEqual(cm.exception.code, check_research_sw.codelist['CRITICAL']) 
            
            # Validate what was written to stdout
            output = out.getvalue().strip()
            assert "CRITICAL" in output
            assert "Invalid response" in output
            	
	        
        finally:
            # Put stdout back the way we found it
            sys.stdout = saved_stdout
    	
	    
# ------------------------------------------------------------------------------
class TestJSONErrors(unittest.TestCase):
    ''' Test cases where JSON is actually returned to check_research_sw '''

    # All type of JSON responses, both good and bad
    json_response_data =  \
        [   dict([('json_response', { u'status': u'OK', u'lastUpdate': u'2014-01-13T21:26:04Z', u'meta': {u'pollingInterval': u'Every 15 minutes'}}), ('exit_code', check_research_sw.codelist['OK'])]),           # status OK
            dict([('json_response', { u'status': u'NOTOK', u'lastUpdate': u'2014-01-13T21:26:04Z', u'meta': {u'pollingInterval': u'Every 15 minutes'}}), ('exit_code', check_research_sw.codelist['CRITICAL'])]),  # status not OK or Unknown
            dict([('json_response', { u'lastUpdate': u'2014-01-13T21:26:04Z', u'meta': {u'pollingInterval': u'Every 15 minutes'}}), ('exit_code', check_research_sw.codelist['CRITICAL'])]),                       # status not in response
            dict([('json_response', { u'status': u'UNKNOWN', u'lastUpdate': u'2014-01-13T21:26:04Z', u'meta': {u'pollingInterval': u'Every 15 minutes'}}), ('exit_code', check_research_sw.codelist['WARNING'])]), # status Unknown, other parameters present            
            dict([('json_response', { u'status': u'ERROR', u'lastUpdate': u'2014-01-13T21:26:04Z', u'meta': {u'pollingInterval': u'Every 15 minutes'}}), ('exit_code', check_research_sw.codelist['CRITICAL'])]),  # status Error, other parameters present            
            dict([('json_response', { u'status': u'ERROR', u'meta': {u'pollingInterval': u'Every 15 minutes'}}), ('exit_code', check_research_sw.codelist['CRITICAL'])]),                                          # status Error, lastUpdate missing            
            dict([('json_response', { u'status': u'ERROR', u'lastUpdate': u'2014-01-13T21:26:04Z', u'meta': {}}), ('exit_code', check_research_sw.codelist['CRITICAL'])]),                                         # status Error, PollingInterval missing
            dict([('json_response', { u'status': u'OK',  u'meta': {u'pollingInterval': u'Every 15 minutes'}}), ('exit_code', check_research_sw.codelist['WARNING'])]),                                             # missing LastUpdate
            dict([('json_response', { u'status': u'OK'}), ('exit_code', check_research_sw.codelist['WARNING'])]),                                                                                                  # missing LastUpdate and PollingInterval
            dict([('json_response', { u'status': u'OK', u'lastUpdate': u'2014-01-13T21:26:04Z', u'meta': {}}), ('exit_code', check_research_sw.codelist['WARNING'])]),                                             # missing PollingInterval
            dict([('json_response', { u'status': u'OK', u'lastUpdate': u'2014-01-13T21:26:04Z'}), ('exit_code', check_research_sw.codelist['WARNING'])]),                                                          # missing meta
            dict([('json_response', { u'status': u'OK', u'lastUpdate': u'2014-01-13T21:26:04Z', u'pollingInterval': u'Every 15 minutes'}), ('exit_code', check_research_sw.codelist['WARNING'])]),                 # pollingInterval not in meta
        ]
		   		   
    json_response_index = 0
    
    # ---------------------------------------
    class TestJSONResponse ():
    	      	    	    
        ''' Simulate the "response" class

            In check_research_sw, a call is made to requests.get() to return an
            object of class "response. We replace that class with this one so we
            can control the execution of the calling code. Specifically, this class
            allows us to set the HTTP response code and to control the content of
            the JSON data returned.
            
            The functions simulate_json_response() below is responsible for 
            delivering objects of this class to check_research_sw.
        '''
        def __init__(self,json_to_return):
            self.the_json = json_to_return
            self.status_code = 200  # We don't want HTTP to fail, so always return 200
    	    	    
        def json(self):
            return self.the_json
    	        
    # -------------------------------------------------
    def simulate_json_response(self,x,timeout):
        ''' Simulate JSON responses from the web services call 
        
            This is done by returning elements of json_response_data[] as defined above.
        '''
            
        r = TestJSONErrors.TestJSONResponse(self.json_response_data[self.json_response_index]['json_response'])    
        return r
	    	  
	    
    def test_json_strings(self):
        ''' Test various JSON return values, both good and bad '''
        
        # As we need to check stdout, we redirect it to our own StringIO object
    	saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out


        try:
            # Test command lines that request information for both service and platforms. Alternate
            # between these two as we perform the tests below.
            command_lines = [["check_research_sw", "service", "49"], ["check_research_sw", "platform", "2"]]
            command_line_index = 0;

            # Replace requests.get() with our own function that returns the JSON
            # values we want to test with.
            requests.get = self.simulate_json_response
	    
            # None of these inputs should result in an exception - if they do, the test fails
            for self.json_response_index in range (0,len(self.json_response_data)):
                out.truncate(0);
                
                # Use a command line that won't cause the command line parser to fail
                sys.argv = command_lines[command_line_index]
                
                # And switch to the other valid command line for the next test
                command_line_index = 1 - command_line_index
                
                with self.assertRaises(SystemExit) as cm:
                    check_research_sw.main()
	            
                # Done. Make sure the system exit code is as expected
                self.assertEqual(cm.exception.code, self.json_response_data[self.json_response_index]['exit_code'])
            	
                output = out.getvalue().strip()
                
                # Find the element of check_research_sw.codelist that we were expecting 
                # (self.json_response_data[self.json_response_index]['exit_code']) and
                # convert its key to a string. This string should appear in generated output.
                # This iterator works because the values (as well as the keys, of course)
                # in check_research_sw.codelist are unique.
                for thekey,thevalue in check_research_sw.codelist.iteritems():
                    if (thevalue == self.json_response_data[self.json_response_index]['exit_code']):
                        break
                        
                assert thekey in output
 
        finally:
            # Put stdout back the way we found it
            sys.stdout = saved_stdout
	    
	    
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
