#
#    Copyright (c) 2009 Vasil Vangelovski (vvangelovski@gmail.com)
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


import sys

is_25 = sys.version.startswith('2.5')
is_26 = sys.version.startswith('2.6')

if is_25:
    import _consolepos25 as _consolepos
elif is_26:
    import _consolepos26 as _consolepos

getpos = _consolepos.getpos
gotoxy = _consolepos.gotoxy
