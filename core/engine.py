#
#    Copyright (c) 2007-2009 Corey Goldberg (corey@goldb.org)
#    License: GNU GPLv3
#
#    This file is part of Pylot.
#    
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.  See the GNU General Public License 
#    for more details.
#
 

import cookielib
import copy
import httplib
import os
import pickle
import Queue
import random
import re
import socket
import sys
import time
import urllib2
import urlparse
from threading import Thread
import config
import results



# get config options from config.py
GENERATE_RESULTS = config.GENERATE_RESULTS  # default is True
COOKIES_ENABLED = config.COOKIES_ENABLED  # default is True
HTTP_DEBUG = config.HTTP_DEBUG  # default is False
SHUFFLE_TESTCASES = config.SHUFFLE_TESTCASES  # default is False
WAITFOR_AGENT_FINISH = config.WAITFOR_AGENT_FINISH  # wait for last requests to complete before stopping. default is True
SOCKET_TIMEOUT = config.SOCKET_TIMEOUT  # global for all socket operations

        
        
class LoadManager(Thread):
    def __init__(self, num_agents, interval, rampup, log_msgs, runtime_stats, error_queue, output_dir=None, test_name=None):
        Thread.__init__(self)
        
        socket.setdefaulttimeout(SOCKET_TIMEOUT)  # this affects all socket operations (including HTTP)
        
        self.running = True
        self.num_agents = num_agents
        self.interval = interval
        self.rampup = rampup
        self.log_msgs = log_msgs
        self.runtime_stats = runtime_stats
        self.error_queue = error_queue  # list used like a queue
        self.test_name = test_name

        if output_dir and test_name:
            self.output_dir = time.strftime(output_dir + '/' + test_name + '_' + 'results_%Y.%m.%d_%H.%M.%S', time.localtime())
        elif output_dir:
            self.output_dir = time.strftime(output_dir + '/' + 'results_%Y.%m.%d_%H.%M.%S', time.localtime())
        elif test_name:
            self.output_dir = time.strftime('results/' + test_name + '_' + 'results_%Y.%m.%d_%H.%M.%S', time.localtime())
        else:
            self.output_dir = time.strftime('results/results_%Y.%m.%d_%H.%M.%S', time.localtime()) 
        
        # initialize/reset stats
        for i in range(self.num_agents): 
            self.runtime_stats[i] = StatCollection(0, '', 0, 0, 0, 0, 0, 0)
            
        self.workload = {
            'num_agents': num_agents, 
            'interval': interval * 1000,  # convert to millisecs   
            'rampup': rampup, 
            'start_epoch': time.mktime(time.localtime())
        }  
        
        self.results_queue = Queue.Queue()  # result stats get queued up by agent threads
        self.agent_refs = []
        self.msg_queue = []  # list of Request objects
        
    
    def run(self):
        self.running = True
        self.agents_started = False
        try:
            os.makedirs(self.output_dir, 0755)
        except OSError:
            self.output_dir = self.output_dir + time.strftime('/results_%Y.%m.%d_%H.%M.%S', time.localtime())
            try:
               os.makedirs(self.output_dir, 0755)
            except OSError:
                sys.stderr.write('ERROR: Can not create output directory\n')
                sys.exit(1)
        
        # start thread for reading and writing queued results
        self.results_writer = ResultWriter(self.results_queue, self.output_dir)
        self.results_writer.setDaemon(True)
        self.results_writer.start()
        
        for i in range(self.num_agents):
            spacing = float(self.rampup) / float(self.num_agents)
            if i > 0:  # first agent starts right away
                time.sleep(spacing)
            if self.running:  # in case stop() was called before all agents are started
                agent = LoadAgent(i, self.interval, self.log_msgs, self.output_dir, self.runtime_stats, self.error_queue, self.msg_queue, self.results_queue)
                agent.start()
                self.agent_refs.append(agent)
                agent_started_line = 'Started agent ' + str(i + 1) 
                if sys.platform.startswith('win'):
                    sys.stdout.write(chr(0x08) * len(agent_started_line))  # move cursor back so we update the same line again
                    sys.stdout.write(agent_started_line)
                else:
                    esc = chr(27) # escape key
                    sys.stdout.write(esc + '[G' )
                    sys.stdout.write(esc + '[A' )
                    sys.stdout.write(agent_started_line + '\n')
        if sys.platform.startswith('win'):
            sys.stdout.write('\n')
        print '\nAll agents running...\n\n'
        self.agents_started = True
        
    
    def stop(self):
        self.running = False
        for agent in self.agent_refs:
            agent.stop()
        
        if WAITFOR_AGENT_FINISH:
            keep_running = True
            while keep_running:
                keep_running = False
                for agent in self.agent_refs:
                    if agent.isAlive():
                        keep_running = True
                        time.sleep(0.1)

        self.results_writer.stop()
        
        if GENERATE_RESULTS:
            # pickle dictionaries to files for results post-processing        
            self.store_for_post_processing(self.output_dir, self.runtime_stats, self.workload)  
            
            # auto-generate results from a new thread when the test is stopped
            self.results_gen = results.ResultsGenerator(self.output_dir, self.test_name)
            self.results_gen.setDaemon(True)
            self.results_gen.start()


    def add_req(self, req):
        self.msg_queue.append(req)
        
    
    def store_for_post_processing(self, dir, runtime_stats, workload):
        fh = open(dir + '/agent_detail.dat', 'w')
        pickle.dump(runtime_stats, fh)
        fh.close()
        fh = open(dir + '/workload_detail.dat', 'w')
        pickle.dump(workload, fh)
        fh.close()         




class LoadAgent(Thread):  # each Agent/VU runs in its own thread
    def __init__(self, id, interval, log_msgs, output_dir, runtime_stats, error_queue, msg_queue, results_queue):
        Thread.__init__(self)
        
        self.running = True
        self.id = id
        self.interval = interval
        self.log_msgs = log_msgs
        self.output_dir = output_dir
            
        self.runtime_stats = runtime_stats  # shared stats dictionary
        self.error_queue = error_queue  # shared error list
        
        # copy message/request queue and all its request objects so we have a unique copy for each agent.
        # this is really slow when there are a lot (1000+) test cases, so we disable it unless we really need to do this.
        # it is necessary for cookies and randomization to work correctly.
        if (SHUFFLE_TESTCASES or COOKIES_ENABLED):
            self.msg_queue = copy.deepcopy(msg_queue)  
        else:
            self.msg_queue = msg_queue
        
        if SHUFFLE_TESTCASES:  # randomize order of testcases per agent
            random.shuffle(self.msg_queue)
        
        self.results_queue = results_queue  # shared results queue
        
        self.count = 0
        self.error_count = 0
        
        # choose timer to use:
        if sys.platform.startswith('win'):
            self.default_timer = time.clock  # time.clock() is more precise on Windows systems
        else:
            self.default_timer = time.time  # time.time() is more precise on Linux/Unix and most other platforms 
            
        self.trace_logging = False
        if self.log_msgs:
            self.enable_trace_logging()
        
        
    def run(self):
        agent_start_time = time.strftime('%H:%M:%S', time.localtime())
        total_latency = 0
        total_connect_latency = 0
        total_bytes = 0
        
        while self.running:
            self.cookie_jar = cookielib.CookieJar()
            for req in self.msg_queue:
                for repeat in range(req.repeat):
                    if self.running:

                        # send the request message
                        resp, content, req_start_time, req_end_time, connect_end_time = self.send(req)

                        # get times for logging and error display
                        tmp_time = time.localtime()
                        cur_date = time.strftime('%d %b %Y', tmp_time)
                        cur_time = time.strftime('%H:%M:%S', tmp_time)
                        
                        # check verifications and status code for errors
                        is_error = False
                        if resp.code >= 400 or resp.code == 0:
                            is_error = True
                        if not req.verify == '':
                            if not re.search(req.verify, content, re.DOTALL): 
                                is_error = True
                        if not req.verify_negative == '':
                            if re.search(req.verify_negative, content, re.DOTALL):
                                is_error = True
                    
                        if is_error:                    
                            self.error_count += 1
                            error_string = 'Agent %s:  %s - %d %s,  url: %s' % (self.id + 1, cur_time, resp.code, resp.msg, req.url)
                            self.error_queue.append(error_string)
                            log_tuple = (self.id + 1, cur_date, cur_time, req_end_time, req.url.replace(',', ''), resp.code, resp.msg.replace(',', ''))
                            self.log_error('%s,%s,%s,%s,%s,%s,%s' % log_tuple)  # write as csv
                            
                        resp_bytes = len(content)
                        latency = (req_end_time - req_start_time)
                        connect_latency = (connect_end_time - req_start_time)
                        
                        self.count += 1
                        total_bytes += resp_bytes
                        total_latency += latency
                        total_connect_latency += connect_latency
                        
                        # update shared stats dictionary
                        self.runtime_stats[self.id] = StatCollection(resp.code, resp.msg, latency, self.count, self.error_count, total_latency, total_connect_latency, total_bytes)
                        self.runtime_stats[self.id].agent_start_time = agent_start_time
                        
                        # put response stats/info on queue for reading by the consumer (ResultWriter) thread
                        q_tuple = (self.id + 1, cur_date, cur_time, req_end_time, req.url.replace(',', ''), resp.code, resp.msg.replace(',', ''), resp_bytes, latency, connect_latency, req.timer_group)
                        self.results_queue.put(q_tuple)
                            
                        expire_time = (self.interval - latency)
                        if expire_time > 0:
                            time.sleep(expire_time)  # sleep remainder of interval so we keep even pacing
                    
                    else:  # don't go through entire range if stop has been called
                        break
        
        
    def stop(self):
        self.running = False
        if self.trace_logging:
            self.disable_trace_logging()
            
            
    def send(self, req):
        # req is our own Request object
        if HTTP_DEBUG:
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie_jar), urllib2.HTTPHandler(debuglevel=1))
        elif COOKIES_ENABLED:
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie_jar))
        else:
            opener = urllib2.build_opener()
        if req.method.upper() == 'POST':
            request = urllib2.Request(req.url, req.body, req.headers)
        else:  
            request = urllib2.Request(req.url, None, req.headers)  # urllib2 assumes a GET if no data is supplied.  PUT and DELETE are not supported
        
        # timed message send+receive (TTLB)
        req_start_time = self.default_timer()
        try:
            resp = opener.open(request)  # this sends the HTTP request and returns as soon as it is done connecting and sending
            connect_end_time = self.default_timer()
            content = resp.read()
            req_end_time = self.default_timer()
        except httplib.HTTPException, e:  # this can happen on an incomplete read, just catch all HTTPException
            connect_end_time = self.default_timer()
            resp = ErrorResponse()
            resp.code = 0
            resp.msg = str(e)
            resp.headers = {}
            content = ''
        except urllib2.HTTPError, e:  # http responses with status >= 400
            connect_end_time = self.default_timer()
            resp = ErrorResponse()
            resp.code = e.code
            resp.msg = httplib.responses[e.code]  # constant dict of http error codes/reasons
            resp.headers = dict(e.info())
            content = ''
        except urllib2.URLError, e:  # this also catches socket errors
            connect_end_time = self.default_timer()
            resp = ErrorResponse()
            resp.code = 0
            resp.msg = str(e.reason)
            resp.headers = {}  # headers are not available in the exception
            content = ''
        req_end_time = self.default_timer()
            
        if self.trace_logging:
            # log request/response messages
            self.log_http_msgs(req, request, resp, content)
            
        return (resp, content, req_start_time, req_end_time, connect_end_time)

    
    def log_error(self, txt):
        try:
            error_log = open('%s/agent_%d_errors.log' % (self.output_dir, self.id + 1), 'a')
            error_log.write('%s\n' % txt)
            error_log.flush()
            error_log.close()
        except IOError, e: 
            sys.stderr.write('ERROR: Can not write to error log file\n')
    
    
    def log_http_msgs(self, req, request, resp, content):
        self.log_trace('\n\n************************* REQUEST *************************\n\n')
        path = urlparse.urlparse(req.url).path
        if path == '':
            path = '/'
        self.log_trace('%s %s' % (req.method.upper(), path))
        for header_tuple in request.header_items():
            self.log_trace('%s: %s' % (header_tuple[0], header_tuple[1]))
        self.log_trace('\n\n************************* RESPONSE ************************\n\n')
        self.log_trace('%s %s' % (resp.code, resp.msg)) 
        for header in resp.headers:
            self.log_trace('%s: %s' % (header, resp.headers[header]))   
        self.log_trace('\n\n%s' % content)
     
     
    def log_trace(self, txt):
        self.trace_log.write('%s\n' % txt)
        self.trace_log.flush()
            
            
    def enable_trace_logging(self):
        self.trace_log = open('%s/agent_%d.log' % (self.output_dir, self.id + 1), 'w')
        self.trace_logging = True
        
        
    def disable_trace_logging(self):
        self.trace_log.flush()
        self.trace_log.close()
        self.trace_logging = False
        
            


class Request():
    def __init__(self, url='http://localhost/', method='GET', body='', headers=None, timer_group='default_timer', repeat=1):
        self.url = url
        self.method = method
        self.body = body
        self.timer_group = timer_group
        self.repeat = repeat
        
        if headers:
            self.headers = headers
        else:
            self.headers = {}
        
        # verification string or regex
        self.verify = ''
        self.verify_negative = ''
        
        # default unless overidden in testcase
        if 'user-agent' not in [header.lower() for header in self.headers]:
            self.add_header('User-Agent', 'Mozilla/4.0 (compatible; Pylot)')
        
        # default unless overidden in testcase
        # just for logging purposes because urllib2 will always add a "Connection: close" header anyway
        if 'connection' not in [header.lower() for header in self.headers]:
            self.add_header('Connection', 'close')             
        
        # default unless overidden in testcase
        # httplib adds this header unless we override it.  you can't read this header from a urrllib2 Request 
        # object so we just explicitly set the default again here so we can log it later
        if 'accept-encoding' not in [header.lower() for header in self.headers]:
            self.add_header('Accept-Encoding', 'identity') 
            
    def add_header(self, header_name, value):
        self.headers[header_name] = value




class ErrorResponse():
    # dummy respone that gets used when we encounter socket or http errors
    def __init__(self):
        self.code = 0
        self.msg = 'Connection error'
        self.headers = {}
        
        
        
        
class StatCollection():
    def __init__(self, status, reason, latency, count, error_count, total_latency, total_connect_latency, total_bytes):
        self.status = status
        self.reason = reason
        self.latency = latency
        self.count = count
        self.error_count = error_count
        self.total_latency = total_latency
        self.total_connect_latency = total_connect_latency
        self.total_bytes = total_bytes

        self.agent_start_time = None
        
        if count > 0:
            self.avg_latency = (total_latency / count)
            self.avg_connect_latency = (total_connect_latency / count)
        else:
            self.avg_latency = 0
            self.avg_connect_latency = 0
            


        
class ResultWriter(Thread):
    # this thread is for reading queued results and writing them to a log file.
    def __init__(self, results_queue, output_dir):
        Thread.__init__(self)
        self.running = True
        self.results_queue = results_queue
        self.output_dir = output_dir        

    def run(self):
        # make sure a results file always exists, even if no agents finished
        fh = open('%s/agent_stats.csv' % self.output_dir, 'w')
        fh.close()

        # The file handle should really be opened once, but this is crashing the
        # Python interpreter when you quit the console with ctrl-c.  
        # This is a bug in Python: http://bugs.python.org/issue5160
        # The workaround is to open/close the handle for each write operation.
        # File handles are cheap, so don't worry
        while self.running:
            try:
                q_tuple = self.results_queue.get(False)
                f = open('%s/agent_stats.csv' % self.output_dir, 'a')
                f.write('%s,%s,%s,%s,%s,%d,%s,%d,%f,%f,%s\n' % q_tuple)  # log as csv
                f.flush()
                f.close()
            except Queue.Empty:
                # re-check queue for messages every x sec
                time.sleep(.10)
                
    def stop(self):
        self.running = False


