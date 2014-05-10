#!/usr/bin/env python

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


"""
  usage: %prog [options] args
  -a, --agents=NUM_AGENTS     :  number of agents
  -d, --duration=DURATION     :  test duration in seconds
  -r, --rampup=RAMPUP         :  rampup in seconds
  -i, --interval=INTERVAL     :  interval in milliseconds
  -x, --xmlfile=TEST_CASE_XML :  test case xml file
  -o, --output_dir=PATH       :  output directory
  -n, --name=TESTNAME	      :  name of test
  -l, --log_msgs              :  log messages
  -b, --blocking              :  blocking mode
  -g, --gui                   :  start GUI
  -p, --port=PORT             :  xml-rpc listening port  
"""


import sys
import core.config as config
import core.optionparse as optionparse


VERSION = '1.26'


# get default config parameters
agents = config.AGENTS
duration = config.DURATION
rampup = config.RAMPUP
interval = config.INTERVAL
tc_xml_filename = config.TC_XML_FILENAME
output_dir = config.OUTPUT_DIR
test_name = config.TEST_NAME
log_msgs = config.LOG_MSGS
blocking = config.BLOCKING
gui = config.GUI


# parse command line arguments
opt, args = optionparse.parse(__doc__)


if not opt and not args:
    print 'version: %s' % VERSION
    optionparse.exit()
try:
    if opt.agents:
        agents = int(opt.agents)
    if opt.duration:
        duration = int(opt.duration)
    if opt.rampup:
        rampup = int(opt.rampup)
    if opt.interval:
        interval = int(opt.interval)
    if opt.xmlfile:
        tc_xml_filename = opt.xmlfile
    if opt.log_msgs: 
        log_msgs = True
    if opt.output_dir:
        output_dir = opt.output_dir
    if opt.name:
        test_name = opt.name
    if opt.blocking:
        blocking = True
    if opt.gui:
        gui = True
    if opt.port:
        port = int(opt.port)
except Exception, e:
   print 'Invalid Argument'
   sys.exit(1)


if gui:  # gui mode
    import ui.gui as pylot_gui
    pylot_gui.main(agents, rampup, interval, duration, tc_xml_filename, log_msgs, VERSION, output_dir, test_name)


elif opt.port:  # xml-rpc listener mode   
    import SimpleXMLRPCServer
    import ui.blocking as pylot_blocking
    class RemoteStarter:
        def start(self):
            return pylot_blocking.main(agents, rampup, interval, duration, tc_xml_filename, log_msgs, output_dir, test_name)
    rs = RemoteStarter()
    server = SimpleXMLRPCServer.SimpleXMLRPCServer(('localhost', port))
    server.register_instance(rs)
    print 'Pylot - listening on port', port
    print 'waiting for xml-rpc start command...\n'
    server.serve_forever()


elif blocking:  # blocked output mode (stdout blocked until test finishes, then result is returned)
    import ui.blocking as pylot_blocking
    try:    
        pylot_blocking.main(agents, rampup, interval, duration, tc_xml_filename, log_msgs, output_dir, test_name)
    except KeyboardInterrupt:
        print '\nInterrupt'
        sys.exit(1)
        
        
else:  # console/shell mode
    import ui.console as pylot_console
    print '\n-------------------------------------------------'
    print 'Test parameters:'
    print '  number of agents:          %s' % agents
    print '  test duration in seconds:  %s' % duration
    print '  rampup in seconds:         %s' % rampup
    print '  interval in milliseconds:  %s' % interval
    print '  test case xml:             %s' % tc_xml_filename
    print '  log messages:              %s' % log_msgs
    if test_name:
        print '  test name:                 %s' % test_name
    if output_dir:
        print '  output directory:           %s' % output_dir
    print '\n'
    try:    
        pylot_console.main(agents, rampup, interval, duration, tc_xml_filename, log_msgs, output_dir, test_name)
    except KeyboardInterrupt:
        print '\nInterrupt'
        sys.exit(1)
    
    