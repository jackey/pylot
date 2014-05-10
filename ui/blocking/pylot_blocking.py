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

#  This function starts the engine in blocked output mode.  
#  stdout is blocked until test finishes, then results are returned as XML


import os
import sys
import time
import core.xmlparse as xmlparse
import core.config as config
from core.engine import LoadManager



original_stdout = sys.stdout  # keep a reference to stdout



def main(num_agents, rampup, interval, duration, tc_xml_filename, log_msgs, output_dir=None, test_name=None):
    if not config.HTTP_DEBUG:
        # turn off stdout and stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
    
    runtime_stats = {}
    error_queue = []
    
    interval = interval / 1000.0  # convert from millisecs to secs
   
    if test_name:
        if output_dir:
            output_dir = output_dir + '/' + test_name

    # create a load manager
    lm = LoadManager(num_agents, interval, rampup, log_msgs, runtime_stats, error_queue, output_dir, test_name,)
    
    # load the test cases
    try:
        cases = xmlparse.load_xml_cases(tc_xml_filename)
        for req in cases:
            lm.add_req(req)
    except Exception, e:
        print 'ERROR: can not parse testcase file: %s' % e
        sys.exit(1)
    
    start_time = time.time()
    
    # start the load manager
    lm.setDaemon(True)
    lm.start()
    
    # wait for the test duration to lapse
    time.sleep(duration)
        
    elapsed_secs = time.time() - start_time

    lm.stop()
    
    # wait until the result generator is finished
    while lm.results_gen.isAlive():
        time.sleep(.10)
    
    ids = runtime_stats.keys()
    agg_count = sum([runtime_stats[id].count for id in ids])  # total req count
    agg_total_latency = sum([runtime_stats[id].total_latency for id in ids])
    agg_error_count = sum([runtime_stats[id].error_count for id in ids])
    total_bytes_received = sum([runtime_stats[id].total_bytes for id in ids])
    avg_resp_time = agg_total_latency / agg_count  # avg response time since start
    avg_throughput = float(agg_count) / elapsed_secs  # avg throughput since start
    
    response_xml = """\
<results>
  <summary-results>
    <requests>%d</requests>
    <errors>%d</errors>
    <avg-response-time>%.3f</avg-response-time>
    <avg-throughput>%.2f</avg-throughput>
    <bytes-received>%i</bytes-received>
  </summary-results>  """ % (agg_count, agg_error_count, avg_resp_time, avg_throughput, total_bytes_received)
    for id in runtime_stats:
        response_xml += """  
  <agent-results>
    <agent-num>%d</agent-num>
    <requests>%d</requests>
    <errors>%d</errors>
    <avg-response-time>%.3f<avg-response-time>
    <bytes-received>%i</bytes-received>
  </agent-results> """ % (id + 1, runtime_stats[id].count, runtime_stats[id].error_count, 
                        runtime_stats[id].avg_latency, runtime_stats[id].total_bytes)
    response_xml += """
</results>"""
    
    sys.stdout = original_stdout  # temporarily turn on stdout
    
    print response_xml
    
    sys.stdout = open(os.devnull, 'w')  # turn off stdout again
    
    return response_xml
