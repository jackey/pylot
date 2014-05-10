#   This file is part of Pylot.
#    
#   optionparse is a wrapper around optparse
#   taken from ASPN Python Coockbook
#   http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/278844


import optparse
import re
import sys


USAGE = re.compile(r'(?s)\s*usage: (.*?)(\n[ \t]*\n|$)')

def nonzero(self): # will become the nonzero method of optparse.Values  
    # True if options were given
    for v in self.__dict__.itervalues():
        if v is not None:
            return True
    return False

optparse.Values.__nonzero__ = nonzero # dynamically fix optparse.Values

class ParsingError(Exception): 
    pass

optionstring = ''

def exit(msg=''):
    raise SystemExit(msg or optionstring.replace('%prog', sys.argv[0]))

def parse(docstring, arglist=None):
    global optionstring
    optionstring = docstring
    match = USAGE.search(optionstring)
    if not match: raise ParsingError('ERROR: Can not find the option string')
    optlines = match.group(1).splitlines()
    try:
        p = optparse.OptionParser(optlines[0])
        for line in optlines[1:]:
            opt, help=line.split(':')[:2]
            short,long=opt.split(',')[:2]
            if '=' in opt:
                action = 'store'
                long = long.split('=')[0]
            else:
                action = 'store_true'
            p.add_option(short.strip(), long.strip(),
                action = action, help = help.strip())
    except (IndexError, ValueError):
        raise ParsingError('ERROR: Can not parse the option string correctly')
    return p.parse_args(arglist)