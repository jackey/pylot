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


import sys


class Stats:
        
    def __init__(self, sequence):
        # sequence of numbers
        # convert all items to floats for numerical processing        
        self.sequence = [float(item) for item in sequence]
    
    
    def sum(self):
        if len(self.sequence) < 1: 
            return None
        else:
            return sum(self.sequence)
    
    
    def count(self):
        return len(self.sequence)

    
    def min(self):
        if len(self.sequence) < 1: 
            return None
        else:
            return min(self.sequence)
    
    
    def max(self):
        if len(self.sequence) < 1: 
            return None
        else:
            return max(self.sequence)
    

    def avg(self):
        if len(self.sequence) < 1: 
            return None
        else: 
            return sum(self.sequence) / len(self.sequence)    
    
    
    def median(self):
        if len(self.sequence) < 1: 
            return None
        else:
            seq.sort()
            return self.sequence[len(self.sequence) // 2]
            
    
    def stdev(self):
        if len(self.sequence) < 1: 
            return None
        if len(self.sequence) == 1: 
            return 0
        else:
            avg = self.avg()
            sdsq = sum([(i - avg) ** 2 for i in self.sequence])
            stdev = (sdsq / (len(self.sequence) - 1)) ** .5
            return stdev
    
    
    def percentile(self, percentile):
        if len(self.sequence) < 1: 
            value = None
        elif (percentile >= 100):
            print 'ERROR: percentile must be < 100.  you supplied: %s\n' % percentile
            value = None
        else:
            element_idx = int(len(self.sequence) * (percentile / 100.0))
            self.sequence.sort()
            value = self.sequence[element_idx]
        return value
