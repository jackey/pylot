#!/usr/bin/env python
#
#    Copyright (c) 2007-2009 Corey Goldberg (corey@goldb.org)
#    License: GNU GPLv3
#    
#
#    This file is part of Pylot.
#    
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.  See the GNU General Public License 
#    for more details.
#
#
#    Original code by David Solomon (dave.c.solomon@gmail.com)
#
#
#  Only works on Windows.
#  Browser capture tool.  Builds Pylot test cases from an IE browsing session.
#  You must have the Win32 Extensions for Python installed
#  http://sourceforge.net/projects/pywin32/



import sys
import threading
import pythoncom
from win32com.client import Dispatch, WithEvents



stop_event = threading.Event()
finished = False

class EventSink(object):        
    def OnBeforeNavigate2(self, *args):
        print '  <case>'
        url = args[1]
        post_data = args[4]
        headers = args[5]
        print '    <url>%s</url>' % url
        if post_data:
            print '    <method>POST</method>'
            print '    <body><![CDATA[%s]]></body>' % post_data
            if headers:
                print '    <add_header>%s</add_header>' % headers
        print "  </case>"
        stop_event.set()
    
    def OnQuit(self):
        global finished
        finished = True
        ie.Visible = 0
        stop_event.set()


ie = Dispatch('InternetExplorer.Application', EventSink)
ev = WithEvents(ie, EventSink)

ie.Visible = 1

print '<testcases>'
while not finished:
    pythoncom.PumpWaitingMessages()
    stop_event.wait(.05)
    stop_event.clear()
print '</testcases>'