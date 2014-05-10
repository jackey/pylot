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


from string import Template
try:
    import xml.etree.ElementTree as etree
except ImportError:
    sys.stderr.write('ERROR: Pylot was unable to find the XML parser.  Make sure you have Python 2.5+ installed.\n')
    sys.exit(1)
from engine import Request



def load_xml_string_cases(tc_xml_blob):
    # parse xml and load request queue with core.engine.Request objects
    # variant to parse from a raw string instead of a filename
    dom = etree.ElementTree(etree.fromstring(tc_xml_blob))
    cases = load_xml_cases_dom(dom)
    return cases


def load_xml_cases(tc_xml_filename):
    # parse xml and load request queue with corey.engine.Request objects
    # variant to load the xml from a file (the default shell behavior)
    dom = etree.parse(tc_xml_filename)
    cases = load_xml_cases_dom(dom)
    return cases


def load_xml_cases_dom(dom):
    # load cases from an already-parsed XML DOM
    cases = []
    param_map = {}
    for child in dom.getiterator():
        if child.tag != dom.getroot().tag and child.tag == 'param':
            name = child.attrib.get('name')
            value = child.attrib.get('value')
            param_map[name] = value
        if child.tag != dom.getroot().tag and child.tag == 'case':
            req = Request()
            repeat = child.attrib.get('repeat')
            if repeat:
                req.repeat = int(repeat)
            else:
                req.repeat = 1
            for element in child:
                if element.tag.lower() == 'url':
                    req.url = element.text
                if element.tag.lower() == 'method': 
                    req.method = element.text
                if element.tag.lower() == 'body':
                    file_payload = element.attrib.get('file')
                    if file_payload:
                        req.body = open(file_payload, 'rb').read()
                    else:
                        req.body = element.text
                if element.tag.lower() == 'verify': 
                    req.verify = element.text
                if element.tag.lower() == 'verify_negative': 
                    req.verify_negative = element.text
                if element.tag.lower() == 'timer_group': 
                    req.timer_group = element.text
                if element.tag.lower() == 'add_header':
                    # this protects against headers that contain colons
                    splat = element.text.split(':')
                    x = splat[0].strip()
                    del splat[0]
                    req.add_header(x, ''.join(splat).strip())
            req = resolve_parameters(req, param_map)  # substitute vars
            cases.append(req)
    return cases


def resolve_parameters(req, param_map):
    # substitute variables based on parameter mapping
    req.url = Template(req.url).substitute(param_map)
    req.body = Template(req.body).substitute(param_map)
    for header in req.headers:
        req.headers[header] = Template(req.headers[header]).substitute(param_map)
    return req
